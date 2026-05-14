from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Literal


HOURS_PER_DAY = 24
GeneratorKind = Literal["diesel", "solar"]
SUPPORTED_GENERATOR_KINDS = {"diesel", "solar"}


@dataclass(frozen=True)
class Consumer:
    name: str
    hourly_demand: list[float]

    def validate(self) -> None:
        _validate_profile(self.name, self.hourly_demand, "demand")


@dataclass(frozen=True)
class Generator:
    name: str
    kind: GeneratorKind
    hourly_generation: list[float]
    cost_per_unit: float

    def validate(self) -> None:
        _validate_profile(self.name, self.hourly_generation, "generation")
        if self.kind not in SUPPORTED_GENERATOR_KINDS:
            allowed = ", ".join(sorted(SUPPORTED_GENERATOR_KINDS))
            raise ValueError(
                f"Generator '{self.name}' has unsupported kind '{self.kind}'. "
                f"Allowed values: {allowed}."
            )
        if self.cost_per_unit < 0:
            raise ValueError(f"Generator '{self.name}' has a negative cost.")


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    consumers: list[Consumer]
    generators: list[Generator]

    def validate(self) -> None:
        if not self.consumers:
            raise ValueError("Scenario must contain at least one consumer.")
        if not self.generators:
            raise ValueError("Scenario must contain at least one generator.")
        _validate_unique_names(
            [consumer.name for consumer in self.consumers],
            entity_type="consumer",
        )
        _validate_unique_names(
            [generator.name for generator in self.generators],
            entity_type="generator",
        )
        for consumer in self.consumers:
            consumer.validate()
        for generator in self.generators:
            generator.validate()


@dataclass(frozen=True)
class HourPlan:
    hour: int
    demanded_energy: float
    served_energy: float
    generated_energy: float
    hourly_cost: float
    active_generators: tuple[str, ...]
    powered_consumers: tuple[str, ...]
    disconnected_consumers: tuple[str, ...]


@dataclass(frozen=True)
class SimulationResult:
    scenario_name: str
    scenario_description: str
    hours: list[HourPlan]

    @property
    def total_cost(self) -> float:
        return sum(hour.hourly_cost for hour in self.hours)

    @property
    def total_demand(self) -> float:
        return sum(hour.demanded_energy for hour in self.hours)

    @property
    def total_served(self) -> float:
        return sum(hour.served_energy for hour in self.hours)

    @property
    def coverage_ratio(self) -> float:
        if self.total_demand == 0:
            return 1.0
        return self.total_served / self.total_demand


def _validate_profile(entity_name: str, profile: list[float], profile_type: str) -> None:
    if len(profile) != HOURS_PER_DAY:
        raise ValueError(
            f"{profile_type.title()} profile for '{entity_name}' must contain "
            f"exactly {HOURS_PER_DAY} hourly values."
        )
    if any(value < 0 for value in profile):
        raise ValueError(
            f"{profile_type.title()} profile for '{entity_name}' contains negative values."
        )


def _validate_unique_names(names: list[str], entity_type: str) -> None:
    duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
    if duplicates:
        duplicate_list = ", ".join(duplicates)
        raise ValueError(
            f"Scenario contains duplicate {entity_type} names: {duplicate_list}."
        )
