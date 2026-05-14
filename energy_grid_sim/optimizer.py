from __future__ import annotations

from itertools import combinations

from .models import Consumer, Generator, HourPlan


def optimize_hour(hour: int, consumers: list[Consumer], generators: list[Generator]) -> HourPlan:
    consumer_plans = _enumerate_consumer_subsets(hour, consumers)
    generator_plans = _enumerate_generator_subsets(hour, generators)

    best_plan: HourPlan | None = None
    best_key: tuple[int, float, float, float, int] | None = None

    full_demand = sum(consumer.hourly_demand[hour] for consumer in consumers)

    for powered_names, disconnected_names, served_energy in consumer_plans:
        generation_plan = _find_cheapest_generation_plan(served_energy, generator_plans)
        if generation_plan is None:
            continue

        active_generators, generated_energy, hourly_cost = generation_plan
        candidate = HourPlan(
            hour=hour,
            demanded_energy=full_demand,
            served_energy=served_energy,
            generated_energy=generated_energy,
            hourly_cost=hourly_cost,
            active_generators=active_generators,
            powered_consumers=powered_names,
            disconnected_consumers=disconnected_names,
        )

        candidate_key = (
            len(powered_names),
            served_energy,
            -hourly_cost,
            -generated_energy,
            -len(active_generators),
        )
        if best_key is None or candidate_key > best_key:
            best_key = candidate_key
            best_plan = candidate

    if best_plan is None:
        raise RuntimeError(f"Could not build a valid plan for hour {hour}.")

    return best_plan


def _enumerate_consumer_subsets(
    hour: int, consumers: list[Consumer]
) -> list[tuple[list[str], list[str], float]]:
    plans: list[tuple[list[str], list[str], float]] = []

    for subset_size in range(len(consumers) + 1):
        for subset in combinations(consumers, subset_size):
            powered_names = [consumer.name for consumer in subset]
            powered_set = set(powered_names)
            disconnected_names = [
                consumer.name for consumer in consumers if consumer.name not in powered_set
            ]
            served_energy = sum(consumer.hourly_demand[hour] for consumer in subset)
            plans.append((powered_names, disconnected_names, served_energy))

    return plans


def _enumerate_generator_subsets(
    hour: int, generators: list[Generator]
) -> list[tuple[list[str], float, float]]:
    plans: list[tuple[list[str], float, float]] = [([], 0.0, 0.0)]

    for subset_size in range(1, len(generators) + 1):
        for subset in combinations(generators, subset_size):
            active_names = [generator.name for generator in subset]
            generated_energy = sum(generator.hourly_generation[hour] for generator in subset)
            hourly_cost = sum(
                generator.hourly_generation[hour] * generator.cost_per_unit for generator in subset
            )
            plans.append((active_names, generated_energy, hourly_cost))

    return plans


def _find_cheapest_generation_plan(
    required_energy: float,
    generator_plans: list[tuple[list[str], float, float]],
) -> tuple[list[str], float, float] | None:
    feasible = [
        plan for plan in generator_plans if plan[1] >= required_energy
    ]
    if not feasible:
        return None

    return min(feasible, key=lambda plan: (plan[2], plan[1], len(plan[0])))
