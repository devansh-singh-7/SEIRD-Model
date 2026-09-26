# Pre-Extension Final Audit Report

`PRE-EXTENSION STATUS: GO`

**Audit timestamp**: 2026-09-27T02:00:15.928868

---

## Part 1: Pre-Extension Final Check

### 1.1 Source File Integrity

| File | SHA-256 (truncated) | Status |
|---|---|---|
| `cleaned_airports.csv` | `f0713c11c6ec7c00e363a065...` | ? Present |
| `cleaned_routes.csv` | `fc1b0a84e4b30cadf3e085fe...` | ? Present |
| `owid_covid.csv` | `040913e2864648573341234c...` | ? Present |

### 1.5 Country Universe Reconciliation

| Metric | Count |
|---|---|
| OWID all locations (incl. aggregates) | 262 |
| OWID filtered (excl. aggregates) | 247 |
| OWID processed countries | 237 |
| Route matrix countries | 225 |
| Route international countries | 225 |
| Simulation countries (actual) | 217 |
| Previously reported OWID countries | 237 |
| Previously reported connected countries | 225 |
| Previously reported modeled countries | 217 |

**Countries in simulation but NOT in route matrix** (5): These are isolated OWID territories modeled with alpha=0.
  Montserrat, Myanmar, Palestine, Saint Helena, Syria

### 1.6 Simulation Date Verification

- Expected: 2020-01-22 to 2020-12-31 (345 days)
- Actual: 2020-01-22 to 2020-12-31 (345 days)
- Match: ?

### 1.7 Alpha Scenario Verification

- Expected scenarios: ['SCEN_0_DECOUPLED', 'SCEN_1_LOW_COUPLING', 'SCEN_2_MODERATE_COUPLING', 'SCEN_3_HIGH_COUPLING']
- Actual scenarios: ['SCEN_0_DECOUPLED', 'SCEN_1_LOW_COUPLING', 'SCEN_2_MODERATE_COUPLING', 'SCEN_3_HIGH_COUPLING']
- Match: ?
- Expected alphas: [0.0, 0.001, 0.01, 0.05]
- Actual alphas: [np.float64(0.0), np.float64(0.001), np.float64(0.01), np.float64(0.05)]
- Match: ?

### 1.8 SEIRD Parameter Verification

| Parameter | Expected | Actual | Match |
|---|---|---|---|
| sigma | 0.19607843137254904 | 0.19607843137254904 | ? |
| gamma | 0.125 | 0.125 | ? |
| mu | 0.0008304811757600161 | 0.0008304811757600161 | ? |
| removal_rate | 0.12583048117576 | 0.12583048117576 | ? |

### 1.9 Initial Seed Country Verification

- Reported seeds (7): ['China', 'Germany', 'Japan', 'South Korea', 'Spain', 'Thailand', 'United States']
- Independently verified (7): ['China', 'Germany', 'Japan', 'South Korea', 'Spain', 'Thailand', 'United States']
- Consistent: ?

### 1.10-1.14 Mechanical Validation Checks

| Check | Result | Status |
|---|---|---|
| Non-negative compartments | min values: {'S': 1844.0, 'E': 0.0, 'I': 0.0, 'R': 0.0, 'D': 0.0} | PASS ? |
| Population conservation | max error: 5.72e-06 | PASS ? |
| Monotonic deaths | -- | PASS ? |
| Monotonic recoveries | -- | PASS ? |
| No spontaneous infection (alpha=0) | max I nonseed: 0.00e+00 | PASS ? |
| Numerical stability | NaN: 0, Inf: 0 | PASS ? |
| Isolated countries Psi=0 | 5 isolated in sim | PASS ? |

### 1.18-1.20 Guardrail Checks

- Alpha interpretation: `ALPHA STATUS: SENSITIVITY ONLY` -- ? Correctly marked as sensitivity-only
- Route language: ? Potential violations: ['passenger volume']
- Observation model: ? No cases=I violations

### Warnings

- Validation report may contain route-as-passenger language: ['passenger volume']

---

## Part 2: Time-Window Audit

- OWID date range: 2020-01-01 to 2026-08-30
- Country-level locations: 247

### Yearly Summary

| Year | Rows | Dates | Countries |
|---|---|---|---|
| 2020 | 93,636 | 366 | 259 |
| 2021 | 94,027 | 365 | 260 |
| 2022 | 94,574 | 365 | 262 |
| 2023 | 92,927 | 365 | 261 |
| 2024 | 91,360 | 366 | 251 |
| 2025 | 90,885 | 365 | 249 |
| 2026 | 60,258 | 242 | 249 |

### Rt_estimated Availability

- Date range: 2020-01-01 to 2026-08-30
- Countries: 237

| Year | Rows | Countries | Rt Non-Null | Rt Null |
|---|---|---|---|---|
| 2020 | 86,220 | 236 | 32,178 | 54,042 |
| 2021 | 86,140 | 236 | 55,929 | 30,211 |
| 2022 | 86,141 | 237 | 51,381 | 34,760 |
| 2023 | 85,482 | 236 | 21,798 | 63,684 |
| 2024 | 85,138 | 234 | 11,133 | 74,005 |
| 2025 | 84,680 | 232 | 5,963 | 78,717 |
| 2026 | 56,144 | 232 | 1,590 | 54,554 |

### Key Variable Missingness by Year

#### 2020

| Variable | Missing % |
|---|---|
| total_cases | 2.3% |
| new_cases | 2.3% |
| new_cases_smoothed | 3.6% |
| total_deaths | 2.3% |
| new_deaths | 2.3% |
| new_deaths_smoothed | 3.6% |
| reproduction_rate | 47.1% |
| population | 0.4% |
| stringency_index | 24.3% |

