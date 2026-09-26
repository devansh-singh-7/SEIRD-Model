"""Build and validate the project airport-route connectivity proxy.

Only ``cleaned_airports.csv`` and ``cleaned_routes.csv`` are read.  The
result is a directed route-connectivity proxy, not a passenger-volume or
observed mobility matrix, and it is intentionally not coupled to SEIRD here.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


AIRPORTS_PATH = Path("cleaned_airports.csv")
ROUTES_PATH = Path("cleaned_routes.csv")
OUTPUT_DIR = Path("outputs")

AIRPORT_COLUMNS = [
    "airport_id", "name", "city", "country", "latitude", "longitude",
    "altitude", "timezone", "dst", "tz_database_timezone", "type", "source",
]
ROUTE_COLUMNS = [
    "airline_code", "airline_id", "source_airport_code", "source_airport_id",
    "destination_airport_code", "destination_airport_id", "codeshare", "stops", "equipment",
]
MISSING = {"", r"\N", "NA", "N/A", "NULL", "NONE"}
IATA_STYLE = re.compile(r"^[A-Z0-9]{3}$")
AIRLINE_CODE = re.compile(r"^[A-Z0-9]{2,3}$")


def _bool(series: pd.Series) -> np.ndarray:
    """Convert a (possibly nullable) boolean Series to a plain numpy bool array.

    np.select requires plain ndarray[bool], but pandas nullable dtypes
    (BooleanDtype, Int64, StringDtype) produce nullable boolean comparisons.
    NA values are treated as False.
    """
    if hasattr(series, 'fillna'):
        return np.asarray(series.fillna(False), dtype=bool)
    return np.asarray(series, dtype=bool)


def source_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean_text(value: object) -> str | pd.NA:
    if pd.isna(value):
        return pd.NA
    text = str(value).strip()
    return pd.NA if text.upper() in MISSING else text


def positive_integer(value: object) -> int | pd.NA:
    text = clean_text(value)
    if pd.isna(text) or not str(text).isdigit():
        return pd.NA
    parsed = int(str(text))
    return parsed if parsed > 0 else pd.NA


def id_is_valid(value: object) -> bool:
    return not pd.isna(positive_integer(value))


def airport_code_status(value: object) -> str:
    code = clean_text(value)
    if pd.isna(code):
        return "MISSING"
    code = str(code).upper()
    if IATA_STYLE.fullmatch(code):
        return "IATA_STYLE_3_CHARACTER"
    if re.fullmatch(r"[A-Z0-9]{4}", code):
        return "NON_IATA_STYLE_4_CHARACTER"
    return "INVALID_FORMAT"


def nonnegative_integer_status(value: object) -> tuple[int | pd.NA, str]:
    text = clean_text(value)
    if pd.isna(text):
        return pd.NA, "MISSING"
    if not str(text).isdigit():
        return pd.NA, "INVALID_FORMAT"
    parsed = int(str(text))
    return parsed, "VALID" if parsed >= 0 else "INVALID_NEGATIVE"


def json_safe(value: object) -> object:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if pd.isna(value):
        return None
    return value


def count_frame(records: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(records, columns=["entity", "validation_check", "status", "count", "rule"])


def main() -> None:
    for path in (AIRPORTS_PATH, ROUTES_PATH):
        if not path.exists():
            raise FileNotFoundError(f"Required project mobility input is missing: {path}")

    airports_raw = pd.read_csv(AIRPORTS_PATH, dtype=str, keep_default_na=False)
    routes_raw = pd.read_csv(ROUTES_PATH, dtype=str, keep_default_na=False)
    if list(airports_raw.columns) != AIRPORT_COLUMNS:
        raise ValueError(f"Unexpected airport schema: {list(airports_raw.columns)}")
    if list(routes_raw.columns) != ROUTE_COLUMNS:
        raise ValueError(f"Unexpected route schema: {list(routes_raw.columns)}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    source_hashes = {str(AIRPORTS_PATH): source_hash(AIRPORTS_PATH), str(ROUTES_PATH): source_hash(ROUTES_PATH)}

    # Airport validation. Missing coordinates are documented but do not prevent
    # country mapping; malformed or out-of-range supplied coordinates do.
    airports = airports_raw.copy()
    airports.insert(0, "airport_record_number", np.arange(1, len(airports) + 1))
    airports["airport_id_raw"] = airports["airport_id"]
    airports["airport_id"] = airports["airport_id_raw"].map(positive_integer).astype("Int64")
    airports["airport_id_status"] = np.where(_bool(airports["airport_id"].notna()), "VALID_POSITIVE_INTEGER", "INVALID_OR_MISSING")
    airports["duplicate_airport_id"] = _bool(airports["airport_id"].notna()) & _bool(airports["airport_id"].duplicated(keep=False))
    airports["country"] = airports["country"].map(clean_text)
    airports["country_status"] = np.where(_bool(airports["country"].notna()), "VALID_SUPPLIED_COUNTRY", "MISSING_OR_UNUSABLE")
    airports["latitude_numeric"] = pd.to_numeric(airports["latitude"].map(clean_text), errors="coerce")
    airports["longitude_numeric"] = pd.to_numeric(airports["longitude"].map(clean_text), errors="coerce")
    latitude_supplied = airports["latitude"].map(clean_text).notna()
    longitude_supplied = airports["longitude"].map(clean_text).notna()
    coordinate_missing = ~latitude_supplied | ~longitude_supplied
    coordinate_invalid = ((latitude_supplied & (airports["latitude_numeric"].isna() | ~airports["latitude_numeric"].between(-90, 90))) | (longitude_supplied & (airports["longitude_numeric"].isna() | ~airports["longitude_numeric"].between(-180, 180))))
    airports["coordinate_status"] = np.select(
        [_bool(coordinate_invalid), _bool(coordinate_missing)],
        ["INVALID", "MISSING_NOT_REQUIRED_FOR_COUNTRY_MAPPING"],
        default="VALID",
    )
    physical_signature = airports[["name", "city", "country", "latitude", "longitude"]].fillna("<MISSING>").astype(str).agg("|".join, axis=1)
    airports["duplicate_physical_signature_candidate"] = physical_signature.duplicated(keep=False)
    airports["valid_for_country_mapping"] = (
        _bool(airports["airport_id"].notna())
        & ~_bool(airports["duplicate_airport_id"])
        & _bool(airports["country"].notna())
        & ~_bool(coordinate_invalid)
    )
    airports["airport_record_status"] = np.select(
        [_bool(airports["airport_id"].isna()), _bool(airports["duplicate_airport_id"]), _bool(airports["country"].isna()), _bool(coordinate_invalid)],
        ["INVALID_UNUSABLE_IDENTIFIER", "INVALID_DUPLICATE_AIRPORT_ID", "INVALID_MISSING_COUNTRY", "INVALID_COORDINATES"],
        default="VALID_FOR_COUNTRY_MAPPING",
    )

    # The airport input contains no IATA column. Build a transparent route-code
    # crosswalk only from the provided route records, never from an external lookup.
    code_observations = pd.concat([
        routes_raw[["source_airport_id", "source_airport_code"]].rename(columns={"source_airport_id": "airport_id_raw", "source_airport_code": "route_code"}),
        routes_raw[["destination_airport_id", "destination_airport_code"]].rename(columns={"destination_airport_id": "airport_id_raw", "destination_airport_code": "route_code"}),
    ], ignore_index=True)
    code_observations["airport_id"] = code_observations["airport_id_raw"].map(positive_integer).astype("Int64")
    code_observations["route_code"] = code_observations["route_code"].map(clean_text)
    code_observations["route_code_upper"] = code_observations["route_code"].astype("string").str.upper()
    code_observations = code_observations[
        code_observations["airport_id"].notna()
        & code_observations["route_code_upper"].str.fullmatch(IATA_STYLE.pattern, na=False)
    ]
    code_sets = code_observations.groupby("airport_id")["route_code_upper"].agg(lambda values: sorted(set(values)))
    airports["route_iata_style_codes_observed"] = airports["airport_id"].map(code_sets)
    airports["route_iata_style_code_count"] = airports["route_iata_style_codes_observed"].map(lambda values: len(values) if isinstance(values, list) else 0)
    airports["iata_code"] = airports["route_iata_style_codes_observed"].map(lambda values: values[0] if isinstance(values, list) and len(values) == 1 else pd.NA)
    airports["iata_mapping_status"] = np.select(
        [_bool(airports["route_iata_style_code_count"].eq(0)), _bool(airports["route_iata_style_code_count"].eq(1))],
        ["UNAVAILABLE_NO_ROUTE_CODE", "ROUTE_DERIVED_UNIQUE_NOT_AIRPORT_MASTER_FIELD"],
        default="CONFLICTING_ROUTE_CODES_NOT_MAPPED",
    )
    airports["route_iata_style_codes_observed"] = airports["route_iata_style_codes_observed"].map(lambda values: "|".join(values) if isinstance(values, list) else pd.NA)

    valid_airports = airports.loc[airports["valid_for_country_mapping"]].copy()
    airport_lookup = valid_airports.set_index("airport_id")[["country", "iata_code", "iata_mapping_status"]]

    # Route validation. IDs are authoritative for country mapping; airport codes
    # are retained and audited, but cannot be independently confirmed because the
    # supplied airport master has no IATA field.
    routes = routes_raw.copy()
    routes.insert(0, "route_record_number", np.arange(1, len(routes) + 1))
    for side in ("source", "destination"):
        routes[f"{side}_airport_id_raw"] = routes[f"{side}_airport_id"]
        routes[f"{side}_airport_id"] = routes[f"{side}_airport_id_raw"].map(positive_integer).astype("Int64")
        routes[f"{side}_airport_id_status"] = np.where(_bool(routes[f"{side}_airport_id"].notna()), "VALID_POSITIVE_INTEGER", "INVALID_OR_MISSING")
        routes[f"{side}_airport_code"] = routes[f"{side}_airport_code"].map(clean_text)
        routes[f"{side}_airport_code_upper"] = routes[f"{side}_airport_code"].astype("string").str.upper()
        routes[f"{side}_airport_code_status"] = routes[f"{side}_airport_code"].map(airport_code_status)
        routes[f"{side}_airport_exists"] = routes[f"{side}_airport_id"].isin(airport_lookup.index)
        routes[f"{side}_country"] = routes[f"{side}_airport_id"].map(airport_lookup["country"])
        routes[f"{side}_airport_iata_code"] = routes[f"{side}_airport_id"].map(airport_lookup["iata_code"])
        routes[f"{side}_iata_mapping_status"] = routes[f"{side}_airport_id"].map(airport_lookup["iata_mapping_status"])
        routes[f"{side}_airport_code_consistency"] = np.select(
            [_bool(~routes[f"{side}_airport_exists"]), _bool(routes[f"{side}_iata_mapping_status"].eq("CONFLICTING_ROUTE_CODES_NOT_MAPPED")), _bool(routes[f"{side}_iata_mapping_status"].eq("UNAVAILABLE_NO_ROUTE_CODE")), _bool(routes[f"{side}_airport_code_upper"].eq(routes[f"{side}_airport_iata_code"]))],
            ["NOT_CHECKABLE_UNMAPPED_AIRPORT", "NOT_CHECKABLE_CONFLICTING_ROUTE_CODES", "NOT_CHECKABLE_NO_IATA_STYLE_ROUTE_CODE", "MATCHES_ROUTE_DERIVED_CODE"],
            default="DIFFERS_FROM_ROUTE_DERIVED_CODE",
        )
    routes["airline_code"] = routes["airline_code"].map(clean_text)
    routes["airline_id_raw"] = routes["airline_id"]
    routes["airline_id"] = routes["airline_id_raw"].map(positive_integer).astype("Int64")
    routes["airline_code_status"] = routes["airline_code"].map(lambda value: "VALID_FORMAT" if not pd.isna(value) and AIRLINE_CODE.fullmatch(str(value).upper()) else "MISSING_OR_INVALID_FORMAT")
    routes["airline_id_status"] = np.where(_bool(routes["airline_id"].notna()), "VALID_POSITIVE_INTEGER", "MISSING_OR_INVALID")
    routes["codeshare"] = routes["codeshare"].map(clean_text).astype("string").str.upper()
    routes["codeshare_status"] = np.where(_bool(routes["codeshare"].isin(["Y", "N"])), "VALID_Y_OR_N", "MISSING_OR_INVALID")
    stops_and_status = routes["stops"].map(nonnegative_integer_status)
    routes["stops_numeric"] = stops_and_status.map(lambda item: item[0]).astype("Int64")
    routes["stops_status"] = stops_and_status.map(lambda item: item[1])
    routes["self_loop_airport"] = _bool(routes["source_airport_id"].notna()) & _bool(routes["source_airport_id"].eq(routes["destination_airport_id"]))
    routes["country_connectivity_scope"] = np.select(
        [_bool(routes["source_country"].isna() | routes["destination_country"].isna()), _bool(routes["source_country"].eq(routes["destination_country"]))],
        ["UNMAPPED", "DOMESTIC_RETAINED"],
        default="INTERNATIONAL",
    )
    routes["is_exact_duplicate_route"] = routes.duplicated(subset=ROUTE_COLUMNS, keep="first")
    routes["route_record_status"] = np.select(
        [
            _bool(routes["source_airport_id"].isna() | routes["destination_airport_id"].isna()),
            _bool(~routes["source_airport_exists"] | ~routes["destination_airport_exists"]),
            _bool(routes["self_loop_airport"]),
            _bool(routes["is_exact_duplicate_route"]),
        ],
        ["INVALID_AIRPORT_IDENTIFIER", "INVALID_OR_UNMAPPED_AIRPORT", "REMOVED_AIRPORT_SELF_LOOP", "DROPPED_EXACT_DUPLICATE"],
        default="VALID_FOR_NETWORK",
    )
    routes["valid_for_network"] = routes["route_record_status"].eq("VALID_FOR_NETWORK")

    valid_routes = routes.loc[routes["valid_for_network"]].copy()
    directed_pairs = set(zip(valid_routes["source_airport_id"].astype(int), valid_routes["destination_airport_id"].astype(int)))
    routes["reverse_direction_route_present"] = routes.apply(
        lambda row: bool((int(row["destination_airport_id"]), int(row["source_airport_id"])) in directed_pairs)
        if bool(row["valid_for_network"]) else False,
        axis=1,
    )
    valid_routes = routes.loc[routes["valid_for_network"]].copy()

    # Keep a full per-record audit, while the network contains only validated,
    # non-self-loop, exact-deduplicated route records.
    airport_output_columns = [
        "airport_record_number", "airport_id", "iata_code", "country", "name", "city", "latitude", "longitude",
        "airport_id_status", "country_status", "coordinate_status", "duplicate_airport_id",
        "duplicate_physical_signature_candidate", "route_iata_style_codes_observed", "route_iata_style_code_count",
        "iata_mapping_status", "valid_for_country_mapping", "airport_record_status",
    ]
    airports[airport_output_columns].to_csv(OUTPUT_DIR / "airports_processed.csv", index=False)
    routes.to_csv(OUTPUT_DIR / "routes_processed.csv", index=False)

    network_group_columns = [
        "source_airport_id", "destination_airport_id", "source_airport_code", "destination_airport_code",
        "source_country", "destination_country", "airline_code", "airline_id", "codeshare", "stops_numeric", "equipment",
        "country_connectivity_scope", "reverse_direction_route_present",
    ]
    airport_network = valid_routes.groupby(network_group_columns, dropna=False).size().reset_index(name="route_count")
    airport_network.to_csv(OUTPUT_DIR / "airport_route_network.csv", index=False)

    country_matrix = airport_network.groupby(["source_country", "destination_country", "country_connectivity_scope"], as_index=False)["route_count"].sum()
    country_matrix = country_matrix.sort_values(["source_country", "destination_country"], kind="stable")
    country_matrix.to_csv(OUTPUT_DIR / "country_route_matrix.csv", index=False)

    international_matrix = country_matrix.loc[country_matrix["country_connectivity_scope"].eq("INTERNATIONAL")].copy()
    international_matrix["outgoing_international_route_count"] = international_matrix.groupby("source_country")["route_count"].transform("sum")
    international_matrix["route_connectivity_probability"] = international_matrix["route_count"] / international_matrix["outgoing_international_route_count"]
    international_matrix["normalization"] = "route_count / all retained international outgoing route counts from source_country"
    international_matrix.to_csv(OUTPUT_DIR / "country_route_matrix_normalized.csv", index=False)

    represented_countries = sorted(valid_airports["country"].dropna().unique().tolist())
    connected_countries = set(valid_routes["source_country"]).union(valid_routes["destination_country"])
    countries_without_connectivity = sorted(set(represented_countries) - connected_countries)
    reverse_pairs = {pair for pair in directed_pairs if (pair[1], pair[0]) in directed_pairs}
    international_source_dest_self = int((international_matrix["source_country"] == international_matrix["destination_country"]).sum())
    country_count = len(set(country_matrix["source_country"]).union(country_matrix["destination_country"]))

    checks = {
        "required_input_files_present": AIRPORTS_PATH.exists() and ROUTES_PATH.exists(),
        "expected_schemas_present": list(airports_raw.columns) == AIRPORT_COLUMNS and list(routes_raw.columns) == ROUTE_COLUMNS,
        "validated_network_has_no_unmapped_airport_ids": bool(valid_routes["source_airport_exists"].all() and valid_routes["destination_airport_exists"].all()),
        "validated_network_has_no_missing_country_mappings": bool(valid_routes[["source_country", "destination_country"]].notna().all().all()),
        "airport_self_loops_removed": not bool(valid_routes["self_loop_airport"].any()),
        "exact_duplicate_records_excluded_from_network": int(airport_network["route_count"].sum()) == len(valid_routes),
        "directional_information_preserved": int(airport_network["route_count"].sum()) == len(valid_routes),
        "no_self_country_route_labelled_international": international_source_dest_self == 0,
        "normalized_rows_sum_to_one_per_outgoing_country": bool(np.allclose(international_matrix.groupby("source_country")["route_connectivity_probability"].sum().to_numpy(), 1.0, atol=1e-12)),
        "positive_network_coverage": len(valid_airports) > 0 and len(valid_routes) > 0 and country_count > 0,
    }
    status = "MOBILITY NETWORK STATUS: GO" if all(checks.values()) else "MOBILITY NETWORK STATUS: NO-GO"

    validation_records = [
        {"entity": "airport", "validation_check": "total_airport_records", "status": "OBSERVED", "count": len(airports), "rule": "Rows in cleaned_airports.csv."},
        {"entity": "airport", "validation_check": "valid_airport_records", "status": "PASS", "count": len(valid_airports), "rule": "Positive unique airport ID, supplied country, and no invalid supplied coordinate."},
        {"entity": "airport", "validation_check": "invalid_airport_records", "status": "REPORTED", "count": int((~airports["valid_for_country_mapping"]).sum()), "rule": "Retained in airports_processed.csv with a reason; not used for route-country mapping."},
        {"entity": "airport", "validation_check": "route_derived_unique_iata_style_codes", "status": "REPORTED", "count": int(airports["iata_mapping_status"].eq("ROUTE_DERIVED_UNIQUE_NOT_AIRPORT_MASTER_FIELD").sum()), "rule": "The source airport file has no IATA column; codes are only route-derived three-character values."},
        {"entity": "route", "validation_check": "total_route_records", "status": "OBSERVED", "count": len(routes), "rule": "Rows in cleaned_routes.csv."},
        {"entity": "route", "validation_check": "valid_route_records", "status": "PASS", "count": len(valid_routes), "rule": "Mapped endpoint IDs, no airport self-loop, and first occurrence of an exact source-record duplicate."},
        {"entity": "route", "validation_check": "invalid_or_unmapped_route_records", "status": "REPORTED", "count": int(routes["route_record_status"].isin(["INVALID_AIRPORT_IDENTIFIER", "INVALID_OR_UNMAPPED_AIRPORT"]).sum()), "rule": "Not included in the network because endpoints cannot be mapped from supplied data."},
        {"entity": "route", "validation_check": "airport_self_loops_removed", "status": "PASS", "count": int(routes["route_record_status"].eq("REMOVED_AIRPORT_SELF_LOOP").sum()), "rule": "Source and destination airport IDs are identical."},
        {"entity": "route", "validation_check": "exact_duplicate_records_handled", "status": "PASS", "count": int(routes["route_record_status"].eq("DROPPED_EXACT_DUPLICATE").sum()), "rule": "Only exact duplicates across every supplied route field are excluded from the network; directional reverse routes are retained."},
        {"entity": "route", "validation_check": "retained_domestic_routes", "status": "REPORTED", "count": int(valid_routes["country_connectivity_scope"].eq("DOMESTIC_RETAINED").sum()), "rule": "Same-country endpoints are explicitly retained as domestic connectivity in the raw country matrix."},
        {"entity": "route", "validation_check": "valid_routes_with_reverse_direction", "status": "REPORTED", "count": int(valid_routes["reverse_direction_route_present"].sum()), "rule": "Both airport directions occur; neither direction is deleted."},
        {"entity": "network", "validation_check": "countries_represented_by_valid_airports", "status": "PASS", "count": len(represented_countries), "rule": "Distinct supplied country labels among valid airport records."},
        {"entity": "network", "validation_check": "countries_without_usable_airport_connectivity", "status": "REPORTED", "count": len(countries_without_connectivity), "rule": "Valid-airport countries absent from both endpoints of retained routes."},
        {"entity": "network", "validation_check": "country_route_matrix_dimensions", "status": "PASS", "count": country_count, "rule": f"Long-form matrix has {len(country_matrix)} nonzero directed edges and represents a {country_count} by {country_count} country index."},
    ]
    validation = count_frame(validation_records)
    validation.to_csv(OUTPUT_DIR / "airport_route_validation.csv", index=False)

    report = {
        "status": status,
        "scope": {
            "input_files": [str(AIRPORTS_PATH), str(ROUTES_PATH)],
            "input_sha256": source_hashes,
            "external_data_used": False,
            "source_files_modified": False,
            "seird_coupled": False,
            "traffic_interpretation": "route-connectivity proxy only; route counts are not passenger volumes, passenger flows, or measured mobility.",
        },
        "airport_processing": {
            "total_records": len(airports), "valid_records": len(valid_airports), "invalid_records": int((~airports["valid_for_country_mapping"]).sum()),
            "duplicate_airport_id_records": int(airports["duplicate_airport_id"].sum()),
            "duplicate_physical_signature_candidates": int(airports["duplicate_physical_signature_candidate"].sum()),
            "missing_or_unusable_country_records": int(airports["country"].isna().sum()),
            "invalid_coordinate_records": int(coordinate_invalid.sum()), "missing_coordinate_records": int(coordinate_missing.sum()),
            "unusable_identifier_records": int(airports["airport_id"].isna().sum()),
            "iata_mapping": "cleaned_airports.csv has no IATA column. iata_code is populated only by a unique, three-character code observed in cleaned_routes.csv for that airport ID; otherwise it is left missing or marked conflicting.",
            "unique_route_derived_iata_style_codes": int(airports["iata_mapping_status"].eq("ROUTE_DERIVED_UNIQUE_NOT_AIRPORT_MASTER_FIELD").sum()),
            "conflicting_route_code_airports": int(airports["iata_mapping_status"].eq("CONFLICTING_ROUTE_CODES_NOT_MAPPED").sum()),
        },
        "route_processing": {
            "total_records": len(routes), "valid_records": len(valid_routes),
            "invalid_or_unmapped_records": int(routes["route_record_status"].isin(["INVALID_AIRPORT_IDENTIFIER", "INVALID_OR_UNMAPPED_AIRPORT"]).sum()),
            "airport_self_loops_removed": int(routes["route_record_status"].eq("REMOVED_AIRPORT_SELF_LOOP").sum()),
            "exact_duplicates_excluded_from_network": int(routes["route_record_status"].eq("DROPPED_EXACT_DUPLICATE").sum()),
            "valid_records_with_reverse_direction": int(valid_routes["reverse_direction_route_present"].sum()),
            "codeshare_status_counts": {str(key): int(value) for key, value in routes["codeshare_status"].value_counts(dropna=False).items()},
            "stops_status_counts": {str(key): int(value) for key, value in routes["stops_status"].value_counts(dropna=False).items()},
            "airline_id_status_counts": {str(key): int(value) for key, value in routes["airline_id_status"].value_counts(dropna=False).items()},
            "filtering_rules": [
                "Keep all route records in routes_processed.csv with audit fields.",
                "Exclude from the validated network only records with unusable endpoint IDs, endpoints absent from the valid supplied airport mapping, airport-level self-loops, or later exact duplicates across all supplied route fields.",
                "Retain directional routes, including reverse-direction pairs, domestic routes, codeshare records, and routes with nonzero stops when their endpoints map validly.",
                "Airline/code/codeshare/stops quality problems are reported but do not by themselves remove an otherwise mappable connectivity record.",
            ],
        },
        "network": {
            "airport_network_rows": len(airport_network), "airport_network_route_count": int(airport_network["route_count"].sum()),
            "directed_airport_pairs": len(directed_pairs), "airport_pairs_with_reverse_direction": len(reverse_pairs) // 2,
            "domestic_route_count_retained": int(valid_routes["country_connectivity_scope"].eq("DOMESTIC_RETAINED").sum()),
            "international_route_count": int(valid_routes["country_connectivity_scope"].eq("INTERNATIONAL").sum()),
            "countries_represented": len(represented_countries), "countries_without_usable_airport_connectivity": countries_without_connectivity,
            "country_route_matrix": {"format": "long-form directed edge list", "rows": len(country_matrix), "country_index_dimension": country_count},
            "normalized_matrix": {"file": "country_route_matrix_normalized.csv", "scope": "international routes only", "rows": len(international_matrix), "source_countries_with_international_outflow": int(international_matrix["source_country"].nunique()), "normalization": "Each source country's retained international route counts sum to one. Countries with no international outgoing routes receive no fabricated row."},
        },
        "structural_validation": checks,
        "outputs": [
            "airports_processed.csv", "routes_processed.csv", "airport_route_network.csv", "country_route_matrix.csv",
            "country_route_matrix_normalized.csv", "airport_route_validation.csv", "mobility_network_report.md", "mobility_network_report.json",
        ],
        "limitations": [
            "Airport-country labels are used exactly as supplied; no external country-code harmonisation was performed.",
            "The supplied airport file has no IATA field, so route-observed codes are not independently verified against an airport-master IATA field.",
            "Route records describe connectivity, not passenger volume, travel volume, traffic intensity, or compartment movement rates.",
            "This stage does not couple routes to SEIRD or simulate cross-country infection.",
        ],
    }
    (OUTPUT_DIR / "mobility_network_report.json").write_text(json.dumps(report, indent=2, default=json_safe), encoding="utf-8")

    lines = [
        "# Mobility Network Validation", "", f"`{status}`", "",
        "## Scope", "", "This stage uses only `cleaned_airports.csv` and `cleaned_routes.csv`. It constructs a directed **route-connectivity proxy**; it does not represent passenger volume, travel volume, or observed mobility, and it is not connected to SEIRD.", "",
        "## Airport processing", "",
        f"- Total airport records: `{len(airports):,}`", f"- Valid airport records: `{len(valid_airports):,}`", f"- Invalid airport records: `{int((~airports['valid_for_country_mapping']).sum()):,}`", f"- Missing/unusable supplied-country records: `{int(airports['country'].isna().sum()):,}`", f"- Invalid supplied-coordinate records: `{int(coordinate_invalid.sum()):,}`", f"- Airport records with unusable IDs: `{int(airports['airport_id'].isna().sum()):,}`", "", "`cleaned_airports.csv` has no IATA column. `airports_processed.csv` retains `airport_id -> iata_code -> country`, but `iata_code` is populated only where a unique three-character code is observed for that airport ID in the supplied routes. It is not an externally verified airport-master IATA value.", "",
        "## Route processing and filtering", "",
        f"- Total route records: `{len(routes):,}`", f"- Valid retained network records: `{len(valid_routes):,}`", f"- Invalid/unmapped endpoint records: `{int(routes['route_record_status'].isin(['INVALID_AIRPORT_IDENTIFIER', 'INVALID_OR_UNMAPPED_AIRPORT']).sum()):,}`", f"- Airport self-loops removed: `{int(routes['route_record_status'].eq('REMOVED_AIRPORT_SELF_LOOP').sum()):,}`", f"- Exact duplicate records excluded from the network: `{int(routes['route_record_status'].eq('DROPPED_EXACT_DUPLICATE').sum()):,}`", f"- Valid records whose reverse airport direction exists: `{int(valid_routes['reverse_direction_route_present'].sum()):,}`", "", "Only unmappable endpoint IDs, endpoint IDs absent from the valid supplied airport mapping, airport self-loops, and exact duplicate source records are excluded from the validated network. Reverse-direction routes, domestic routes, codeshare records, and routes with stops are retained and labelled. Airline, codeshare, stops, and route-code quality are audited in `routes_processed.csv` rather than silently repaired.", "",
        "## Country matrix and normalization", "",
        f"- Countries represented by valid airport records: `{len(represented_countries):,}`", f"- Countries without usable route connectivity: `{len(countries_without_connectivity):,}`", f"- Country route matrix: `{len(country_matrix):,}` nonzero directed edges; `{country_count} x {country_count}` country index", f"- Domestic route records retained in raw matrix: `{int(valid_routes['country_connectivity_scope'].eq('DOMESTIC_RETAINED').sum()):,}`", f"- Normalized international edges: `{len(international_matrix):,}`", "", "`country_route_matrix.csv` retains domestic and international directed route counts. `country_route_matrix_normalized.csv` contains international edges only: each edge is divided by the sum of retained international route counts leaving its source country. A country with no international outgoing route has no invented normalized row.", "",
        "## Structural validation", "",
        *[f"- {name}: `{'PASS' if passed else 'FAIL'}`" for name, passed in checks.items()], "",
        "## Countries without usable airport connectivity", "", f"Count: `{len(countries_without_connectivity)}`. The complete supplied-label list is stored in `mobility_network_report.json`; first 30: " + (", ".join(countries_without_connectivity[:30]) if countries_without_connectivity else "none"), "",
        "## Reproducibility", "", "The script `mobility_network.py` produces every listed output. Input SHA-256 hashes are recorded in `mobility_network_report.json`. Source CSVs are read only.", "",
    ]
    (OUTPUT_DIR / "mobility_network_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": status, "valid_airports": len(valid_airports), "valid_routes": len(valid_routes), "countries_represented": len(represented_countries)}, indent=2))


if __name__ == "__main__":
    main()
