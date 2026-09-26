# Alpha Identifiability and Sensitivity Audit Report

`ALPHA STATUS: SENSITIVITY ONLY`

## Executive Summary

This report provides the formal mathematical and empirical audit of the international coupling parameter $\alpha$ for the country-level SEIRD metapopulation model.

### Key Audit Finding
$$\mathbf{ALPHA: NOT \ EMPIRICALLY \ IDENTIFIABLE \ FROM \ APPROVED \ DATA}$$

The approved project datasets (`cleaned_airports.csv`, `cleaned_routes.csv`, and `owid_covid.csv`) provide **flight route network topology** ($C_{ij}, P_{ij}$) and country populations ($N_i$), but contain:
- **Zero passenger volume data** ($V_{ij}$)
- **Zero daily per-capita travel rates** ($\theta_i$)
- **Zero average traveler stay durations** ($\tau$)
- **Zero infected traveler counts** ($\Phi_{ij}^I$)

Because passenger volumes and travel frequencies are unobserved, **$\alpha$ cannot be uniquely estimated or identified from the approved data**. 

### Critical Retraction
> [!IMPORTANT]
> The statement in the previous draft that Formulation A was *"FULLY IDENTIFIABLE"* is **RETRACTED**.
> While Formulation A is **computationally evaluable** (the ODE system can be integrated once a value of $\alpha$ is specified), $\alpha$ is **NOT empirically identifiable**.
> Having all variables required to RUN an equation is fundamentally different from having enough data to ESTIMATE those variables empirically.

---

## 1. Clear Separation of Four Distinct Concepts

To maintain scientific integrity and prevent invalid data conflation, we formally distinguish:

| Concept | Mathematical Object | Units | Status in Project Data | Epistemological Meaning |
|---|---|---|---|---|
| **1. Route-Connectivity Information** | $C_{ij}, P_{ij}, Q_{ji}$ | Dimensionless probabilities / counts | **AVAILABLE** | Topological structure of scheduled commercial airline graph. Indicates *where* flights connect, not *how many people* fly. |
| **2. Human Mobility Information** | $V_{ij}, \theta_i$ | Passengers / day; Day$^{-1}$ | **BLOCKED — NOT AVAILABLE** | Actual physical movement of human beings across international borders. |
| **3. Infection Importation Rate** | $\Phi_{ij}^I(t) = V_{ij} \frac{I_i(t)}{N_i(t)}$ | Infected persons / day | **BLOCKED — NOT AVAILABLE** | Physical flux of contagious human vectors arriving in destination countries. |
| **4. International Coupling Strength** | $\alpha_j \in [0, 1)$ | Dimensionless weight | **SENSITIVITY PARAMETER ONLY** | Mathematical partition of force of infection between local and international exposure. |

These four concepts are **NOT interchangeable**. Treating route count as passenger volume or coupling weight as importation rate violates `AI_MODELLING_GUARDRAILS.md`.

---

## 2. Mathematical Proof of Structural Unidentifiability

### Physical Exposure vs Model Exposure
In reality, the imported exposure rate in destination country $j$ depends on the physical volume of incoming travelers $V_j^{\text{in}}$:
$$\text{Exposures}_{\text{imported}}(t) = \left( V_j^{\text{in}} \cdot T_{\text{stay}} \cdot k_j \cdot p_{\text{trans}} \right) \cdot \Psi_j(t) \cdot \frac{S_j(t)}{N_j(t)}$$

In our hazard-coupling SEIRD model, the imported exposure rate is:
$$\text{Exposures}_{\text{model}}(t) = \left( \beta_j(t) \cdot \alpha_j \right) \cdot \Psi_j(t) \cdot \frac{S_j(t)}{N_j(t)} \cdot N_j(t)$$

Equating the physical hazard to the model hazard yields:
$$\alpha_j = \left( \frac{V_j^{\text{in}}}{N_j} \right) \cdot T_{\text{stay}} \cdot \left( \frac{k_j \cdot p_{\text{trans}}}{\beta_j(t)} \right)$$

### Unidentifiability Result (Scale Invariance / Gauge Freedom)
Because $V_j^{\text{in}}$ (passenger volume) is completely unobserved in the approved flight route data:
1. Two different values of $\alpha$ (e.g. $\alpha_A = 0.01$ and $\alpha_B = 0.05$) are **equally consistent** with the exact same route-connectivity matrix $P_{ij}$.
2. A choice of $\alpha_B = 5 \times \alpha_A$ simply corresponds to an unobserved 5-fold difference in assumed passenger traffic $V_j^{\text{in}}$ or traveler contact intensity $k_j$.
3. Furthermore, because observed epidemic curves in OWID reflect the composite force of infection $\lambda_j(t)$, any shift in $\alpha_j$ can be perfectly compensated by a microscopic adjustment to $\beta_j(t)$:
   $$\beta_j^{\text{compensating}}(t) = \frac{\lambda_j(t)}{(1 - \alpha_j) \frac{I_j(t)}{N_j} + \alpha_j \Psi_j(t)}$$
   producing identical $\lambda_j(t)$, identical $dS_j/dt$, and identical simulated case/death curves.

