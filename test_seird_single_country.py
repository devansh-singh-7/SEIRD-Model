"""Regression tests for the mechanics-only SEIRD replay."""

import unittest

import numpy as np
import pandas as pd

from seird_single_country import simulate_mechanics_v2


class BetaFlowAlignmentTests(unittest.TestCase):
    def test_interval_beta_equals_beta_recorded_with_its_infection_flow(self) -> None:
        """Each interval-end row must retain the beta used to create its flow."""
        population = 1_000_000.0
        sigma, gamma, mu = 0.2, 0.125, 0.001
        dates = pd.date_range("2020-01-01", periods=4, freq="D")
        reproduction_numbers = np.array([np.nan, 1.25, 2.50, 0.75])
        simulation = simulate_mechanics_v2(
            initial=np.array([999_900.0, 50.0, 50.0, 0.0, 0.0]),
            dates=dates,
            rt=reproduction_numbers,
            validation_start=pd.Timestamp("2021-01-01"),
            fixed_validation_beta=0.0,
            population=population,
            sigma=sigma,
            gamma=gamma,
            mu=mu,
        )
        transitioned = simulation.iloc[1:]

        np.testing.assert_allclose(
            transitioned["beta_used_for_transition"],
            transitioned["beta_used_for_reported_flow"],
            rtol=0.0,
            atol=1e-12,
        )
        expected_beta = reproduction_numbers[1:] * (gamma + mu) * population / transitioned["S_transition_start"].to_numpy()
        np.testing.assert_allclose(transitioned["beta_used_for_transition"], expected_beta, rtol=0.0, atol=1e-12)
        np.testing.assert_allclose(
            transitioned["new_infections_simulated"],
            transitioned["S_transition_start"] - transitioned["S_simulated"],
            rtol=0.0,
            atol=1e-8,
        )


if __name__ == "__main__":
    unittest.main()
