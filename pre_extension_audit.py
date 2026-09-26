"""Pre-Extension Final Audit & Time-Window Audit for Coupled SEIRD Model.

Performs sequential checks:
1. PRE-EXTENSION FINAL CHECK on existing 2020 model
2. TIME-WINDOW AUDIT of owid_covid.csv for extension feasibility
3. EXTENDED SEIRD TIME-WINDOW DESIGN assessment

Does NOT modify any source datasets.
Does NOT extend the model -- only assesses feasibility.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from datetime import datetime

# Ensure utf-8 encoding on Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import numpy as np
import pandas as pd

# --- Paths -------------------------------------------------------------------
ROOT = Path(".")
OUT = Path("outputs")

SRC_AIRPORTS = ROOT / "cleaned_airports.csv"
SRC_ROUTES = ROOT / "cleaned_routes.csv"
SRC_OWID = ROOT / "owid_covid.csv"

AIRPORTS_PROC = OUT / "airports_processed.csv"
ROUTES_PROC = OUT / "routes_processed.csv"
ROUTE_MATRIX = OUT / "country_route_matrix.csv"
ROUTE_MATRIX_NORM = OUT / "country_route_matrix_normalized.csv"
OWID_PROC = OUT / "owid_covid_processed.csv"
RT_EST = OUT / "rt_estimates.csv"

SIM_CSV = OUT / "coupled_seird_simulation.csv"
COUNTRY_SUMMARY = OUT / "coupled_seird_country_summary.csv"
SCENARIO_COMP = OUT / "coupled_seird_scenario_comparison.csv"
NETWORK_FX = OUT / "coupled_seird_network_effects.csv"
VAL_JSON = OUT / "coupled_seird_validation.json"
VAL_MD = OUT / "coupled_seird_validation.md"

ASSUMPTIONS_JSON = ROOT / "seird_assumptions.json"
ALPHA_JSON = ROOT / "alpha_identifiability_report.json"

START_DATE = pd.Timestamp("2020-01-22")
END_DATE = pd.Timestamp("2020-12-31")

# Expected SEIRD parameters from seird_assumptions.json PRIMARY scenario
EXPECTED_SIGMA = 0.19607843137254904
EXPECTED_GAMMA = 0.125
EXPECTED_MU = 0.0008304811757600161
EXPECTED_REMOVAL = EXPECTED_GAMMA + EXPECTED_MU

SCENARIOS = [
    {"id": "SCEN_0_DECOUPLED", "alpha": 0.0},
    {"id": "SCEN_1_LOW_COUPLING", "alpha": 0.001},
    {"id": "SCEN_2_MODERATE_COUPLING", "alpha": 0.01},
    {"id": "SCEN_3_HIGH_COUPLING", "alpha": 0.05},
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def section(title: str):
    print(f"\n{'='*72}")
    print(f"  {title}")
    print(f"{'='*72}")


# ???????????????????????????????????????????????????????????????????????????????
# PART 1: PRE-EXTENSION FINAL AUDIT
# ???????????????????????????????????????????????????????????????????????????????
def pre_extension_audit():
    section("PART 1: PRE-EXTENSION FINAL AUDIT")
    t0 = time.time()
    checks = {}
    findings = []
    warnings = []

    # -- 1.1 Source File Integrity ------------------------------------------
    print("\n[1.1] Source file integrity (SHA-256 hashes)...")
    hashes = {}
    for label, path in [("cleaned_airports.csv", SRC_AIRPORTS),
                         ("cleaned_routes.csv", SRC_ROUTES),
                         ("owid_covid.csv", SRC_OWID)]:
        if path.exists():
            hashes[label] = sha256_file(path)
            print(f"  {label}: {hashes[label][:16]}...")
        else:
            hashes[label] = "FILE_NOT_FOUND"
            findings.append(f"CRITICAL: Source file missing: {label}")
    checks["source_file_hashes"] = hashes
    checks["source_files_exist"] = all(v != "FILE_NOT_FOUND" for v in hashes.values())

    # -- 1.2 Existing Output File Existence ---------------------------------
    print("\n[1.2] Existing output file existence...")
    required_outputs = {
        "coupled_seird_simulation.csv": SIM_CSV,
        "coupled_seird_country_summary.csv": COUNTRY_SUMMARY,
        "coupled_seird_scenario_comparison.csv": SCENARIO_COMP,
        "coupled_seird_network_effects.csv": NETWORK_FX,
        "coupled_seird_validation.json": VAL_JSON,
        "coupled_seird_validation.md": VAL_MD,
    }
    output_exists = {}
    for name, path in required_outputs.items():
        output_exists[name] = path.exists()
        if not path.exists():
            findings.append(f"CRITICAL: Required output missing: {name}")
    checks["output_files_exist"] = output_exists
    checks["all_outputs_present"] = all(output_exists.values())

    if not checks["all_outputs_present"]:
        checks["pre_extension_status"] = "NO-GO"
        checks["pre_extension_reason"] = "Missing required output files"
        return checks, findings, warnings

    # -- 1.3 Load Existing Validation JSON ----------------------------------
    print("\n[1.3] Loading existing validation JSON...")
    with open(VAL_JSON, "r", encoding="utf-8") as f:
        existing_val = json.load(f)
    checks["existing_status"] = existing_val.get("status", "UNKNOWN")
    checks["existing_scope"] = existing_val.get("scope", {})

    # -- 1.4 Load & Audit Simulation CSV ------------------------------------
    print("\n[1.4] Loading coupled_seird_simulation.csv...")
    sim = pd.read_csv(SIM_CSV, parse_dates=["date"])
    print(f"  Shape: {sim.shape}")
    print(f"  Columns: {list(sim.columns)}")

    # Basic shape checks
    n_rows = len(sim)
    n_countries_sim = sim["country"].nunique()
    n_scenarios_sim = sim["scenario"].nunique()
    n_dates_sim = sim["date"].nunique()
    date_min = sim["date"].min()
    date_max = sim["date"].max()

    checks["simulation_csv"] = {
        "rows": n_rows,
        "countries": n_countries_sim,
        "scenarios": n_scenarios_sim,
        "dates": n_dates_sim,
        "date_min": str(date_min.date()),
        "date_max": str(date_max.date()),
        "expected_rows": n_countries_sim * n_scenarios_sim * n_dates_sim,
        "null_count": int(sim.isnull().sum().sum()),
    }
    print(f"  Countries: {n_countries_sim}, Scenarios: {n_scenarios_sim}, Dates: {n_dates_sim}")
    print(f"  Date range: {date_min.date()} to {date_max.date()}")

    # -- 1.5 Country Universe Reconciliation --------------------------------
    print("\n[1.5] Country universe reconciliation...")
    owid = pd.read_csv(SRC_OWID)
    owid["date"] = pd.to_datetime(owid["date"], dayfirst=True)
    # This OWID CSV uses 'country' column, not 'location'
    country_col = "country" if "country" in owid.columns else "location"
    owid_countries_all = sorted(owid[country_col].unique())

    # OWID aggregate locations to exclude
    aggregate_names = [
        "World", "Africa", "Asia", "Europe", "North America", "South America",
        "Oceania", "European Union", "International",
        "High income", "Upper middle income", "Lower middle income", "Low income",
        "High-income countries", "Upper-middle-income countries",
        "Lower-middle-income countries", "Low-income countries",
    ]
    # Also filter using is_country column if available
    if "is_country" in owid.columns:
        actual_countries = sorted(owid[owid["is_country"] == True][country_col].unique())
        owid_countries_filtered = actual_countries
    else:
        owid_countries_filtered = [c for c in owid_countries_all if c not in aggregate_names]
    n_owid_all = len(owid_countries_all)
    n_owid_filtered = len(owid_countries_filtered)

    # Countries in OWID processed
    owid_proc = pd.read_csv(OWID_PROC, parse_dates=["date"])
    owid_proc_countries = sorted(owid_proc["country"].unique()) if "country" in owid_proc.columns else sorted(owid_proc["location"].unique()) if "location" in owid_proc.columns else []

    # Countries in simulation
    sim_countries = sorted(sim["country"].unique())

    # Countries in route matrix
    route_mat = pd.read_csv(ROUTE_MATRIX)
    route_countries_src = set(route_mat["source_country"].unique())
    route_countries_dst = set(route_mat["destination_country"].unique())
    route_countries_all = sorted(route_countries_src | route_countries_dst)

    # Countries in route matrix with international routes
    route_intl = route_mat[route_mat["country_connectivity_scope"] == "INTERNATIONAL"]
    route_intl_countries = sorted(set(route_intl["source_country"].unique()) | set(route_intl["destination_country"].unique()))

    checks["country_reconciliation"] = {
        "owid_all_locations": n_owid_all,
        "owid_filtered_countries": n_owid_filtered,
        "owid_processed_countries": len(owid_proc_countries),
        "route_matrix_countries": len(route_countries_all),
        "route_intl_countries": len(route_intl_countries),
        "simulation_countries": n_countries_sim,
        "previously_reported_owid_countries": 237,
        "previously_reported_connected_countries": 225,
        "previously_reported_modeled_countries": 217,
    }

    # Identify differences
    sim_set = set(sim_countries)
    owid_proc_set = set(owid_proc_countries)
    route_set = set(route_countries_all)

    in_sim_not_route = sorted(sim_set - route_set)
    in_route_not_sim = sorted(route_set - sim_set)
    in_owid_not_sim = sorted(owid_proc_set - sim_set)
    in_sim_not_owid = sorted(sim_set - owid_proc_set)

    checks["country_reconciliation"]["in_sim_not_route_matrix"] = in_sim_not_route
    checks["country_reconciliation"]["in_route_not_sim"] = in_route_not_sim
    checks["country_reconciliation"]["in_owid_proc_not_sim"] = len(in_owid_not_sim)
    checks["country_reconciliation"]["in_sim_not_owid_proc"] = len(in_sim_not_owid)

    print(f"  OWID all locations: {n_owid_all}")
    print(f"  OWID filtered (excl. aggregates): {n_owid_filtered}")
    print(f"  OWID processed countries: {len(owid_proc_countries)}")
    print(f"  Route matrix countries: {len(route_countries_all)}")
    print(f"  Simulation countries: {n_countries_sim}")
    print(f"  In sim but not route matrix: {len(in_sim_not_route)} -> {in_sim_not_route[:10]}...")
    print(f"  In route matrix but not sim: {len(in_route_not_sim)}")

    # -- 1.6 Simulation Dates -----------------------------------------------
    print("\n[1.6] Simulation date verification...")
    expected_dates = pd.date_range(START_DATE, END_DATE, freq="D")
    n_expected_days = len(expected_dates)
    sim_dates = sorted(sim["date"].unique())

    checks["date_verification"] = {
        "expected_start": str(START_DATE.date()),
        "expected_end": str(END_DATE.date()),
        "expected_days": n_expected_days,
        "actual_start": str(sim_dates[0].date() if len(sim_dates) > 0 else "NONE"),
        "actual_end": str(sim_dates[-1].date() if len(sim_dates) > 0 else "NONE"),
        "actual_days": len(sim_dates),
        "dates_match": n_dates_sim == n_expected_days,
    }
    if n_dates_sim != n_expected_days:
        findings.append(f"Date count mismatch: expected {n_expected_days}, got {n_dates_sim}")

    # -- 1.7 Alpha Scenarios ------------------------------------------------
    print("\n[1.7] Alpha scenario verification...")
    sim_scenarios = sorted(sim["scenario"].unique())
    expected_scenarios = [s["id"] for s in SCENARIOS]
    sim_alphas = sorted(sim["alpha"].unique())
    expected_alphas = sorted([s["alpha"] for s in SCENARIOS])

    checks["scenario_verification"] = {
        "expected_scenarios": expected_scenarios,
        "actual_scenarios": sim_scenarios,
        "scenarios_match": sim_scenarios == sorted(expected_scenarios),
        "expected_alphas": expected_alphas,
        "actual_alphas": sim_alphas,
        "alphas_match": sim_alphas == expected_alphas,
    }
    if not checks["scenario_verification"]["scenarios_match"]:
        findings.append("Scenario names do not match expected set")
    if not checks["scenario_verification"]["alphas_match"]:
        findings.append("Alpha values do not match expected set")

    # -- 1.8 SEIRD Parameter Verification -----------------------------------
    print("\n[1.8] SEIRD parameter verification from seird_assumptions.json...")
    assumptions = json.loads(ASSUMPTIONS_JSON.read_text(encoding="utf-8"))
    params = assumptions["parameters"]
    actual_sigma = float(params["sigma"]["value"])
    actual_gamma = float(params["gamma"]["value"])
    actual_mu = float(params["mortality_transition_parameter"]["value"])
    actual_removal = actual_gamma + actual_mu

    checks["seird_parameters"] = {
        "sigma": {"expected": EXPECTED_SIGMA, "actual": actual_sigma, "match": abs(actual_sigma - EXPECTED_SIGMA) < 1e-12},
        "gamma": {"expected": EXPECTED_GAMMA, "actual": actual_gamma, "match": abs(actual_gamma - EXPECTED_GAMMA) < 1e-12},
        "mu": {"expected": EXPECTED_MU, "actual": actual_mu, "match": abs(actual_mu - EXPECTED_MU) < 1e-12},
        "removal_rate": {"expected": EXPECTED_REMOVAL, "actual": actual_removal, "match": abs(actual_removal - EXPECTED_REMOVAL) < 1e-12},
    }
    for pname, pinfo in checks["seird_parameters"].items():
        if not pinfo["match"]:
            findings.append(f"Parameter mismatch: {pname} expected={pinfo['expected']}, actual={pinfo['actual']}")

    # -- 1.9 Initial Seed Countries -----------------------------------------
    print("\n[1.9] Initial seed country verification...")
    existing_seed = existing_val.get("initial_seeding_strategy", {})
    reported_seeds = existing_seed.get("seed_countries", [])
    reported_seed_count = existing_seed.get("seed_countries_count", 0)

    # Independently verify from OWID
    owid_t0 = owid[owid["date"] == START_DATE]
    owid_t0_cases = owid_t0[owid_t0["total_cases"] > 0][[country_col, "total_cases"]].sort_values(country_col)
    # Filter to only the simulation country set
    independent_seeds = sorted(owid_t0_cases[owid_t0_cases[country_col].isin(sim_set)][country_col].tolist())

    checks["seed_verification"] = {
        "reported_seeds": reported_seeds,
        "reported_seed_count": reported_seed_count,
        "independently_verified_seeds": independent_seeds,
        "independent_seed_count": len(independent_seeds),
        "seeds_consistent": set(reported_seeds) == set(independent_seeds),
    }
    if not checks["seed_verification"]["seeds_consistent"]:
        diff_reported_not_indep = sorted(set(reported_seeds) - set(independent_seeds))
        diff_indep_not_reported = sorted(set(independent_seeds) - set(reported_seeds))
        checks["seed_verification"]["in_reported_not_verified"] = diff_reported_not_indep
        checks["seed_verification"]["in_verified_not_reported"] = diff_indep_not_reported
        warnings.append(f"Seed country discrepancy: reported={reported_seeds}, verified={independent_seeds}")

    print(f"  Reported seeds ({reported_seed_count}): {reported_seeds}")
    print(f"  Independently verified seeds ({len(independent_seeds)}): {independent_seeds}")

    # -- 1.10 Non-negative Compartments -------------------------------------
    print("\n[1.10] Non-negative compartment check...")
    compartments = ["S", "E", "I", "R", "D"]
    min_vals = {}
    for c in compartments:
        min_vals[c] = float(sim[c].min())
    all_nonneg = all(v >= -1e-5 for v in min_vals.values())
    checks["nonnegative_compartments"] = {
        "min_values": min_vals,
        "pass": all_nonneg,
    }
    if not all_nonneg:
        findings.append(f"Negative compartment values found: {min_vals}")

    # -- 1.11 Population Conservation ---------------------------------------
    print("\n[1.11] Population conservation check...")
    sim["total_pop"] = sim["S"] + sim["E"] + sim["I"] + sim["R"] + sim["D"]
    # Get population for each country
    pop_ref = sim.groupby("country")["total_pop"].first()
    # Check within each scenario
    max_pop_err = 0.0
    for scen_id in sim["scenario"].unique():
        sub = sim[sim["scenario"] == scen_id]
        for country in sub["country"].unique():
            csub = sub[sub["country"] == country]
            pop_first = csub["total_pop"].iloc[0]
            max_dev = float(abs(csub["total_pop"] - pop_first).max())
            if max_dev > max_pop_err:
                max_pop_err = max_dev
    checks["population_conservation"] = {
        "max_absolute_error": max_pop_err,
        "pass": max_pop_err < 1e-3,
    }
    if max_pop_err >= 1e-3:
        findings.append(f"Population conservation violated: max error = {max_pop_err}")

    # -- 1.12 Monotonic Deaths and Recoveries -------------------------------
    print("\n[1.12] Monotonic deaths and recoveries check...")
    death_monotonic = True
    recovery_monotonic = True
    for scen_id in sim["scenario"].unique():
        for country in sim["country"].unique():
            mask = (sim["scenario"] == scen_id) & (sim["country"] == country)
            d_vals = sim.loc[mask, "D"].values
            r_vals = sim.loc[mask, "R"].values
            d_diff = np.diff(d_vals)
            r_diff = np.diff(r_vals)
            if d_diff.min() < -1e-5:
                death_monotonic = False
            if r_diff.min() < -1e-5:
                recovery_monotonic = False
    checks["monotonicity"] = {
        "deaths_nondecreasing": death_monotonic,
        "recovered_nondecreasing": recovery_monotonic,
        "pass": death_monotonic and recovery_monotonic,
    }
    if not death_monotonic:
        findings.append("Deaths are NOT monotonically non-decreasing")
    if not recovery_monotonic:
        findings.append("Recoveries are NOT monotonically non-decreasing")

    # -- 1.13 No Spontaneous Infection (alpha=0 scenario) -------------------
    print("\n[1.13] No spontaneous infection check (alpha=0)...")
    scen0 = sim[sim["scenario"] == "SCEN_0_DECOUPLED"]
    seed_set = set(reported_seeds)
    non_seed_scen0 = scen0[~scen0["country"].isin(seed_set)]
    max_I_nonseed = float(non_seed_scen0["I"].max())
    max_E_nonseed = float(non_seed_scen0["E"].max())
    checks["no_spontaneous_infection"] = {
        "max_I_nonseed_alpha0": max_I_nonseed,
        "max_E_nonseed_alpha0": max_E_nonseed,
        "pass": max_I_nonseed < 1e-8 and max_E_nonseed < 1e-8,
    }
    if not checks["no_spontaneous_infection"]["pass"]:
        findings.append(f"Spontaneous infection detected in alpha=0 scenario: max I={max_I_nonseed}, max E={max_E_nonseed}")

    # -- 1.14 Numerical Stability -------------------------------------------
    print("\n[1.14] Numerical stability check...")
    nan_count = int(sim[compartments + ["beta", "Rt", "imported_infectious_pressure"]].isna().sum().sum())
    inf_count = int(np.isinf(sim[compartments + ["beta", "Rt", "imported_infectious_pressure"]].select_dtypes(include=[np.number]).values).sum())
    checks["numerical_stability"] = {
        "nan_count": nan_count,
        "inf_count": inf_count,
        "pass": nan_count == 0 and inf_count == 0,
    }
    if nan_count > 0 or inf_count > 0:
        findings.append(f"Numerical instability: {nan_count} NaN, {inf_count} Inf values")

    # -- 1.15 Beta/Rt Relationship ------------------------------------------
    print("\n[1.15] Beta/Rt effective-Rt relationship check...")
    # beta = Rt * (gamma + mu) * N / S
    # => Rt_check = beta * S / (N * (gamma + mu))
    # Since we stored Rt from rt_matrix (not recomputed), we verify the identity
    # For a random sample of rows
    sample = sim.sample(min(5000, len(sim)), random_state=42)
    sample_N = sample["S"] + sample["E"] + sample["I"] + sample["R"] + sample["D"]
    rt_recomputed = sample["beta"] * sample["S"] / (sample_N * EXPECTED_REMOVAL)
    rt_stored = sample["Rt"]
    rt_diff = abs(rt_recomputed - rt_stored)
    max_rt_diff = float(rt_diff.max())
    mean_rt_diff = float(rt_diff.mean())
    checks["beta_rt_identity"] = {
        "max_difference": max_rt_diff,
        "mean_difference": mean_rt_diff,
        "pass": max_rt_diff < 0.5,
        "note": "Rt stored is from rt_estimates.csv; beta is derived. Small differences are expected due to S/N?1 approximation in some implementations."
    }

    # -- 1.16 Route Directionality ------------------------------------------
    print("\n[1.16] Route directionality check...")
    norm_mat = pd.read_csv(ROUTE_MATRIX_NORM)
    # Check that Q_ji != Q_ij for most pairs
    intl_norm = norm_mat[norm_mat["connectivity_scope"] == "INTERNATIONAL"] if "connectivity_scope" in norm_mat.columns else norm_mat
    if "source_country" in intl_norm.columns and "destination_country" in intl_norm.columns:
        value_col = [c for c in intl_norm.columns if "normalized" in c.lower() or "share" in c.lower() or "probability" in c.lower()]
        if len(value_col) > 0:
            value_col = value_col[0]
        else:
            value_col = [c for c in intl_norm.columns if c not in ["source_country", "destination_country", "connectivity_scope", "country_connectivity_scope"]][0]
        pivot_check = intl_norm.pivot_table(index="source_country", columns="destination_country", values=value_col, fill_value=0)
        # Check asymmetry
        common_idx = sorted(set(pivot_check.index) & set(pivot_check.columns))
        sym_count = 0
        asym_count = 0
        for i_idx, c1 in enumerate(common_idx):
            for c2 in common_idx[i_idx+1:]:
                v1 = pivot_check.loc[c1, c2] if c2 in pivot_check.columns and c1 in pivot_check.index else 0
                v2 = pivot_check.loc[c2, c1] if c1 in pivot_check.columns and c2 in pivot_check.index else 0
                if abs(v1 - v2) < 1e-10:
                    sym_count += 1
                else:
                    asym_count += 1
        total_pairs = sym_count + asym_count
        asym_frac = asym_count / total_pairs if total_pairs > 0 else 0
        checks["route_directionality"] = {
            "asymmetric_pairs": asym_count,
            "symmetric_pairs": sym_count,
            "asymmetry_fraction": round(asym_frac, 4),
            "pass": asym_frac > 0.5,
        }
    else:
        checks["route_directionality"] = {"pass": False, "note": "Could not verify - unexpected column structure"}
        warnings.append("Route matrix normalized has unexpected structure")

    # -- 1.17 Isolated Country Handling -------------------------------------
    print("\n[1.17] Isolated country handling check...")
    ISOLATED_12 = [
        "Antarctica", "British Indian Ocean Territory", "Johnston Atoll",
        "Midway Islands", "Montserrat", "Myanmar", "Palestine",
        "Saint Helena", "Svalbard", "Syria", "Wake Island", "West Bank",
    ]
    isolated_in_sim = [c for c in ISOLATED_12 if c in sim_set]
    isolated_not_in_sim = [c for c in ISOLATED_12 if c not in sim_set]

    # For isolated countries in sim, verify alpha_effective = 0
    iso_psi_check = True
    for iso_c in isolated_in_sim:
        iso_rows = sim[sim["country"] == iso_c]
        max_psi = float(iso_rows["imported_infectious_pressure"].max())
        if max_psi > 1e-10:
            iso_psi_check = False
            findings.append(f"Isolated country {iso_c} has non-zero Psi = {max_psi}")

    checks["isolated_countries"] = {
        "total_isolated_12": len(ISOLATED_12),
        "isolated_in_simulation": isolated_in_sim,
        "isolated_not_in_simulation": isolated_not_in_sim,
        "count_in_sim": len(isolated_in_sim),
        "count_not_in_sim": len(isolated_not_in_sim),
        "psi_zero_verified": iso_psi_check,
        "pass": iso_psi_check,
    }

    # -- 1.18 Alpha Interpretation Guardrail --------------------------------
    print("\n[1.18] Alpha interpretation guardrail check...")
    alpha_report = json.loads(ALPHA_JSON.read_text(encoding="utf-8"))
    alpha_status = alpha_report.get("status", "UNKNOWN")
    is_sensitivity_only = "SENSITIVITY ONLY" in alpha_status
    is_not_identifiable = alpha_report.get("identifiability_assessment", {}).get("is_empirically_identifiable") is False

    checks["alpha_guardrail"] = {
        "alpha_status": alpha_status,
        "is_sensitivity_only": is_sensitivity_only,
        "is_not_empirically_identifiable": is_not_identifiable,
        "pass": is_sensitivity_only and is_not_identifiable,
    }
    if not checks["alpha_guardrail"]["pass"]:
        findings.append("Alpha guardrail violation: alpha is not marked as sensitivity-only or non-identifiable")

    # -- 1.19 Route Connectivity Language -----------------------------------
    print("\n[1.19] Route connectivity vs passenger volume language check...")
    val_md_text = VAL_MD.read_text(encoding="utf-8")
    passenger_volume_claims = []
    problematic_phrases = [
        "passenger volume", "passenger count", "passenger flow",
        "measured travel", "observed mobility", "travel volume",
        "daily passengers", "flight frequency data",
    ]
    for phrase in problematic_phrases:
        if phrase.lower() in val_md_text.lower():
            # Check context -- exclude negated forms
            import re
            matches = re.findall(rf'(?i)(?<!not )(?<!no )(?<!without )(?<!absence of ){re.escape(phrase)}', val_md_text)
            if matches:
                passenger_volume_claims.append(phrase)

    checks["route_language_guardrail"] = {
        "problematic_claims_found": passenger_volume_claims,
        "pass": len(passenger_volume_claims) == 0,
    }
    if passenger_volume_claims:
        warnings.append(f"Validation report may contain route-as-passenger language: {passenger_volume_claims}")

    # -- 1.20 Observation Model Check ---------------------------------------
    print("\n[1.20] Observation model check (confirmed cases != I compartment)...")
    # Verify that the validation report does not equate confirmed cases to I
    obs_model_phrases = [
        "confirmed cases equal",
        "cases represent the infectious",
        "cases are the infectious compartment",
    ]
    obs_model_violations = []
    for phrase in obs_model_phrases:
        if phrase.lower() in val_md_text.lower():
            obs_model_violations.append(phrase)
    checks["observation_model_guardrail"] = {
        "violations_found": obs_model_violations,
        "pass": len(obs_model_violations) == 0,
    }

    # -- 1.21 Population Totals ---------------------------------------------
    print("\n[1.21] Population total verification...")
    # Compare reported population with what's in the existing validation JSON
    reported_pop = existing_val.get("scope", {}).get("global_population_represented", 0)
    # Recompute from simulation day 0
    day0 = sim[(sim["scenario"] == "SCEN_0_DECOUPLED") & (sim["date"] == START_DATE)]
    recomputed_pop = int(day0["total_pop"].sum())

    checks["population_totals"] = {
        "reported_in_validation_json": reported_pop,
        "recomputed_from_sim_day0": recomputed_pop,
        "difference": abs(reported_pop - recomputed_pop),
        "pass": abs(reported_pop - recomputed_pop) < 1000,
    }

    # -- 1.22 Row Count Verification ----------------------------------------
    print("\n[1.22] Row count verification...")
    expected_rows = n_countries_sim * n_scenarios_sim * n_dates_sim
    checks["row_count"] = {
        "expected": expected_rows,
        "actual": n_rows,
        "pass": n_rows == expected_rows,
    }
    if n_rows != expected_rows:
        findings.append(f"Row count mismatch: expected {expected_rows} ({n_countries_sim} ? {n_scenarios_sim} ? {n_dates_sim}), got {n_rows}")

    # -- AGGREGATE STATUS ---------------------------------------------------
    critical_checks = [
        checks.get("source_files_exist", False),
        checks.get("all_outputs_present", False),
        checks["nonnegative_compartments"]["pass"],
        checks["population_conservation"]["pass"],
        checks["monotonicity"]["pass"],
        checks["no_spontaneous_infection"]["pass"],
        checks["numerical_stability"]["pass"],
        checks["scenario_verification"]["scenarios_match"],
        checks["scenario_verification"]["alphas_match"],
        checks["alpha_guardrail"]["pass"],
        checks["isolated_countries"]["pass"],
        checks["row_count"]["pass"],
        checks["date_verification"]["dates_match"],
    ]
    for pname, pinfo in checks["seird_parameters"].items():
        critical_checks.append(pinfo["match"])

    all_pass = all(critical_checks)
    checks["pre_extension_status"] = "GO" if all_pass else "NO-GO"
    if not all_pass:
        checks["pre_extension_reason"] = f"{len(findings)} critical findings: " + "; ".join(findings[:5])

    elapsed = time.time() - t0
    checks["audit_elapsed_seconds"] = round(elapsed, 2)
    print(f"\n  PRE-EXTENSION STATUS: {'GO ?' if all_pass else 'NO-GO ?'}")
    print(f"  Critical findings: {len(findings)}")
    print(f"  Warnings: {len(warnings)}")

    return checks, findings, warnings


# ???????????????????????????????????????????????????????????????????????????????
# PART 2: OWID TIME-WINDOW AUDIT
# ???????????????????????????????????????????????????????????????????????????????
def time_window_audit():
    section("PART 2: TIME-WINDOW AUDIT of owid_covid.csv")
    t0 = time.time()
    audit = {}

    print("\n[2.1] Loading owid_covid.csv (raw)...")
    owid = pd.read_csv(SRC_OWID)
    owid["date"] = pd.to_datetime(owid["date"], dayfirst=True)
    country_col = "country" if "country" in owid.columns else "location"
    print(f"  Shape: {owid.shape}")
    print(f"  Columns ({len(owid.columns)}): {list(owid.columns)[:20]}...")

    # -- 2.2 Date Range -----------------------------------------------------
    print("\n[2.2] Date range determination...")
    date_min = owid["date"].min()
    date_max = owid["date"].max()
    print(f"  Minimum date: {date_min}")
    print(f"  Maximum date: {date_max}")
    audit["date_range"] = {
        "min_date": str(date_min.date()),
        "max_date": str(date_max.date()),
        "total_days": (date_max - date_min).days + 1,
    }

    # -- 2.3 Yearly Row Counts ----------------------------------------------
    print("\n[2.3] Yearly row counts...")
    owid["year"] = owid["date"].dt.year
    yearly = owid.groupby("year").agg(
        rows=("date", "count"),
        unique_dates=("date", "nunique"),
        unique_locations=(country_col, "nunique"),
    ).reset_index()
    print(yearly.to_string(index=False))
    audit["yearly_summary"] = yearly.to_dict(orient="records")

    # Filter to country-level locations (exclude aggregates)
    aggregate_names = [
        "World", "Africa", "Asia", "Europe", "North America", "South America",
        "Oceania", "European Union", "International",
        "High income", "Upper middle income", "Lower middle income", "Low income",
        "High-income countries", "Upper-middle-income countries",
        "Lower-middle-income countries", "Low-income countries",
    ]
    # Filter to country-level entries
    if "is_country" in owid.columns:
        owid_countries = owid[owid["is_country"] == True].copy()
    else:
        owid_countries = owid[~owid[country_col].isin(aggregate_names)].copy()
    n_countries_owid = owid_countries[country_col].nunique()
    print(f"\n  Country-level locations (excl. aggregates): {n_countries_owid}")
    audit["country_level_locations"] = n_countries_owid

    # -- 2.4 Country Coverage by Year ---------------------------------------
    print("\n[2.4] Country coverage by year...")
    yearly_countries = owid_countries.groupby("year")[country_col].nunique().reset_index()
    yearly_countries.columns = ["year", "unique_countries"]
    print(yearly_countries.to_string(index=False))
    audit["countries_by_year"] = yearly_countries.to_dict(orient="records")

    # -- 2.5 Modelling Variable Availability by Year ------------------------
    print("\n[2.5] Modelling variable availability by year...")
    key_vars = [
        "total_cases", "new_cases", "new_cases_smoothed",
        "total_deaths", "new_deaths", "new_deaths_smoothed",
        "reproduction_rate", "population", "stringency_index",
    ]
    # Check which variables exist
    available_vars = [v for v in key_vars if v in owid.columns]
    missing_vars = [v for v in key_vars if v not in owid.columns]
    audit["available_modelling_vars"] = available_vars
    audit["missing_modelling_vars"] = missing_vars

    missingness_by_year = {}
    for year in sorted(owid_countries["year"].unique()):
        year_data = owid_countries[owid_countries["year"] == year]
        n_rows = len(year_data)
        miss = {}
        for v in available_vars:
            n_miss = int(year_data[v].isna().sum())
            miss[v] = {
                "missing_count": n_miss,
                "missing_pct": round(100 * n_miss / n_rows, 1) if n_rows > 0 else 0,
            }
        missingness_by_year[int(year)] = miss
    audit["missingness_by_year"] = missingness_by_year

    # Print summary
    for year, miss in missingness_by_year.items():
        print(f"\n  Year {year}:")
        for var, info in miss.items():
            pct = info["missing_pct"]
            status = "OK" if pct < 20 else "WARN" if pct < 50 else "HIGH"
            print(f"    {var:30s}: {pct:5.1f}% missing [{status}]")

    # -- 2.6 Rt_estimated Availability --------------------------------------
    print("\n[2.6] Rt_estimated availability check...")
    rt_path = OUT / "rt_estimates.csv"
    if rt_path.exists():
        rt_df = pd.read_csv(rt_path, parse_dates=["date"])
        rt_date_min = rt_df["date"].min()
        rt_date_max = rt_df["date"].max()
        rt_countries = rt_df["country"].nunique() if "country" in rt_df.columns else 0
        rt_df["year"] = rt_df["date"].dt.year
        rt_yearly = rt_df.groupby("year").agg(
            rows=("date", "count"),
            countries=("country", "nunique"),
            rt_non_null=("Rt_estimated", lambda x: int(x.notna().sum())),
            rt_null=("Rt_estimated", lambda x: int(x.isna().sum())),
        ).reset_index()
        print(f"  Rt estimates date range: {rt_date_min.date()} to {rt_date_max.date()}")
        print(f"  Rt countries: {rt_countries}")
        print(rt_yearly.to_string(index=False))
        audit["rt_estimates"] = {
            "date_min": str(rt_date_min.date()),
            "date_max": str(rt_date_max.date()),
            "countries": rt_countries,
            "yearly": rt_yearly.to_dict(orient="records"),
        }
    else:
        audit["rt_estimates"] = {"status": "FILE NOT FOUND"}
        print("  rt_estimates.csv NOT FOUND")

    # -- 2.7 Population & Mortality Variable Coverage -----------------------
    print("\n[2.7] Population and mortality variable coverage...")
    pop_coverage = {}
    for year in sorted(owid_countries["year"].unique()):
        year_data = owid_countries[owid_countries["year"] == year]
        countries_year = year_data[country_col].unique()
        n_total = len(countries_year)
        n_with_pop = int(year_data.groupby(country_col)["population"].first().notna().sum())
        n_with_deaths = int(year_data.groupby(country_col)["total_deaths"].max().notna().sum())
        pop_coverage[int(year)] = {
            "total_countries": n_total,
            "with_population": n_with_pop,
            "with_deaths_data": n_with_deaths,
        }
    audit["population_mortality_coverage"] = pop_coverage
    for year, info in pop_coverage.items():
        print(f"  {year}: {info['total_countries']} countries, {info['with_population']} with pop, {info['with_deaths_data']} with deaths")

    # -- 2.8 Countries with Insufficient Data ------------------------------
    print("\n[2.8] Countries with insufficient data for extended modelling...")
    insufficient_countries = {}
    for year in sorted(owid_countries["year"].unique()):
        year_data = owid_countries[owid_countries["year"] == year]
        # A country is insufficient if: no cases data, no population, or fewer than 30 observation days
        insuff = []
        for loc in year_data[country_col].unique():
            loc_data = year_data[year_data[country_col] == loc]
            n_obs = len(loc_data)
            has_pop = loc_data["population"].notna().any()
            has_cases = loc_data["total_cases"].notna().any() and loc_data["total_cases"].max() > 0
            if n_obs < 30 or not has_pop or not has_cases:
                insuff.append({
                    "country": loc,
                    "observations": n_obs,
                    "has_population": bool(has_pop),
                    "has_cases": bool(has_cases),
                })
        insufficient_countries[int(year)] = insuff

    audit["insufficient_countries_by_year"] = {
        year: len(insuff) for year, insuff in insufficient_countries.items()
    }
    for year, insuff in insufficient_countries.items():
        print(f"  {year}: {len(insuff)} countries with insufficient data")

    elapsed = time.time() - t0
    audit["audit_elapsed_seconds"] = round(elapsed, 2)
    return audit, insufficient_countries


# ???????????????????????????????????????????????????????????????????????????????
# PART 3: EXTENDED SEIRD TIME-WINDOW DESIGN ASSESSMENT
# ???????????????????????????????????????????????????????????????????????????????
def extension_design_assessment(time_audit, insufficient_by_year):
    section("PART 3: EXTENDED SEIRD TIME-WINDOW DESIGN ASSESSMENT")
    design = {}

    # Determine latest defensible date
    rt_info = time_audit.get("rt_estimates", {})
    rt_max_date = rt_info.get("date_max", "2020-12-31")
    owid_max_date = time_audit.get("date_range", {}).get("max_date", "2020-12-31")
    rt_yearly = rt_info.get("yearly", [])

    # The simulation is limited by Rt_estimated availability (since beta depends on it)
    design["limiting_factor"] = "Rt_estimated availability determines maximum simulation date, since beta(t) = Rt(t) * (gamma+mu) * N/S(t)"
    design["owid_max_date"] = owid_max_date
    design["rt_max_date"] = rt_max_date

    # Assess year-by-year feasibility
    feasibility = {}
    for yr_info in rt_yearly:
        year = yr_info["year"]
        rt_non_null = yr_info.get("rt_non_null", 0)
        rt_null = yr_info.get("rt_null", 0)
        total = rt_non_null + rt_null
        coverage = rt_non_null / total if total > 0 else 0
        n_insuff = len(insufficient_by_year.get(year, []))

        feasible = coverage > 0.5 and rt_non_null > 1000
        feasibility[int(year)] = {
            "rt_non_null": rt_non_null,
            "rt_total": total,
            "rt_coverage_pct": round(100 * coverage, 1),
            "insufficient_countries": n_insuff,
            "feasible": feasible,
        }
    design["year_feasibility"] = feasibility

    # Determine recommended extension window
    feasible_years = sorted([y for y, f in feasibility.items() if f["feasible"]])
    if feasible_years:
        max_feasible_year = max(feasible_years)
        # Find the last date in rt_estimates for the max feasible year
        recommended_end = f"{max_feasible_year}-12-31"
        if rt_max_date < recommended_end:
            recommended_end = rt_max_date
    else:
        recommended_end = "2020-12-31"

    design["recommended_extension_end_date"] = recommended_end
    design["recommended_extension_start_date"] = "2020-01-22"
    design["feasible_years"] = feasible_years

    # Parameter regime assessment
    design["parameter_regime_assessment"] = {
        "sigma": {
            "value": EXPECTED_SIGMA,
            "period_validity": "2020 ancestral strain evidence",
            "post_2020_concern": "Omicron and later variants have shorter incubation (3.42 d vs 5.1 d); using 2020 sigma throughout is a documented limitation",
            "recommendation": "RETAIN with explicit limitation documentation; variant-specific sigma would require additional parameter evidence",
        },
        "gamma": {
            "value": EXPECTED_GAMMA,
            "period_validity": "2020 ancestral strain evidence",
            "post_2020_concern": "Omicron viable-virus shedding 5.16 d vs ancestral 8 d; infectious period shortens",
            "recommendation": "RETAIN with explicit limitation documentation",
        },
        "mu": {
            "value": EXPECTED_MU,
            "period_validity": "2020 early China IFR estimate",
            "post_2020_concern": "IFR changed substantially with vaccination, variants, treatment improvements; 2020 IFR applied to 2021+ is a significant simplification",
            "recommendation": "RETAIN with STRONG limitation warning; IFR evolution is NOT modeled",
        },
        "alpha": {
            "values": [0.0, 0.001, 0.01, 0.05],
            "period_validity": "Sensitivity parameter, not empirically identified",
            "post_2020_concern": "Travel restrictions were implemented and lifted asymmetrically; static alpha does not capture border policy dynamics",
            "recommendation": "RETAIN as sensitivity parameter with documented limitation",
        },
        "route_network": {
            "source": "Static OpenFlights route topology",
            "post_2020_concern": "Actual flight routes changed dramatically during 2020-2022 due to border closures; static topology is a simplification for the entire period",
            "recommendation": "RETAIN with explicit caveat that network does not model border closures or route suspensions",
        },
        "beta_rt_mapping": {
            "formula": "beta(t) = Rt_estimated(t) * (gamma+mu) * N/S(t)",
            "post_2020_concern": "If Rt_estimated is computed from OWID new_cases using Cori method, it implicitly captures some intervention/vaccination/variant effects through the case curve",
            "recommendation": "RETAIN; Rt_estimated naturally absorbs some time-varying effects, but its interpretation changes with vaccination and testing capacity",
        },
    }

    # Explicit limitations for extended period
    design["extension_limitations"] = [
        "Fixed biological parameters (sigma, gamma, mu) do not reflect variant evolution (Alpha, Delta, Omicron)",
        "IFR 0.66% from early 2020 does not account for vaccination, improved treatment, or variant virulence changes",
        "Static flight route network does not model border closures, travel bans, or route suspensions",
        "Alpha remains a sensitivity parameter; static alpha does not capture time-varying border policies",
        "Vaccination is not modeled: no immunity waning, booster effects, or reduced susceptibility",
        "Reinfection is not modeled: the SEIRD R compartment is absorbing",
        "Ascertainment rate changes (testing capacity evolution) are not explicitly modeled",
        "Confirmed cases are not directly comparable to the model I compartment without an observation model",
    ]

    for year, f in sorted(feasibility.items()):
        print(f"  {year}: Rt coverage {f['rt_coverage_pct']}%, insufficient countries: {f['insufficient_countries']}, feasible: {f['feasible']}")

    print(f"\n  Recommended extension end date: {recommended_end}")
    print(f"  Feasible years: {feasible_years}")

    return design


# ???????????????????????????????????????????????????????????????????????????????
# MAIN
# ???????????????????????????????????????????????????????????????????????????????
def main():
    print("=" * 72)
    print("  PRE-EXTENSION AUDIT & TIME-WINDOW ASSESSMENT")
    print(f"  Timestamp: {datetime.now().isoformat()}")
    print("=" * 72)

    # -- PART 1 -------------------------------------------------------------
    pre_checks, pre_findings, pre_warnings = pre_extension_audit()

    # -- PART 2 -------------------------------------------------------------
    tw_audit, insufficient_by_year = time_window_audit()

    # -- PART 3 -------------------------------------------------------------
    ext_design = extension_design_assessment(tw_audit, insufficient_by_year)

    # ??? Compile JSON Report ??????????????????????????????????????????????
    section("COMPILING REPORTS")

    report_json = {
        "report_type": "pre_extension_final_audit",
        "timestamp": datetime.now().isoformat(),
        "pre_extension_status": pre_checks.get("pre_extension_status", "UNKNOWN"),
        "pre_extension_audit": pre_checks,
        "pre_extension_findings": pre_findings,
        "pre_extension_warnings": pre_warnings,
        "time_window_audit": tw_audit,
        "extension_design_assessment": ext_design,
    }

    # Save JSON
    OUT.mkdir(parents=True, exist_ok=True)
    json_path = OUT / "pre_extension_final_audit.json"
    json_path.write_text(json.dumps(report_json, indent=2, default=str), encoding="utf-8")
    print(f"  Written: {json_path}")

    # ??? Compile Markdown Report ??????????????????????????????????????????
    pre_status = pre_checks.get("pre_extension_status", "UNKNOWN")

    md_lines = []
    md_lines.append("# Pre-Extension Final Audit Report")
    md_lines.append("")
    md_lines.append(f"`PRE-EXTENSION STATUS: {pre_status}`")
    md_lines.append("")
    md_lines.append(f"**Audit timestamp**: {datetime.now().isoformat()}")
    md_lines.append("")

    # Part 1 Summary
    md_lines.append("---")
    md_lines.append("")
    md_lines.append("## Part 1: Pre-Extension Final Check")
    md_lines.append("")

    # Source integrity
    md_lines.append("### 1.1 Source File Integrity")
    md_lines.append("")
    md_lines.append("| File | SHA-256 (truncated) | Status |")
    md_lines.append("|---|---|---|")
    for fname, h in pre_checks.get("source_file_hashes", {}).items():
        status = "? Present" if h != "FILE_NOT_FOUND" else "? MISSING"
        md_lines.append(f"| `{fname}` | `{h[:24]}...` | {status} |")
    md_lines.append("")

    # Country reconciliation
    cr = pre_checks.get("country_reconciliation", {})
    md_lines.append("### 1.5 Country Universe Reconciliation")
    md_lines.append("")
    md_lines.append("| Metric | Count |")
    md_lines.append("|---|---|")
    md_lines.append(f"| OWID all locations (incl. aggregates) | {cr.get('owid_all_locations', '?')} |")
    md_lines.append(f"| OWID filtered (excl. aggregates) | {cr.get('owid_filtered_countries', '?')} |")
    md_lines.append(f"| OWID processed countries | {cr.get('owid_processed_countries', '?')} |")
    md_lines.append(f"| Route matrix countries | {cr.get('route_matrix_countries', '?')} |")
    md_lines.append(f"| Route international countries | {cr.get('route_intl_countries', '?')} |")
    md_lines.append(f"| Simulation countries (actual) | {cr.get('simulation_countries', '?')} |")
    md_lines.append(f"| Previously reported OWID countries | {cr.get('previously_reported_owid_countries', '?')} |")
    md_lines.append(f"| Previously reported connected countries | {cr.get('previously_reported_connected_countries', '?')} |")
    md_lines.append(f"| Previously reported modeled countries | {cr.get('previously_reported_modeled_countries', '?')} |")
    md_lines.append("")

    if cr.get("in_sim_not_route_matrix"):
        md_lines.append(f"**Countries in simulation but NOT in route matrix** ({len(cr['in_sim_not_route_matrix'])}): These are isolated OWID territories modeled with alpha=0.")
        md_lines.append(f"  {', '.join(cr['in_sim_not_route_matrix'][:20])}")
        md_lines.append("")

    # Simulation dates
    dv = pre_checks.get("date_verification", {})
    md_lines.append("### 1.6 Simulation Date Verification")
    md_lines.append("")
    md_lines.append(f"- Expected: {dv.get('expected_start')} to {dv.get('expected_end')} ({dv.get('expected_days')} days)")
    md_lines.append(f"- Actual: {dv.get('actual_start')} to {dv.get('actual_end')} ({dv.get('actual_days')} days)")
    md_lines.append(f"- Match: {'?' if dv.get('dates_match') else '?'}")
    md_lines.append("")

    # Scenarios
    sv = pre_checks.get("scenario_verification", {})
    md_lines.append("### 1.7 Alpha Scenario Verification")
    md_lines.append("")
    md_lines.append(f"- Expected scenarios: {sv.get('expected_scenarios')}")
    md_lines.append(f"- Actual scenarios: {sv.get('actual_scenarios')}")
    md_lines.append(f"- Match: {'?' if sv.get('scenarios_match') else '?'}")
    md_lines.append(f"- Expected alphas: {sv.get('expected_alphas')}")
    md_lines.append(f"- Actual alphas: {sv.get('actual_alphas')}")
    md_lines.append(f"- Match: {'?' if sv.get('alphas_match') else '?'}")
    md_lines.append("")

    # SEIRD Parameters
    md_lines.append("### 1.8 SEIRD Parameter Verification")
    md_lines.append("")
    md_lines.append("| Parameter | Expected | Actual | Match |")
    md_lines.append("|---|---|---|---|")
    for pname, pinfo in pre_checks.get("seird_parameters", {}).items():
        md_lines.append(f"| {pname} | {pinfo['expected']} | {pinfo['actual']} | {'?' if pinfo['match'] else '?'} |")
    md_lines.append("")

    # Seed countries
    seed = pre_checks.get("seed_verification", {})
    md_lines.append("### 1.9 Initial Seed Country Verification")
    md_lines.append("")
    md_lines.append(f"- Reported seeds ({seed.get('reported_seed_count')}): {seed.get('reported_seeds')}")
    md_lines.append(f"- Independently verified ({seed.get('independent_seed_count')}): {seed.get('independently_verified_seeds')}")
    md_lines.append(f"- Consistent: {'?' if seed.get('seeds_consistent') else '? DISCREPANCY'}")
    md_lines.append("")

    # Mechanical checks
    md_lines.append("### 1.10-1.14 Mechanical Validation Checks")
    md_lines.append("")
    md_lines.append("| Check | Result | Status |")
    md_lines.append("|---|---|---|")

    nn = pre_checks.get("nonnegative_compartments", {})
    md_lines.append(f"| Non-negative compartments | min values: {nn.get('min_values', {})} | {'PASS ?' if nn.get('pass') else 'FAIL ?'} |")

    pc = pre_checks.get("population_conservation", {})
    md_lines.append(f"| Population conservation | max error: {pc.get('max_absolute_error', '?'):.2e} | {'PASS ?' if pc.get('pass') else 'FAIL ?'} |")

    mo = pre_checks.get("monotonicity", {})
    md_lines.append(f"| Monotonic deaths | -- | {'PASS ?' if mo.get('deaths_nondecreasing') else 'FAIL ?'} |")
    md_lines.append(f"| Monotonic recoveries | -- | {'PASS ?' if mo.get('recovered_nondecreasing') else 'FAIL ?'} |")

    nsi = pre_checks.get("no_spontaneous_infection", {})
    md_lines.append(f"| No spontaneous infection (alpha=0) | max I nonseed: {nsi.get('max_I_nonseed_alpha0', '?'):.2e} | {'PASS ?' if nsi.get('pass') else 'FAIL ?'} |")

    ns = pre_checks.get("numerical_stability", {})
    md_lines.append(f"| Numerical stability | NaN: {ns.get('nan_count')}, Inf: {ns.get('inf_count')} | {'PASS ?' if ns.get('pass') else 'FAIL ?'} |")

    iso = pre_checks.get("isolated_countries", {})
    md_lines.append(f"| Isolated countries Psi=0 | {iso.get('count_in_sim')} isolated in sim | {'PASS ?' if iso.get('pass') else 'FAIL ?'} |")
    md_lines.append("")

    # Guardrails
    md_lines.append("### 1.18-1.20 Guardrail Checks")
    md_lines.append("")
    ag = pre_checks.get("alpha_guardrail", {})
    md_lines.append(f"- Alpha interpretation: `{ag.get('alpha_status')}` -- {'? Correctly marked as sensitivity-only' if ag.get('pass') else '? VIOLATION'}")
    rl = pre_checks.get("route_language_guardrail", {})
    md_lines.append(f"- Route language: {'? No passenger-volume claims' if rl.get('pass') else '? Potential violations: ' + str(rl.get('problematic_claims_found'))}")
    om = pre_checks.get("observation_model_guardrail", {})
    md_lines.append(f"- Observation model: {'? No cases=I violations' if om.get('pass') else '? VIOLATIONS FOUND'}")
    md_lines.append("")

    # Findings
    if pre_findings:
        md_lines.append("### Critical Findings")
        md_lines.append("")
        for f in pre_findings:
            md_lines.append(f"- **{f}**")
        md_lines.append("")

    if pre_warnings:
        md_lines.append("### Warnings")
        md_lines.append("")
        for w in pre_warnings:
            md_lines.append(f"- {w}")
        md_lines.append("")

    # Part 2: Time-Window Audit
    md_lines.append("---")
    md_lines.append("")
    md_lines.append("## Part 2: Time-Window Audit")
    md_lines.append("")
    md_lines.append(f"- OWID date range: {tw_audit.get('date_range', {}).get('min_date')} to {tw_audit.get('date_range', {}).get('max_date')}")
    md_lines.append(f"- Country-level locations: {tw_audit.get('country_level_locations')}")
    md_lines.append("")

    md_lines.append("### Yearly Summary")
    md_lines.append("")
    md_lines.append("| Year | Rows | Dates | Countries |")
    md_lines.append("|---|---|---|---|")
    for ys in tw_audit.get("yearly_summary", []):
        md_lines.append(f"| {ys['year']} | {ys['rows']:,} | {ys['unique_dates']} | {ys['unique_locations']} |")
    md_lines.append("")

    # Rt availability
    rt_info = tw_audit.get("rt_estimates", {})
    md_lines.append("### Rt_estimated Availability")
    md_lines.append("")
    md_lines.append(f"- Date range: {rt_info.get('date_min')} to {rt_info.get('date_max')}")
    md_lines.append(f"- Countries: {rt_info.get('countries')}")
    md_lines.append("")
    if "yearly" in rt_info:
        md_lines.append("| Year | Rows | Countries | Rt Non-Null | Rt Null |")
        md_lines.append("|---|---|---|---|---|")
        for ry in rt_info["yearly"]:
            md_lines.append(f"| {ry['year']} | {ry['rows']:,} | {ry['countries']} | {ry['rt_non_null']:,} | {ry['rt_null']:,} |")
        md_lines.append("")

    # Missingness summary for key years
    md_lines.append("### Key Variable Missingness by Year")
    md_lines.append("")
    miss_by_year = tw_audit.get("missingness_by_year", {})
    for year in sorted(miss_by_year.keys()):
        md_lines.append(f"#### {year}")
        md_lines.append("")
        md_lines.append("| Variable | Missing % |")
        md_lines.append("|---|---|")
        for var, info in miss_by_year[year].items():
            md_lines.append(f"| {var} | {info['missing_pct']}% |")
        md_lines.append("")

    # Part 3: Extension Design
    md_lines.append("---")
    md_lines.append("")
    md_lines.append("## Part 3: Extension Design Assessment")
    md_lines.append("")
    md_lines.append(f"- OWID max date: {ext_design.get('owid_max_date')}")
    md_lines.append(f"- Rt max date: {ext_design.get('rt_max_date')}")
    md_lines.append(f"- Limiting factor: {ext_design.get('limiting_factor')}")
    md_lines.append(f"- Recommended extension end: {ext_design.get('recommended_extension_end_date')}")
    md_lines.append(f"- Feasible years: {ext_design.get('feasible_years')}")
    md_lines.append("")

    md_lines.append("### Year-by-Year Feasibility")
    md_lines.append("")
    md_lines.append("| Year | Rt Coverage | Insufficient Countries | Feasible |")
    md_lines.append("|---|---|---|---|")
    for year, f in sorted(ext_design.get("year_feasibility", {}).items()):
        md_lines.append(f"| {year} | {f['rt_coverage_pct']}% | {f['insufficient_countries']} | {'?' if f['feasible'] else '?'} |")
    md_lines.append("")

    md_lines.append("### Parameter Regime Assessment for Extension")
    md_lines.append("")
    for pname, pinfo in ext_design.get("parameter_regime_assessment", {}).items():
        md_lines.append(f"**{pname}**: {pinfo.get('recommendation', 'N/A')}")
        if pinfo.get("post_2020_concern"):
            md_lines.append(f"  - Post-2020 concern: {pinfo['post_2020_concern']}")
        md_lines.append("")

    md_lines.append("### Documented Limitations for Extended Period")
    md_lines.append("")
    for lim in ext_design.get("extension_limitations", []):
        md_lines.append(f"1. {lim}")
    md_lines.append("")

    md_lines.append("---")
    md_lines.append("")
    md_lines.append(f"## Final Status: `PRE-EXTENSION STATUS: {pre_status}`")
    md_lines.append("")

    md_path = OUT / "pre_extension_final_audit.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"  Written: {md_path}")

    print(f"\n{'='*72}")
    print(f"  PRE-EXTENSION STATUS: {pre_status}")
    print(f"{'='*72}")

    return report_json


if __name__ == "__main__":
    main()
