from __future__ import annotations

from .models import HOURS_PER_DAY, Scenario, SimulationResult
from .optimizer import optimize_hour


def simulate_day(scenario: Scenario) -> SimulationResult:
    scenario.validate()
    hourly_plans = [
        optimize_hour(hour=hour, consumers=scenario.consumers, generators=scenario.generators)
        for hour in range(HOURS_PER_DAY)
    ]
    return SimulationResult(
        scenario_name=scenario.name,
        scenario_description=scenario.description,
        hours=hourly_plans,
    )
