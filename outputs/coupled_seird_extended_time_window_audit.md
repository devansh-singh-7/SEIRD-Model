# Coupled SEIRD Extended Time-Window Audit Report

**Audit Timestamp**: 2026-09-27T02:00:15.926441
**Primary Dataset**: `owid_covid.csv`
**Connectivity Layer**: Validated Airport Route Topology (`country_route_matrix.csv`)

---

## Executive Summary

Before extending the multi-country coupled SEIRD model beyond the baseline 2020 period (`2020-01-22` to `2020-12-31`), a rigorous chronological and variable-completeness audit of `owid_covid.csv` and `rt_estimates.csv` was conducted. The objective was to determine the true empirical date boundaries and identify which historical periods satisfy the scientific eligibility criteria required to support coupled epidemiological modeling.

### Key Audit Findings
- **Raw Data Date Range**: `2020-01-01` to `2026-08-30` (Total 2434 calendar days). *(Note: The dataset does NOT end on 2026-12-31; the empirical maximum observation is 2026-08-30).*
- **Data Availability vs Model Availability**: While raw case and death accumulators exist through August 2026, **dynamic transmission modeling is only defensible through 2022-12-31**.
- **Recommended Extended Simulation Window**: `2020-01-22` to `2022-12-31` (1,075 days, 153.6 weeks).
- **Defensible Feasible Years**: **2021** and **2022**.
- **Excluded Ineligible Years**: **2023, 2024, 2025, and 2026**.

---

## 1. Yearly Row Counts and Date Coverage

| Year | Rows | Unique Dates | Unique Locations | Country Locations |
|---|---|---|---|---|
| 2020 | 93,636 | 366 | 259 | 241-247 |
| 2021 | 94,027 | 365 | 260 | 241-247 |
| 2022 | 94,574 | 365 | 262 | 241-247 |
| 2023 | 92,927 | 365 | 261 | 241-247 |
| 2024 | 91,360 | 366 | 251 | 241-247 |
| 2025 | 90,885 | 365 | 249 | 241-247 |
| 2026 | 60,258 | 242 | 249 | 241-247 |

**Observation**: The raw dataset contains 617,667 rows spanning 2020 through mid-2026. Country-level locations remain stable between 241 and 247 across all years.

---

## 2. Modelling Variable Availability by Year

The SEIRD model requires dynamic transmission rates $\beta_j(t)$ derived from $R_t$, population totals $N_j$, and cumulative deaths/cases for validation and initial seeding. The table below reports the missingness percentage for key variables in `owid_covid.csv`:

| Year | total_cases | new_cases | total_deaths | new_deaths | reproduction_rate | population | stringency_index |
|---|---|---|---|---|---|---|---|
| 2020 | 2.3% | 2.3% | 2.3% | 2.3% | **47.1%** | 0.4% | **24.3%** |
| 2021 | 1.6% | 1.7% | 1.6% | 1.7% | **25.0%** | 0.4% | **24.5%** |
| 2022 | 1.6% | 1.7% | 1.6% | 1.7% | **21.7%** | 0.4% | **24.5%** |
| 2023 | 0.9% | 1.8% | 0.9% | 1.5% | **99.6%** | 0.4% | **100.0%** |
| 2024 | 0.3% | 1.9% | 0.3% | 1.5% | **100.0%** | 0.4% | **100.0%** |
| 2025 | 0.0% | 1.7% | 0.0% | 1.2% | **100.0%** | 0.4% | **100.0%** |
| 2026 | 0.0% | 1.7% | 0.0% | 1.2% | **100.0%** | 0.4% | **100.0%** |

> [!IMPORTANT]
> **Surveillance Regime Transition (Post-2022 Collapse)**:
> - In **2020-2022**, `reproduction_rate` missingness was 21.7% - 47.1% (with active estimation for all major transmission centers).
> - In **2023**, `reproduction_rate` missingness surged to **99.6%** (practically 100%).
> - In **2024-2026**, `reproduction_rate` is **100.0% missing** in `owid_covid.csv`.
> - Similarly, Oxford Blavatnik School's `stringency_index` officially terminated data collection on **2022-12-31**, resulting in **100.0% missingness** from 2023 onwards.

---

## 3. Availability of Rt_estimated in the Project Pipeline

The project generates `outputs/rt_estimates.csv` from case incidence series. The empirical availability of non-null $R_t$ estimates across the 237 OWID countries is summarized below:

| Year | Total Country-Days | Non-Null Rt Rows | Null Rt Rows | Empirical Rt Coverage | Feasibility Status |
|---|---|---|---|---|---|
| 2020 | 86,220 | 32,178 | 54,042 | 37.3% | **FEASIBLE** |
| 2021 | 86,140 | 55,929 | 30,211 | 64.9% | **FEASIBLE** |
| 2022 | 86,141 | 51,381 | 34,760 | 59.6% | **FEASIBLE** |
| 2023 | 85,482 | 21,798 | 63,684 | 25.5% | **INSUFFICIENT** |
| 2024 | 85,138 | 11,133 | 74,005 | 13.1% | **INSUFFICIENT** |
| 2025 | 84,680 | 5,963 | 78,717 | 7.0% | **INSUFFICIENT** |
| 2026 | 56,144 | 1,590 | 54,554 | 2.8% | **INSUFFICIENT** |

