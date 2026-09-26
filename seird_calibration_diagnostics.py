"""Reproducible diagnostic report for the United Kingdom SEIRD calibration gate.

This script is deliberately read-only with respect to raw OWID data.  It uses
the single-country artefacts produced by ``seird_single_country.py`` and writes
only the three calibration-diagnostic deliverables in ``outputs``.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


OUTPUT = Path("outputs")
COUNTRY = "United Kingdom"


def score(observed: pd.Series, simulated: pd.Series) -> dict[str, float | int | None]:
    pair = pd.concat([observed, simulated], axis=1).dropna()
    if pair.empty:
        return {"n": 0, "mae": None, "rmse": None, "correlation": None}
    residual = pair.iloc[:, 0] - pair.iloc[:, 1]
    return {
        "n": int(len(pair)),
        "mae": float(np.abs(residual).mean()),
        "rmse": float(np.sqrt(np.mean(np.square(residual)))),
        "correlation": float(pair.iloc[:, 0].corr(pair.iloc[:, 1])) if len(pair) > 1 else None,
    }


def lag_scan(observed: pd.Series, simulated: pd.Series, maximum_days: int = 30) -> list[dict[str, float | int | None]]:
    """Correlation-only scan; it does not alter the selected death comparison."""
    records: list[dict[str, float | int | None]] = []
    for lag in range(-maximum_days, maximum_days + 1):
        # Positive lag means compare observed deaths on t with simulation on t-lag.
        value = score(observed.reset_index(drop=True), simulated.reset_index(drop=True).shift(lag))
        records.append({"lag_days_simulation_relative_to_observation": lag, **value})
    return records


def compact(value: float | int | None) -> str:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return "not available"
    if isinstance(value, int):
        return str(value)
    return f"{value:,.3f}"


def main() -> None:
    simulation = pd.read_csv(OUTPUT / "seird_single_country_simulation.csv", parse_dates=["date"])
    validation = pd.read_csv(OUTPUT / "seird_single_country_validation.csv")
    parameters = pd.read_csv(OUTPUT / "seird_single_country_parameters.csv").iloc[0]
    sensitivity = pd.read_csv(OUTPUT / "seird_single_country_sensitivity.csv")
    report = json.loads((OUTPUT / "seird_single_country_report.json").read_text(encoding="utf-8"))

    if set(simulation["phase"].dropna()) != {"calibration", "validation"}:
        raise ValueError("Expected calibration and validation phases in the simulation output")
    if parameters["country"] != COUNTRY:
        raise ValueError("This diagnostic is scoped to the United Kingdom artefacts")

    calibration = simulation[simulation["phase"] == "calibration"].copy()
    held_out = simulation[simulation["phase"] == "validation"].copy()
    removal_rate = float(parameters["gamma"]) + float(parameters["mu"])
    fixed_beta = float(parameters["beta_calibration_median"])
    beta_identity_error = np.abs(
        calibration["beta"] - calibration["Rt_estimated"] * removal_rate
    )
    rt_missing_by_phase = {
        "calibration": int(calibration["Rt_estimated"].isna().sum()),
        "validation": int(held_out["Rt_estimated"].isna().sum()),
    }
    daily_death_same_day = score(held_out["observed_deaths_smoothed"], held_out["new_deaths_simulated"])
    cumulative_death_score = score(held_out["observed_deaths_smoothed"].cumsum(), held_out["D_simulated"] - held_out["D_simulated"].iloc[0])
    death_lags = lag_scan(held_out["observed_deaths_smoothed"], held_out["new_deaths_simulated"])
    best_lag = max(death_lags, key=lambda record: -np.inf if record["correlation"] is None else record["correlation"])

    initial = report["initial_conditions"]
    initial_accounted = sum(float(initial[key]) for key in ("E0", "I0", "R0", "D0"))
    initial_confirmed = float(initial["S0"]) + initial_accounted
    # The initialization algebra makes N - S0 equal the reported cumulative cases.
    confirmed_history = float(parameters["population"]) - float(initial["S0"])

    validation_row = validation.loc[validation["phase"] == "validation"].iloc[0]
    comparison = pd.DataFrame([
        {
            "strategy": "A_fixed_beta_replay",
            "status": "diagnostic_only_not_accepted_as_forecast",
            "calibration_transmission_input": "date-specific Rt_estimated*(gamma+mu) during calibration; no fitted free parameter",
            "validation_transmission_input": "median calibration beta held fixed",
            "observation_mapping": "direct reported 7-day-smoothed cases/deaths versus simulated incidence/death flow (known mismatch)",
            "calibration_period": f"{parameters['calibration_start']} to {parameters['calibration_end']}",
            "validation_period": f"{parameters['validation_start']} to {parameters['validation_end']}",
            "case_rmse": validation_row["cases_rmse"],
            "death_rmse": validation_row["deaths_rmse"],
            "case_correlation": validation_row["cases_correlation"],
            "death_correlation": validation_row["deaths_correlation"],
            "peak_date_error_days": validation_row["peak_date_error_days"],
            "peak_size_error_cases": validation_row["peak_size_error"],
            "selection": "retain only as mechanistic replay/diagnostic baseline",
        },
        {
            "strategy": "B_formal_parameter_fit",
            "status": "not_estimable_under_current_approved_observation_model",
            "calibration_transmission_input": "would fit only an explicitly allowed beta parameter or low-dimensional beta multiplier on calibration dates",
            "validation_transmission_input": "would be frozen before validation",
            "observation_mapping": "requires explicit confirmed-case ascertainment/reporting-delay mapping; none is specified or identifiable from the approved inputs",
            "calibration_period": f"{parameters['calibration_start']} to {parameters['calibration_end']}",
            "validation_period": f"{parameters['validation_start']} to {parameters['validation_end']}",
            "case_rmse": np.nan,
            "death_rmse": np.nan,
            "case_correlation": np.nan,
            "death_correlation": np.nan,
            "peak_date_error_days": np.nan,
            "peak_size_error_cases": np.nan,
            "selection": "do not run or select until observation model and permissible fitted parameter set are documented",
        },
    ])
    comparison.to_csv(OUTPUT / "seird_calibration_comparison.csv", index=False)

    diagnostics = {
        "status": "CALIBRATION METHOD: REQUIRES REVISION",
        "scope": {
            "country": COUNTRY,
            "raw_owid_modified": False,
            "excluded": ["airport routes", "OpenFlights", "mobility data", "VIW_FNT", "intervention coefficients", "external datasets"],
        },
        "chronological_design": {
            "calibration_start": str(parameters["calibration_start"]),
            "calibration_end": str(parameters["calibration_end"]),
            "validation_start": str(parameters["validation_start"]),
            "validation_end": str(parameters["validation_end"]),
            "calibration_rows": int(len(calibration)),
            "validation_rows": int(len(held_out)),
            "validation_beta_future_information_used": False,
            "note": "Rt-derived beta was contemporaneous in calibration; the held-out period used only the calibration median beta. The Rt estimator uses incidence on t and prior incidence, so it is retrospective/nowcast input rather than an independently available future forecast covariate.",
        },
        "initial_conditions_and_population": {
            "population_definition": "OWID United Kingdom population, 68,179,315 people; compartments are absolute people and conserve this total.",
            "initial_conditions": {key: float(initial[key]) for key in ("S0", "E0", "I0", "R0", "D0")},
            "non_susceptible_initial_total": initial_accounted,
            "reported_cumulative_cases_implicit_in_initialisation": confirmed_history,
            "finding": "The initialization equates the non-susceptible history to reported cumulative cases. This is internally population-conserving, but it treats reported confirmed infections as the total infection history and therefore inherits under-ascertainment. It is not a defensible estimate of true S/E/I/R/D without a reporting model.",
        },
        "beta_construction": {
            "implemented_equations": "dI/dt=sigma*E-(gamma+mu)*I; dR/dt=gamma*I; dD/dt=mu*I",
            "implemented_formula": "beta(t)=Rt_estimated(t)*(gamma+mu)",
            "removal_rate_per_day": removal_rate,
            "calibration_identity_max_abs_error": float(beta_identity_error.max()),
            "fixed_validation_beta_per_day": fixed_beta,
            "fixed_validation_beta_over_removal_rate": fixed_beta / removal_rate,
            "calibration_beta_range_per_day": {"min": float(calibration["beta"].min()), "median": float(calibration["beta"].median()), "max": float(calibration["beta"].max())},
            "validation_observed_Rt_for_audit_only": {"min": float(held_out["Rt_estimated"].min()), "median": float(held_out["Rt_estimated"].median()), "max": float(held_out["Rt_estimated"].max())},
            "finding": "The numeric identity is exact for the beta values recorded in calibration. However, a renewal-ratio Rt estimated from incidence is an effective reproduction number. For these equations Reff(t)=beta(t)*S(t)/[N*(gamma+mu)], so beta=Rt*(gamma+mu) is exact only when Rt is defined for a fully susceptible population (or S/N is approximately one). An effective Rt input requires beta(t)=Rt(t)*(gamma+mu)*N/S(t), with an explicit decision about how susceptibility, vaccination, reinfection, and reporting are represented.",
            "date_alignment_finding": "The ODE step ending on date t uses betas[t-1], while new_infections_simulated and the beta column on date t use betas[t]. Thus the stored daily flow is not the integrated flow for the state transition that produced that date's state. This one-day alignment issue must be corrected before a calibrated fit is accepted.",
        },
        "Rt_smoothing_availability_and_leakage": {
            "estimator_input": "OWID new_cases_smoothed, used as current incidence at t and prior incidence in a Cori renewal ratio with a discretised gamma serial interval (mean 5 days, SD 2 days).",
            "missing_Rt_estimated_in_selected_period": rt_missing_by_phase,
            "missing_data_handling": "No Rt values were imputed; the selected run would have stopped if any selected-period Rt_estimated value were unavailable.",
            "future_information_check": "The renewal-ratio code uses incidence at t and earlier dates only. It therefore does not index an Rt value dated after the transition it informs. However, temporal causality of the upstream supplied 7-day-smoothed field itself must be documented (trailing versus centred smoothing) before describing the resulting Rt as a real-time input.",
            "finding": "Smoothing reduces reporting noise but can dampen peaks and delay changes. Combining a contemporaneous, smoothed Rt-derived beta in calibration with observed cases as the score target is a retrospective replay design, not an out-of-sample transmission forecast.",
        },
        "magnitude_mismatch": {
            "validation_case_rmse": float(validation_row["cases_rmse"]),
            "validation_case_correlation": float(validation_row["cases_correlation"]),
            "validation_peak_date_error_days": float(validation_row["peak_date_error_days"]),
            "validation_peak_size_error_cases": float(validation_row["peak_size_error"]),
            "finding": "The zero-day peak-date error is not evidence of quantitative agreement: both validation maxima occur at the right boundary (2021-12-31), while simulated peak incidence is 646.99 versus 166,404.14 observed. Holding beta at its calibration median removes the large time variation seen in Rt, and the direct infection-to-confirmed-case comparison supplies no ascertainment scale or reporting delay.",
        },
        "observation_model": {
            "current_comparison": "simulated new infections versus OWID new_cases_smoothed",
            "verdict": "not mathematically direct",
            "required_case_mapping": "Observed confirmed cases at date t should be modelled as an observation process, e.g. reported_cases(t) approximately ascertainment(t) times delayed simulated incident infections, with a documented reporting-delay distribution and any smoothing applied consistently.",
            "available_data_decision": "The supplied data contain reported cases and testing fields but no validated, country-date ascertainment probability or reporting-delay distribution. A free reporting factor would be an additional empirical nuisance parameter, not an observed fact; it cannot be silently assumed. Consequently direct case fitting is not currently an admissible epidemiological calibration.",
        },
        "deaths": {
            "implemented_mortality_interpretation": "mu is the I-to-D competing hazard and IFR=mu/(gamma+mu); model daily deaths are mu*I and cumulative deaths are D.",
            "appropriate_primary_comparison": "daily observed deaths (with the same 7-day smoothing only if it is also applied to simulated daily death flow) versus same-date simulated daily I-to-D flow, after any explicit death-reporting delay is specified. Cumulative deaths may be supplementary but are not a replacement for daily trajectory validation.",
            "same_day_daily_metrics": daily_death_same_day,
            "cumulative_death_metrics_supplementary_only": cumulative_death_score,
            "best_correlation_in_plus_minus_30_day_lag_scan_diagnostic_only": best_lag,
            "finding": "No unmodelled lag was adopted to improve the score. The SEIRD E-to-I-to-D progression already creates biological timing; a reporting lag would require evidence and an observation model. The low daily-death correlation is robust evidence that current mortality timing/scale and the reported-death observation process are not represented adequately.",
        },
        "calibration_strategy": {
            "A_fixed_beta_replay": "Retain only as a reproducible mechanistic replay/diagnostic baseline, not a successful forecast.",
            "B_formal_fit": "The project plan calls for transmission rates fitted from historical case curves, so a formal, restricted fit is justified in principle. It must first define an observation model and correct beta/date alignment. Then fit only the project-allowed transmission quantity (for example a low-dimensional beta multiplier) using calibration dates only; keep sigma, gamma, and mu sourced rather than freely fitting all parameters; freeze the result for validation.",
            "current_decision": "Strategy B metrics are deliberately unavailable rather than fabricated because no approved observation model makes reported cases a direct target for infections. Validation observations must not be used to resolve this.",
        },
        "sensitivity_analysis": sensitivity.to_dict(orient="records"),
        "sensitivity_finding": "All three evidence-based scenarios retain very large validation case RMSEs (52,045.87 to 54,653.11) and death RMSEs (129.02 to 137.73) under the same invalid direct observation comparison and fixed-beta validation design. The mismatch is therefore robust to the supplied parameter scenarios; these results do not justify changing mortality or duration parameters to improve fit.",
        "required_before_expansion": [
            "Correct the beta/state/date alignment and state whether Rt is effective or fully susceptible.",
            "Approve and document a case and death observation model, including whether/why ascertainment and reporting delays can be estimated from available data.",
            "Define the small, project-allowed fitted parameter set and objective before fitting; do not fit all epidemiological rates independently.",
            "Fit calibration dates only, freeze parameters, and re-evaluate the unchanged chronological validation period with daily and supplementary cumulative death metrics.",
            "Do not expand to all countries or run the airport/mobility component until this gate passes.",
        ],
    }
    (OUTPUT / "seird_calibration_diagnostics.json").write_text(json.dumps(diagnostics, indent=2, allow_nan=False), encoding="utf-8")

    sensitivity_lines = [
        "| Scenario | Case RMSE | Death RMSE |",
        "|---|---:|---:|",
    ]
    for row in sensitivity.itertuples(index=False):
        sensitivity_lines.append(f"| {row.scenario} | {row.validation_cases_rmse:,.2f} | {row.validation_deaths_rmse:,.2f} |")
    md = [
        "# SEIRD Calibration Diagnostics",
        "",
        "## Decision",
        "",
        "`CALIBRATION METHOD: REQUIRES REVISION`",
        "",
        "The existing fixed-beta run is reproducible and its mathematical solver checks pass, but it is a mechanistic replay/diagnostic baseline only. It is not a successful forecast and must not be expanded to all countries.",
        "",
        "## Scope and chronology",
        "",
        f"United Kingdom; calibration `{parameters['calibration_start']}` to `{parameters['calibration_end']}` ({len(calibration)} days); validation `{parameters['validation_start']}` to `{parameters['validation_end']}` ({len(held_out)} days). The validation beta is the calibration median `{fixed_beta:.6f}` per day, so it does not use validation-period Rt. Calibration Rt is contemporaneous/retrospective because its renewal estimate uses incidence at t and prior incidence; it is not a prospective forecast input.",
        "",
        "## Why timing can look plausible while magnitude fails",
        "",
        f"Validation maxima both fall on the endpoint, 2021-12-31, giving a 0-day peak-date error. That is not agreement: observed peak incidence is {validation_row['observed_peak_magnitude']:,.2f}, simulated peak incidence is {validation_row['simulated_peak_magnitude']:,.2f}, and the peak-size error is {validation_row['peak_size_error']:,.2f}. Case RMSE is {validation_row['cases_rmse']:,.2f}; correlation is {validation_row['cases_correlation']:.3f}.",
        "",
        "The calibration-period beta varies with Rt, but validation freezes it at an R-equivalent `beta/(gamma+mu)` of " + f"{fixed_beta / removal_rate:.3f}. It therefore cannot represent the marked validation-period change in the audited Rt series. More fundamentally, initialization makes all historical confirmed cases the simulated non-susceptible history (N−S0 = {confirmed_history:,.0f}); confirmed cases are not total infections. Neither the initial state nor the comparison has an ascertainment factor or reporting-delay model.",
        "",
        "## Beta verification",
        "",
        "For the implemented equations, removal from I is `(gamma + mu) I`, so the recorded calibration beta exactly satisfies `beta = Rt_estimated * (gamma + mu)` (maximum numerical difference " + f"{beta_identity_error.max():.3g}`). This maps `Rt` to beta only if Rt is interpreted at full susceptibility. The renewal-ratio Rt derived from incidence is normally effective Rt; under the exact ODE, `Reff = beta*S/[N*(gamma+mu)]`. An effective Rt input requires `beta = Rt*(gamma+mu)*N/S`, plus an explicit treatment of depletion, vaccination, reinfection, and reporting.",
        "",
        "There is also a date-alignment defect: the state on date t is advanced with the previous row's beta, while that row's reported infection flow is calculated with beta(t). This must be aligned before using a fitted objective.",
        "",
        "## Rt smoothing, availability, and temporal use",
        "",
        f"`Rt_estimated` is a Cori renewal ratio using OWID `new_cases_smoothed` at t and earlier incidence, with a discretised gamma serial interval (mean 5 days; SD 2 days). There are no missing Rt values in either the selected calibration ({rt_missing_by_phase['calibration']}) or validation ({rt_missing_by_phase['validation']}) periods, and none was imputed. The estimator code does not index a future date. The provenance of OWID's supplied 7-day smoothing still needs to state whether it is trailing rather than centred before the input can be called real-time; in either event, calibration is a retrospective replay because beta at t is informed by observed incidence at t. Smoothing also damps sharp changes, while the validation median-beta rule removes time variation altogether.",
        "",
        "## Observation and mortality models",
        "",
        "`simulated I` is prevalence and should not be compared with reported new cases. The current code instead compares simulated incident infections with reported confirmed cases, but that is still not direct. A defensible case target is an explicit delayed reporting process applied to incident infections, with documented ascertainment. The approved inputs do not provide a validated country-date ascertainment fraction or reporting-delay distribution; testing fields do not, by themselves, identify one. Do not silently declare reported cases to be infections.",
        "",
        f"For deaths, `mu*I` is the implemented daily I→D flow and `D` is cumulative simulated deaths. Daily observed deaths should be compared to same-date daily simulated death flow after any explicit reporting delay; cumulative deaths are supplementary only. Same-day daily validation gives death RMSE {daily_death_same_day['rmse']:.2f} and correlation {daily_death_same_day['correlation']:.3f}. A ±30-day lag scan is diagnostic only (best correlation {best_lag['correlation']:.3f} at lag {best_lag['lag_days_simulation_relative_to_observation']:+d}); no lag was selected to improve fit.",
        "",
        "## Calibration comparison",
        "",
        "| Strategy | Case RMSE | Death RMSE | Case correlation | Death correlation | Peak-date error | Peak-size error |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| A. Fixed-beta replay | {validation_row['cases_rmse']:,.2f} | {validation_row['deaths_rmse']:,.2f} | {validation_row['cases_correlation']:.3f} | {validation_row['deaths_correlation']:.3f} | {validation_row['peak_date_error_days']:.0f} days | {validation_row['peak_size_error']:,.2f} |",
        "| B. Formal restricted fit | Not estimable | Not estimable | Not estimable | Not estimable | Not estimable | Not estimable |",
        "",
        "The Plan supports fitting transmission rates from historical case curves, so a formal fit is warranted in principle. It cannot validly begin by treating reported cases as total infections. First approve an observation model and a small, allowed fitted set (for example a low-dimensional beta multiplier); keep sigma, gamma, and mu sourced rather than fitting all rates. Fit calibration dates only, freeze the fit, then score the unchanged validation period. Strategy B is not scored here because inventing a reporting factor or using validation data to infer it would violate the modelling guardrails.",
        "",
        "## Re-run sensitivity scenarios",
        "",
        *sensitivity_lines,
        "",
        "The poor magnitude/death fit persists across every supplied scenario. The scenarios are evidence-based sensitivity cases, not candidates to select for lower error.",
        "",
        "## Required revision gate",
        "",
        "1. Align beta, ODE transition, and daily-flow dates; state whether Rt is effective or full-susceptibility.",
        "2. Document and approve explicit case/death observation mappings, including ascertainment and reporting-delay treatment.",
        "3. Pre-specify a restricted, project-permitted calibration objective on calibration dates only.",
        "4. Freeze fitted quantities before validation and report daily case/death and supplementary cumulative-death diagnostics.",
        "5. Do not expand to all countries or run airport/mobility work until the revised method is documented and validated.",
        "",
        "The machine-readable findings are in `seird_calibration_diagnostics.json`; the strategy table is in `seird_calibration_comparison.csv`.",
        "",
    ]
    (OUTPUT / "seird_calibration_diagnostics.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps({"status": diagnostics["status"], "comparison_rows": len(comparison), "sensitivity_rows": len(sensitivity)}, indent=2))


if __name__ == "__main__":
    main()
