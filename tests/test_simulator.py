from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from energy_grid_sim.loader import load_scenario
from energy_grid_sim.simulator import simulate_day


ROOT = Path(__file__).resolve().parents[1]


class SimulatorTests(unittest.TestCase):
    def _write_temp_scenario(self, scenario: dict) -> Path:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(scenario, tmp)
            return Path(tmp.name)

    def test_surplus_case_serves_every_consumer_every_hour(self) -> None:
        result = simulate_day(load_scenario(ROOT / "data" / "surplus_case.json"))

        for hour in result.hours:
            self.assertEqual(hour.served_energy, hour.demanded_energy)
            self.assertFalse(hour.disconnected_consumers)

    def test_shortage_case_contains_expected_shortfalls(self) -> None:
        result = simulate_day(load_scenario(ROOT / "data" / "shortage_case.json"))

        self.assertTrue(any(hour.disconnected_consumers for hour in result.hours))

        hour_0 = result.hours[0]
        self.assertEqual(hour_0.served_energy, 18.0)
        self.assertEqual(len(hour_0.powered_consumers), 9)
        self.assertEqual(len(hour_0.disconnected_consumers), 1)

        hour_11 = result.hours[11]
        self.assertEqual(hour_11.served_energy, 32.0)
        self.assertEqual(hour_11.disconnected_consumers, ["office_a"])

    def test_generation_always_covers_served_energy(self) -> None:
        for scenario_name in ("surplus_case.json", "shortage_case.json"):
            result = simulate_day(load_scenario(ROOT / "data" / scenario_name))
            for hour in result.hours:
                self.assertGreaterEqual(hour.generated_energy, hour.served_energy)

    def test_coverage_ratio_for_shortage_case_is_below_one(self) -> None:
        result = simulate_day(load_scenario(ROOT / "data" / "shortage_case.json"))
        self.assertLess(result.coverage_ratio, 1.0)

    def test_zero_demand_requires_no_generation_and_zero_cost(self) -> None:
        scenario = {
            "name": "zero_demand",
            "description": "all consumers have zero demand",
            "consumers": [
                {"name": "consumer_a", "hourly_demand": [0] * 24},
                {"name": "consumer_b", "hourly_demand": [0] * 24},
            ],
            "generators": [
                {
                    "name": "diesel_alpha",
                    "kind": "diesel",
                    "hourly_generation": [10] * 24,
                    "cost_per_unit": 7,
                }
            ],
        }

        tmp_path = self._write_temp_scenario(scenario)
        try:
            result = simulate_day(load_scenario(tmp_path))
        finally:
            tmp_path.unlink(missing_ok=True)

        for hour in result.hours:
            self.assertEqual(hour.demanded_energy, 0.0)
            self.assertEqual(hour.served_energy, 0.0)
            self.assertEqual(hour.generated_energy, 0.0)
            self.assertEqual(hour.hourly_cost, 0.0)
            self.assertEqual(hour.active_generators, [])
            self.assertEqual(len(hour.powered_consumers), 2)
            self.assertEqual(hour.disconnected_consumers, [])

    def test_optimizer_prioritizes_number_of_powered_consumers(self) -> None:
        scenario = {
            "name": "consumer_count_priority",
            "description": "two smaller consumers should be preferred over one larger consumer",
            "consumers": [
                {"name": "consumer_a", "hourly_demand": [4] * 24},
                {"name": "consumer_b", "hourly_demand": [4] * 24},
                {"name": "consumer_c", "hourly_demand": [7] * 24},
            ],
            "generators": [
                {
                    "name": "diesel_alpha",
                    "kind": "diesel",
                    "hourly_generation": [8] * 24,
                    "cost_per_unit": 5,
                }
            ],
        }

        tmp_path = self._write_temp_scenario(scenario)
        try:
            result = simulate_day(load_scenario(tmp_path))
        finally:
            tmp_path.unlink(missing_ok=True)

        hour = result.hours[0]
        self.assertEqual(len(hour.powered_consumers), 2)
        self.assertEqual(set(hour.powered_consumers), {"consumer_a", "consumer_b"})
        self.assertEqual(hour.disconnected_consumers, ["consumer_c"])
        self.assertEqual(hour.served_energy, 8.0)

    def test_optimizer_prioritizes_served_energy_when_consumer_count_is_equal(self) -> None:
        scenario = {
            "name": "served_energy_priority",
            "description": "with equal consumer count the algorithm should maximize served energy",
            "consumers": [
                {"name": "consumer_a", "hourly_demand": [4] * 24},
                {"name": "consumer_b", "hourly_demand": [5] * 24},
                {"name": "consumer_c", "hourly_demand": [6] * 24},
            ],
            "generators": [
                {
                    "name": "diesel_alpha",
                    "kind": "diesel",
                    "hourly_generation": [5] * 24,
                    "cost_per_unit": 5,
                }
            ],
        }

        tmp_path = self._write_temp_scenario(scenario)
        try:
            result = simulate_day(load_scenario(tmp_path))
        finally:
            tmp_path.unlink(missing_ok=True)

        hour = result.hours[0]
        self.assertEqual(hour.powered_consumers, ["consumer_b"])
        self.assertEqual(set(hour.disconnected_consumers), {"consumer_a", "consumer_c"})
        self.assertEqual(hour.served_energy, 5.0)

    def test_optimizer_chooses_cheapest_generator_plan(self) -> None:
        scenario = {
            "name": "generator_cost_priority",
            "description": "among feasible generator plans the cheapest one should be selected",
            "consumers": [
                {"name": "consumer_a", "hourly_demand": [5] * 24},
            ],
            "generators": [
                {
                    "name": "diesel_alpha",
                    "kind": "diesel",
                    "hourly_generation": [5] * 24,
                    "cost_per_unit": 10,
                },
                {
                    "name": "solar_alpha",
                    "kind": "solar",
                    "hourly_generation": [5] * 24,
                    "cost_per_unit": 1,
                },
            ],
        }

        tmp_path = self._write_temp_scenario(scenario)
        try:
            result = simulate_day(load_scenario(tmp_path))
        finally:
            tmp_path.unlink(missing_ok=True)

        hour = result.hours[0]
        self.assertEqual(hour.active_generators, ["solar_alpha"])
        self.assertEqual(hour.hourly_cost, 5.0)

    def test_duplicate_consumer_names_are_rejected(self) -> None:
        scenario = {
            "name": "invalid_duplicates",
            "description": "duplicate consumer names",
            "consumers": [
                {"name": "consumer_a", "hourly_demand": [1] * 24},
                {"name": "consumer_a", "hourly_demand": [2] * 24},
            ],
            "generators": [
                {
                    "name": "diesel_alpha",
                    "kind": "diesel",
                    "hourly_generation": [10] * 24,
                    "cost_per_unit": 5,
                }
            ],
        }

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(scenario, tmp)
            tmp_path = Path(tmp.name)

        try:
            with self.assertRaises(ValueError):
                load_scenario(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_duplicate_generator_names_are_rejected(self) -> None:
        scenario = {
            "name": "invalid_generator_duplicates",
            "description": "duplicate generator names",
            "consumers": [
                {"name": "consumer_a", "hourly_demand": [1] * 24},
            ],
            "generators": [
                {
                    "name": "generator_x",
                    "kind": "diesel",
                    "hourly_generation": [10] * 24,
                    "cost_per_unit": 5,
                },
                {
                    "name": "generator_x",
                    "kind": "solar",
                    "hourly_generation": [2] * 24,
                    "cost_per_unit": 1,
                },
            ],
        }

        tmp_path = self._write_temp_scenario(scenario)
        try:
            with self.assertRaises(ValueError):
                load_scenario(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_unsupported_generator_kind_is_rejected(self) -> None:
        scenario = {
            "name": "invalid_generator_kind",
            "description": "unsupported kind",
            "consumers": [
                {"name": "consumer_a", "hourly_demand": [1] * 24},
            ],
            "generators": [
                {
                    "name": "wind_alpha",
                    "kind": "wind",
                    "hourly_generation": [10] * 24,
                    "cost_per_unit": 5,
                }
            ],
        }

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(scenario, tmp)
            tmp_path = Path(tmp.name)

        try:
            with self.assertRaises(ValueError):
                load_scenario(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_negative_demand_is_rejected(self) -> None:
        scenario = {
            "name": "negative_demand",
            "description": "negative demand is invalid",
            "consumers": [
                {"name": "consumer_a", "hourly_demand": [1] * 23 + [-1]},
            ],
            "generators": [
                {
                    "name": "diesel_alpha",
                    "kind": "diesel",
                    "hourly_generation": [10] * 24,
                    "cost_per_unit": 5,
                }
            ],
        }

        tmp_path = self._write_temp_scenario(scenario)
        try:
            with self.assertRaises(ValueError):
                load_scenario(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_invalid_profile_length_is_rejected(self) -> None:
        scenario = {
            "name": "invalid_profile_length",
            "description": "profiles must contain 24 values",
            "consumers": [
                {"name": "consumer_a", "hourly_demand": [1] * 23},
            ],
            "generators": [
                {
                    "name": "diesel_alpha",
                    "kind": "diesel",
                    "hourly_generation": [10] * 24,
                    "cost_per_unit": 5,
                }
            ],
        }

        tmp_path = self._write_temp_scenario(scenario)
        try:
            with self.assertRaises(ValueError):
                load_scenario(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
