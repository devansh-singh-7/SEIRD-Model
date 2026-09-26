# Mathematical Formulation: Metapopulation SEIRD Mobility Coupling

`MOBILITY COUPLING DESIGN: READY`

This document provides the complete mathematical specification and derivation of the country-level SEIRD metapopulation coupling layer using the validated route-connectivity network.

---

## 1. Network Primitives and Definitions

Let $\mathcal{C}$ be the global set of countries with valid airport data ($|\mathcal{C}| = 237$).
Let $\mathcal{C}_{\text{net}} \subset \mathcal{C}$ be the set of countries with international route connectivity ($|\mathcal{C}_{\text{net}}| = 225$).
Let $\mathcal{C}_{\text{iso}} = \mathcal{C} \setminus \mathcal{C}_{\text{net}}$ be the set of 12 isolated territories without international flight connectivity.

For any pair $(i, j) \in \mathcal{C}_{\text{net}} \times \mathcal{C}_{\text{net}}$ with $i \neq j$:
- $C_{ij} \in \mathbb{N}_{0}$ is the count of valid scheduled flight routes departing from any airport in source country $i$ and arriving at any airport in destination country $j$.
- $C_i^{\text{out}} = \sum_{k \in \mathcal{C}, k \neq i} C_{ik}$ is the total outgoing international route count from country $i$.
- $C_j^{\text{in}} = \sum_{k \in \mathcal{C}, k \neq j} C_{kj}$ is the total incoming international route count into country $j$.

### Outbound-Normalized Route Connectivity Matrix $P_{ij}$

$$P_{ij} = \frac{C_{ij}}{C_i^{\text{out}}} = \frac{C_{ij}}{\sum_{k \neq i} C_{ik}} \quad \forall i \in \mathcal{C}_{\text{net}}, \ j \in \mathcal{C}, \ j \neq i$$

For countries $m \in \mathcal{C}_{\text{iso}}$:
$$P_{mj} = 0 \quad \forall j \in \mathcal{C}$$

### Row Stochasticity Property
For every source country $i \in \mathcal{C}_{\text{net}}$:
$$\sum_{j \in \mathcal{C}, j \neq i} P_{ij} = 1.0$$
*(Empirically verified across all 225 countries: $\min = 1.000000, \max = 1.000000$).*

### Strict Directional Asymmetry
In general, $P_{ij} \neq P_{ji}$.
*(Empirically verified: 4,550 of 4,558 edges (99.82%) are strictly asymmetric).*

---

## 2. Inbound Coupling Weights $\Pi_{ji}$ and $Q_{ji}$

From the perspective of destination country $j$, exposure arrives from multiple source countries $i$. We define two structurally defensible inbound weighting matrices:

### Option 1: Destination-Normalized Inbound Route Share $Q_{ji}$
The fraction of destination country $j$'s incoming international flight connections that originate in country $i$:
$$Q_{ji} = \frac{C_{ij}}{C_j^{\text{in}}} = \frac{C_{ij}}{\sum_{k \neq j} C_{kj}}$$

Properties:
- $\sum_{i \neq j} Q_{ji} = 1.0$ for all $j$ with $C_j^{\text{in}} > 0$.
- $Q_{ji} \in [0, 1]$.
- Scales exposure directly by the destination country's inbound portfolio composition.

### Option 2: Destination-Normalized Outbound Probability Share $\Pi_{ji}$
The normalized outbound routing probability arriving at destination $j$:
$$\Pi_{ji} = \frac{P_{ij}}{\sum_{k \neq j} P_{kj}}$$

Properties:
- $\sum_{i \neq j} \Pi_{ji} = 1.0$ for all $j$ with $\sum_k P_{kj} > 0$.
- Directly utilizes the pre-normalized $P_{ij}$ values from `country_route_matrix_normalized.csv`.

---

## 3. Coupled Metapopulation SEIRD Equations (Formulation A: Imported-Infection Pressure)

