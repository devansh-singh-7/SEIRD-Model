"""Mechanically consistent, single-country SEIRD replay (United Kingdom).

This mechanics-only revision neither fits parameters nor invents a case
ascertainment or reporting-delay observation model.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp

from covid_pipeline import validate_seird_assumptions

OUTPUT_DIR = Path("outputs")
PLOT_DIR = OUTPUT_DIR / "seird_plots"
COUNTRY = "United Kingdom"
CALIBRATION_START = pd.Timestamp("2020-03-10")
PERIOD_END = pd.Timestamp("2021-12-31")


def metrics(observed: pd.Series, simulated: pd.Series) -> dict:
    pair = pd.concat([observed, simulated], axis=1).dropna()
    residual = pair.iloc[:, 0] - pair.iloc[:, 1]
    return {"n": int(len(pair)), "mae": float(np.abs(residual).mean()), "rmse": float(np.sqrt(np.mean(np.square(residual)))), "correlation": float(pair.iloc[:, 0].corr(pair.iloc[:, 1]))}


def peak_metrics(observed: pd.Series, simulated: pd.Series, dates: pd.Series) -> dict:
    pair = pd.concat([dates, observed, simulated], axis=1).dropna()
    actual, model = pair.iloc[pair.iloc[:, 1].argmax()], pair.iloc[pair.iloc[:, 2].argmax()]
    return {"observed_peak_date": pd.Timestamp(actual.iloc[0]).strftime("%Y-%m-%d"), "simulated_peak_date": pd.Timestamp(model.iloc[0]).strftime("%Y-%m-%d"), "peak_date_error_days": float((pd.Timestamp(model.iloc[0]) - pd.Timestamp(actual.iloc[0])).days), "observed_peak_magnitude": float(actual.iloc[1]), "simulated_peak_magnitude": float(model.iloc[2]), "peak_size_error": float(model.iloc[2] - actual.iloc[1])}


def rhs(_time: float, state: np.ndarray, population: float, beta: float, sigma: float, gamma: float, mu: float) -> np.ndarray:
    susceptible, exposed, infectious, recovered, deceased = state
    force = beta * susceptible * infectious / population
    return np.array([-force, force - sigma * exposed, sigma * exposed - (gamma + mu) * infectious, gamma * infectious, mu * infectious])


def initial_conditions(data: pd.DataFrame, start: pd.Timestamp, population: float, incubation_days: float, infectious_days: float) -> tuple[np.ndarray, dict]:
    first = data.loc[data.date.eq(start)].iloc[0]
    i0 = float(data.loc[(data.date >= start - pd.Timedelta(days=infectious_days)) & (data.date < start), "new_cases_smoothed"].sum(min_count=1))
    e0 = float(data.loc[(data.date >= start - pd.Timedelta(days=incubation_days + infectious_days)) & (data.date < start - pd.Timedelta(days=infectious_days)), "new_cases_smoothed"].sum(min_count=1))
    d0, cases = float(first.total_deaths), float(first.total_cases)
    r0, s0 = cases - e0 - i0 - d0, population - cases
    if not np.isfinite([s0, e0, i0, r0, d0]).all() or min(s0, e0, i0, r0, d0) < 0:
        raise ValueError("Observed-derived initial compartments are unavailable or negative")
    return np.array([s0, e0, i0, r0, d0]), {"initialization": "E0 and I0 are reported-case windows; D0 is reported cumulative deaths; R0 is residual reported cumulative cases.", "limitation": "These are surveillance proxies, not identified true infection compartments.", "S0": s0, "E0": e0, "I0": i0, "R0": r0, "D0": d0}


def simulate_mechanics_v2(initial: np.ndarray, dates: pd.DatetimeIndex, rt: np.ndarray, validation_start: pd.Timestamp, fixed_validation_beta: float, population: float, sigma: float, gamma: float, mu: float) -> pd.DataFrame:
    """Rows after initialization are interval-end states for [t-1,t]."""
    states = np.zeros((len(dates), 5)); states[0] = initial
    rows = [{"date": dates[0], "S_transition_start": np.nan, "Rt_estimated_input": np.nan, "beta_used_for_transition": np.nan, "beta_used_for_reported_flow": np.nan, "Reff_transition_start": np.nan, "instantaneous_death_flow_mu_times_I_start": np.nan, "new_infections_simulated": np.nan, "new_deaths_simulated": np.nan, "transition_type": "initial_state_no_preceding_interval"}]
    removal = gamma + mu
    for index in range(1, len(dates)):
        state_start, date = states[index - 1], dates[index]
        if date < validation_start:
            rt_input = float(rt[index])
            beta = rt_input * removal * population / state_start[0]
            transition_type = "calibration_Rt_effective"
        else:
            rt_input, beta, transition_type = np.nan, fixed_validation_beta, "validation_fixed_calibration_median_beta"
        solution = solve_ivp(lambda time, state: rhs(time, state, population, beta, sigma, gamma, mu), (0.0, 1.0), state_start, t_eval=[1.0], rtol=1e-8, atol=1e-6)
        if not solution.success:
            raise RuntimeError(f"ODE solver failed for transition ending {date.date()}: {solution.message}")
        state_end = solution.y[:, -1]; states[index] = state_end
        rows.append({"date": date, "S_transition_start": float(state_start[0]), "Rt_estimated_input": rt_input, "beta_used_for_transition": beta, "beta_used_for_reported_flow": beta, "Reff_transition_start": beta * state_start[0] / (population * removal), "instantaneous_death_flow_mu_times_I_start": mu * state_start[2], "new_infections_simulated": max(0.0, float(state_start[0] - state_end[0])), "new_deaths_simulated": max(0.0, float(state_end[4] - state_start[4])), "transition_type": transition_type})
    result = pd.DataFrame(rows)
    result[["S_simulated", "E_simulated", "I_simulated", "R_simulated", "D_simulated"]] = states
    return result


def mechanics_tests(simulation: pd.DataFrame, population: float) -> dict:
    compartments = simulation[["S_simulated", "E_simulated", "I_simulated", "R_simulated", "D_simulated"]]
    transitioned = simulation[simulation.transition_type.ne("initial_state_no_preceding_interval")]
    calibration = transitioned[transitioned.transition_type.eq("calibration_Rt_effective")]
    beta_error = np.abs(transitioned.beta_used_for_transition - transitioned.beta_used_for_reported_flow)
    reff_error = np.abs(calibration.Reff_transition_start - calibration.Rt_estimated_input)
    flow_error = np.abs(transitioned.new_infections_simulated - (transitioned.S_transition_start - transitioned.S_simulated))
    zero = simulate_mechanics_v2(np.array([population, 0., 0., 0., 0.]), pd.date_range("2020-01-01", periods=4), np.array([np.nan, 2., 2., 2.]), pd.Timestamp("2021-01-01"), 0.2, population, 0.2, 0.125, 0.001)
    return {"nonnegative_compartments": bool((compartments.to_numpy() >= -1e-6).all()), "population_accounting": bool(np.max(np.abs(compartments.sum(axis=1) - population)) < 1e-3), "no_spontaneous_infection": bool(zero[["E_simulated", "I_simulated"]].to_numpy().max() < 1e-8), "monotonic_death_accumulation": bool(simulation.D_simulated.diff().fillna(0).ge(-1e-7).all()), "beta_alignment": bool(beta_error.max() < 1e-12 and flow_error.max() < 1e-5), "Rt_Reff_relationship": bool(reff_error.max() < 1e-10), "consistent_time_indexing": bool((transitioned.date.diff().dropna().dt.days == 1).all()), "numerical_stability": bool(np.isfinite(compartments.to_numpy()).all()), "max_beta_alignment_error": float(beta_error.max()), "max_infection_balance_error": float(flow_error.max()), "max_Rt_Reff_error": float(reff_error.max())}


def main() -> None:
    assumptions = validate_seird_assumptions(Path("seird_assumptions.json"))
    processed = pd.read_csv(OUTPUT_DIR / "owid_covid_processed.csv", parse_dates=["date"])
    rt_data = pd.read_csv(OUTPUT_DIR / "rt_estimates.csv", parse_dates=["date"])
    data = processed.loc[processed.country.eq(COUNTRY)].sort_values("date")
    rt_data = rt_data.loc[rt_data.country.eq(COUNTRY)].sort_values("date")
    p = assumptions["parameters"]
    population = float(data.population.dropna().iloc[0]); sigma, gamma, mu = (float(p[key]["value"]) for key in ("sigma", "gamma", "mortality_transition_parameter"))
    period = data.loc[data.date.between(CALIBRATION_START, PERIOD_END)].copy()
    merged = period.merge(rt_data[["date", "Rt_estimated"]], on="date", how="left", validate="one_to_one")
    if merged.Rt_estimated.isna().any():
        raise ValueError("Selected period has unavailable Rt_estimated; no imputation is permitted")
    dates, split_index = pd.DatetimeIndex(merged.date), int(len(merged) * 0.8)
    validation_start = dates[split_index]
    initial, initial_metadata = initial_conditions(data, CALIBRATION_START, population, float(p["incubation_period"]["value"]), float(p["infectious_recovery_period"]["value"]))
    provisional = simulate_mechanics_v2(initial, dates, merged.Rt_estimated.to_numpy(), validation_start, 0.0, population, sigma, gamma, mu)
    calibration_beta = float(provisional.loc[provisional.transition_type.eq("calibration_Rt_effective"), "beta_used_for_transition"].median())
    sim = simulate_mechanics_v2(initial, dates, merged.Rt_estimated.to_numpy(), validation_start, calibration_beta, population, sigma, gamma, mu)
    simulation = merged[["date", "new_cases_smoothed", "new_deaths", "new_deaths_smoothed", "total_deaths"]].rename(columns={"new_cases_smoothed": "observed_cases_smoothed", "new_deaths": "observed_daily_deaths", "new_deaths_smoothed": "observed_deaths_smoothed", "total_deaths": "observed_cumulative_deaths"}).merge(sim, on="date", validate="one_to_one")
    simulation["phase"] = np.where(simulation.date < validation_start, "calibration", "validation")
    tests = mechanics_tests(simulation, population)
    if not all(value for key, value in tests.items() if not key.startswith("max_")):
        raise RuntimeError("Mechanical validation failed; v2 outputs not accepted")
    validation = simulation[simulation.phase.eq("validation")]
    cases, deaths, cumulative_deaths = metrics(validation.observed_cases_smoothed, validation.new_infections_simulated), metrics(validation.observed_daily_deaths, validation.new_deaths_simulated), metrics(validation.observed_cumulative_deaths, validation.D_simulated)
    peak = peak_metrics(validation.observed_cases_smoothed, validation.new_infections_simulated, validation.date)
    validation_table = pd.DataFrame([{ "country": COUNTRY, "phase": "validation", "status": "SEIRD MECHANICS STATUS: GO", "case_comparison_status": "NOT IDENTIFIABLE: no ascertainment/reporting-delay observation model", "death_comparison_status": "VALID WITH CAVEAT: no identified death-reporting delay", "cumulative_death_comparison_status": "VALID WITH CAVEAT: supplementary trajectory only", **{f"cases_{key}": value for key, value in cases.items()}, **{f"deaths_{key}": value for key, value in deaths.items()}, **{f"cumulative_deaths_{key}": value for key, value in cumulative_deaths.items()}, **peak }])
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 1, figsize=(13, 9), sharex=True)
    axes[0].plot(simulation.date, simulation.observed_cases_smoothed, label="Observed reported cases (not direct model target)"); axes[0].plot(simulation.date, simulation.new_infections_simulated, label="Simulated incident infections"); axes[0].set_ylabel("people/day"); axes[0].legend()
    axes[1].plot(simulation.date, simulation.observed_daily_deaths, label="Observed daily deaths (unsmoothed)"); axes[1].plot(simulation.date, simulation.new_deaths_simulated, label="Simulated I-to-D interval flow"); axes[1].set_ylabel("people/day"); axes[1].set_xlabel("interval end date"); axes[1].legend()
    fig.suptitle(f"{COUNTRY}: mechanically aligned SEIRD replay v2"); fig.tight_layout(); fig.savefig(PLOT_DIR / "observed_vs_simulated_v2.png", dpi=150); plt.close(fig)
    fig, ax = plt.subplots(figsize=(13, 5))
    for column in ["S_simulated", "E_simulated", "I_simulated", "R_simulated", "D_simulated"]: ax.plot(simulation.date, simulation[column], label=column[0])
    ax.set_title(f"{COUNTRY}: SEIRD compartments v2"); ax.set_xlabel("interval end date"); ax.set_ylabel("people"); ax.legend(); fig.tight_layout(); fig.savefig(PLOT_DIR / "compartments_v2.png", dpi=150); plt.close(fig)
    simulation.to_csv(OUTPUT_DIR / "seird_single_country_simulation_v2.csv", index=False, date_format="%Y-%m-%d")
    validation_table.to_csv(OUTPUT_DIR / "seird_single_country_validation_v2.csv", index=False)
    comparisons = [{"model_quantity": "Simulated incident infections", "OWID_quantity": "reported confirmed new cases", "status": "NOT IDENTIFIABLE", "reason": "No approved ascertainment or reporting-delay observation model."}, {"model_quantity": "Simulated I prevalence", "OWID_quantity": "reported confirmed new cases", "status": "NOT IDENTIFIABLE", "reason": "Prevalence and incident reports differ."}, {"model_quantity": "Cumulative simulated infections (N-S)", "OWID_quantity": "reported cumulative confirmed cases", "status": "NOT IDENTIFIABLE", "reason": "Cumulative confirmed cases do not identify cumulative infections without ascertainment."}, {"model_quantity": "Simulated daily I→D flow", "OWID_quantity": "reported daily deaths", "status": "VALID WITH CAVEAT", "reason": "Death reporting delay is not identified and was not invented."}, {"model_quantity": "Simulated cumulative D", "OWID_quantity": "reported cumulative deaths", "status": "VALID WITH CAVEAT", "reason": "Supplementary only; retains reporting and IFR caveats."}]
    mechanics = {"status": "SEIRD MECHANICS STATUS: GO", "scope": "Mechanical consistency only; no parameter optimisation, observation-model fitting, mobility, intervention coefficients, external datasets, or raw-OWID modification.", "time_convention": "Each row t after initialization is the interval-end state after [t-1,t]. The same beta scalar is used for the transition and recorded integrated flows: infections=S(t-1)-S(t), deaths=D(t)-D(t-1).", "Rt_beta_interpretation": {"R0": "beta/(gamma+mu) at full susceptibility", "Reff": "beta*S/[N*(gamma+mu)]", "Rt_estimated": "Cori renewal-ratio estimate treated as Reff only during calibration", "beta": "calibration beta(t)=Rt_estimated(t)*(gamma+mu)*N/S(t-1), held over [t-1,t]; validation beta is calibration-only median."}, "parameters": {"sigma": sigma, "gamma": gamma, "mu": mu, "population": population, "calibration_median_beta": calibration_beta}, "initial_conditions": initial_metadata, "mechanics_tests": tests, "comparability": comparisons, "descriptive_validation_metrics_not_case_calibration": validation_table.iloc[0].to_dict(), "limitation": "No ascertainment rate or reporting delay was created; death lag was not selected or fitted.", "plots": [str(PLOT_DIR / "observed_vs_simulated_v2.png"), str(PLOT_DIR / "compartments_v2.png")]}
    (OUTPUT_DIR / "seird_mechanics_validation.json").write_text(json.dumps(mechanics, indent=2, default=str), encoding="utf-8")
    lines = ["# SEIRD Mechanics Validation v2", "", "`SEIRD MECHANICS STATUS: GO`", "", "## Time convention", "", mechanics["time_convention"], "", "## Rt and beta", "", "For these equations, `R0 = beta/(gamma+mu)` at full susceptibility and `Reff = beta*S/[N*(gamma+mu)]`. `Rt_estimated` is treated as effective Rt during calibration, so `beta(t) = Rt_estimated(t)*(gamma+mu)*N/S(t-1)` for the interval ending t. Validation uses the calibration-only median beta and no validation Rt.", "", "## Mechanical checks", "", *[f"- {key}: `{value}`" for key, value in tests.items()], "", "## What can be compared with approved inputs", "", "| Model quantity | OWID quantity | Status |", "|---|---|---|", *[f"| {row['model_quantity']} | {row['OWID_quantity']} | {row['status']} |" for row in comparisons], "", "Case metrics are descriptive only, not calibration validity evidence. No ascertainment rate, reporting delay, or parameter optimisation was introduced.", "", "## Mortality", "", "`mu*I` is retained as the instantaneous mortality flow and is exported at each interval start. The stored daily death total is its integrated interval flow `D(t)-D(t-1)`. Daily reported deaths are valid with caveat because an observation/reporting delay is not identified by approved inputs and was not fitted. Cumulative D comparison is supplementary only.", "", f"Descriptive validation case RMSE: `{cases['rmse']}`; daily-death RMSE: `{deaths['rmse']}`. These do not establish forecast or case-calibration accuracy.", ""]
    (OUTPUT_DIR / "seird_mechanics_validation.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": mechanics["status"], "validation_case_rmse_descriptive_only": cases["rmse"], "validation_death_rmse": deaths["rmse"]}, indent=2))


if __name__ == "__main__":
    main()
