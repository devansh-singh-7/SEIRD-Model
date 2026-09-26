# Epidemic Intelligence Platform — AI Modelling Guardrails

## Purpose

This document is a **strict instruction and verification layer** for any AI system working on the Epidemic Intelligence Platform project.

The AI must use the supplied project plan and supplied datasets as the primary source of truth.

The AI must **not invent data, assumptions, model results, dates, country mappings, parameter values, or scientific conclusions** that are not supported by the available sources.

If information is missing, uncertain, ambiguous, or unavailable, the AI must explicitly say so.

---

# 1. SOURCE-OF-TRUTH RULE

Use this priority order:

1. **Project plan / supplied project documentation**
2. **Actual supplied datasets**
3. **Official documentation for the supplied datasets**
4. **Peer-reviewed / authoritative external sources when the project plan requires additional methodology**
5. General model knowledge only when the above sources do not specify something

Never silently replace project-plan requirements with a different approach.

If the project plan specifies a method, follow that method unless the user explicitly asks for an alternative.

---

# 2. DATASETS AND THEIR PURPOSES

## OWID COVID Dataset

File:

`owid-covid-data_final_HDI_zeros_preserved.csv`

Primary use:

- COVID epidemic time series
- Country/date analysis
- Cases
- Deaths
- Demographic variables
- Healthcare variables
- GDP
- Population
- Population density
- Median age
- HDI
- Stringency
- Reference reproduction-rate data

Important:

`reproduction_rate` is an OWID/reference variable.

It must NOT automatically be treated as the independently estimated `Rt` required by the project.

The model must create:

`Rt_estimated`

separately when performing the project's Rt analysis.

---

## WHO Daily COVID Dataset

File:

`WHO-COVID-19-global-daily-data.csv`

Use for:

- Independent COVID case validation
- Independent death validation
- Historical epidemic-curve comparison
- Sensitivity/robustness analysis

Do not blindly merge WHO and OWID observations.

Country names/codes and dates must be standardised before comparison.

---

## WHO Monthly Death-by-Age Dataset

File:

`WHO-COVID-19-global-monthly-death-by-age-data.csv`

Use for:

- Age-specific mortality analysis
- Mortality validation
- Supporting country-specific mortality assumptions

Do NOT use this as the primary daily epidemic time-series dataset.

Do NOT convert missing death values to zero.

---

## OpenFlights Airports

File:

`cleaned_airports(5).csv`

Use for:

- Airport-to-country mapping
- Geographic information
- Airport coordinates

---

## OpenFlights Routes

File:

`cleaned_routes(5).csv`

Use for:

- Airport-to-airport connectivity
- Country-to-country mobility network
- Mobility matrix construction

Important:

A route record is NOT automatically a passenger count.

Do not claim that route frequency represents actual passenger volume unless passenger-volume data is supplied.

---

## VIW_FNT Respiratory Dataset

File:

`VIW_FNT(6).csv`

Use for:

- Respiratory-virus seasonality
- Wave detection
- Growth analysis
- Secondary generalisation/validation

Do NOT merge respiratory-virus observations with COVID observations as if they were the same disease.

---

# 3. ABSOLUTE ANTI-HALLUCINATION RULES

The AI MUST NOT:

- Invent missing values.
- Guess missing dates.
- Guess country mappings.
- Guess airport mappings.
- Guess passenger volumes.
- Invent HDI values.
- Invent Rt values.
- Invent intervention effects.
- Invent SEIRD parameters.
- Claim that a model was trained if it was not actually trained.
- Claim that a model was validated if validation was not performed.
- Claim a dataset contains a variable that has not been checked.
- Claim a source supports a result unless the source actually supports it.
- Convert missing values into zero without explicit justification.
- Convert legitimate zeros into missing values without explicit justification.
- Randomly generate epidemiological observations.
- Fabricate model metrics.
- Fabricate plots or results.
- Present hypothetical simulation outputs as historical observations.
- Present simulated outcomes as predictions of what actually happened.
- Treat correlation as causation.
- Treat an ML prediction as a measured epidemiological parameter.
- Treat a route count as passenger volume.
- Treat OWID's `reproduction_rate` as independently estimated Rt.
- Train on duplicate CSV and JSON copies of the same observations.

---

# 4. MISSING DATA RULES

Missing data is NOT automatically an error.

The AI must first determine why a variable is missing and whether that variable is required for the specific analysis.

Never perform blanket deletion such as:

```python
df.dropna()
```

unless there is a documented reason.

Never perform blanket imputation such as:

```python
df.fillna(0)
```

for epidemiological variables.

Instead:

1. Report missingness.
2. Identify the model that needs the variable.
3. Use only the relevant observations for that model.
4. Document the resulting sample size.
5. State how missingness affects interpretation.

Legitimate zeros must remain zeros.

---

# 5. DATE RULES

Dates must be checked before time-series modelling.

Required checks:

