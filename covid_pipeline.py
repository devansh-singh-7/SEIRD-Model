"""Reproducible OWID COVID analysis pipeline.

The input CSV is read-only. Outputs are written beside it, with observed,
calculated, estimated, simulated, external, and assumption fields kept explicit.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp
from scipy.signal import find_peaks
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


CORE_NUMERIC = [
    "total_cases", "new_cases", "new_cases_smoothed", "total_deaths",
    "new_deaths", "new_deaths_smoothed", "reproduction_rate",
    "stringency_index", "population", "population_density", "median_age",
    "gdp_per_capita", "hospital_beds_per_thousand", "human_development_index",
]


def metrics(observed: pd.Series, predicted: pd.Series) -> dict[str, float]:
    pair = pd.concat([observed, predicted], axis=1).dropna()
    if pair.empty:
        return {"n": 0, "mae": np.nan, "rmse": np.nan, "correlation": np.nan, "r2": np.nan}
    y, p = pair.iloc[:, 0], pair.iloc[:, 1]
    return {
        "n": int(len(pair)),
        "mae": float(mean_absolute_error(y, p)),
        "rmse": float(np.sqrt(mean_squared_error(y, p))),
        "correlation": float(y.corr(p)) if len(pair) > 1 else np.nan,
        "r2": float(r2_score(y, p)) if len(pair) > 1 else np.nan,
    }


SEIRD_REQUIRED_ENTRIES = (
    "incubation_period",
    "sigma",
    "infectious_recovery_period",
    "gamma",
    "mortality_transition_parameter",
    "mortality_parameter_definition",
)


def validate_seird_assumptions(assumptions_path: Path) -> dict:
    """Load and validate the source-required SEIRD parameter specification.

    This gate intentionally rejects incomplete assumptions before any simulation.
    It does not infer values from OWID data or fill missing values.
    """
    assumptions = json.loads(assumptions_path.read_text(encoding="utf-8"))
    parameters = assumptions.get("parameters", {})
    errors: list[str] = []
    for name in SEIRD_REQUIRED_ENTRIES:
        entry = parameters.get(name)
        if not isinstance(entry, dict):
            errors.append(f"missing parameter entry: {name}")
            continue
        if name == "mortality_parameter_definition":
            if not isinstance(entry.get("value"), str) or not entry["value"].strip():
                errors.append(f"missing mortality definition: {name}")
        elif entry.get("value") is None:
            errors.append(f"missing numerical value: {name}")
        elif not isinstance(entry.get("value"), (int, float)) or not np.isfinite(entry["value"]) or entry["value"] <= 0:
            errors.append(f"parameter must be a finite positive number: {name}")
        for field in ("source", "source_date", "evidence_justification", "applicability_limitations"):
            if not entry.get(field):
                errors.append(f"missing traceability field {field}: {name}")
    sigma = parameters.get("sigma", {}).get("value")
    incubation = parameters.get("incubation_period", {}).get("value")
    if sigma is not None and incubation is not None and not np.isclose(sigma, 1.0 / incubation):
        errors.append("sigma does not equal 1 / incubation_period")
    gamma = parameters.get("gamma", {}).get("value")
    infectious_period = parameters.get("infectious_recovery_period", {}).get("value")
    if gamma is not None and infectious_period is not None and not np.isclose(gamma, 1.0 / infectious_period):
        errors.append("gamma does not equal 1 / infectious_recovery_period")
    beta = assumptions.get("beta_calibration", {})
    if beta.get("status") != "BLOCKED" and not beta.get("source"):
        errors.append("beta calibration lacks source traceability")
    if errors:
        raise ValueError("SEIRD parameter gate failed; no simulation permitted: " + "; ".join(errors))
    return assumptions


def load_and_clean(input_path: Path, output_path: Path) -> tuple[pd.DataFrame, dict]:
    raw = pd.read_csv(input_path, low_memory=False)
    raw_columns = list(raw.columns)
    raw.columns = (
        raw.columns.str.strip().str.lower().str.replace(r"[^a-z0-9]+", "_", regex=True).str.strip("_")
    )
    if "country" not in raw or "date" not in raw:
        raise ValueError("Required columns country and date are missing")
    raw["date"] = pd.to_datetime(raw["date"], format="%d-%m-%Y", errors="coerce")
    invalid_dates = int(raw["date"].isna().sum())
    if invalid_dates:
        raise ValueError(f"STOP: {invalid_dates} invalid dates found")
    for col in CORE_NUMERIC:
        if col in raw:
            raw[col] = pd.to_numeric(raw[col], errors="coerce")
    if "is_country" not in raw or "code" not in raw:
        raise ValueError("STOP: is_country and code are required for country filtering")
    raw["is_country"] = raw["is_country"].astype("boolean")
    raw["code"] = raw["code"].astype("string").str.strip().str.upper()
    exact_duplicates = int(raw.duplicated().sum())
    raw = raw.drop_duplicates(keep="first")
    country_date_duplicates = int(raw.duplicated(["country", "date"]).sum())
    if country_date_duplicates:
        raw = raw.drop_duplicates(["country", "date"], keep="first")
    raw = raw.sort_values(["country", "date"]).reset_index(drop=True)
    actual_country_mask = raw["is_country"].fillna(False) & raw["code"].str.fullmatch(r"[A-Z]{3}").fillna(False)
    aggregate_locations = sorted(raw.loc[~actual_country_mask, "country"].unique().tolist())
    country_rows = raw.loc[actual_country_mask].copy()
    country_rows.to_csv(output_path, index=False, date_format="%Y-%m-%d")
    audit = {
        "source": str(input_path),
        "raw_columns": raw_columns,
        "processed_rows": int(len(country_rows)),
        "processed_columns": int(len(country_rows.columns)),
        "country_rows": int(len(country_rows)),
        "locations": int(raw["country"].nunique()),
        "countries": int(country_rows["country"].nunique()),
        "aggregate_rows": int(len(raw) - len(country_rows)),
        "aggregate_locations": aggregate_locations,
        "country_filter": "is_country=True and code matches exactly three uppercase letters; non-ISO OWID aggregate and uncertain OWID-coded locations are excluded without guessing a mapping",
        "date_min": raw["date"].min().strftime("%Y-%m-%d"),
        "date_max": raw["date"].max().strftime("%Y-%m-%d"),
        "invalid_dates": invalid_dates,
        "exact_duplicates_removed": exact_duplicates,
        "country_date_duplicates_removed": country_date_duplicates,
        "missing_values": {k: int(v) for k, v in country_rows.isna().sum().items()},
        "zero_counts": {k: int((country_rows[k] == 0).sum()) for k in CORE_NUMERIC if k in country_rows},
        "status": "calculated from supplied CSV",
    }
    return country_rows, audit


def detect_waves(
    df: pd.DataFrame,
    output_path: Path | None,
    min_distance_days: int = 28,
    prominence_fraction: float = 0.20,
    height_fraction: float = 0.05,
    minimum_peak_cases: float = 20.0,
) -> pd.DataFrame:
    records: list[dict] = []
    for country, group in df[df["is_country"].fillna(False)].groupby("country", sort=True):
        group = group.sort_values("date").copy()
        signal = group["new_cases_smoothed"].to_numpy(dtype=float)
        valid = np.isfinite(signal)
        if valid.sum() < 30 or np.nanmax(signal) <= 0:
            continue
        signal = np.nan_to_num(signal, nan=0.0)
        max_value = float(signal.max())
        prominence = max(10.0, prominence_fraction * max_value)
        height = max(minimum_peak_cases, height_fraction * max_value)
        peaks, properties = find_peaks(signal, distance=min_distance_days, prominence=prominence, height=height)
        for wave_number, peak_idx in enumerate(peaks, start=1):
            peak_value = float(signal[peak_idx])
            threshold = max(1.0, 0.20 * peak_value)
            start_idx = peak_idx
            while start_idx > 0 and signal[start_idx - 1] >= threshold:
                start_idx -= 1
            end_idx = peak_idx
            while end_idx < len(signal) - 1 and signal[end_idx + 1] >= threshold:
                end_idx += 1
            records.append({
                "country": country,
                "wave_number": wave_number,
                "peak_date": group.iloc[peak_idx]["date"],
                "peak_magnitude_cases_7d_smoothed": peak_value,
                "start_date": group.iloc[start_idx]["date"],
                "end_date": group.iloc[end_idx]["date"],
                "duration_days": int((group.iloc[end_idx]["date"] - group.iloc[start_idx]["date"]).days + 1),
                "peak_prominence_threshold": prominence,
                "peak_min_distance_days": min_distance_days,
                "peak_min_height_cases": height,
                "wave_detection_rule": "7-day smoothed incidence; fixed minimum height plus relative prominence and minimum separation",
                "status": "calculated from observed OWID new_cases_smoothed",
            })
    result = pd.DataFrame(records)
    if not result.empty:
        result = result.sort_values(["country", "peak_date"])
    if output_path is not None:
        result.to_csv(output_path, index=False, date_format="%Y-%m-%d")
    return result


def estimate_growth(df: pd.DataFrame, waves: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    records: list[dict] = []
    for country, first_wave in waves.sort_values("peak_date").groupby("country", sort=True).first().iterrows():
        group = df[(df["country"] == country) & (df["is_country"].fillna(False))].copy()
        group = group[(group["date"] >= first_wave["start_date"]) & (group["date"] <= first_wave["peak_date"])]
        group = group[group["new_cases_smoothed"].gt(0)].dropna(subset=["new_cases_smoothed"])
        if len(group) < 5:
            continue
        x = (group["date"] - group["date"].min()).dt.days.to_numpy().reshape(-1, 1)
        y = np.log(group["new_cases_smoothed"].to_numpy())
        fit = LinearRegression().fit(x, y)
        rate = float(fit.coef_[0])
        records.append({
            "country": country,
            "growth_start_date": group["date"].min(),
            "growth_end_date": group["date"].max(),
            "n_observations": int(len(group)),
            "growth_rate_r_per_day": rate,
            "doubling_time_days": float(np.log(2) / rate) if rate > 0 else np.nan,
            "r_squared": float(fit.score(x, y)),
            "status": "estimated by log-linear regression on first detected wave rise",
        })
    result = pd.DataFrame(records)
    result.to_csv(output_path, index=False, date_format="%Y-%m-%d")
    return result


def estimate_rt(
    df: pd.DataFrame,
    output_path: Path,
    serial_mean: float = 5.0,
    serial_sd: float = 2.0,
    minimum_renewal_denominator: float = 20.0,
    maximum_current_to_prior_median_ratio: float = 5.0,
) -> pd.DataFrame:
    """Cori-style renewal estimate with a discretised gamma serial interval.

    The serial-interval values are explicit modelling assumptions, not OWID data.
    A seven-day case curve is used. Rt is unavailable when the prior-incidence
    renewal denominator is below 20 smoothed reported cases or when the current
    smoothed incidence exceeds five times the preceding seven-day median. These
    are data-quality rules for unstable low-baseline/reporting-spike periods,
    not caps on Rt.
    """
    days = np.arange(1, 22)
    shape = (serial_mean / serial_sd) ** 2
    scale = serial_sd**2 / serial_mean
    weights = np.exp((shape - 1) * np.log(days) - days / scale)
    weights /= weights.sum()
    records: list[dict] = []
    for country, group in df[df["is_country"].fillna(False)].groupby("country", sort=True):
        group = group.sort_values("date").copy()
        incidence = group["new_cases_smoothed"].to_numpy(dtype=float).copy()
        incidence[~np.isfinite(incidence)] = np.nan
        estimates = np.full(len(group), np.nan)
        denominators = np.full(len(group), np.nan)
        prior_medians = np.full(len(group), np.nan)
        continuity_ratios = np.full(len(group), np.nan)
        quality = np.full(len(group), "insufficient_history", dtype=object)
        for idx in range(1, len(group)):
            window = incidence[max(0, idx - len(weights)):idx][::-1]
            w = weights[: len(window)]
            valid = np.isfinite(window) & (window >= 0)
            denominator = float(np.sum(window[valid] * w[valid]))
            numerator = incidence[idx]
            prior_median = float(np.nanmedian(incidence[max(0, idx - 7):idx])) if np.isfinite(incidence[max(0, idx - 7):idx]).any() else np.nan
            continuity_ratio = numerator / prior_median if np.isfinite(prior_median) and prior_median > 0 else np.inf
            denominators[idx] = denominator
            prior_medians[idx] = prior_median
            continuity_ratios[idx] = continuity_ratio
            if not np.isfinite(numerator):
                quality[idx] = "missing_current_incidence"
            elif np.any(window[~np.isfinite(window)] if (~np.isfinite(window)).any() else np.array([], dtype=float)):
                quality[idx] = "missing_prior_incidence"
            elif np.any(window < 0) or numerator < 0:
                quality[idx] = "negative_incidence_not_used"
            elif denominator < minimum_renewal_denominator:
                quality[idx] = "low_renewal_denominator"
            elif continuity_ratio > maximum_current_to_prior_median_ratio:
                quality[idx] = "reporting_spike_or_low_baseline"
            else:
                estimates[idx] = numerator / denominator
                quality[idx] = "valid"
        for date, estimate, reference, denominator, prior_median, continuity_ratio, quality_flag in zip(group["date"], estimates, group["reproduction_rate"], denominators, prior_medians, continuity_ratios, quality):
            records.append({
                "country": country,
                "date": date,
                "Rt_estimated": estimate,
                "reproduction_rate_owid_reference": reference,
                "renewal_denominator": denominator,
                "prior_7d_median_incidence": prior_median,
                "current_to_prior_7d_median_ratio": continuity_ratio,
                "rt_quality_flag": quality_flag,
                "minimum_renewal_denominator": minimum_renewal_denominator,
                "maximum_current_to_prior_median_ratio": maximum_current_to_prior_median_ratio,
                "serial_interval_mean_days": serial_mean,
                "serial_interval_sd_days": serial_sd,
                "method": "Cori renewal ratio using prior 7-day-smoothed incidence and discretised gamma serial interval",
                "status": "estimated; OWID reproduction_rate retained as reference only",
            })
    result = pd.DataFrame(records)
    result.to_csv(output_path, index=False, date_format="%Y-%m-%d")
    return result


def intervention_model(df: pd.DataFrame, rt: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    country_data = df[df["is_country"].fillna(False)][["country", "date", "stringency_index"]].copy()
    joined = country_data.merge(rt, on=["country", "date"], how="inner", validate="one_to_one")
    joined = joined.sort_values(["country", "date"]).reset_index(drop=True)
    joined["previous_Rt"] = joined.groupby("country")["Rt_estimated"].shift(1)
    joined["previous_Rt_date"] = joined.groupby("country")["date"].shift(1)
    joined["target_day_gap"] = (joined["date"] - joined["previous_Rt_date"]).dt.days
    joined["delta_Rt"] = joined["Rt_estimated"] - joined["previous_Rt"]
    records: list[dict] = []
    for lag in (7, 21):
        joined[f"stringency_lag_{lag}"] = joined.groupby("country")["stringency_index"].shift(lag)
        joined[f"stringency_lag_date_{lag}"] = joined.groupby("country")["date"].shift(lag)
        joined[f"lag_day_gap_{lag}"] = (joined["date"] - joined[f"stringency_lag_date_{lag}"]).dt.days
        target_value_available = joined["delta_Rt"].notna()
        target_date_continuous = joined["target_day_gap"].eq(1)
        target_available = target_value_available & target_date_continuous
        lagged_stringency_available = joined[f"stringency_lag_{lag}"].notna()
        exact_lag = joined[f"lag_day_gap_{lag}"].eq(lag)
        model_data = joined[target_available & lagged_stringency_available & exact_lag].copy()
        if len(model_data) < 20:
            continue
        cutoff = model_data["date"].quantile(0.8)
        train = model_data[model_data["date"] <= cutoff]
        test = model_data[model_data["date"] > cutoff]
        if len(train) < 10 or len(test) < 10:
            continue
        feature = f"stringency_lag_{lag}"
        model = Ridge(alpha=1.0).fit(train[[feature]], train["delta_Rt"])
        prediction = model.predict(test[[f"stringency_lag_{lag}"]])
        score = metrics(test["delta_Rt"], pd.Series(prediction, index=test.index))
        train_prediction = model.predict(train[[feature]])
        train_score = metrics(train["delta_Rt"], pd.Series(train_prediction, index=train.index))
        records.append({
            "lag_days": lag,
            "n_country_date_matches": int(len(joined)),
            "n_target_rows_before_filter": int(target_value_available.sum()),
            "n_rows_with_lagged_stringency_before_date_check": int((target_available & lagged_stringency_available).sum()),
            "n_rows_rejected_for_missing_rt_target": int((~target_value_available).sum()),
            "n_rows_rejected_for_nonconsecutive_target_date": int((target_value_available & ~target_date_continuous).sum()),
            "n_rows_rejected_for_missing_lagged_stringency": int((target_available & ~lagged_stringency_available).sum()),
            "n_rows_rejected_for_nonexact_lag_date": int((target_available & lagged_stringency_available & ~exact_lag).sum()),
            "n_rows_used": int(len(model_data)),
            "countries_used": int(model_data["country"].nunique()),
            "used_date_min": model_data["date"].min(),
            "used_date_max": model_data["date"].max(),
            "n_train": int(len(train)),
            "n_validation": int(len(test)),
            "train_date_min": train["date"].min(),
            "train_date_max": train["date"].max(),
            "validation_date_min": test["date"].min(),
            "validation_date_max": test["date"].max(),
            "train_end_date": cutoff,
            "minimum_total_rows": 20,
            "minimum_rows_per_split": 10,
            "lag_direction_verified": bool((model_data["date"] - model_data[f"stringency_lag_date_{lag}"]).dt.days.eq(lag).all()),
            "target_definition": "delta_Rt = Rt_estimated at date t minus Rt_estimated at previous calendar day; nonconsecutive country dates are excluded",
            "target_date_continuity_verified": bool((model_data["target_day_gap"] == 1).all()),
            "features_used": f"stringency_index at date t-{lag}; no current or future stringency values",
            "target_leakage_check": "passed: feature date precedes target date and target Rt is not used as a feature",
            "stringency_train_unique": int(train[feature].nunique()),
            "stringency_train_std": float(train[feature].std(ddof=1)),
            "stringency_validation_unique": int(test[feature].nunique()),
            "stringency_validation_std": float(test[feature].std(ddof=1)),
            "coefficient_delta_Rt_per_stringency_point": float(model.coef_[0]),
            "intercept": float(model.intercept_),
            "train_r2": train_score["r2"],
            "validation_r2": score["r2"],
            "r2": score["r2"],
            "mae": score["mae"],
            "rmse": score["rmse"],
            "correlation": score["correlation"],
            "model": "Ridge regression, chronological 80/20 split",
            "interpretation": "VALID IMPLEMENTATION / NON-PREDICTIVE RESULT; association only, not causal evidence",
            "status": "estimated from OWID stringency_index and independently estimated Rt; excluded from SEIRD calibration",
        })
    result = pd.DataFrame(records)
    result.to_csv(output_path, index=False, date_format="%Y-%m-%d")
    return result


def mortality_model_data(df: pd.DataFrame, output_path: Path, reference_date: str = "2021-12-31", lag_days: int = 14) -> pd.DataFrame:
    date = pd.Timestamp(reference_date)
    base = df[df["is_country"].fillna(False)].copy()
    lagged = base[base["date"] == date - pd.Timedelta(days=lag_days)][["country", "total_cases"]].rename(columns={"total_cases": "cases_lagged"})
    current = base[base["date"] == date][["country", "total_cases", "total_deaths", "median_age", "hospital_beds_per_thousand", "human_development_index", "gdp_per_capita", "population"]]
    result = current.merge(lagged, on="country", how="inner")
    result["lagged_case_fatality_ratio"] = result["total_deaths"] / result["cases_lagged"]
    result = result[(result["cases_lagged"] > 0) & result["total_deaths"].notna()]
    for sensitivity_lag in (7, 21):
        sensitivity = base[base["date"] == date - pd.Timedelta(days=sensitivity_lag)][["country", "total_cases"]].rename(columns={"total_cases": f"cases_lagged_{sensitivity_lag}d"})
        result = result.merge(sensitivity, on="country", how="left")
        result[f"cfr_lag_{sensitivity_lag}d"] = result["total_deaths"] / result[f"cases_lagged_{sensitivity_lag}d"]
    result["mortality_model_eligible_min_cases"] = 1000
    result["mortality_model_eligible"] = result["cases_lagged"] >= result["mortality_model_eligible_min_cases"]
    result["outcome_definition"] = f"observed cumulative deaths on {reference_date} / observed cumulative cases {lag_days} days earlier"
    result["sensitivity_definition"] = "same observed cumulative deaths divided by cases 7 and 21 days earlier; denominator sensitivity only"
    result["status"] = "calculated from OWID; lagged reported CFR-like outcome, not an infection fatality rate and not causal"
    result.to_csv(output_path, index=False)
    return result


def mortality_regression(data: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    predictors = ["median_age", "hospital_beds_per_thousand", "human_development_index", "gdp_per_capita"]
    usable = data[data["mortality_model_eligible"]].dropna(subset=predictors + ["lagged_case_fatality_ratio"]).copy()
    usable = usable[np.isfinite(usable["lagged_case_fatality_ratio"])]
    if len(usable) < 10:
        result = pd.DataFrame([{"status": "blocked: fewer than 10 complete country rows for the specified predictors"}])
        result.to_csv(output_path, index=False)
        return result
    usable = usable.sort_values("country")
    split = max(1, int(len(usable) * 0.8))
    train, test = usable.iloc[:split], usable.iloc[split:]
    model = LinearRegression().fit(train[predictors], train["lagged_case_fatality_ratio"])
    prediction = model.predict(test[predictors])
    score = metrics(test["lagged_case_fatality_ratio"], pd.Series(prediction, index=test.index))
    rows = [{
        "term": predictor, "coefficient": float(coefficient), "n_complete": int(len(usable)),
        "n_train": int(len(train)), "n_validation": int(len(test)), "validation_end_rule": "alphabetical country holdout, not random",
        "model": "ordinary least squares country-level association; minimum 1000 lagged cases", "status": "estimated; not causal",
    } for predictor, coefficient in zip(predictors, model.coef_)]
    rows.append({"term": "intercept", "coefficient": float(model.intercept_), "n_complete": int(len(usable)), "n_train": int(len(train)), "n_validation": int(len(test)), "validation_end_rule": "alphabetical country holdout, not random", "model": "ordinary least squares country-level association; minimum 1000 lagged cases", "status": "estimated; not causal"})
    rows.append({"term": "validation_metrics", **score, "n_complete": int(len(usable)), "n_train": int(len(train)), "n_validation": int(len(test)), "validation_end_rule": "alphabetical country holdout, not random", "model": "ordinary least squares country-level association; minimum 1000 lagged cases", "status": "estimated; not causal"})
    result = pd.DataFrame(rows)
    result.to_csv(output_path, index=False)
    return result


def seird_validation(
    df: pd.DataFrame,
    rt: pd.DataFrame,
    mortality: pd.DataFrame,
    output_dir: Path,
    country: str,
    assumptions_path: Path = Path("seird_assumptions.json"),
) -> tuple[pd.DataFrame, pd.DataFrame]:
    assumptions = validate_seird_assumptions(assumptions_path)
    parameters_spec = assumptions["parameters"]
    incubation_days = float(parameters_spec["incubation_period"]["value"])
    infectious_days = float(parameters_spec["infectious_recovery_period"]["value"])
    sigma = float(parameters_spec["sigma"]["value"])
    gamma = float(parameters_spec["gamma"]["value"])
    mu = float(parameters_spec["mortality_transition_parameter"]["value"])
    data = df[(df["country"] == country) & df["is_country"].fillna(False)].sort_values("date").copy()
    rts = rt[rt["country"] == country].set_index("date")["Rt_estimated"]
    if data.empty or rts.dropna().empty:
        raise ValueError(f"STOP: no usable OWID data or Rt estimates for {country}")
    calibration = data[(data["date"] >= "2020-03-01") & (data["date"] <= "2020-12-31")].copy()
    validation = data[(data["date"] >= "2021-01-01") & (data["date"] <= "2021-12-31")].copy()
    if calibration.empty or validation.empty:
        raise ValueError("STOP: chronological 2020 calibration and 2021 validation periods are unavailable")
    population = float(data["population"].dropna().iloc[0])
    rt_median = float(rts.reindex(calibration["date"]).dropna().median())
    beta = rt_median * (gamma + mu)
    first = calibration[calibration["new_cases_smoothed"].gt(0)].iloc[0]
    idx = data.index.get_loc(first.name)
    infectious_window = data.iloc[max(0, idx - int(infectious_days) + 1): idx + 1]["new_cases_smoothed"].sum(min_count=1)
    exposed_start = max(0, idx - int(incubation_days) - int(infectious_days) + 1)
    exposed_end = max(0, idx - int(infectious_days) + 1)
    exposed_window = data.iloc[exposed_start:exposed_end]["new_cases_smoothed"].sum(min_count=1)
    i0 = float(infectious_window) if np.isfinite(infectious_window) else np.nan
    e0 = float(exposed_window) if np.isfinite(exposed_window) else np.nan
    d0 = float(first["total_deaths"]) if pd.notna(first["total_deaths"]) else np.nan
    r0 = float(first["total_cases"] - i0 - e0 - d0) if np.isfinite(i0 + e0 + d0) else np.nan
    s0 = population - e0 - i0 - r0 - d0 if np.isfinite(r0) else np.nan
    if not np.isfinite(s0) or min(s0, e0, i0, r0, d0) < 0:
        raise ValueError("STOP: observed-derived initial compartments are not non-negative")

    def rhs(_t: float, y: np.ndarray) -> list[float]:
        s, e, i, r, d = y
        force = beta * s * i / population
        return [-force, force - sigma * e, sigma * e - (gamma + mu) * i, gamma * i, mu * i]

    sim_dates = pd.date_range(calibration["date"].min(), validation["date"].max(), freq="D")
    sol = solve_ivp(rhs, (0, len(sim_dates) - 1), [s0, e0, i0, r0, d0], t_eval=np.arange(len(sim_dates)), rtol=1e-6, atol=1e-3)
    simulated = pd.DataFrame({"date": sim_dates, "S_simulated": sol.y[0], "E_simulated": sol.y[1], "I_simulated": sol.y[2], "R_simulated": sol.y[3], "D_simulated": sol.y[4]})
    simulated["new_cases_simulated"] = np.maximum(0, np.r_[np.nan, np.diff(simulated["R_simulated"] + simulated["I_simulated"] + simulated["D_simulated"])])
    simulated["new_deaths_simulated"] = np.maximum(0, np.r_[np.nan, np.diff(simulated["D_simulated"])])
    comparison = validation[["date", "new_cases_smoothed", "new_deaths_smoothed"]].merge(simulated, on="date", how="left")
    case_metrics = metrics(comparison["new_cases_smoothed"], comparison["new_cases_simulated"])
    death_metrics = metrics(comparison["new_deaths_smoothed"], comparison["new_deaths_simulated"])
    validation_row = pd.DataFrame([{
        "country": country, "calibration_period": "2020-03-01 to 2020-12-31", "validation_period": "2021-01-01 to 2021-12-31",
        "cases_mae": case_metrics["mae"], "cases_rmse": case_metrics["rmse"], "cases_correlation": case_metrics["correlation"],
        "deaths_mae": death_metrics["mae"], "deaths_rmse": death_metrics["rmse"], "deaths_correlation": death_metrics["correlation"],
        "status": "simulated SEIRD compared with later observed OWID series", "fit_type": "beta derived from median estimated Rt; no generic ML fit",
    }])
    parameters = pd.DataFrame([{
        "country": country, "beta": beta, "sigma": sigma, "gamma": gamma, "mu": mu, "incubation_days_assumption": incubation_days,
        "infectious_days_assumption": infectious_days, "rt_calibration_median": rt_median, "mortality_parameter_source": parameters_spec["mortality_transition_parameter"]["source"],
        "parameter_status": "beta estimated from approved Rt_estimated and explicitly sourced gamma/mu; not from intervention coefficients or reported CFR",
    }])
    parameters.to_csv(output_dir / "seird_parameters.csv", index=False)
    validation_row.to_csv(output_dir / "seird_validation.csv", index=False)
    comparison.to_csv(output_dir / "seird_replay_timeseries.csv", index=False, date_format="%Y-%m-%d")
    return parameters, validation_row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("owid_covid.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--seird-country")
    parser.add_argument("--seird-assumptions", type=Path, default=Path("seird_assumptions.json"))
    parser.add_argument("--validate-seird-assumptions", action="store_true")
    args = parser.parse_args()
    if args.validate_seird_assumptions:
        validate_seird_assumptions(args.seird_assumptions)
        print("SEIRD parameter gate passed")
        return
    args.output_dir.mkdir(parents=True, exist_ok=True)
    processed, audit = load_and_clean(args.input, args.output_dir / "owid_covid_processed.csv")
    waves = detect_waves(processed, args.output_dir / "epidemic_waves.csv")
    wave_sensitivity = {}
    for label, distance, prominence, height in (
        ("permissive", 21, 0.10, 0.02),
        ("selected", 28, 0.20, 0.05),
        ("strict_distance", 42, 0.20, 0.05),
    ):
        candidate = detect_waves(processed, None, distance, prominence, height, 20.0)
        wave_sensitivity[label] = {"rows": int(len(candidate)), "countries": int(candidate["country"].nunique()) if not candidate.empty else 0, "max_waves_per_country": int(candidate.groupby("country").size().max()) if not candidate.empty else 0}
    growth = estimate_growth(processed, waves, args.output_dir / "growth_rates.csv")
    rt = estimate_rt(processed, args.output_dir / "rt_estimates.csv")
    intervention = intervention_model(processed, rt, args.output_dir / "intervention_analysis.csv")
    mortality = mortality_model_data(processed, args.output_dir / "mortality_model_data.csv")
    mortality_results = mortality_regression(mortality, args.output_dir / "mortality_model_results.csv")
    report = {
        "audit": audit,
        "outputs": {
            "epidemic_waves": int(len(waves)), "growth_rates": int(len(growth)), "rt_estimates": int(len(rt)),
            "intervention_models": int(len(intervention)), "mortality_rows": int(len(mortality)),
            "mortality_complete_predictor_rows": int(mortality.dropna(subset=["median_age", "hospital_beds_per_thousand", "human_development_index", "gdp_per_capita", "lagged_case_fatality_ratio"]).shape[0]),
        },
        "stage_diagnostics": {
            "waves": {"input_country_rows": int(len(processed)), "input_missing_new_cases_smoothed": int(processed["new_cases_smoothed"].isna().sum()), "output_rows": int(len(waves)), "sensitivity": wave_sensitivity},
            "growth": {"output_rows": int(len(growth)), "model_variables": ["date", "new_cases_smoothed"]},
            "rt": {"output_rows": int(len(rt)), "valid_Rt_estimated": int(rt["Rt_estimated"].notna().sum()), "valid_OWID_reference": int(rt["reproduction_rate_owid_reference"].notna().sum()), "quality_flags": {str(k): int(v) for k, v in rt["rt_quality_flag"].value_counts(dropna=False).items()}},
            "intervention": {"output_rows": int(len(intervention)), "model_variables": ["Rt_estimated", "stringency_index_lag_7_or_14"]},
            "mortality": {"output_rows": int(len(mortality)), "complete_predictor_rows": int(mortality.dropna(subset=["median_age", "hospital_beds_per_thousand", "human_development_index", "gdp_per_capita", "lagged_case_fatality_ratio"]).shape[0])},
        },
        "assumptions": {
            "rt": "Cori renewal ratio using prior incidence only; serial interval mean 5 days and SD 2 days; estimates unavailable below a 20-case renewal denominator or above a 5x current/prior-seven-day-median continuity ratio; OWID reproduction_rate is reference only",
            "waves": "find_peaks distance 28 days, prominence max(10, 20% of country maximum), height max(20, 5% of maximum); sensitivity counts for permissive and stricter settings are recorded",
            "growth": "log-linear fit only from first detected wave start through its peak; r <= 0 has no positive doubling time",
            "intervention": "Ridge association with 7- and 14-day lagged stringency, chronological 80/20 split; not causal",
            "mortality": "cumulative deaths at 2021-12-31 divided by cumulative cases 14 days earlier; 7-day and 21-day denominator sensitivity included; 1000-case eligibility used only for regression; not IFR",
            "unsupported_stages": "WHO, OpenFlights, respiratory-virus generalisation, and metapopulation mobility are not run because those sources are not used in this OWID-only pipeline",
        },
        "status": "observations kept separate from calculated, estimated, and simulated outputs",
    }
    report["seird"] = "not run by task instruction; requires separate approval and documented parameters"
    (args.output_dir / "pipeline_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report["outputs"], indent=2))
    print(report["seird"])


if __name__ == "__main__":
    main()