*(Numerical test verified in `alpha_identifiability_test.py`: $\lambda_A - \lambda_B = 0.00e+00$).*

Therefore, **$\alpha$ cannot be identified from route data, population data, or epidemic curves alone**.

---

## 3. Project-Plan Audit

A systematic scan of `Plan.pdf` for coupling and mobility parameters yielded:

| Search Term | Occurrences in Project Plan | Explicit Numerical Value / Formula? |
|---|---|---|
| `alpha` | **0** | None |
| `coupling strength` | **0** | None |
| `international transmission coefficient` | **0** | None |
| `mobility coefficient` | **0** | None |
| `travel rate` | **0** | None |
| `importation rate` | **0** | None |
| `metapopulation coupling` | 1 (Page 8) | Conceptual description only ("moves a fraction of each compartment... travel restrictions become a simple scaling of the mobility matrix"). No numerical fraction is given. |

### Conclusion
`Plan.pdf` specifies the *architectural intent* to couple country models using flight routes, but provides **zero numerical values, calibration equations, or empirical sources for $\alpha$**.

---

## 4. Legitimate Sensitivity Framework

Because $\alpha$ is not empirically identifiable, the project **must proceed using $\alpha$ as an explicitly labelled sensitivity parameter**.

We define a 4-tier sensitivity framework in [`alpha_sensitivity_design.csv`](file:///c:/Users/devansh/Desktop/CDS/Sem%201%20End%20Sem%20project/alpha_sensitivity_design.csv):

| Scenario ID | Scenario Name | Symbolic $\alpha$ | Numerical Benchmark | Epidemiological Meaning | Status |
|---|---|---|---|---|---|
| `SCEN_0_DECOUPLED` | Decoupled Baseline | $0.0$ | $0.0$ | Zero international exposure; exact single-country SEIRD mechanics v2 baseline. | **IDENTIFIABLE BASELINE** |
| `SCEN_1_LOW_COUPLING` | Low International Coupling | $\alpha_{\text{low}}$ | $0.001$ | 0.1% transmission hazard from air routes; strict border friction / low mixing. | **OPERATIONAL ASSUMPTION** |
| `SCEN_2_MODERATE_COUPLING` | Moderate International Coupling | $\alpha_{\text{med}}$ | $0.01$ | 1.0% transmission hazard from air routes; reference international connectivity benchmark. | **OPERATIONAL ASSUMPTION** |
| `SCEN_3_HIGH_COUPLING` | High International Coupling | $\alpha_{\text{high}}$ | $0.05$ | 5.0% transmission hazard from air routes; major international transit hubs / stress scenario. | **OPERATIONAL ASSUMPTION** |

### Operational Rules for Sensitivity Analysis
1. **No single "best" $\alpha$ is selected.**
2. Numerical benchmarks ($0.0, 0.001, 0.01, 0.05$) are **operational sensitivity bounds**, NOT measured real-world travel parameters.
3. The project will evaluate model behavior across the spectrum $\alpha \in [0, 0.05]$, documenting how epidemic timing and imported waves respond to the coupling parameter.
4. If a specific country is known to be isolated (the 12 territories), $\alpha_m = 0$ holds across all scenarios.

---

## 5. Summary of Deliverables

1. [`alpha_identifiability_report.md`](file:///c:/Users/devansh/Desktop/CDS/Sem%201%20End%20Sem%20project/alpha_identifiability_report.md) — Comprehensive identifiability audit and mathematical proofs.
2. [`alpha_identifiability_report.json`](file:///c:/Users/devansh/Desktop/CDS/Sem%201%20End%20Sem%20project/alpha_identifiability_report.json) — Structured audit results and Plan.pdf search verification.
3. [`alpha_sensitivity_design.csv`](file:///c:/Users/devansh/Desktop/CDS/Sem%201%20End%20Sem%20project/alpha_sensitivity_design.csv) — Formal 4-scenario sensitivity specification table.
4. [`alpha_identifiability_test.py`](file:///c:/Users/devansh/Desktop/CDS/Sem%201%20End%20Sem%20project/alpha_identifiability_test.py) — Reproducible mathematical proof and test script.

---

## Final Audit Status

```
ALPHA STATUS: SENSITIVITY ONLY
```
*(Coupled SEIRD simulation remains unexecuted until sensitivity experiments are authorized).*
