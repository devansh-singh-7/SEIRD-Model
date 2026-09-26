# SEIRD Mechanics Validation v2

`SEIRD MECHANICS STATUS: GO`

## Time convention

Each row t after initialization is the interval-end state after [t-1,t]. The same beta scalar is used for the transition and recorded integrated flows: infections=S(t-1)-S(t), deaths=D(t)-D(t-1).

## Rt and beta

For these equations, `R0 = beta/(gamma+mu)` at full susceptibility and `Reff = beta*S/[N*(gamma+mu)]`. `Rt_estimated` is treated as effective Rt during calibration, so `beta(t) = Rt_estimated(t)*(gamma+mu)*N/S(t-1)` for the interval ending t. Validation uses the calibration-only median beta and no validation Rt.

## Mechanical checks

- nonnegative_compartments: `True`
- population_accounting: `True`
- no_spontaneous_infection: `True`
- monotonic_death_accumulation: `True`
- beta_alignment: `True`
- Rt_Reff_relationship: `True`
- consistent_time_indexing: `True`
- numerical_stability: `True`
- max_beta_alignment_error: `0.0`
- max_infection_balance_error: `0.0`
- max_Rt_Reff_error: `4.440892098500626e-16`

## What can be compared with approved inputs

| Model quantity | OWID quantity | Status |
|---|---|---|
| Simulated incident infections | reported confirmed new cases | NOT IDENTIFIABLE |
| Simulated I prevalence | reported confirmed new cases | NOT IDENTIFIABLE |
| Cumulative simulated infections (N-S) | reported cumulative confirmed cases | NOT IDENTIFIABLE |
| Simulated daily I→D flow | reported daily deaths | VALID WITH CAVEAT |
| Simulated cumulative D | reported cumulative deaths | VALID WITH CAVEAT |

Case metrics are descriptive only, not calibration validity evidence. No ascertainment rate, reporting delay, or parameter optimisation was introduced.

## Mortality

`mu*I` is retained as the instantaneous mortality flow and is exported at each interval start. The stored daily death total is its integrated interval flow `D(t)-D(t-1)`. Daily reported deaths are valid with caveat because an observation/reporting delay is not identified by approved inputs and was not fitted. Cumulative D comparison is supplementary only.

Descriptive validation case RMSE: `54433.53741796919`; daily-death RMSE: `139.11443452788365`. These do not establish forecast or case-calibration accuracy.
