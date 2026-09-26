# OWID Analysis QA Report

## Decision
GO WITH INTERVENTION EXCLUDED: corrected OWID Rt and mortality components may proceed to SEIRD calibration; intervention coefficients are not calibration inputs.

This report audits the corrected OWID outputs. The original CSV was not modified, SEIRD was not run, and this QA script did not rerun modelling stages.

Checks passed: 19
Checks failed or flagged: 1

## Key findings
- **WARNING (growth):** Some first-wave log-linear fits are weak. Evidence: `{"rows_below_r2_0_5": 27, "minimum_r2": 0.0096169109161273}`
- **ERROR (intervention regression):** Validation performance is no better than a mean baseline and association is near zero. Evidence: `[{"lag_days": 7, "coefficient_delta_Rt_per_stringency_point": -6.045118025822821e-06, "n_train": 101296, "n_validation": 25298, "correlation": 0.0072788733939443, "r2": -9.629673481681422e-05}, {"lag_days": 21, "coefficient_delta_Rt_per_stringency_point": 0.0001599047156412, "n_train": 102340, "n_validation": 25567, "correlation": -0.0111651839764968, "r2": -0.0005490059087067}]`
- **WARNING (mortality):** Lagged CFR contains extreme values and incomplete predictors. Evidence: `{"rows_under_100_cases": 11, "rows_cfr_over_10_percent": 1, "high_cfr_examples": [{"country": "Yemen", "cases_lagged": 10086.0, "total_deaths": 1984.0, "lagged_case_fatality_ratio": 0.1967083085465001}], "missing_predictors": {"median_age": 0, "hospital_beds_per_thousand": 56, "human_development_index": 36, "gdp_per_capita": 31}}`

## Checks

| Check | Result | Severity | Evidence |
|---|---|---|---|
| required_output_files_present | PASS | error | `{"missing": []}` |
| processed_dates_and_duplicates | PASS | error | `{"rows": 569945, "date_min": "2020-01-01", "date_max": "2026-08-30"}` |
| processed_rows_are_sorted | PASS | error | `{"sorted": true}` |
| aggregate_regions_excluded_downstream | PASS | error | `[]` |
| non_iso_country_locations_are_explicitly_flagged | PASS | info | `[]` |
| rt_nonnegative | PASS | error | `{"negative_rows": 0}` |
| rt_no_extreme_values_over_10 | PASS | error | `{"rows_over_10": 0, "maximum": 5.944488052295346}` |
| rt_reference_agreement | PASS | warning | `{"paired_rows": 129414, "correlation": 0.592316163194605, "median_difference": 0.0025898744096884974}` |
| wave_peak_dates_exist | PASS | error | `{"missing_matches": 0}` |
| wave_peaks_not_tiny | PASS | warning | `{"rows_below_20": 0}` |
| wave_count_not_obviously_noisy | PASS | warning | `{"max_waves_per_location": 11}` |
| growth_doubling_formula | PASS | error | `{"maximum_formula_error": 1.74395609064959e-10, "invalid_rows": 0}` |
| growth_periods_nonreversed | PASS | error | `{"rows": 224}` |
| intervention_lags_7_and_21 | PASS | error | `[7, 21]` |
| intervention_metrics_finite | PASS | error | `[{"lag_days": 7, "mae": 0.0814949046498474, "rmse": 0.1905193242868447, "r2": -9.629673481681422e-05}, {"lag_days": 21, "mae": 0.0836217225964679, "rmse": 0.1936891659907467, "r2": -0.0005490059087067}]` |
| intervention_model_is_calibration_ready | FAIL | error | `[{"lag_days": 7, "correlation": 0.0072788733939443, "r2": -9.629673481681422e-05}, {"lag_days": 21, "correlation": -0.0111651839764968, "r2": -0.0005490059087067}]` |
| mortality_definition_explicit | PASS | error | `{"definitions": ["observed cumulative deaths on 2021-12-31 / observed cumulative cases 14 days earlier"]}` |
| mortality_missingness_reported | PASS | info | `{"median_age": 0, "hospital_beds_per_thousand": 56, "human_development_index": 36, "gdp_per_capita": 31}` |
| mortality_lag_sensitivity_present | PASS | info | `{"columns": ["country", "total_cases", "total_deaths", "median_age", "hospital_beds_per_thousand", "human_development_index", "gdp_per_capita", "population", "cases_lagged", "lagged_case_fatality_ratio", "cases_lagged_7d", "cfr_lag_7d", "cases_lagged_21d", "cfr_lag_21d", "mortality_model_eligible_min_cases", "mortality_model_eligible", "outcome_definition", "sensitivity_definition", "status"]}` |
| mortality_nonnegative | PASS | error | `{"rows": 221}` |

## Plots

- `outputs\qa_plots\united_states_waves.png`
- `outputs\qa_plots\india_waves.png`
- `outputs\qa_plots\new_zealand_waves.png`
- `outputs\qa_plots\nicaragua_waves.png`
- `outputs\qa_plots\peru_waves.png`

## Recommendations

- Do not use current intervention coefficients in SEIRD; refit after stabilizing Rt with justified country/time controls and uncertainty.
- Retain as labelled lagged reported CFR, but add minimum-case and alternative-lag sensitivity before using mortality parameters in SEIRD.
