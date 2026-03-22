from __future__ import annotations

from copy import deepcopy

import pandas as pd

from .idc_secondary_loop import evaluate_idc_secondary_loop


def _with_idc_granularity_scenario(config: dict, scenario: dict[str, object]) -> dict:
    trial = deepcopy(config)
    loop_cfg = trial["idc_secondary_loop"]
    if "parallel_circuits" in scenario:
        loop_cfg["parallel_circuits"] = int(scenario["parallel_circuits"])
    if "horizontal_distribution_length_factor" in scenario:
        loop_cfg["horizontal_distribution_length_factor"] = float(scenario["horizontal_distribution_length_factor"])
    if "minor_loss_multiplier" in scenario:
        loop_cfg["minor_loss_k"] = float(loop_cfg["minor_loss_k"]) * float(scenario["minor_loss_multiplier"])
    if "terminal_pressure_drop_multiplier" in scenario:
        multiplier = float(scenario["terminal_pressure_drop_multiplier"])
        loop_cfg["idc_hx_pressure_drop_kpa"] = float(loop_cfg["idc_hx_pressure_drop_kpa"]) * multiplier
        loop_cfg["coil_and_valve_pressure_drop_kpa"] = float(loop_cfg["coil_and_valve_pressure_drop_kpa"]) * multiplier
        loop_cfg["miscellaneous_pressure_drop_kpa"] = float(loop_cfg["miscellaneous_pressure_drop_kpa"]) * multiplier
    if "additional_header_pressure_drop_kpa" in scenario:
        loop_cfg["miscellaneous_pressure_drop_kpa"] = (
            float(loop_cfg["miscellaneous_pressure_drop_kpa"]) + float(scenario["additional_header_pressure_drop_kpa"])
        )
    return trial


def evaluate_idc_secondary_loop_granularity(
    config: dict,
    chilled_water_mass_flow_kg_s: float,
) -> dict[str, object]:
    scenarios = list(config.get("idc_secondary_loop_granularity", {}).get("scenarios", []))
    if not scenarios:
        raise RuntimeError("No IDC secondary-loop granularity scenarios were configured.")

    base_result = evaluate_idc_secondary_loop(config, chilled_water_mass_flow_kg_s)
    base_selected = base_result["selected_design"]
    rows: list[dict[str, object]] = []

    for scenario in scenarios:
        scenario_name = str(scenario.get("name", "unnamed"))
        scenario_label = str(scenario.get("label", scenario_name))
        trial_config = _with_idc_granularity_scenario(config, scenario)
        result = evaluate_idc_secondary_loop(trial_config, chilled_water_mass_flow_kg_s)
        selected = result["selected_design"]
        rows.append(
            {
                "scenario_name": scenario_name,
                "scenario_label": scenario_label,
                "parallel_circuits": int(result["parallel_circuits"]),
                "horizontal_distribution_length_factor": float(trial_config["idc_secondary_loop"]["horizontal_distribution_length_factor"]),
                "minor_loss_k": float(trial_config["idc_secondary_loop"]["minor_loss_k"]),
                "selected_diameter_m": float(selected["diameter_m"]),
                "equivalent_length_m": float(selected["equivalent_length_m"]),
                "total_pressure_drop_kpa": float(selected["total_pressure_drop_kpa"]),
                "pump_power_kw": float(selected["pump_power_kw"]),
                "pump_power_delta_kw_vs_base": float(selected["pump_power_kw"]) - float(base_selected["pump_power_kw"]),
                "pump_power_delta_pct_vs_base": (
                    (float(selected["pump_power_kw"]) - float(base_selected["pump_power_kw"])) / float(base_selected["pump_power_kw"]) * 100.0
                ),
            }
        )

    table = pd.DataFrame(rows).sort_values("pump_power_kw").reset_index(drop=True)
    return {
        "table": table,
        "base_selected": base_selected,
        "selected_conservative": table.sort_values("pump_power_kw", ascending=False).iloc[0].to_dict() if not table.empty else None,
    }
