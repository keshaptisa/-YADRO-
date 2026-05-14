from __future__ import annotations

import json
from pathlib import Path

from .models import Consumer, Generator, Scenario


def load_scenario(path: str | Path) -> Scenario:
    scenario_path = Path(path)
    with scenario_path.open("r", encoding="utf-8") as file:
        raw_data = json.load(file)

    scenario = Scenario(
        name=raw_data["name"],
        description=raw_data.get("description", ""),
        consumers=[
            Consumer(
                name=consumer["name"],
                hourly_demand=[float(value) for value in consumer["hourly_demand"]],
            )
            for consumer in raw_data["consumers"]
        ],
        generators=[
            Generator(
                name=generator["name"],
                kind=generator["kind"],
                hourly_generation=[float(value) for value in generator["hourly_generation"]],
                cost_per_unit=float(generator["cost_per_unit"]),
            )
            for generator in raw_data["generators"]
        ],
    )
    scenario.validate()
    return scenario
