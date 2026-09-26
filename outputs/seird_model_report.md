# Country-Level SEIRD Stage Report

## SEIRD PARAMETER STATUS: READY

The country-level SEIRD model was not run. The parameter gate now passes using traceable peer-reviewed evidence and explicit derivations/assumptions; separate simulation authorization is still required.

Only the approved OWID outputs were inspected. No airport, WHO, VIW_FNT, web, or other external data was used. The original `owid_covid.csv` was not modified.

## Approved Inputs Audited

- `owid_covid_processed.csv`: 569,945 rows, 237 countries, 2020-01-01 through 2026-08-30.
- `rt_estimates.csv`: 569,945 country-date rows; 179,972 valid `Rt_estimated` values and 389,973 unavailable values under the approved data-quality rules.
- `mortality_model_data.csv`: 221 country rows; outcome is cumulative deaths on 2021-12-31 divided by cumulative cases 14 days earlier.
- `mortality_model_results.csv`: country-level regression result table; it does not provide a mechanistic mortality transition rate.

## Parameter Audit

| Parameter | Status | Reason |
|---|---|---|
| `beta` | Method ready, numeric beta conditional | `Rt_estimated` supports `beta = Rt_estimated * (gamma + mu)` under the implemented equations. |
| `sigma` | 0.1960784314 1/day | Derived as `1 / 5.1`; primary early-pandemic incubation source. |
| `gamma` | 0.125 1/day | Derived as `1 / 8`; explicit operational assumption anchored to viable-virus evidence. |
| `mu` | 0.0008304812 1/day | Derived from Verity IFR 0.0066 using `mu = gamma*p/(1-p)`; OWID CFR is not used. |

The Plan specifies symbolic compartments and equations. Numerical values are now traceable to Lauer, Wu, Cevik, Wu, and Verity evidence, with variant and applicability limitations documented in the parameter evidence files.

## Equations Prepared But Not Run

$$
\frac{dS}{dt} = -\beta \frac{SI}{N}
$$

$$
\frac{dE}{dt} = \beta \frac{SI}{N} - \sigma E
$$

$$
\frac{dI}{dt} = \sigma E - (\gamma + \mu)I
$$

$$
\frac{dR}{dt} = \gamma I
$$

$$
\frac{dD}{dt} = \mu I
$$

No calibration, simulation, validation metrics, or plots were fabricated.

## Outputs Not Generated

The following files were intentionally not created because simulation was not run:

- `seird_country_parameters.csv`
- `seird_calibration_results.csv`
- `seird_validation.csv`
- Representative SEIRD plots

## Required To Proceed

Authorize a single-country validation run after reviewing the primary and sensitivity scenarios. Intervention coefficients remain excluded from calibration, and the approved OWID CFR-like outcome remains excluded from the `mu` derivation.
