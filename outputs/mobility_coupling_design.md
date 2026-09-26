# Mobility Coupling Design: Metapopulation SEIRD Architecture

`MOBILITY COUPLING DESIGN: READY`

## Executive Summary

This document establishes and structurally validates the mathematical method for coupling country-level SEIRD models using the project's validated route-connectivity proxy (`country_route_matrix_normalized.csv`).

In strict compliance with `AI_MODELLING_GUARDRAILS.md`:
- **No simulation is executed in this stage.**
- **No passenger volumes are fabricated.**
- **Route counts are NOT assumed to equal passenger counts.**
- **No intervention coefficients or external mobility datasets are introduced.**
- **Original data files remain completely unmodified.**

---

## 1. Definition of the Mobility Matrix

The mobility coupling uses the validated normalized international route matrix:
`outputs/country_route_matrix_normalized.csv`

### Mathematical Definition of $P_{ij}$
Let $C_{ij}$ be the number of scheduled commercial flight routes departing from an airport in source country $i$ and arriving at an airport in destination country $j$, where $i \neq j$.

The normalized route-connectivity probability $P_{ij}$ is defined as:
$$P_{ij} = \frac{C_{ij}}{\sum_{k \neq i} C_{ik}}$$

### Structural Properties
1. **Dimension**: 4,558 nonzero directed edges representing a $225 \times 224$ international connectivity network.
2. **Row Stochasticity**: For every source country $i$ with international outbound connectivity:
   $$\sum_{j \neq i} P_{ij} = 1.0$$
   *Verification*: Min row sum = `1.000000`, Max row sum = `1.000000`. All 225 source countries satisfy the stochastic condition within $10^{-10}$ tolerance.
3. **Empty Rows**: The 12 countries without international flight connectivity have no outgoing international routes ($P_{mj} = 0$).

---

## 2. Epistemological Scope: What $P_{ij}$ Represents vs What Cannot Be Inferred

### What $P_{ij}$ Represents
- **Conditional Routing Distribution**: $P_{ij}$ represents the empirical probability that an outbound international flight connection departing country $i$ terminates in country $j$.
- **Topological Route Connectivity Proxy**: It captures the relative structural wiring of global commercial aviation between countries.
- **Directional Channeling**: It identifies which countries are direct network neighbors in the international flight graph.

### What CANNOT Be Inferred (Explicit Non-Identifiability)
Under `AI_MODELLING_GUARDRAILS.md`, the AI must not hallucinate or guess unobserved parameters. The following quantities cannot be inferred from the provided data:
1. **Passenger Count / Traveler Volume ($V_{ij}$)**: The route file records carrier routes, not passenger tickets, passenger load factors, or aircraft seating configurations.
2. **Travel Frequency / Flight Cadence**: A route entry represents an existing route, not daily flight departures (e.g. 5 flights/day vs 1 flight/week).
3. **Infected Traveler Volume**: No passenger health records, symptom screenings, or border test results are provided.
4. **Airport Passenger Capacity / Terminal Throughput**: Physical terminal volumes are absent.
5. **Per-Capita Population Mobility Rate ($\theta_i$)**: The fraction of a country's population that travels abroad per unit time is completely unobserved.
6. **Non-Aviation Mobility**: Terrestrial border crossings, maritime transit, and rail are unrecorded.

**Scientific Principle**: $P_{ij}$ is strictly a **route-connectivity proxy**, not a passenger-volume matrix or an empirical population flux.

---

## 3. Coupling Formulation Design

### Selection of Epidemiological Mechanism
We evaluated five potential points of entry for network coupling in SEIRD:
1. **Direct injection into Infectious compartment ($I$)**: REJECTED. Requires unobserved absolute counts of infected travelers; violates mass conservation unless subtracted from source; creates discontinuous numerical shocks.
2. **Direct injection into Exposed compartment ($E$)**: REJECTED. Same physical and data limitations as compartment $I$.
3. **Direct scaling of transmission parameter ($\beta$)**: REJECTED. Transmission rate $\beta$ governs biological virus-host transmissibility within a country. Foreign flights do not alter the virus's domestic infectiousness.
4. **Modification of Force of Infection ($\lambda_j(t)$)**: **ACCEPTED (RECOMMENDED)**. Susceptibles in country $j$ experience exposure from two distinct channels: domestic infectious contacts and imported infectious pressure arriving via international connectivity.

### Mathematical Formulation
$$\frac{dS_j}{dt} = - \lambda_j(t) S_j(t)$$
$$\frac{dE_j}{dt} = \lambda_j(t) S_j(t) - \sigma E_j(t)$$
$$\frac{dI_j}{dt} = \sigma E_j(t) - (\gamma + \mu_j) I_j(t)$$
$$\frac{dR_j}{dt} = \gamma I_j(t)$$
$$\frac{dD_j}{dt} = \mu_j I_j(t)$$

