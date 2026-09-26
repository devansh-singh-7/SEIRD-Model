# Single-Country SEIRD Report

SINGLE-COUNTRY SEIRD STATUS: GO

Country: **United Kingdom**

The country was selected before fitting using data sufficiency, not model fit.

## Chronological design
Calibration: `2020-03-10` to `2021-08-20` (529 rows)
Validation: `2021-08-21` to `2021-12-31` (133 rows)

## Initial conditions
E0=sum observed new_cases_smoothed over preceding incubation+infectious window; I0=sum over preceding infectious window; D0=observed total_deaths; R0=observed total_cases-E0-I0-D0; S0=population-E0-I0-R0-D0
Confirmed cases are an observed surveillance proxy, not true infections; R0 and S0 inherit under-ascertainment and reporting limitations.

## Results
Validation case RMSE: `54410.55923058267`; validation death RMSE: `137.73457746743134`; case peak-date error: `0.0` days; case peak-size error: `-165757.15141934188`.

## Sanity tests
All reported sanity tests passed: nonnegative_compartments, population_conserved, deaths_non_decreasing, recoveries_non_decreasing, zero_initial_infection_no_spontaneous_infection, higher_beta_increases_transmission, higher_gamma_changes_duration, sigma_changes_exposure_timing, solver_stable

## Limitations
- Observed confirmed cases are surveillance proxies, not true infections.
- R0/E0/I0 initialization uses observed smoothed incidence windows and inherits reporting under-ascertainment.
- The 8-day infectious/recovery period is an explicit operational assumption anchored to viable-virus evidence.
- The IFR and competing-hazard mu are early-pandemic evidence and not country/variant-specific.
- Validation beta is held at the calibration-period median; no future Rt or intervention model is used.

## Plots
- `outputs/seird_plots/observed_vs_simulated.png`
- `outputs/seird_plots/compartments.png`
- `outputs/seird_plots/sensitivity_infections.png`