For each country $j \in \mathcal{C}$, let the resident population compartments be:
- $S_j(t)$: Susceptible individuals
- $E_j(t)$: Exposed individuals (latent, non-infectious)
- $I_j(t)$: Infectious individuals
- $R_j(t)$: Recovered / removed individuals
- $D_j(t)$: Deceased individuals
- $N_j = S_j(t) + E_j(t) + I_j(t) + R_j(t) + D_j(t)$: Total country population.

### Governing Ordinary Differential Equations

$$\frac{dS_j}{dt} = - \lambda_j(t) S_j(t)$$

$$\frac{dE_j}{dt} = \lambda_j(t) S_j(t) - \sigma E_j(t)$$

$$\frac{dI_j}{dt} = \sigma E_j(t) - (\gamma + \mu_j) I_j(t)$$

$$\frac{dR_j}{dt} = \gamma I_j(t)$$

$$\frac{dD_j}{dt} = \mu_j I_j(t)$$

where:
- $\sigma$: Incubation progression rate (days$^{-1}$)
- $\gamma$: Recovery rate (days$^{-1}$)
- $\mu_j$: Disease-induced mortality rate (days$^{-1}$)
- $\lambda_j(t)$: Total force of infection in country $j$ (days$^{-1}$).

---

## 4. Force of Infection Decomposition and Coupling

$$\lambda_j(t) = \beta_j(t) \left[ (1 - \alpha_j) \frac{I_j(t)}{N_j} + \alpha_j \Psi_j(t) \right]$$

where:
- $\beta_j(t)$: Country $j$'s internal baseline transmission parameter, derived from single-country SEIRD calibration:
  $$\beta_j(t) = R_{t, j}^{\text{est}}(t) \cdot (\gamma + \mu_j) \cdot \frac{N_j}{S_j(t-1)}$$
- $\alpha_j \in [0, 1)$: International coupling strength (fraction of transmission hazard attributable to international connectivity).
- $(1 - \alpha_j)$: Domestic exposure fraction. Note $(1 - \alpha_j) + \alpha_j = 1.0$ (convex partitioning, prevents double counting).
- $\Psi_j(t)$: Incoming imported infectious pressure (dimensionless, bounded in $[0, 1]$).

### Imported Infectious Pressure $\Psi_j(t)$

$$\Psi_j(t) = \sum_{i \in \mathcal{C}, i \neq j} Q_{ji} \cdot \rho_i(t)$$

where:
$$\rho_i(t) = \frac{I_i(t)}{N_i}$$
is the **per-capita infectious prevalence** in source country $i$.

---

## 5. Mathematical Proofs of Fundamental Properties

### Theorem 1 (Strict Mass Conservation)
*For every individual country $j \in \mathcal{C}$, total population is strictly conserved:*
$$\frac{d N_j}{dt} = \frac{d}{dt} \left( S_j(t) + E_j(t) + I_j(t) + R_j(t) + D_j(t) \right) = 0$$

*Proof:*
Summing the five ODEs for country $j$:
$$\frac{dN_j}{dt} = -\lambda_j S_j + (\lambda_j S_j - \sigma E_j) + (\sigma E_j - (\gamma + \mu_j) I_j) + \gamma I_j + \mu_j I_j$$
$$= (-\lambda_j + \lambda_j) S_j + (-\sigma + \sigma) E_j + (-(\gamma + \mu_j) + \gamma + \mu_j) I_j = 0$$
Hence $N_j(t) = N_j(0) = \text{constant}$ for all $t \ge 0$.
Consequently, global metapopulation is also identically conserved:
$$\frac{d}{dt} \sum_{j \in \mathcal{C}} N_j = \sum_{j \in \mathcal{C}} \frac{dN_j}{dt} = 0 \quad \blacksquare$$

### Theorem 2 (Non-Negativity of Compartments)
*If $S_j(0), E_j(0), I_j(0), R_j(0), D_j(0) \ge 0$, then all compartments remain non-negative for all $t > 0$.*

