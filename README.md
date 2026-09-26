# Multi-Country Coupled SEIRD Epidemic Model with Air Route Mobility

**M.Sc. Big Data Analytics — Semester 1 End-Semester Project**  
**Department of Computational and Data Sciences (CDS)**  
**Author**: Devansh Singh (`devanshsingh159753@gmail.com`)  
**GitHub Repository**: [https://github.com/devansh-singh-7/SEIRD-Model.git](https://github.com/devansh-singh-7/SEIRD-Model.git)

---

## Executive Summary

This repository contains the complete implementation, mechanical verification, chronological audit, and multi-scenario sensitivity evaluation of a **Coupled Multi-Country SEIRD Epidemiological Model**. The model couples national SEIRD compartmental systems across **217 countries** (representing **7.895 billion people**) using an international airline route-connectivity proxy constructed from verified OpenFlights network topology (`cleaned_airports.csv` and `cleaned_routes.csv`), driven by dynamic effective reproduction rates $R_t(t)$ estimated from Our World in Data (`owid_covid.csv`).

The project incorporates strict **AI and scientific modeling guardrails**, ensuring mass conservation, non-negative states, monotonic absorbing compartments, and full transparency regarding the non-identifiability of travel volumes.

---

## Project Status

| Component | Status | Validation Summary |
|---|---|---|
| **Mobility Network Topology** | `MOBILITY NETWORK STATUS: GO` | 225 connected countries, 4,697 directed international edges |
| **SEIRD Mechanics** | `SEIRD MECHANICS STATUS: GO` | Mass conservation error $< 10^{-5}$, zero spontaneous infection |
| **Alpha Identifiability** | `ALPHA STATUS: SENSITIVITY ONLY` | $\alpha$ is non-identifiable from topology; sensitivity scenarios evaluated |
| **Pre-Extension Audit (2020)** | `PRE-EXTENSION STATUS: GO` | Baseline 345-day window verified, 217 countries reconciled |
| **Extended Model (2020–2022)** | `EXTENDED MODEL STATUS: GO` | 1,075 days, 933,100 state rows, zero numerical instability |
| **Overall Scientific Verdict** | **`VALIDATED SENSITIVITY MODEL`** | Structurally validated across 4 approved operational $\alpha$ scenarios |

---

## Quick Start: How to Run the Models

All scripts use the project virtual environment (`.venv/Scripts/python.exe` or standard `python`):

### 1. Run the Primary Extended Coupled Simulation (2020–2022)
To see the complete multi-country coupled SEIRD model running across all 217 countries, 1,075 days, and 4 sensitivity scenarios:
```bash
python coupled_seird_extended_simulation.py
```
* **Execution Time**: ~25 seconds.
* **Outputs Generated**:
  * `outputs/coupled_seird_extended_simulation.csv` (Full daily state matrix: 933,100 rows)
  * `outputs/coupled_seird_extended_country_summary.csv` (Peak dates, arrival timing, cumulative metrics)
  * `outputs/coupled_seird_extended_scenario_comparison.csv` (Cross-scenario sensitivity aggregates)
  * `outputs/coupled_seird_extended_network_effects.csv` (Imported pressure and baseline differentials)
  * `outputs/coupled_seird_extended_validation.md` & `.json` (Full validation metrics)

### 2. Run the Baseline 2020 Coupled Simulation (2020-01-22 to 2020-12-31)
To run the original 345-day benchmark model:
```bash
python coupled_seird_simulation.py
```

### 3. Run the Pre-Extension & Chronological Time-Window Audit
To reproduce the independent data completeness audit and source file integrity checks:
```bash
python pre_extension_audit.py
```

### 4. Run the Standalone Single-Country SEIRD Model
To inspect the single-country calibration and diagnostics:
```bash
python seird_single_country.py
```

### 5. Run the Mobility Route Network Preprocessing
To re-generate the international route connectivity matrices from raw airport/route catalogs:
```bash
python mobility_network.py
```

---

## Mathematical Formulation

The coupled multi-country system models each country $j \in \{1, \dots, M\}$ ($M = 217$) via continuous-time ordinary differential equations stepped daily using Runge-Kutta 4(5) numerical integration (`solve_ivp` with absolute and relative error tolerances of $10^{-7}$):

$$\begin{aligned}
\frac{dS_j}{dt} &= -\lambda_j(t) S_j(t) \\
\frac{dE_j}{dt} &= \lambda_j(t) S_j(t) - \sigma E_j(t) \\
\frac{dI_j}{dt} &= \sigma E_j(t) - (\gamma + \mu) I_j(t) \\
\frac{dR_j}{dt} &= \gamma I_j(t) \\
\frac{dD_j}{dt} &= \mu I_j(t)
\end{aligned}$$

### Force of Infection & Network Coupling
$$\lambda_j(t) = \beta_j(t) \left[ (1 - \alpha_j) \frac{I_j(t)}{N_j} + \alpha_j \Psi_j(t) \right]$$

where:
* **Imported Infectious Pressure**:
  $$\Psi_j(t) = \sum_{i \neq j} Q_{ji} \frac{I_i(t)}{N_i}$$
* **Inbound-Normalized Route Matrix**:
  $$Q_{ji} = \frac{C_{ji}}{\sum_{k} C_{jk}}$$
  where $C_{ji}$ is the scheduled direct commercial flight route count from origin $i$ to destination $j$.
* **Time-Varying Transmission Rate**:
  $$\beta_j(t) = R_{t,j}(t) \cdot (\gamma + \mu) \cdot \frac{N_j}{S_j(t)}$$
  guaranteeing exact mathematical equivalence to the Cori renewal equation effective reproduction number.

### Fixed Epidemiological Parameters
* Incubation rate: $\sigma = 0.196078\ \text{day}^{-1}$ (Mean incubation: 5.10 days)
* Recovery rate: $\gamma = 0.125000\ \text{day}^{-1}$ (Mean infectious duration: 8.00 days)
* Mortality transition parameter: $\mu = 0.00083048\ \text{day}^{-1}$ (IFR ~0.66%)
* Removal rate: $\gamma + \mu = 0.12583048\ \text{day}^{-1}$

---

## Approved Alpha Sensitivity Scenarios

Because absolute passenger travel volumes are unobserved in the approved route network, $\alpha$ is treated as an operational sensitivity parameter, evaluated across four standardized scenarios:

| Scenario ID | $\alpha$ Value | Description | Countries Reached ($\ge 1\ I$) | Global Peak Infectious | Global Peak Date |
|---|---|---|---|---|---|
| `SCEN_0_DECOUPLED` | `0.0` | Decoupled baseline; zero cross-border transmission | **7** (Seeds only) | 49,900 | 2022-12-31 |
| `SCEN_1_LOW_COUPLING` | `0.001` | Low international transmission coupling | **18** | 46,249 | 2022-12-31 |
| `SCEN_2_MODERATE_COUPLING` | `0.01` | Moderate international transmission coupling | **53** | 25,867 | 2022-12-31 |
| `SCEN_3_HIGH_COUPLING` | `0.05` | High international transmission coupling | **108** | 10,490 | 2022-12-31 |

### Key Sensitivity Findings
1. **Zero Spontaneous Infection**: In the decoupled baseline ($\alpha = 0$), infection remains strictly confined to the 7 initial seed nations (China, Germany, Japan, South Korea, Spain, Thailand, United States). Non-seed nations remain at exactly $0.00 \times 10^0$ infections.
2. **Monotonic Dissemination**: Countries reached scales monotonically: $7 \to 18 \to 53 \to 108$ as $\alpha$ increases from 0.0 to 0.05.
3. **Isolated Territories**: 5 territories lacking inbound routes (Montserrat, Myanmar, Palestine, Saint Helena, Syria) remain unreached across all scenarios ($\alpha_j = 0, \Psi_j = 0$).

---

## Time-Window Audit & Extension Decision

A comprehensive chronological audit of `owid_covid.csv` was conducted prior to model extension:

* **Raw Data Horizon**: `2020-01-01` to `2026-08-30` (617,667 rows).
* **Surveillance Collapse (Post-2022)**:
  * Oxford Blavatnik School's `stringency_index` officially terminated on **2022-12-31** (100% missing thereafter).
  * OWID official `reproduction_rate` missingness surged to **99.6% in 2023** and **100.0% in 2024–2026**.
  * On May 5, 2023, the WHO declared the end of the PHEIC, leading to the dismantling of national daily PCR dashboards.
* **Mathematical Restriction**: In a classical SEIRD model without waning immunity ($R \to S$), prolonged 6-year simulation leads to susceptible depletion ($S \to 0$), making $\beta(t)$ diverge.
* **Defensible Extension Window**: **`2020-01-22` to `2022-12-31`** (1,075 days, 153.6 weeks). Feasible years: **2021 and 2022**. Years 2023–2026 are excluded due to surveillance non-identifiability.

---

## Repository Structure & Key Deliverables

```
├── README.md                                  # Comprehensive project documentation
├── AI_MODELLING_GUARDRAILS.md                 # Modeling constraints and scientific guardrails
├── .gitattributes                             # Git LFS tracking configuration for large datasets
├── .gitignore                                 # Environment and temporary file ignores
│
├── coupled_seird_extended_simulation.py       # Primary simulation script (2020–2022 extended)
├── coupled_seird_simulation.py                # Baseline simulation script (2020)
├── pre_extension_audit.py                     # Pre-extension and time-window audit script
├── mobility_network.py                        # Airline network preprocessing pipeline
├── seird_single_country.py                    # Single-country SEIRD model & ODE solver
├── alpha_identifiability_test.py              # Identifiability proof & sensitivity analysis
│
├── cleaned_airports.csv                       # Source airport database (OpenFlights)
├── cleaned_routes.csv                         # Source route database (OpenFlights)
├── owid_covid.csv                             # Primary COVID-19 dataset (Our World in Data)
├── seird_assumptions.json                     # Formal parameter declarations and sources
├── seird_parameter_evidence.json              # Biomedical literature citations
│
└── outputs/                                   # Model artifacts and validation reports
    ├── coupled_seird_extended_simulation.csv  # Extended daily simulation series (933,100 rows)
    ├── coupled_seird_extended_country_summary.csv # Country summary metrics (868 rows)
    ├── coupled_seird_extended_scenario_comparison.csv # 4-scenario comparison table
    ├── coupled_seird_extended_network_effects.csv # Network exposure and baseline deltas
    ├── coupled_seird_extended_validation.md   # Extended validation report (Markdown)
    ├── coupled_seird_extended_validation.json # Extended validation metrics (Machine-readable)
    ├── coupled_seird_extended_time_window_audit.md # Time-window audit report
    ├── coupled_seird_extended_time_window_audit.json # Time-window audit metrics
    ├── pre_extension_final_audit.md           # Baseline 2020 pre-extension audit report
    ├── pre_extension_final_audit.json         # Baseline 2020 audit metrics
    ├── country_route_matrix.csv               # Directed route count matrix
    ├── country_route_matrix_normalized.csv    # Destination-normalized route probability matrix Q
    ├── airports_processed.csv                 # Cleaned airport registry (3,196 airports)
    ├── routes_processed.csv                   # Cleaned route registry (66,747 routes)
    └── rt_estimates.csv                       # Estimated reproduction numbers (2020-2026)
```

---

## Methodological Limitations & Guardrails

1. **Route Topology $\neq$ Passenger Throughput**: The route matrix $Q_{ji}$ reflects scheduled commercial flight connectivity, not measured ticketed passenger counts.
2. **$\alpha$ is Non-Identifiable**: The coupling parameter $\alpha$ cannot be uniquely estimated from route topology alone. It is evaluated strictly as an operational sensitivity parameter.
3. **Observation-Model Limitation**: The SEIRD $I$ compartment represents true active infectious population. Reported confirmed cases in OWID reflect diagnostic testing capacity and ascertainment fractions (~10%-30%). Numerical level comparisons (RMSE) are incommensurable without an explicit observation model.
4. **Ancestral Parameter Homogeneity**: Fixed $\sigma = 0.1961$ and $\gamma = 0.125$ represent ancestral strain parameters and do not account for shorter incubation periods observed in Omicron subvariants.
5. **Absence of Vaccination / Mortality Attenuation**: Constant $\mu = 0.00083$ reflects early pre-vaccination IFR (~0.66%) and does not model vaccine-induced clinical severity reductions.
