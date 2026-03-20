from __future__ import annotations

from copy import deepcopy
import math

import pandas as pd

from .economics import add_annualized_columns
from .fluid_screening import compute_fluid_screening
from .hx_lng_vaporizer import design_lng_vaporizer
from .pipeline_loop import design_pipeline


def evaluate_feasible_alternatives(config: dict, load_result: object, baseline: dict, screening: dict) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    feasible_candidates = screening["table"][screening["table"]["feasible"]].copy()

    for _, candidate in feasible_candidates.iterrows():
        selected_fluid = candidate.to_dict()
        try:
            hx_result = design_lng_vaporizer(config, selected_fluid, screening["total_lng_duty_kw"])
            pipeline_result = design_pipeline(config, selected_fluid, load_result.total_kw, hx_result)
            selected_pipeline = pipeline_result["selected_design"]
            pump_power_kw = float(selected_pipeline["pump_power_kw"])
            available_cooling_kw = hx_result["required_lng_duty_kw"] - float(selected_pipeline["heat_gain_kw"])
            rows.append(
                {
                    "fluid": candidate["fluid"],
                    "coolprop_name": candidate["coolprop_name"],
                    "screening_score": float(candidate["score"]),
                    "required_mass_flow_kg_s": float(candidate["required_mass_flow_kg_s"]),
                    "hx_tube_count": int(hx_result["selected_geometry"]["tube_count"]),
                    "hx_tube_length_m": float(hx_result["selected_geometry"]["tube_length_m"]),
                    "hx_shell_diameter_m": float(hx_result["selected_geometry"]["shell_diameter_m"]),
                    "hx_min_pinch_k": float(hx_result["min_pinch_k"]),
                    "pipeline_supply_id_m": float(selected_pipeline["supply_id_m"]),
                    "pipeline_return_id_m": float(selected_pipeline["return_id_m"]),
                    "pipeline_insulation_thickness_m": float(selected_pipeline["insulation_thickness_m"]),
                    "pipeline_heat_gain_kw": float(selected_pipeline["heat_gain_kw"]),
                    "pump_power_kw": pump_power_kw,
                    "available_cooling_kw": available_cooling_kw,
                    "power_saving_kw": baseline["compressor_power_kw"] - pump_power_kw,
                    "equivalent_cop": load_result.total_kw / pump_power_kw,
                    "design_feasible": available_cooling_kw >= load_result.total_kw - 1e-6,
                    "failure_reason": "",
                }
            )
        except Exception as exc:  # pragma: no cover
            rows.append(
                {
                    "fluid": candidate["fluid"],
                    "coolprop_name": candidate["coolprop_name"],
                    "screening_score": float(candidate["score"]),
                    "required_mass_flow_kg_s": float(candidate["required_mass_flow_kg_s"]),
                    "hx_tube_count": math.nan,
                    "hx_tube_length_m": math.nan,
                    "hx_shell_diameter_m": math.nan,
                    "hx_min_pinch_k": math.nan,
                    "pipeline_supply_id_m": math.nan,
                    "pipeline_return_id_m": math.nan,
                    "pipeline_insulation_thickness_m": math.nan,
                    "pipeline_heat_gain_kw": math.nan,
                    "pump_power_kw": math.nan,
                    "available_cooling_kw": math.nan,
                    "power_saving_kw": math.nan,
                    "equivalent_cop": math.nan,
                    "design_feasible": False,
                    "failure_reason": str(exc),
                }
            )

    alternatives = pd.DataFrame(rows).sort_values(
        ["design_feasible", "pump_power_kw", "screening_score"], ascending=[False, True, False]
    ).reset_index(drop=True)
    if alternatives.empty:
        raise RuntimeError("No alternative designs were produced from the feasible screening set.")
    alternatives = add_annualized_columns(alternatives, "pump_power_kw", baseline["compressor_power_kw"], config)

    feasible_designs = alternatives[alternatives["design_feasible"]]
    selected = feasible_designs.iloc[0].to_dict() if not feasible_designs.empty else None
    return {
        "alternatives": alternatives,
        "selected": selected,
    }


