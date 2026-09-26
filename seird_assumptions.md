# SEIRD Assumptions Specification

**Status: NUMERICAL PARAMETERS SOURCED; MECHANICAL REPLAY MAY RUN, BUT CALIBRATION REMAINS BLOCKED**

This specification contains a primary historical set and explicit sensitivity scenarios. Numerical values are traceable to peer-reviewed evidence or clearly labelled derivations/assumptions. A mechanics-only replay may be run; fitting/calibration remains blocked until an identifiable observation model is approved.

## Required Parameters

| Entry | Required definition | Current status |
|---|---|---|
| Incubation period | 5.1 days primary; 3.42 and 6.57 day sensitivity scenarios | READY |
| Sigma | 0.1960784314 1/day primary, exact reciprocal | READY |
| Infectious/recovery period | 8 days primary operational assumption; 5.16 and 9 day scenarios | READY WITH ASSUMPTION |
| Gamma | 0.125 1/day primary, exact reciprocal | READY |
| Mortality transition parameter | 0.0008304812 1/day primary, derived from IFR and competing hazards | READY WITH ASSUMPTION |
| Mortality parameter definition | $\mu$ is the per-time $I\to D$ hazard; IFR $p=\mu/(\gamma+\mu)$ | READY |
| Source | Lauer, Wu, Cevik, Wu, and Verity peer-reviewed evidence | READY |
| Source date | 2020-03-10 through 2023-02-18 | READY |
| Evidence/justification | See `seird_parameter_evidence.md` and JSON source records | READY |
| Applicability/limitations | Variant, age, severity, vaccination, treatment, and early-pandemic limitations remain | DOCUMENTED |

## Required Distinctions

- **CFR:** reported deaths divided by reported cases under a defined observation window.
- **IFR:** deaths among all infections, including infections that were not observed or reported.
- **Mortality probability:** probability of death over a defined disease course or compartment transition.
- **Mortality transition rate:** a per-time parameter $\mu$ governing flow from $I$ to $D$.

These quantities are not interchangeable. The approved `mortality_model_data.csv` contains a lagged reported CFR-like outcome and must not be copied directly into `mu`.

## SEIRD Formulation

The intended deterministic compartments are:

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

Here $N = S + E + I + R + D$. All compartment quantities must use one consistent population unit. The implementation must keep observed OWID cases and deaths separate from simulated incidence and deaths.

## Beta Calibration

The approved `rt_estimates.csv` provides independently estimated `Rt_estimated`; OWID `reproduction_rate` is reference data only. The implemented renewal-ratio estimate is interpreted as an effective reproduction number, not automatically as $R_0$. Under the equations above:

$$
R_0(t) = \frac{\beta(t)}{\gamma + \mu}
$$

at full susceptibility, whereas

$$
R_{eff}(t) = \frac{\beta(t)S(t)}{N[\gamma + \mu]}.
$$

Therefore, when `Rt_estimated` is used as $R_{eff}$ for an interval beginning at state $S(t)$:

$$
\beta(t) = Rt_{estimated}(t)\,[\gamma + \mu]\frac{N}{S(t)}.
$$

The shorter expression $\beta=Rt_{estimated}(\gamma+\mu)$ is valid only if `Rt_estimated` is explicitly defined as a full-susceptibility $R_0$ (or as an $S/N\approx1$ approximation). Missing `Rt_estimated` values remain unavailable. No beta values may be generated while required rate parameters, the mortality formulation, or the transition-start susceptible state are missing. This mathematical mapping does not identify reporting ascertainment, a reporting delay, vaccination effects, reinfection, or true susceptible history.

## Evidence Sources

- Lauer et al. (2020-03-10): [Europe PMC](https://europepmc.org/articles/PMC7081172), median incubation 5.1 days.
- Wu et al. (2022-08-22): [Europe PMC](https://europepmc.org/articles/PMC9396366), Alpha/Delta/Omicron means 5.00/4.41/3.42 days.
- Cevik et al. (2020-11-19): [Europe PMC](https://europepmc.org/articles/PMC7837230), viable-virus evidence distinct from prolonged RNA shedding.
- Wu et al. (2023-02-18): [Europe PMC](https://europepmc.org/articles/PMC9937726), Omicron viable-virus shedding mean 5.16 days.
- Verity et al. (2020-03-30): [Europe PMC](https://europepmc.org/article/MED/32240634), early China IFR 0.66% with 0.39%-1.33% credible interval.

## Sensitivity Scenarios

- **PRIMARY:** incubation 5.1 days, infectious/recovery period 8 days, IFR 0.66%; intended for historical 2020 replay.
- **LOWER_DURATION_HIGH_RATE:** incubation 3.42 days, infectious/recovery period 5.16 days, IFR 0.39%; Omicron/uncertainty sensitivity, not a 2020 default.
- **UPPER_DURATION_LOW_RATE:** incubation 6.57 days, infectious/recovery period 9 days, IFR 1.33%; pooled/upper-bound sensitivity, not universal.

The scenarios are not selected to improve validation metrics. Each has different variant, period, age, severity, and evidence limitations. Sigma and gamma are derived separately within each scenario.

## Pre-Simulation Gate

Before any country-level simulation, validate that:

1. Every required value is non-null, positive, and unit-consistent.
2. Each value has a source, source date, evidence, and applicability limitations.
3. The mortality definition and mapping to $\mu$ are explicit.
4. The beta relationship matches the implemented equations.
5. Population conservation, non-negative compartments, and numerical stability checks are implemented.
6. Calibration and validation periods are chronological.

Until these conditions are met:

- **Incubation:** READY
- **Sigma:** READY
- **Infectious period:** READY WITH EXPLICIT OPERATIONAL ASSUMPTION
- **Gamma:** READY
- **Mortality parameter:** READY WITH EXPLICIT COMPETING-HAZARD ASSUMPTION
- **Beta calibration:** READY METHOD / NUMERIC BETA CONDITIONAL ON Rt