- Parse dates.
- Check invalid dates.
- Sort by country and date.
- Check duplicate country/date observations.
- Check chronological continuity where relevant.
- Do not fabricate dates from row order.

If dates are unavailable:

**STOP and report that dates are missing.**

Do not infer dates unless an authoritative source provides the mapping.

---

# 6. COUNTRY RULES

Separate:

### Actual countries

from:

### Aggregate locations

Examples of aggregates include:

- World
- continents
- income groups
- regional aggregates

Do not use aggregate regions as if they were countries in a country-level SEIRD metapopulation model.

Country identifiers should be standardised using official country codes where possible.

If a country mapping is uncertain:

**flag it instead of guessing.**

---

# 7. OWID VARIABLE RULES

Important variables:

```text
location
date
total_cases
new_cases
new_cases_smoothed
total_deaths
new_deaths
new_deaths_smoothed
reproduction_rate
stringency_index
population
population_density
median_age
gdp_per_capita
hospital_beds_per_thousand
human_development_index
```

Keep legitimate zeros.

Missing values remain missing unless a model-specific method is explicitly chosen.

---

# 8. Rt RULE

The project requires estimation of effective reproduction number Rt.

Do not simply copy:

`reproduction_rate`

into:

`Rt_estimated`

Instead:

```text
COVID case curve
        ↓
Preprocessing
        ↓
7-day smoothing
        ↓
Rt estimation method
        ↓
Rt_estimated
```

Possible methods specified by the project include:

- Cori method
- Wallinga–Teunis method

The exact method and generation-interval assumptions must be documented.

OWID `reproduction_rate` may be used as a reference/comparison variable.

---

# 9. WAVE DETECTION RULE

Use the project-required 7-day-smoothed epidemic curve.

A suitable peak-detection method may use:

`scipy.signal.find_peaks`

For each wave record:

- Country
- Wave number
- Peak date
- Peak magnitude
- Start date
- End date
- Approximate duration

Do not claim a peak exists merely because a random local increase occurred.

Document threshold and prominence rules.

---

# 10. GROWTH RATE AND DOUBLING TIME

Early epidemic growth should be estimated from the appropriate early-growth period.

Do NOT fit an exponential curve across the entire pandemic.

For each selected growth period:

```text
Cases
↓
log(Cases)
↓
linear growth estimate
↓
r
↓
doubling time
```

For exponential growth:

`doubling_time = ln(2) / r`

If `r <= 0`, interpret carefully rather than reporting an invalid positive doubling time.

---

# 11. INTERVENTION MODEL

The project requires analysis of:

`change in Rt`

against:

`stringency`

with approximately:

`7–14 day lag`

Use an interpretable regression approach first.

Possible models:

- Linear Regression
- Ridge Regression

Do not automatically use complex ML models.

Report:

- coefficient
- uncertainty where available
- MAE
- RMSE
- R²
- limitations

Do not describe the coefficient as causal evidence unless the design supports causal inference.

Use wording such as:

> "The model estimates an association under the stated assumptions."

not:

> "Stringency caused Rt to decrease."

---

# 12. MORTALITY MODEL

The project requires country-specific mortality analysis.

Potential predictors include:

- Median age
- Hospital beds per thousand
- HDI
- GDP per capita where justified

Outcome:

An appropriately defined mortality/CFR measure.

The AI must explicitly define:

- numerator
- denominator
- time window
- lag assumptions

Do not calculate naive same-day CFR and present it as the true infection fatality rate.

Do not infer causality from demographic regression.

---

# 13. SEIRD RULE

SEIRD is a mechanistic epidemiological model.

It is NOT simply a conventional ML classifier/regressor.

The model contains:

```text
S = Susceptible
E = Exposed
I = Infectious
R = Recovered
D = Deceased
```

Parameters may include:

```text
β = transmission
σ = progression/incubation-related rate
γ = recovery rate
μ = mortality rate
```

The AI must document how each parameter is obtained.

Do not invent parameter values.

Parameters should come from:

- literature assumptions where required
- fitted historical data
- project-derived statistical models
- clearly documented calibration

---

# 14. MOBILITY RULE

Construct:

```text
airport → airport
```

then aggregate to:

```text
country → country
```

to create the mobility matrix.

Required checks:

- Unmatched airport IDs
- Missing countries
- Self-loops
- Duplicate routes
- Route direction
- Weighting method

Do not claim the matrix represents passenger volumes unless actual passenger-volume data exists.

The matrix represents a connectivity/route-based mobility proxy unless otherwise supported.

---

# 15. METAPOPULATION RULE

Each country should have its own SEIRD system.

The systems are coupled through the mobility matrix.

Conceptually:

```text
Country A SEIRD
       ↕
Mobility network
       ↕
Country B SEIRD
```

Check:

- population conservation
- non-negative compartment sizes
- numerical stability
- reasonable parameter ranges
- no unexplained creation/destruction of people

---

# 16. VALIDATION RULE

Never validate a model against the same observations used to fit/calibrate it without clearly labelling the result as in-sample validation.

