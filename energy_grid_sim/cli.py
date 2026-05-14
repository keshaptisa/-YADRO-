from __future__ import annotations

import argparse
from pathlib import Path

from .loader import load_scenario
from .reporting import render_text_report
from .simulator import simulate_day


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Симуляция энергосети на 24 часа с оптимизацией включения генераторов."
    )
    parser.add_argument(
        "--scenario",
        required=True,
        help="Путь к JSON-файлу со списком потребителей и генераторов.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    scenario_path = Path(args.scenario)
    scenario = load_scenario(scenario_path)
    result = simulate_day(scenario)
    print(render_text_report(result))
    return 0