where total force of infection is:
$$\lambda_j(t) = \beta_j(t) \left[ (1 - \alpha_j) \frac{I_j(t)}{N_j} + \alpha_j \Psi_j(t) \right]$$

and the incoming imported infectious pressure is:
$$\Psi_j(t) = \sum_{i \in \mathcal{C}, i \neq j} Q_{ji} \frac{I_i(t)}{N_i}$$
where $Q_{ji} = \frac{C_{ij}}{\sum_{k \neq j} C_{kj}}$ is the destination-normalized inbound route share.

---

## 4. Preservation of Country Populations and Scale Invariance

### Population Scaling
To prevent countries with large populations or numerous routes from artificially overwhelming smaller countries:
- Inbound exposure uses **per-capita infectious prevalence**:
  $$\rho_i(t) = \frac{I_i(t)}{N_i}$$
- Because $\rho_i(t) \in [0, 1]$ is scale-free, a large country with low prevalence generates small imported pressure, whereas a small country with high prevalence generates high imported pressure.
- Route weights $Q_{ji}$ sum to $1.0$, ensuring that $\Psi_j(t) \in [0, 1]$ remains bounded and scale-invariant. A country with 500 incoming routes does not suffer an arbitrary 500-fold explosion in exposure compared to a country with 10 incoming routes.

---

## 5. Directionality: Preservation of $P_{ij} \neq P_{ji}$

- In the validated normalized matrix:
  - Total directed international edges: `4,558`
  - Asymmetric directed edges ($P_{ij} \neq P_{ji}$): `4,550` (**99.82%**)
  - Symmetric pairs: `8` (only **0.18%**)
- Empirical example: Niue connects outbound to New Zealand ($P_{\text{Niue} \to \text{NZ}} = 1.0$), but New Zealand has zero routes to Niue ($P_{\text{NZ} \to \text{Niue}} = 0$).
- **Rule**: No matrix symmetrization is applied. Directional asymmetry is strictly maintained in both $P_{ij}$ and $Q_{ji}$.

---

## 6. Handling the 12 Countries Without International Connectivity

The 12 countries/territories without usable international connectivity are:
1. Antarctica
2. British Indian Ocean Territory
3. Johnston Atoll
4. Midway Islands
5. Montserrat
6. Myanmar
7. Palestine
8. Saint Helena
9. Svalbard
10. Syria
11. Wake Island
12. West Bank

### Methodological Decision
- **They are NOT removed** from the project's country coverage.
- **No artificial or synthetic flight routes are invented.**
- **Mathematical treatment**:
  For all $m \in \mathcal{C}_{\text{iso}}$:
  $$\alpha_m = 0, \quad \Psi_m(t) = 0$$
  $$\lambda_m(t) = \beta_m(t) \frac{I_m(t)}{N_m}$$
- These countries evolve strictly according to their internal single-country SEIRD dynamics.

---

## 7. Mass Conservation Consideration

### Individual Country Conservation
Summing the compartment derivatives for any country $j$:
$$\frac{dN_j}{dt} = \frac{d}{dt} (S_j + E_j + I_j + R_j + D_j) = 0$$
Country population $N_j$ is rigorously constant over time.

### Global Metapopulation Conservation
$$\frac{d}{dt} \sum_{j \in \mathcal{C}} N_j = \sum_{j \in \mathcal{C}} \frac{dN_j}{dt} = 0$$
Global population is strictly conserved across all compartments.

### Distinction: Hazard Coupling vs Physical Migration
Formulation A represents an **epidemiological hazard model**, not permanent migration. Susceptibles become exposed via international contact hazard without changing their country of residence. This avoids the severe population distortions that occur when modeling travel without return-migration data.

---

## 8. Avoidance of Double Counting

1. **Convex Partition of Exposure Hazard**:
   $$(1 - \alpha_j) + \alpha_j = 1.0$$
   Domestic transmission is scaled by $(1 - \alpha_j)$, ensuring that imported exposure does not artificially add on top of 100% domestic contact rates.
2. **Single Infection Conduit**:
   Infection occurs exclusively via $S_j \to E_j$ driven by $\lambda_j(t)$. No separate or concurrent additions are made to $E$ or $I$.
3. **No Spontaneous Disease Generation**:
   If $I_i(t) = 0$ across all countries, then $\Psi_j(t) = 0$ and $\lambda_j(t) = 0$. The mobility network cannot create disease de novo.

---

## 9. Technical Comparison of Formulations