*Proof:*
1. $S_j(t) = S_j(0) \exp\left( -\int_0^t \lambda_j(\tau) d\tau \right) \ge 0$ since $S_j(0) \ge 0$ and the exponential is strictly positive.
2. At any boundary $E_j = 0$ with $S_j \ge 0, \lambda_j \ge 0$: $dE_j/dt = \lambda_j S_j \ge 0$. Trajectories cannot exit the non-negative orthant.
3. At $I_j = 0$ with $E_j \ge 0$: $dI_j/dt = \sigma E_j \ge 0$.
4. $dR_j/dt = \gamma I_j \ge 0$ and $dD_j/dt = \mu_j I_j \ge 0$, so $R_j$ and $D_j$ are monotonically non-decreasing. $\blacksquare$

### Theorem 3 (No Spontaneous Disease Generation)
*If $I_i(0) = 0$ and $E_i(0) = 0$ for all $i \in \mathcal{C}$, then $\lambda_j(t) = 0$ and no infections can occur.*

*Proof:*
If $I_i(0) = 0 \ \forall i$, then $\rho_i(0) = 0 \ \forall i$, which implies $\Psi_j(0) = 0 \ \forall j$.
Since $I_j(0) = 0$, the local term $(1 - \alpha_j)(I_j / N_j) = 0$.
Thus $\lambda_j(0) = \beta_j(0) [0 + 0] = 0$.
Since $dE_j/dt = 0$ and $dI_j/dt = 0$, $E_j(t) = 0$ and $I_j(t) = 0$ for all $t$. $\blacksquare$

---

## 6. Boundary Conditions: Isolated Countries

For any isolated territory $m \in \mathcal{C}_{\text{iso}}$ ($|\mathcal{C}_{\text{iso}}| = 12$):
1. Inbound route connections: $C_{im} = 0 \ \forall i \implies C_m^{\text{in}} = 0$.
2. Inbound coupling weights: $Q_{mi} = 0 \ \forall i$.
3. Incoming infectious pressure: $\Psi_m(t) = 0$.
4. Effective international coupling: $\alpha_m = 0$.
5. Force of infection collapses strictly to domestic transmission:
   $$\lambda_m(t) = \beta_m(t) \frac{I_m(t)}{N_m}$$

Isolated countries are preserved within the global model but remain epidemiologically uncoupled from cross-border air travel.

---

## 7. Contrast: Formulation B (Explicit Metapopulation Movement ODEs)

Under an explicit population movement model (Lagrangian or Eulerian flux):
$$\frac{dX_j}{dt} = \text{SEIRD}_j(X_j) + \sum_{i \neq j} \Phi_{ij}^X(t) - \sum_{k \neq j} \Phi_{jk}^X(t) \quad \text{for } X \in \{S, E, I, R\}$$

where $\Phi_{ij}^X(t)$ is the physical flow of persons in compartment $X$ from country $i$ to country $j$ (persons / day).

To compute $\Phi_{ij}^X(t)$ without fabricating data, the following relationship would be required:
$$\Phi_{ij}^X(t) = V_{ij} \cdot \frac{X_i(t)}{N_i(t)}$$
where $V_{ij}$ is the absolute passenger volume (passengers / day) between country $i$ and country $j$.

### Parameter Availability Audit for Formulation B:
- $V_{ij}$ (daily passenger volume): **BLOCKED — REQUIRED INPUT NOT AVAILABLE**.
- $\theta_i$ (per-capita travel rate): **BLOCKED — REQUIRED INPUT NOT AVAILABLE**.
- $\tau$ (trip duration / return rate): **BLOCKED — REQUIRED INPUT NOT AVAILABLE**.

Because these parameters cannot be derived from `cleaned_routes.csv` (which contains static route records without frequency or passenger manifests), **Formulation B cannot be implemented without violating anti-hallucination guardrails**.