#### 2021

| Variable | Missing % |
|---|---|
| total_cases | 1.6% |
| new_cases | 1.7% |
| new_cases_smoothed | 1.6% |
| total_deaths | 1.6% |
| new_deaths | 1.7% |
| new_deaths_smoothed | 1.6% |
| reproduction_rate | 25.0% |
| population | 0.4% |
| stringency_index | 24.5% |

#### 2022

| Variable | Missing % |
|---|---|
| total_cases | 1.6% |
| new_cases | 1.7% |
| new_cases_smoothed | 1.6% |
| total_deaths | 1.6% |
| new_deaths | 1.7% |
| new_deaths_smoothed | 1.6% |
| reproduction_rate | 21.7% |
| population | 0.4% |
| stringency_index | 24.5% |

#### 2023

| Variable | Missing % |
|---|---|
| total_cases | 0.9% |
| new_cases | 1.8% |
| new_cases_smoothed | 1.8% |
| total_deaths | 0.9% |
| new_deaths | 1.5% |
| new_deaths_smoothed | 1.5% |
| reproduction_rate | 99.6% |
| population | 0.4% |
| stringency_index | 100.0% |

#### 2024

| Variable | Missing % |
|---|---|
| total_cases | 0.3% |
| new_cases | 1.9% |
| new_cases_smoothed | 1.9% |
| total_deaths | 0.3% |
| new_deaths | 1.5% |
| new_deaths_smoothed | 1.5% |
| reproduction_rate | 100.0% |
| population | 0.4% |
| stringency_index | 100.0% |

#### 2025

| Variable | Missing % |
|---|---|
| total_cases | 0.0% |
| new_cases | 1.7% |
| new_cases_smoothed | 1.7% |
| total_deaths | 0.0% |
| new_deaths | 1.2% |
| new_deaths_smoothed | 1.2% |
| reproduction_rate | 100.0% |
| population | 0.4% |
| stringency_index | 100.0% |

#### 2026

| Variable | Missing % |
|---|---|
| total_cases | 0.0% |
| new_cases | 1.7% |
| new_cases_smoothed | 1.7% |
| total_deaths | 0.0% |
| new_deaths | 1.2% |
| new_deaths_smoothed | 1.2% |
| reproduction_rate | 100.0% |
| population | 0.4% |
| stringency_index | 100.0% |

---

## Part 3: Extension Design Assessment

- OWID max date: 2026-08-30
- Rt max date: 2026-08-30
- Limiting factor: Rt_estimated availability determines maximum simulation date, since beta(t) = Rt(t) * (gamma+mu) * N/S(t)
- Recommended extension end: 2022-12-31
- Feasible years: [2021, 2022]

### Year-by-Year Feasibility

| Year | Rt Coverage | Insufficient Countries | Feasible |
|---|---|---|---|
| 2020 | 37.3% | 20 | ? |
| 2021 | 64.9% | 16 | ? |
| 2022 | 59.6% | 9 | ? |
| 2023 | 25.5% | 8 | ? |
| 2024 | 13.1% | 5 | ? |
| 2025 | 7.0% | 3 | ? |
| 2026 | 2.8% | 3 | ? |

### Parameter Regime Assessment for Extension

**sigma**: RETAIN with explicit limitation documentation; variant-specific sigma would require additional parameter evidence
  - Post-2020 concern: Omicron and later variants have shorter incubation (3.42 d vs 5.1 d); using 2020 sigma throughout is a documented limitation

**gamma**: RETAIN with explicit limitation documentation
  - Post-2020 concern: Omicron viable-virus shedding 5.16 d vs ancestral 8 d; infectious period shortens

**mu**: RETAIN with STRONG limitation warning; IFR evolution is NOT modeled
  - Post-2020 concern: IFR changed substantially with vaccination, variants, treatment improvements; 2020 IFR applied to 2021+ is a significant simplification

**alpha**: RETAIN as sensitivity parameter with documented limitation
  - Post-2020 concern: Travel restrictions were implemented and lifted asymmetrically; static alpha does not capture border policy dynamics

**route_network**: RETAIN with explicit caveat that network does not model border closures or route suspensions
  - Post-2020 concern: Actual flight routes changed dramatically during 2020-2022 due to border closures; static topology is a simplification for the entire period

**beta_rt_mapping**: RETAIN; Rt_estimated naturally absorbs some time-varying effects, but its interpretation changes with vaccination and testing capacity
  - Post-2020 concern: If Rt_estimated is computed from OWID new_cases using Cori method, it implicitly captures some intervention/vaccination/variant effects through the case curve

### Documented Limitations for Extended Period

1. Fixed biological parameters (sigma, gamma, mu) do not reflect variant evolution (Alpha, Delta, Omicron)
1. IFR 0.66% from early 2020 does not account for vaccination, improved treatment, or variant virulence changes
1. Static flight route network does not model border closures, travel bans, or route suspensions
1. Alpha remains a sensitivity parameter; static alpha does not capture time-varying border policies
1. Vaccination is not modeled: no immunity waning, booster effects, or reduced susceptibility
1. Reinfection is not modeled: the SEIRD R compartment is absorbing
1. Ascertainment rate changes (testing capacity evolution) are not explicitly modeled
1. Confirmed cases are not directly comparable to the model I compartment without an observation model

---

## Final Status: `PRE-EXTENSION STATUS: GO`