Prefer:

```text
Earlier period
     ↓
Training/calibration

Later period
     ↓
Validation
```

For historical replay:

- calibrate appropriately
- replay 2020
- compare simulated cases with observed cases
- compare simulated deaths with observed deaths

Use WHO data as an independent reference where appropriate.

Metrics may include:

- MAE
- RMSE
- MAPE where valid
- correlation
- peak-date error
- peak-size error

Never invent metric values.

---

# 17. TIME-SERIES SPLITTING

Never randomly shuffle time-series observations for standard train/test splitting.

Use chronological splits.

Example:

```text
2020
↓
Training

2021
↓
Validation
```

The exact split must follow the project's modelling design.

---

# 18. JSON VS CSV

Do not train duplicate copies of the same dataset.

For analytical/model training:

**Prefer CSV + pandas/DataFrame.**

JSON should be used primarily for:

- APIs
- frontend consumption
- application interchange
- structured configuration

If both CSV and JSON contain the same observations:

**load only one into the model.**

---

# 19. MODEL SELECTION RULE

Use the simplest scientifically appropriate model first.

Recommended mapping:

| Task | Preferred approach |
|---|---|
| Wave detection | Signal processing / `find_peaks` |
| Growth rate | Log-linear regression |
| Doubling time | Mathematical calculation |
| Rt | Cori / Wallinga–Teunis |
| Intervention effect | Interpretable regression |
| Mortality relationship | Interpretable regression |
| Mobility | Network/matrix construction |
| SEIRD | Mechanistic ODE model |
| Historical validation | Time-series comparison |
| Respiratory generalisation | Time-series/wave analysis |

Do not add:

- Random Forest
- XGBoost
- Neural networks
- LSTM
- Transformers

unless there is a clearly justified project requirement and sufficient data.

Using a more complicated model does not automatically make the project better.

---

# 20. REQUIRED OUTPUTS

The AI should produce, where applicable:

```text
owid_covid_processed.csv
epidemic_waves.csv
growth_rates.csv
rt_estimates.csv
intervention_analysis.csv
mortality_model_data.csv
mobility_matrix.csv
seird_parameters.csv
seird_validation.csv
respiratory_analysis.csv
```

Each output must have:

- clear column names
- documented units
- documented source
- documented preprocessing
- reproducible generation code

---

# 21. MODEL RESULT INTEGRITY

Every reported result must be classified as one of:

### OBSERVED

Directly present in a supplied dataset.

### CALCULATED

Computed from supplied data using a documented formula.

### ESTIMATED

Produced by a statistical or epidemiological model.

### SIMULATED

Produced by the SEIRD/metapopulation simulator.

### EXTERNAL

Obtained from an external authoritative source.

### ASSUMPTION

An explicit modelling assumption.

Never mix these categories.

For example:

`Observed cases` ≠ `Simulated cases`

`OWID reproduction_rate` ≠ `Estimated Rt`

`Flight routes` ≠ `Passenger volumes`

---

# 22. UNCERTAINTY RULE

If an answer depends on an assumption, state the assumption.

If multiple reasonable methodologies exist:

1. State the available choices.
2. Select one only if the project plan supports it.
3. Document why it was selected.
4. Do not present it as uniquely correct.

---

# 23. STOP CONDITIONS

The AI must STOP and ask for clarification or report the problem if:

- A required dataset is missing.
- A required column does not exist.
- Dates cannot be verified.
- Country mappings cannot be verified.
- The project plan conflicts with the requested modelling method.
- A requested metric cannot be calculated from the available data.
- A model requires a parameter that has no defensible source.
- A result would require fabricated data.

Do not silently improvise.

---

# 24. FINAL PRE-MODELLING CHECKLIST

Before training/fitting any model, verify:

- [ ] Correct dataset selected
- [ ] Correct columns present
- [ ] Dates valid
- [ ] Country identifiers valid
- [ ] Duplicate country/date rows checked
- [ ] Aggregate regions handled
- [ ] Missingness measured
- [ ] Legitimate zeros preserved
- [ ] Missing values not blindly converted to zero
- [ ] Units checked
- [ ] Time-series sorted
- [ ] Train/validation split is chronological
- [ ] Target variable defined
- [ ] Features documented
- [ ] Model choice justified
- [ ] Assumptions documented
- [ ] External sources identified
- [ ] Results labelled as observed/calculated/estimated/simulated
- [ ] No fabricated values
- [ ] No fabricated metrics
- [ ] No unsupported scientific claims

---

# 25. FINAL PRINCIPLE

When uncertain:

**Do not guess.**

Use this sequence:

```text
Check project plan
        ↓
Check actual dataset
        ↓
Check authoritative documentation
        ↓
Determine whether the required information exists
        ↓
If yes → use it
If no → report the gap
        ↓
Never fabricate the missing information
```

The purpose of this document is not to prevent useful modelling.

It is to prevent the AI from producing plausible-looking but unsupported epidemiological results.
