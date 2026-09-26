# SEIRD Parameter Evidence Table

**Status: PARAMETERS SOURCED; MECHANICAL REPLAY MAY RUN, BUT CALIBRATION REMAINS BLOCKED**

This table contains a primary historical set and explicit sensitivity scenarios. A mechanics-only replay may run; calibration remains blocked without an identifiable observation model.

| Parameter | Numerical value | Unit | Mathematical definition | Source | Publication date | Exact evidence | COVID-period applicability | Limitations | Classification | Readiness |
|---|---:|---|---|---|---|---|---|---|---|---|
| Incubation period | 5.1 primary; 3.42/6.57 scenarios | days | Duration from exposure to symptom onset; project uses it as E-to-I proxy | Lauer 2020; Wu 2022 | 2020-03-10; 2022-08-22 | Lauer median 5.1; Wu Alpha 5.00, Delta 4.41, Omicron 3.42 | Primary targets historical 2020; variants require scenario selection | Symptom incubation is not identical to latent period | Sourced | READY |
| Sigma | 0.1960784314 primary | 1/day | `sigma = 1 / incubation_period` | Derived from Lauer primary | 2020-03-10 | `1 / 5.1` | Historical primary only | Inherits incubation limitations | Derived | READY |
| Infectious/recovery period | 8 primary; 5.16/9 scenarios | days | Operational duration for I removal/recovery | Cevik 2020; Wu 2023 | 2020-11-19; 2023-02-18 | Cevik no live virus beyond day 9/no respiratory culture after day 8; Wu Omicron viable-virus mean 5.16 | Primary early-pandemic operational set; Omicron is not a 2020 default | Viable culture duration is not population infectiousness; RNA shedding is not substituted | Assumed from sourced bounds | READY WITH ASSUMPTION |
| Gamma | 0.125 primary | 1/day | `gamma = 1 / infectious_period` | Derived from Cevik primary operational period | 2020-11-19 | `1 / 8` | Historical primary only | Depends on operational infectious-period assumption | Derived | READY |
| Mortality transition parameter `mu` | 0.0008304812 primary | 1/day | `mu` governs `I -> D`; IFR `p=mu/(gamma+mu)` | Derived from Verity 2020 IFR and primary gamma | 2020-03-30 | IFR p=0.0066; `mu=gamma*p/(1-p)` | Early China evidence; age and period dependent | Not an OWID CFR conversion; competing-hazard mapping is an explicit assumption | Derived under assumption | READY WITH ASSUMPTION |
| Beta mechanics method | No fitted beta | Method; beta would be 1/day | `Reff=beta*S/[N*(gamma+mu)]`; when renewal-ratio `Rt_estimated` is treated as Reff, `beta(t)=Rt_estimated(t)*(gamma+mu)*N/S(t)` | Guardrails, assumptions, approved Rt | Not applicable | `Rt_estimated` is independently estimated; intervention coefficients are excluded | Conditional on valid Rt, transition-start S, and selected scenario | Does not identify reporting, true susceptibility, or a case calibration; numeric beta remains time-varying | Mechanics only | READY METHOD / CONDITIONAL |

## Mortality Definitions

- **CFR:** reported deaths divided by reported cases under a stated observation window.
- **IFR:** deaths among all infections, including infections not observed or reported.
- **Mortality probability:** probability of death over a defined disease course or compartment transition.
- **Mortality transition rate:** per-time rate `mu` governing flow from `I` to `D`.

The approved lagged reported CFR-like outcome must not be copied directly into `mu`.

## Beta Method

For the deterministic formulation:

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

For the deterministic formulation, the full-susceptibility basic reproduction number is:

$$
R_0(t) = \frac{\beta(t)}{\gamma + \mu}.
$$

The effective reproduction number at state $S(t)$ is:

$$
R_{eff}(t) = \frac{\beta(t)S(t)}{N[\gamma+\mu]}.
$$

`Rt_estimated` is a renewal-ratio estimate and is used as $R_{eff}$ only for the mechanics replay. Accordingly, the transition-start beta is:

$$
\beta(t) = Rt_{estimated}(t)\,[\gamma+\mu]\frac{N}{S(t)}.
$$

The simplified expression `beta=Rt_estimated*(gamma+mu)` applies only when Rt is a full-susceptibility $R_0$ or when $S/N\approx1$ is an explicitly accepted approximation. Only valid `Rt_estimated` observations may be used. OWID `reproduction_rate` and non-predictive intervention coefficients are excluded. This relationship does not provide an ascertainment rate or reporting delay, so it does not authorize case calibration.

## Evidence Sources

- Lauer et al. (2020-03-10): [Europe PMC](https://europepmc.org/articles/PMC7081172), median incubation 5.1 days.
- Wu et al. (2022-08-22): [Europe PMC](https://europepmc.org/articles/PMC9396366), Alpha/Delta/Omicron means 5.00/4.41/3.42 days.
- Cevik et al. (2020-11-19): [Europe PMC](https://europepmc.org/articles/PMC7837230), viable-virus evidence distinct from prolonged RNA shedding.
- Wu et al. (2023-02-18): [Europe PMC](https://europepmc.org/articles/PMC9937726), Omicron viable-virus shedding mean 5.16 days.
- Verity et al. (2020-03-30): [Europe PMC](https://europepmc.org/article/MED/32240634), early China IFR 0.66% with 0.39%-1.33% credible interval.

## Sensitivity-Analysis Design

The numerical scenarios are evidence-based and are not selected to improve validation metrics.

### Primary Set

The primary set uses incubation 5.1 days, infectious/recovery period 8 days as an operational viable-virus assumption, and IFR 0.66% for historical 2020 replay.

### Alternative Sets

1. **LOWER_DURATION_HIGH_RATE:** incubation 3.42 days, infectious period 5.16 days, IFR 0.39%; Omicron/uncertainty sensitivity, not a 2020 default.
2. **UPPER_DURATION_LOW_RATE:** incubation 6.57 days, infectious period 9 days, IFR 1.33%; pooled/upper-bound sensitivity, not universal.

Each set must have its own source, publication date, exact evidence, applicability limits, and derived `sigma`/`gamma`. Sets must not be selected because they improve validation metrics.

## Readiness

- Incubation: **READY**
- Sigma: **READY**
- Infectious period: **READY WITH EXPLICIT OPERATIONAL ASSUMPTION**
- Gamma: **READY**
- Mortality parameter: **READY WITH EXPLICIT COMPETING-HAZARD ASSUMPTION**
- Beta method: **READY METHOD / NUMERIC BETA CONDITIONAL ON Rt**

**SEIRD execution remains unrun pending separate authorization and final traceability review.**
