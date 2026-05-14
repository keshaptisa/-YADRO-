from __future__ import annotations

from .models import SimulationResult


def render_text_report(result: SimulationResult) -> str:
    generator_column_width = max(
        len("Активные генераторы"),
        max(
            (len(", ".join(hour.active_generators)) for hour in result.hours if hour.active_generators),
            default=1,
        ),
    )
    disconnected_column_width = max(
        len("Отключенные потребители"),
        max(
            (
                len(", ".join(hour.disconnected_consumers))
                for hour in result.hours
                if hour.disconnected_consumers
            ),
            default=1,
        ),
    )
    header = (
        "Час | Спрос  | Покрыто | Генерация | Цена   | "
        f"{'Активные генераторы':<{generator_column_width}} | "
        f"{'Отключенные потребители':<{disconnected_column_width}}"
    )
    lines = [
        f"Сценарий: {result.scenario_name}",
        result.scenario_description,
        "",
        header,
        "-" * len(header),
    ]

    for hour in result.hours:
        generators = ", ".join(hour.active_generators) if hour.active_generators else "-"
        disconnected = (
            ", ".join(hour.disconnected_consumers)
            if hour.disconnected_consumers
            else "-"
        )
        lines.append(
            f"{hour.hour:02d}   | "
            f"{hour.demanded_energy:6.1f} | "
            f"{hour.served_energy:6.1f} | "
            f"{hour.generated_energy:9.1f} | "
            f"{hour.hourly_cost:6.1f} | "
            f"{generators:<{generator_column_width}} | "
            f"{disconnected}"
        )

    lines.extend(
        [
            "",
            f"Суммарный спрос:      {result.total_demand:.1f}",
            f"Суммарно покрыто:     {result.total_served:.1f}",
            f"Доля покрытия спроса: {result.coverage_ratio:.2%}",
            f"Итоговая стоимость:   {result.total_cost:.1f}",
        ]
    )
    return "\n".join(lines)