| Dimension | Formulation A: Imported-Infection Pressure Model | Formulation B: Explicit Metapopulation Movement Model |
|---|---|---|
| **Mechanism** | Hazard-based modification of Force of Infection $\lambda_j(t)$ | Physical ODE flux of people across compartments: $\Phi_{ij}^X$ |
| **Required Inputs** | $P_{ij}$ (available), $N_i$ (available), $\beta_j$ (available), $\alpha_j \in [0, 1)$ | $P_{ij}$ (available), $V_{ij}$ passenger volumes (**UNAVAILABLE**), $\theta_i$ daily flux rate (**UNAVAILABLE**), $\tau$ trip duration (**UNAVAILABLE**) |
| **Mass Conservation** | Strictly conserved for every country individually and globally | Conserved globally only if $\sum_{i} \Phi_{ij} = \sum_k \Phi_{jk}$; distorts country populations without return trip modeling |
| **Mathematical Structure** | Smooth convex ODE system; naturally reduces to single-country SEIRD when $\alpha = 0$ | High-dimensional coupled flux ODE system ($5 \times M$ compartments with $M^2$ flux terms) |
| **Double Counting Risk** | Fully prevented via convex weights $(1-\alpha_j) + \alpha_j = 1$ | High risk if travelers transmit locally in country $j$ while also counted in country $i$ |
| **Identifiability with Approved Data** | **COMPUTATIONALLY EVALUABLE UNDER SENSITIVITY FRAMEWORK; ALPHA NOT EMPIRICALLY IDENTIFIABLE** | **UNIDENTIFIABLE (Requires fabricated passenger data)** |
| **Status** | **READY** | **BLOCKED — REQUIRED INPUT NOT AVAILABLE** |

---

## 10. Recommended Implementation & Parameter Availability Audit

### Parameter Status Table

| Parameter / Data Object | Role | Value / Range | Source / Status |
|---|---|---|---|
| $P_{ij}$ | Outbound normalized route connectivity | Matrix $[225 \times 224]$, row sum = 1.0 | `country_route_matrix_normalized.csv` (**AVAILABLE**) |
| $Q_{ji}$ | Inbound normalized route connectivity | Matrix $[224 \times 225]$, col sum = 1.0 | Computed from `country_route_matrix.csv` (**AVAILABLE**) |
| $N_j$ | Country resident population | Positive integer | `owid_covid_processed.csv` (**AVAILABLE**) |
| $S_j, E_j, I_j, R_j, D_j$ | SEIRD state variables | Persons | Single-country SEIRD mechanics v2 (**AVAILABLE**) |
| $\sigma, \gamma, \mu_j$ | Disease transition parameters | $\sigma = 0.2, \gamma = 0.125, \mu = \text{calibrated}$ | `seird_assumptions.json` (**AVAILABLE**) |
| $\beta_j(t)$ | Local transmission rate | Positive float | Derived from $R_{t, j}^{\text{est}}$ (**AVAILABLE**) |
| $V_{ij}$ | Absolute daily passenger volume | Persons/day | **BLOCKED — REQUIRED INPUT NOT AVAILABLE** |
| $\theta_i$ | Per-capita daily travel fraction | Day$^{-1}$ | **BLOCKED — REQUIRED INPUT NOT AVAILABLE** |
| $\tau$ | Average traveler stay duration | Days | **BLOCKED — REQUIRED INPUT NOT AVAILABLE** |
| $\alpha_j$ | International coupling strength | Parameter in $[0, 1)$ | **FORMAL COUPLING PARAMETER (To be calibrated / sensitivity evaluated)** |

### Recommendation
Formulation A (Imported-Infection Pressure Model) is the **only mathematically defensible approach** that respects the project guardrails against data fabrication. It fully leverages the approved route-connectivity network without inventing fictitious passenger volume numbers.

---

## 11. Final Verification Checklist

- [x] Input files unmodified (`cleaned_airports.csv`, `cleaned_routes.csv`, `owid_covid.csv`)
- [x] No external mobility or passenger datasets used
- [x] $P_{ij}$ defined and verified: $\sum_j P_{ij} = 1.0$ for all 225 connected countries
- [x] Explicit documentation that route counts $\neq$ passenger volume
- [x] Population scale invariance proved using prevalence $\rho_i = I_i / N_i$
- [x] Directional asymmetry preserved ($P_{ij} \neq P_{ji}$)
- [x] 12 isolated territories handled explicitly (internal SEIRD, $\alpha = 0$)
- [x] Exact population conservation proved ($dN_j/dt = 0$)
- [x] Double counting prevented via convex combination of forces of infection
- [x] Formulation A and Formulation B compared across all technical dimensions
- [x] Unobserved parameters explicitly marked `BLOCKED — REQUIRED INPUT NOT AVAILABLE`
- [x] No cross-country SEIRD simulation executed in this stage

---

## Final Milestone Status

`MOBILITY COUPLING DESIGN: READY`
