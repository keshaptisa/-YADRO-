from __future__ import annotations

from decimal import Decimal
from itertools import combinations

from .models import Consumer, Generator, HourPlan


def optimize_hour(hour: int, consumers: list[Consumer], generators: list[Generator]) -> HourPlan:
    generator_plans = _enumerate_generator_subsets(hour, generators)
    consumer_plans = _build_consumer_plans(hour, consumers, generator_plans)

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


def _build_consumer_plans(
    hour: int,
    consumers: list[Consumer],
    generator_plans: list[tuple[list[str], float, float]],
) -> list[tuple[list[str], list[str], float]]:
    hour_demands = [consumer.hourly_demand[hour] for consumer in consumers]
    max_generation = max((plan[1] for plan in generator_plans), default=0.0)

    scaled_demands, scale = _scale_hour_values(hour_demands + [max_generation])
    max_generation_scaled = scaled_demands[-1]
    consumer_demands_scaled = scaled_demands[:-1]

    states: dict[int, tuple[int, tuple[int, ...]]] = {0: (0, tuple())}

    for index, demand_scaled in enumerate(consumer_demands_scaled):
        current_states = list(states.items())
        for served_scaled, (count, indices) in reversed(current_states):
            new_served_scaled = served_scaled + demand_scaled
            if new_served_scaled > max_generation_scaled:
                continue

            new_state = (count + 1, indices + (index,))
            existing_state = states.get(new_served_scaled)
            if existing_state is None or new_state[0] > existing_state[0]:
                states[new_served_scaled] = new_state

    plans: list[tuple[list[str], list[str], float]] = []
    for served_scaled, (_, indices) in sorted(states.items()):
        powered_index_set = set(indices)
        powered_names = [consumers[index].name for index in indices]
        disconnected_names = [
            consumer.name
            for index, consumer in enumerate(consumers)
            if index not in powered_index_set
        ]
        served_energy = served_scaled / scale
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


def _scale_hour_values(values: list[float]) -> tuple[list[int], int]:
    decimals = [Decimal(str(value)).normalize() for value in values]
    max_digits = max(max(0, -decimal_value.as_tuple().exponent) for decimal_value in decimals)
    scale = 10 ** max_digits
    scaled_values = [int(decimal_value * scale) for decimal_value in decimals]
    return scaled_values, scale
