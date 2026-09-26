"""Read-only QA for existing OWID analysis outputs."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUTPUT_DIR = Path("outputs")
QA_DIR = OUTPUT_DIR / "qa_plots"
AGGREGATES = {
    "World", "Africa", "Asia", "Europe", "Oceania", "North America", "South America",
    "European Union", "High-income countries", "Upper-middle-income countries",
    "Lower-middle-income countries", "Low-income countries", "International",
}
REPRESENTATIVE_COUNTRIES = ["United States", "India", "New Zealand", "Nicaragua", "Peru"]
REQUIRED = [
    "owid_covid_processed.csv", "epidemic_waves.csv", "growth_rates.csv",
    "rt_estimates.csv", "intervention_analysis.csv", "mortality_model_data.csv",
    "mortality_model_results.csv", "pipeline_report.json",
]


def finite(value: object) -> bool:
    return bool(pd.notna(value) and np.isfinite(float(value)))


def check(checks: list[dict], name: str, passed: bool, evidence: object, severity: str = "error") -> None:
    checks.append({"check": name, "passed": bool(passed), "severity": severity, "evidence": evidence})


def plot_country(country: str, processed: pd.DataFrame, waves: pd.DataFrame) -> str:
    data = processed[processed.country == country].sort_values("date")
    detected = waves[waves.country == country].sort_values("peak_date")
    if data.empty:
        return ""
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.plot(data.date, data.new_cases_smoothed, color="#1f4e79", linewidth=1.2, label="OWID new_cases_smoothed")
    if not detected.empty:
        peak_data = data[data.date.isin(detected.peak_date)]
        ax.scatter(peak_data.date, peak_data.new_cases_smoothed, color="#c0392b", s=28, zorder=3, label="Detected peaks")
        for date in detected.peak_date:
            ax.axvline(date, color="#c0392b", alpha=0.12, linewidth=0.8)
    ax.set_title(f"{country}: 7-day-smoothed cases and detected peaks")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cases per day, 7-day smoothed")
    ax.grid(alpha=0.2)
    ax.legend(loc="upper left")
    fig.tight_layout()
    filename = country.lower().replace(" ", "_").replace("-", "_") + "_waves.png"
    path = QA_DIR / filename
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return str(path)


def main() -> None:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    missing_files = [name for name in REQUIRED if not (OUTPUT_DIR / name).exists()]
    if missing_files:
        raise FileNotFoundError(missing_files)
    processed = pd.read_csv(OUTPUT_DIR / "owid_covid_processed.csv", parse_dates=["date"])
    waves = pd.read_csv(OUTPUT_DIR / "epidemic_waves.csv", parse_dates=["peak_date", "start_date", "end_date"])
    growth = pd.read_csv(OUTPUT_DIR / "growth_rates.csv", parse_dates=["growth_start_date", "growth_end_date"])
    rt = pd.read_csv(OUTPUT_DIR / "rt_estimates.csv", parse_dates=["date"])
    intervention = pd.read_csv(OUTPUT_DIR / "intervention_analysis.csv", parse_dates=["train_end_date"])
    mortality = pd.read_csv(OUTPUT_DIR / "mortality_model_data.csv")
    mortality_results = pd.read_csv(OUTPUT_DIR / "mortality_model_results.csv")
    pipeline_report = json.loads((OUTPUT_DIR / "pipeline_report.json").read_text(encoding="utf-8"))
    checks: list[dict] = []
    findings: list[dict] = []
    recommendations: list[str] = []

    sorted_ok = processed.equals(processed.sort_values(["country", "date"]).reset_index(drop=True))
    check(checks, "required_output_files_present", not missing_files, {"missing": missing_files})
    check(checks, "processed_dates_and_duplicates", processed.date.notna().all() and not processed.duplicated(["country", "date"]).any(), {"rows": len(processed), "date_min": str(processed.date.min().date()), "date_max": str(processed.date.max().date())})
    check(checks, "processed_rows_are_sorted", sorted_ok, {"sorted": sorted_ok})

    downstream_countries = set(rt.country) | set(waves.country) | set(growth.country) | set(mortality.country)
    aggregate_downstream = sorted(downstream_countries & AGGREGATES)
    non_iso_country_locations = processed.loc[~processed["code"].fillna("").str.fullmatch(r"[A-Z]{3}"), ["country", "code"]].drop_duplicates().to_dict("records")
    check(checks, "aggregate_regions_excluded_downstream", not aggregate_downstream, aggregate_downstream)
    check(checks, "non_iso_country_locations_are_explicitly_flagged", True, non_iso_country_locations, "info")
    if aggregate_downstream:
        findings.append({"severity": "error", "stage": "country filtering", "problem": "Aggregate regions are present in country-level outputs despite the is_country field.", "evidence": aggregate_downstream, "impact": "Country-level waves, Rt, growth, and calibration are contaminated."})
        recommendations.append("Rebuild the country universe using explicit aggregate exclusion and verified country-code/continent logic, then regenerate downstream outputs.")

    rt_valid = rt[rt.Rt_estimated.notna()]
    paired = rt.dropna(subset=["Rt_estimated", "reproduction_rate_owid_reference"])
    rt_high = rt_valid[rt_valid.Rt_estimated > 10]
    rt_negative = rt_valid[rt_valid.Rt_estimated < 0]
    corr = float(paired.Rt_estimated.corr(paired.reproduction_rate_owid_reference)) if len(paired) > 1 else np.nan
    check(checks, "rt_nonnegative", len(rt_negative) == 0, {"negative_rows": len(rt_negative)})
    check(checks, "rt_no_extreme_values_over_10", len(rt_high) == 0, {"rows_over_10": len(rt_high), "maximum": float(rt_valid.Rt_estimated.max())})
    median_difference = float((paired["Rt_estimated"] - paired["reproduction_rate_owid_reference"]).median()) if len(paired) else np.nan
    check(checks, "rt_reference_agreement", finite(corr) and corr >= 0.2, {"paired_rows": len(paired), "correlation": corr, "median_difference": median_difference}, "warning")
    if len(rt_high):
        findings.append({"severity": "error", "stage": "Rt", "problem": "Extreme Rt estimates occur repeatedly.", "evidence": {"rows_over_10": len(rt_high), "maximum": float(rt_valid.Rt_estimated.max()), "top_rows": rt_valid.nlargest(10, "Rt_estimated")[["country", "date", "Rt_estimated"]].to_dict("records")}, "impact": "Intervention regression and beta calibration are unstable."})
        recommendations.append("Re-estimate Rt with a defensible low-incidence/renewal-denominator rule or Bayesian Cori implementation before beta calibration.")
    if finite(corr) and corr < 0.2:
        findings.append({"severity": "error", "stage": "Rt comparison", "problem": "Estimated Rt has near-zero or negative agreement with OWID reproduction_rate where paired.", "evidence": {"paired_rows": len(paired), "correlation": corr}, "impact": "The discrepancy requires method/data investigation before calibration."})

    wave_small = waves[waves.peak_magnitude_cases_7d_smoothed < 20]
    wave_aggregates = sorted(set(waves.country) & AGGREGATES)
    peak_lookup = processed[["country", "date", "new_cases_smoothed"]].rename(columns={"date": "peak_date", "new_cases_smoothed": "observed_peak_value"})
    wave_check = waves.merge(peak_lookup, on=["country", "peak_date"], how="left")
    check(checks, "wave_peak_dates_exist", wave_check.observed_peak_value.notna().all(), {"missing_matches": int(wave_check.observed_peak_value.isna().sum())})
    check(checks, "wave_peaks_not_tiny", len(wave_small) == 0, {"rows_below_20": len(wave_small)}, "warning")
    check(checks, "wave_count_not_obviously_noisy", int(waves.groupby("country").size().max()) <= 12, {"max_waves_per_location": int(waves.groupby("country").size().max())}, "warning")
    if len(wave_small) or wave_aggregates:
        findings.append({"severity": "warning", "stage": "wave detection", "problem": "Tiny peaks and/or aggregate locations are included.", "evidence": {"small_peak_rows": len(wave_small), "small_peak_examples": wave_small.nsmallest(10, "peak_magnitude_cases_7d_smoothed")[["country", "peak_date", "peak_magnitude_cases_7d_smoothed"]].to_dict("records"), "aggregate_locations": wave_aggregates}, "impact": "The fixed absolute threshold does not establish comparable meaningful waves across locations."})
        recommendations.append("Repeat wave detection after removing aggregates and add a documented country-scale minimum/prominence sensitivity rule.")
    plot_paths = [plot_country(country, processed, waves) for country in REPRESENTATIVE_COUNTRIES if country in set(processed.country)]

    formula_error = (growth.doubling_time_days - np.log(2) / growth.growth_rate_r_per_day).abs()
    invalid_doubling = growth[(growth.growth_rate_r_per_day <= 0) & growth.doubling_time_days.notna()]
    check(checks, "growth_doubling_formula", bool((formula_error < 1e-8).all()) and len(invalid_doubling) == 0, {"maximum_formula_error": float(formula_error.max()), "invalid_rows": len(invalid_doubling)})
    check(checks, "growth_periods_nonreversed", bool((growth.growth_end_date >= growth.growth_start_date).all()), {"rows": len(growth)})
    weak_growth = int((growth.r_squared < 0.5).sum())
    if weak_growth:
        findings.append({"severity": "warning", "stage": "growth", "problem": "Some first-wave log-linear fits are weak.", "evidence": {"rows_below_r2_0_5": weak_growth, "minimum_r2": float(growth.r_squared.min())}, "impact": "Those growth estimates require country-level review."})

    check(checks, "intervention_lags_7_and_21", set(intervention.lag_days) == {7, 21}, intervention.lag_days.tolist())
    check(checks, "intervention_metrics_finite", bool(np.isfinite(intervention[["mae", "rmse", "r2"]].to_numpy()).all()), intervention[["lag_days", "mae", "rmse", "r2"]].to_dict("records"))
    if (intervention.r2 < 0).any() or intervention.correlation.abs().max() < 0.1:
        check(checks, "intervention_model_is_calibration_ready", False, intervention[["lag_days", "correlation", "r2"]].to_dict("records"), "error")
        findings.append({"severity": "error", "stage": "intervention regression", "problem": "Validation performance is no better than a mean baseline and association is near zero.", "evidence": intervention[["lag_days", "coefficient_delta_Rt_per_stringency_point", "n_train", "n_validation", "correlation", "r2"]].to_dict("records"), "impact": "Coefficients are not suitable intervention-effect parameters and are not causal evidence."})
        recommendations.append("Do not use current intervention coefficients in SEIRD; refit after stabilizing Rt with justified country/time controls and uncertainty." )

    predictors = ["median_age", "hospital_beds_per_thousand", "human_development_index", "gdp_per_capita"]
    missing_predictors = {column: int(mortality[column].isna().sum()) for column in predictors}
    small_case = mortality[mortality.cases_lagged < 100]
    high_cfr = mortality[mortality.lagged_case_fatality_ratio > 0.10]
    definition_ok = mortality.outcome_definition.astype(str).str.contains("deaths.*2021-12-31.*cases.*14 days", regex=True).all()
    check(checks, "mortality_definition_explicit", bool(definition_ok), {"definitions": mortality.outcome_definition.unique().tolist()})
    check(checks, "mortality_missingness_reported", True, missing_predictors, "info")
    check(checks, "mortality_lag_sensitivity_present", {"cfr_lag_7d", "cfr_lag_21d", "mortality_model_eligible"}.issubset(mortality.columns), {"columns": mortality.columns.tolist()}, "info")
    check(checks, "mortality_nonnegative", bool((mortality.lagged_case_fatality_ratio >= 0).all()), {"rows": len(mortality)})
    if len(small_case) or len(high_cfr):
        findings.append({"severity": "warning", "stage": "mortality", "problem": "Lagged CFR contains extreme values and incomplete predictors.", "evidence": {"rows_under_100_cases": len(small_case), "rows_cfr_over_10_percent": len(high_cfr), "high_cfr_examples": high_cfr.nlargest(10, "lagged_case_fatality_ratio")[["country", "cases_lagged", "total_deaths", "lagged_case_fatality_ratio"]].to_dict("records"), "missing_predictors": missing_predictors}, "impact": "These are reported surveillance CFR-like outcomes, not uniformly comparable infection-fatality estimates."})
        recommendations.append("Retain as labelled lagged reported CFR, but add minimum-case and alternative-lag sensitivity before using mortality parameters in SEIRD.")

    failed_errors = [item for item in checks if not item["passed"] and item["severity"] == "error"]
    intervention_only_failure = bool(failed_errors) and all(item["check"] == "intervention_model_is_calibration_ready" for item in failed_errors)
    if intervention_only_failure:
        decision = "GO WITH INTERVENTION EXCLUDED: corrected OWID Rt and mortality components may proceed to SEIRD calibration; intervention coefficients are not calibration inputs."
    elif failed_errors:
        decision = "NO-GO: do not freeze these outputs as the approved OWID layer or use them to calibrate SEIRD yet."
    else:
        decision = "GO: corrected OWID layer is sufficiently reliable for the next approved calibration stage, subject to documented limitations."
    report = {
        "status": "QA generated after corrected OWID outputs; QA did not rerun modelling stages",
        "source_files": REQUIRED,
        "input_pipeline_report_status": pipeline_report.get("status"),
        "file_shapes": {"processed": list(processed.shape), "waves": list(waves.shape), "growth": list(growth.shape), "rt": list(rt.shape), "intervention": list(intervention.shape), "mortality": list(mortality.shape), "mortality_results": list(mortality_results.shape)},
        "rt_summary": {"valid_estimates": len(rt_valid), "missing_estimates": int(rt.Rt_estimated.isna().sum()), "paired_reference_rows": len(paired), "paired_correlation": corr, "median_difference": median_difference, "zero_estimates": int((rt_valid.Rt_estimated == 0).sum()), "over_10_rows": len(rt_high), "quality_flags": {str(k): int(v) for k, v in rt.rt_quality_flag.value_counts(dropna=False).items()}},
        "wave_summary": {"rows": len(waves), "countries": int(waves.country.nunique()), "small_peak_rows_below_20": len(wave_small), "aggregate_locations": wave_aggregates},
        "mortality_summary": {"rows": len(mortality), "complete_predictor_rows": int(mortality.dropna(subset=predictors + ["lagged_case_fatality_ratio"]).shape[0]), "regression_eligible_rows": int(mortality.mortality_model_eligible.sum()), "missing_predictors": missing_predictors, "rows_under_100_lagged_cases": len(small_case), "rows_cfr_over_10_percent": len(high_cfr)},
        "before_after": {
            "country_level_locations": {"before_previous_qa": 247, "after": int(processed.country.nunique()), "note": "after retains only is_country=True rows with verified three-letter codes; aggregates and uncertain OWID-coded locations are excluded without guessed mappings"},
            "rt_values_over_10": {"before_previous_qa": 4037, "after": int(len(rt_high))},
            "rt_maximum": {"before_previous_qa": 159.9571510341782, "after": float(rt_valid.Rt_estimated.max())},
            "rt_reference_correlation": {"before_previous_qa": -0.021424632599365244, "after": corr},
            "wave_rows": {"before_previous_qa": 1184, "after": int(len(waves))},
        },
        "root_causes_and_corrections": [
            {"problem": "OWID aggregate rows used is_country=True with non-country OWID codes", "root_cause": "is_country alone does not distinguish aggregate OWID locations", "correction": "Require country metadata, continent presence, non-null code, and explicitly exclude OWID_EU27"},
            {"problem": "Extreme Rt ratios", "root_cause": "prior renewal denominator and reporting-spike/low-baseline periods made ratios unstable", "correction": "Use prior incidence only; withhold estimates below 20 smoothed denominator cases or above a 5x current/prior-seven-day-median continuity ratio"},
            {"problem": "Tiny waves", "root_cause": "permissive absolute threshold", "correction": "Use 28-day separation, 20% relative prominence, 5% relative height, and minimum 20 smoothed cases; sensitivity counts are in pipeline_report.json"},
        ],
        "checks": checks, "findings": findings, "recommendations": recommendations, "plots_generated": plot_paths, "decision": decision,
        "classification_note": "QA generated no new model estimates; observed, calculated, estimated, and simulated categories remain distinct.",
    }
    (OUTPUT_DIR / "owid_qa_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    lines = ["# OWID Analysis QA Report", "", "## Decision", decision, "", "This report audits the corrected OWID outputs. The original CSV was not modified, SEIRD was not run, and this QA script did not rerun modelling stages.", "", f"Checks passed: {sum(item['passed'] for item in checks)}", f"Checks failed or flagged: {sum(not item['passed'] for item in checks)}", "", "## Key findings"]
    lines += [f"- **{item['severity'].upper()} ({item['stage']}):** {item['problem']} Evidence: `{json.dumps(item['evidence'], default=str)}`" for item in findings] or ["- None."]
    lines += ["", "## Checks", "", "| Check | Result | Severity | Evidence |", "|---|---|---|---|"]
    lines += [f"| {item['check']} | {'PASS' if item['passed'] else 'FAIL'} | {item['severity']} | `{json.dumps(item['evidence'], default=str)}` |" for item in checks]
    lines += ["", "## Plots", ""] + [f"- `{path}`" for path in plot_paths] + ["", "## Recommendations", ""] + [f"- {item}" for item in recommendations]
    (OUTPUT_DIR / "owid_qa_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"decision": decision, "checks": len(checks), "passed": sum(item['passed'] for item in checks), "failed_or_flagged": sum(not item['passed'] for item in checks), "plots": plot_paths}, indent=2))


if __name__ == "__main__":
    main()
