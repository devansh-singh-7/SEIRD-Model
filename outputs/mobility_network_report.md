# Mobility Network Validation

`MOBILITY NETWORK STATUS: GO`

## Scope

This stage uses only `cleaned_airports.csv` and `cleaned_routes.csv`. It constructs a directed **route-connectivity proxy**; it does not represent passenger volume, travel volume, or observed mobility, and it is not connected to SEIRD.

## Airport processing

- Total airport records: `7,698`
- Valid airport records: `7,698`
- Invalid airport records: `0`
- Missing/unusable supplied-country records: `0`
- Invalid supplied-coordinate records: `0`
- Airport records with unusable IDs: `0`

`cleaned_airports.csv` has no IATA column. `airports_processed.csv` retains `airport_id -> iata_code -> country`, but `iata_code` is populated only where a unique three-character code is observed for that airport ID in the supplied routes. It is not an externally verified airport-master IATA value.

## Route processing and filtering

- Total route records: `67,240`
- Valid retained network records: `66,770`
- Invalid/unmapped endpoint records: `469`
- Airport self-loops removed: `1`
- Exact duplicate records excluded from the network: `0`
- Valid records whose reverse airport direction exists: `65,821`

Only unmappable endpoint IDs, endpoint IDs absent from the valid supplied airport mapping, airport self-loops, and exact duplicate source records are excluded from the validated network. Reverse-direction routes, domestic routes, codeshare records, and routes with stops are retained and labelled. Airline, codeshare, stops, and route-code quality are audited in `routes_processed.csv` rather than silently repaired.

## Country matrix and normalization

- Countries represented by valid airport records: `237`
- Countries without usable route connectivity: `12`
- Country route matrix: `4,697` nonzero directed edges; `225 x 225` country index
- Domestic route records retained in raw matrix: `32,060`
- Normalized international edges: `4,558`

`country_route_matrix.csv` retains domestic and international directed route counts. `country_route_matrix_normalized.csv` contains international edges only: each edge is divided by the sum of retained international route counts leaving its source country. A country with no international outgoing route has no invented normalized row.

## Structural validation

- required_input_files_present: `PASS`
- expected_schemas_present: `PASS`
- validated_network_has_no_unmapped_airport_ids: `PASS`
- validated_network_has_no_missing_country_mappings: `PASS`
- airport_self_loops_removed: `PASS`
- exact_duplicate_records_excluded_from_network: `PASS`
- directional_information_preserved: `PASS`
- no_self_country_route_labelled_international: `PASS`
- normalized_rows_sum_to_one_per_outgoing_country: `PASS`
- positive_network_coverage: `PASS`

## Countries without usable airport connectivity

Count: `12`. The complete supplied-label list is stored in `mobility_network_report.json`; first 30: Antarctica, British Indian Ocean Territory, Johnston Atoll, Midway Islands, Montserrat, Myanmar, Palestine, Saint Helena, Svalbard, Syria, Wake Island, West Bank

## Reproducibility

The script `mobility_network.py` produces every listed output. Input SHA-256 hashes are recorded in `mobility_network_report.json`. Source CSVs are read only.
