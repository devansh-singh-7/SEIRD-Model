# SEIRD Calibration Diagnostics

## Decision

`CALIBRATION METHOD: REQUIRES REVISION`

The existing fixed-beta run is reproducible and its mathematical solver checks pass, but it is a mechanistic replay/diagnostic baseline only. It is not a successful forecast and must not be expanded to all countries.

## Scope and chronology

United Kingdom; calibration `2020-03-10` to `2021-08-20` (529 days); validation `2021-08-21` to `2021-12-31` (133 days). The validation beta is the calibration median `0.129453` per day, so it does not use validation-period Rt. Calibration Rt is contemporaneous/retrospective because its renewal estimate uses incidence at t and prior incidence; it is not a prospective forecast input.

## Why timing can look plausible while magnitude fails

Validation maxima both fall on the endpoint, 2021-12-31, giving a 0-day peak-date error. That is not agreement: observed peak incidence is 166,404.14, simulated peak incidence is 646.99, and the peak-size error is -165,757.15. Case RMSE is 54,410.56; correlation is 0.671.

The calibration-period beta varies with Rt, but validation freezes it at an R-equivalent `beta/(gamma+mu)` of 1.029. It therefore cannot represent the marked validation-period change in the audited Rt series. More fundamentally, initialization makes all historical confirmed cases the simulated non-susceptible history (N−S0 = 502); confirmed cases are not total infections. Neither the initial state nor the comparison has an ascertainment factor or reporting-delay model.

## Beta verification

For the implemented equations, removal from I is `(gamma + mu) I`, so the recorded calibration beta exactly satisfies `beta = Rt_estimated * (gamma + mu)` (maximum numerical difference 9.71e-17`). This maps `Rt` to beta only if Rt is interpreted at full susceptibility. The renewal-ratio Rt derived from incidence is normally effective Rt; under the exact ODE, `Reff = beta*S/[N*(gamma+mu)]`. An effective Rt input requires `beta = Rt*(gamma+mu)*N/S`, plus an explicit treatment of depletion, vaccination, reinfection, and reporting.

There is also a date-alignment defect: the state on date t is advanced with the previous row's beta, while that row's reported infection flow is calculated with beta(t). This must be aligned before using a fitted objective.

## Rt smoothing, availability, and temporal use

`Rt_estimated` is a Cori renewal ratio using OWID `new_cases_smoothed` at t and earlier incidence, with a discretised gamma serial interval (mean 5 days; SD 2 days). There are no missing Rt values in either the selected calibration (0) or validation (0) periods, and none was imputed. The estimator code does not index a future date. The provenance of OWID's supplied 7-day smoothing still needs to state whether it is trailing rather than centred before the input can be called real-time; in either event, calibration is a retrospective replay because beta at t is informed by observed incidence at t. Smoothing also damps sharp changes, while the validation median-beta rule removes time variation altogether.

## Observation and mortality models

`simulated I` is prevalence and should not be compared with reported new cases. The current code instead compares simulated incident infections with reported confirmed cases, but that is still not direct. A defensible case target is an explicit delayed reporting process applied to incident infections, with documented ascertainment. The approved inputs do not provide a validated country-date ascertainment fraction or reporting-delay distribution; testing fields do not, by themselves, identify one. Do not silently declare reported cases to be infections.

For deaths, `mu*I` is the implemented daily I→D flow and `D` is cumulative simulated deaths. Daily observed deaths should be compared to same-date daily simulated death flow after any explicit reporting delay; cumulative deaths are supplementary only. Same-day daily validation gives death RMSE 137.73 and correlation 0.022. A ±30-day lag scan is diagnostic only (best correlation 0.471 at lag -30); no lag was selected to improve fit.

## Calibration comparison

| Strategy | Case RMSE | Death RMSE | Case correlation | Death correlation | Peak-date error | Peak-size error |
|---|---:|---:|---:|---:|---:|---:|
| A. Fixed-beta replay | 54,410.56 | 137.73 | 0.671 | 0.022 | 0 days | -165,757.15 |
| B. Formal restricted fit | Not estimable | Not estimable | Not estimable | Not estimable | Not estimable | Not estimable |

The Plan supports fitting transmission rates from historical case curves, so a formal fit is warranted in principle. It cannot validly begin by treating reported cases as total infections. First approve an observation model and a small, allowed fitted set (for example a low-dimensional beta multiplier); keep sigma, gamma, and mu sourced rather than fitting all rates. Fit calibration dates only, freeze the fit, then score the unchanged validation period. Strategy B is not scored here because inventing a reporting factor or using validation data to infer it would violate the modelling guardrails.

## Re-run sensitivity scenarios

| Scenario | Case RMSE | Death RMSE |
|---|---:|---:|
| PRIMARY | 54,410.56 | 137.73 |
| LOWER_DURATION_HIGH_RATE | 52,045.87 | 129.02 |
| UPPER_DURATION_LOW_RATE | 54,653.11 | 137.50 |

The poor magnitude/death fit persists across every supplied scenario. The scenarios are evidence-based sensitivity cases, not candidates to select for lower error.

## Required revision gate

1. Align beta, ODE transition, and daily-flow dates; state whether Rt is effective or full-susceptibility.
2. Document and approve explicit case/death observation mappings, including ascertainment and reporting-delay treatment.
3. Pre-specify a restricted, project-permitted calibration objective on calibration dates only.
4. Freeze fitted quantities before validation and report daily case/death and supplementary cumulative-death diagnostics.
5. Do not expand to all countries or run airport/mobility work until the revised method is documented and validated.

The machine-readable findings are in `seird_calibration_diagnostics.json`; the strategy table is in `seird_calibration_comparison.csv`.