def build_distance_scenarios(config: dict, load_result: object, baseline: dict, hx_result: dict, pipeline_result: dict) -> pd.DataFrame:
    rows: list[dict[str, float | bool]] = []
    for _, sensitivity_row in pipeline_result["sensitivity"].iterrows():
        pump_power_kw = float(sensitivity_row["pump_power_kw"])
        heat_gain_kw = float(sensitivity_row["heat_gain_kw"])
        available_cooling_kw = hx_result["required_lng_duty_kw"] - heat_gain_kw
        rows.append(
            {
                "distance_m": float(sensitivity_row["distance_m"]),
                "distance_km": float(sensitivity_row["distance_m"]) / 1000.0,
                "heat_gain_kw": heat_gain_kw,
                "heat_gain_fraction": float(sensitivity_row["heat_gain_fraction"]),
                "pump_power_kw": pump_power_kw,
                "available_cooling_kw": available_cooling_kw,
                "thermal_margin_kw": available_cooling_kw - load_result.total_kw,
                "equivalent_cop": load_result.total_kw / pump_power_kw,
                "power_saving_kw": baseline["compressor_power_kw"] - pump_power_kw,
                "meets_idc_load": available_cooling_kw >= load_result.total_kw - 1e-6,
                "max_feasible_distance_m": float(pipeline_result["max_feasible_distance_m"]),
            }
        )
    return add_annualized_columns(pd.DataFrame(rows), "pump_power_kw", baseline["compressor_power_kw"], config)


def _with_supply_temperature(config: dict, supply_temp_k: float) -> dict:
    trial = deepcopy(config)
    base_loop = config["coolant_loop"]
    delta_idc = base_loop["after_idc_temp_k"] - base_loop["supply_temp_k"]
    delta_return = base_loop["return_to_lng_temp_k"] - base_loop["after_idc_temp_k"]
    trial["coolant_loop"]["supply_temp_k"] = supply_temp_k
    trial["coolant_loop"]["after_idc_temp_k"] = supply_temp_k + delta_idc
    trial["coolant_loop"]["return_to_lng_temp_k"] = supply_temp_k + delta_idc + delta_return
    return trial


def evaluate_supply_temperature_sweep(config: dict, load_result: object, baseline: dict) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for supply_temp_k in config.get("sensitivity", {}).get("coolant_supply_temp_candidates_k", [config["coolant_loop"]["supply_temp_k"]]):
        trial_config = _with_supply_temperature(config, float(supply_temp_k))
        try:
            screening = compute_fluid_screening(trial_config, load_result.total_kw)
            hx_result = design_lng_vaporizer(trial_config, screening["selected"], screening["total_lng_duty_kw"])
            pipeline_result = design_pipeline(trial_config, screening["selected"], load_result.total_kw, hx_result)
            selected_design = pipeline_result["selected_design"]
            long_distance_row = pipeline_result["sensitivity"].sort_values("distance_m").iloc[-1]
            available_cooling_kw = hx_result["required_lng_duty_kw"] - float(selected_design["heat_gain_kw"])
            long_distance_available_kw = hx_result["required_lng_duty_kw"] - float(long_distance_row["heat_gain_kw"])
            rows.append(
                {
                    "supply_temp_k": float(supply_temp_k),
                    "supply_temp_c": float(supply_temp_k) - 273.15,
                    "selected_fluid": screening["selected"]["fluid"],
                    "screening_score": float(screening["selected"]["score"]),
                    "pump_power_kw": float(selected_design["pump_power_kw"]),
                    "pipeline_heat_gain_kw": float(selected_design["heat_gain_kw"]),
                    "hx_shell_diameter_m": float(hx_result["selected_geometry"]["shell_diameter_m"]),
                    "hx_tube_count": int(hx_result["selected_geometry"]["tube_count"]),
                    "available_cooling_kw": available_cooling_kw,
                    "thermal_margin_kw": available_cooling_kw - load_result.total_kw,
                    "power_saving_kw": baseline["compressor_power_kw"] - float(selected_design["pump_power_kw"]),
                    "max_feasible_distance_km": float(pipeline_result["max_feasible_distance_m"]) / 1000.0,
                    "long_distance_meets_load": long_distance_available_kw >= load_result.total_kw - 1e-6,
                    "status": "feasible",
                    "failure_reason": "",
                }
            )
        except Exception as exc:  # pragma: no cover
            rows.append(
                {
                    "supply_temp_k": float(supply_temp_k),
                    "supply_temp_c": float(supply_temp_k) - 273.15,
                    "selected_fluid": "",
                    "screening_score": math.nan,
                    "pump_power_kw": math.nan,
                    "pipeline_heat_gain_kw": math.nan,
                    "hx_shell_diameter_m": math.nan,
                    "hx_tube_count": math.nan,
                    "available_cooling_kw": math.nan,
                    "thermal_margin_kw": math.nan,
                    "power_saving_kw": math.nan,
                    "max_feasible_distance_km": math.nan,
                    "long_distance_meets_load": False,
                    "status": "failed",
                    "failure_reason": str(exc),
                }
            )
    return add_annualized_columns(pd.DataFrame(rows).sort_values("supply_temp_k").reset_index(drop=True), "pump_power_kw", baseline["compressor_power_kw"], config)