### Epidemiological Significance of the Coverage Drop
1. **2020 (Baseline)**: Coverage is 37.3% because early 2020 had zero cases in most countries prior to February/March 2020. Once epidemics established, coverage was high.
2. **2021 (Peak Pandemic)**: Highest empirical coverage at 64.9% (55,929 country-days). Active global genomic and PCR surveillance.
3. **2022 (Omicron Era)**: Strong coverage at 59.6% (51,381 country-days). Continued high-volume reporting despite home antigen test emergence.
4. **2023-2026 (Surveillance Dismantling)**: Rt non-null rows drop precipitously from 25.5% (2023) to 13.1% (2024), 7.0% (2025), and 2.8% (2026). Any SEIRD model attempting to run across 2023-2026 would be forced to rely on static historical medians for >85% of country-days, fabricating dynamic transmission signals where none exist in the empirical data.

---

## 4. Assessment of Fixed Epidemiological Assumptions Over Time

| Parameter / Assumption | Baseline 2020 Value | 2021-2022 Assessment | Post-2022 Assessment | Recommended Handling |
|---|---|---|---|---|
| $\sigma$ (Incubation rate) | 0.1961 (5.1 days) | Ancestral/Alpha/Delta: ~4-5 d. Omicron: ~3.4 d. | Sublineages evolved shorter incubation. | **RETAIN 0.1961** with documented variant limitation. |
| $\gamma$ (Recovery rate) | 0.1250 (8.0 days) | Shedding duration shortened slightly in vaccinated/Omicron. | Endemic shedding ~5-6 d. | **RETAIN 0.1250** with documented limitation. |
| $\mu$ (Mortality rate) | 0.00083 (IFR ~0.66%) | Severe IFR reduction due to vaccination and treatment. | Near influenza-level IFR (<0.05%). | **RETAIN with STRONG warning**; deaths will be simulated based on 2020 baseline IFR. |
| $\beta_j(t) / R_t$ Mapping | $\beta_j(t) = R_t(t) \cdot (\gamma+\mu) \frac{N_j}{S_j(t)}$ | Valid when $S_j(t) > 0$. $R_t$ derived from reported cases. | Case reporting collapsed; $S_j(t)$ depleted in SEIRD. | **VALID for 2021-2022**; degenerate post-2022. |
| $\alpha$ Sensitivity Scenarios | [0.0, 0.001, 0.01, 0.05] | Consistent operational sensitivity proxy. | Static flight network ignores border reopenings. | **RETAIN all 4 scenarios** as sensitivity parameters. |
| Airport Route Topology | Static 225-country matrix | Flight bans were eased gradually; network topology largely restored. | Post-pandemic recovery; route shifts. | **RETAIN validated static topology**; documented limitation. |

---

## 5. Model Eligibility and Time-Window Decision

### Documented Eligibility Criteria for Extension
A historical simulation period is eligible for coupled SEIRD modeling if and only if:
1. **Dynamic $R_t$ Signal**: Country-level $R_t$ estimates are empirically available for at least 50% of active transmission days.
2. **Epidemiological Context**: Policy stringency or behavioral context data exists to interpret transmission changes.
3. **Compartment Interpretability**: The absence of a waning-immunity parameter ($R \to S$) does not completely degenerate susceptible availability ($S/N$).

### Decision: Extended Time Window Bounded to 2020-01-22 through 2022-12-31
- **Start Date**: `2020-01-22` (Validated baseline start date)
- **End Date**: `2022-12-31` (End of OxCGRT tracking and active WHO global surveillance)
- **Total Duration**: 1,075 days (35.7 months)
- **Included Periods**: Ancestral Wave (2020), Alpha/Beta/Gamma Waves (Spring 2021), Delta Wave (Autumn 2021), Omicron BA.1/BA.2 Waves (2022).
- **Explicitly Excluded Period**: 2023-01-01 to 2026-08-30 (Surveillance collapse; model non-identifiable).

---

## 6. Documented Limitations of the Extended Window

1. **Absorbing Recovered Compartment (No Waning Immunity)**: The classical SEIRD architecture does not permit reinfection. In reality, Omicron subvariants frequently reinfected individuals who recovered from Ancestral or Delta strains.
2. **Constant Infection Fatality Ratio (IFR)**: The mortality parameter $\mu = 0.00083$ reflects pre-vaccination early-pandemic severity. Because vaccination is not modeled, simulated cumulative deaths in 2021-2022 will overestimate real-world reported deaths.
3. **Static Route Connectivity Proxy**: The route matrix represents pre-pandemic international flight routes. While international travel resumed extensively by 2022, border closures in 2020-2021 were heterogeneous.
4. **Alpha Remains Operational Sensitivity**: $\alpha$ is NOT an empirically measured passenger travel fraction and must NOT be interpreted as real passenger volume.