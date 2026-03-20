from __future__ import annotations

from copy import deepcopy
import math

import pandas as pd

from .economics import add_annualized_columns
from .fluid_screening import compute_fluid_screening
from .hx_lng_vaporizer import design_lng_vaporizer
from .pipeline_loop import design_pipeline


def _merge_fluid_with_pipeline(selected_fluid: dict, pipeline_result: dict) -> dict[str, object]:
    merged = dict(selected_fluid)
    merged["required_mass_flow_kg_s"] = float(pipeline_result["selected_design"]["required_mass_flow_kg_s"])
    merged["after_idc_temp_k"] = float(pipeline_result["after_idc_temp_k"])
    merged["return_to_lng_temp_k"] = float(pipeline_result["selected_design"]["return_to_lng_temp_k"])
    return merged


def _target_distance_row(sensitivity: pd.DataFrame, target_distance_m: float) -> pd.Series:
    target_rows = sensitivity.loc[(sensitivity["distance_m"] - target_distance_m).abs() < 1e-6]
    if not target_rows.empty:
        return target_rows.iloc[0]
    return sensitivity.iloc[(sensitivity["distance_m"] - target_distance_m).abs().argmin()]


def evaluate_feasible_alternatives(config: dict, load_result: object, baseline: dict, screening: dict) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    feasible_candidates = screening["table"][screening["table"]["feasible"]].copy()

    for _, candidate in feasible_candidates.iterrows():
        selected_fluid = candidate.to_dict()
        try:
            pipeline_result = design_pipeline(config, selected_fluid, load_result.total_kw)
            hx_result = design_lng_vaporizer(
                config,
                _merge_fluid_with_pipeline(selected_fluid, pipeline_result),
                float(pipeline_result["selected_design"]["actual_lng_duty_kw"]),
            )
            selected_pipeline = pipeline_result["selected_design"]
            pump_power_kw = float(selected_pipeline["pump_power_kw"])
            available_cooling_kw = (
                hx_result["required_lng_duty_kw"]
                - float(selected_pipeline["heat_gain_kw"])
                - float(selected_pipeline["supplemental_warmup_kw"])
            )
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
                    "supplemental_warmup_kw": float(selected_pipeline["supplemental_warmup_kw"]),
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
        supplemental_warmup_kw = float(sensitivity_row["supplemental_warmup_kw"])
        available_cooling_kw = hx_result["required_lng_duty_kw"] - heat_gain_kw - supplemental_warmup_kw
        rows.append(
            {
                "distance_m": float(sensitivity_row["distance_m"]),
                "distance_km": float(sensitivity_row["distance_m"]) / 1000.0,
                "heat_gain_kw": heat_gain_kw,
                "heat_gain_fraction": float(sensitivity_row["heat_gain_fraction"]),
                "supplemental_warmup_kw": supplemental_warmup_kw,
                "pump_power_kw": pump_power_kw,
                "available_cooling_kw": available_cooling_kw,
                "thermal_margin_kw": available_cooling_kw - load_result.total_kw,
                "equivalent_cop": load_result.total_kw / pump_power_kw,
                "power_saving_kw": baseline["compressor_power_kw"] - pump_power_kw,
                "return_to_lng_temp_k": float(sensitivity_row["return_to_lng_temp_k"]),
                "hot_end_margin_k": float(sensitivity_row["hot_end_margin_k"]),
                "meets_idc_load": bool(sensitivity_row["feasible"]),
                "max_feasible_distance_m": float(pipeline_result["max_feasible_distance_m"]),
            }
        )
    return add_annualized_columns(pd.DataFrame(rows), "pump_power_kw", baseline["compressor_power_kw"], config)


def _with_supply_temperature(config: dict, supply_temp_k: float) -> dict:
    trial = deepcopy(config)
    trial["coolant_loop"]["supply_temp_k"] = supply_temp_k
    return trial


def evaluate_supply_temperature_sweep(config: dict, load_result: object, baseline: dict) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for supply_temp_k in config.get("sensitivity", {}).get("coolant_supply_temp_candidates_k", [config["coolant_loop"]["supply_temp_k"]]):
        trial_config = _with_supply_temperature(config, float(supply_temp_k))
        try:
            screening = compute_fluid_screening(trial_config, load_result.total_kw)
            pipeline_result = design_pipeline(trial_config, screening["selected"], load_result.total_kw)
            hx_result = design_lng_vaporizer(
                trial_config,
                _merge_fluid_with_pipeline(screening["selected"], pipeline_result),
                float(pipeline_result["selected_design"]["actual_lng_duty_kw"]),
            )
            selected_design = pipeline_result["selected_design"]
            target_distance_m = float(trial_config["system_targets"]["long_distance_pipeline_m"])
            long_distance_row = _target_distance_row(pipeline_result["sensitivity"], target_distance_m)
            available_cooling_kw = (
                hx_result["required_lng_duty_kw"]
                - float(selected_design["heat_gain_kw"])
                - float(selected_design["supplemental_warmup_kw"])
            )
            rows.append(
                {
                    "supply_temp_k": float(supply_temp_k),
                    "supply_temp_c": float(supply_temp_k) - 273.15,
                    "selected_fluid": screening["selected"]["fluid"],
                    "screening_score": float(screening["selected"]["score"]),
                    "pump_power_kw": float(selected_design["pump_power_kw"]),
                    "pipeline_heat_gain_kw": float(selected_design["heat_gain_kw"]),
                    "supplemental_warmup_kw": float(selected_design["supplemental_warmup_kw"]),
                    "hx_shell_diameter_m": float(hx_result["selected_geometry"]["shell_diameter_m"]),
                    "hx_tube_count": int(hx_result["selected_geometry"]["tube_count"]),
                    "available_cooling_kw": available_cooling_kw,
                    "thermal_margin_kw": available_cooling_kw - load_result.total_kw,
                    "power_saving_kw": baseline["compressor_power_kw"] - float(selected_design["pump_power_kw"]),
                    "max_feasible_distance_km": float(pipeline_result["max_feasible_distance_m"]) / 1000.0,
                    "long_distance_meets_load": bool(long_distance_row["feasible"]),
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


def evaluate_ambient_closure_map(config: dict, load_result: object, baseline: dict) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    target_distance_m = float(config["system_targets"]["long_distance_pipeline_m"])
    base_distance_m = float(config["assignment"]["pipeline_distance_m"])
    tolerance_kw = 1e-3

    for supply_temp_k in config.get("sensitivity", {}).get(
        "coolant_supply_temp_candidates_k", [config["coolant_loop"]["supply_temp_k"]]
    ):
        trial_config = _with_supply_temperature(config, float(supply_temp_k))
        screening = compute_fluid_screening(trial_config, load_result.total_kw)
        feasible_candidates = screening["table"][screening["table"]["feasible"]].copy()

        for _, candidate in feasible_candidates.iterrows():
            selected_fluid = candidate.to_dict()
            is_screening_selected = str(candidate["fluid"]) == str(screening["selected"]["fluid"])
            try:
                pipeline_result = design_pipeline(trial_config, selected_fluid, load_result.total_kw)
                hx_result = design_lng_vaporizer(
                    trial_config,
                    _merge_fluid_with_pipeline(selected_fluid, pipeline_result),
                    float(pipeline_result["selected_design"]["actual_lng_duty_kw"]),
                )
                selected_design = pipeline_result["selected_design"]
                long_distance_row = _target_distance_row(pipeline_result["sensitivity"], target_distance_m)
                closure_distance_m = float(pipeline_result.get("ambient_only_closure_distance_m", math.nan))
                closure_distance_km = closure_distance_m / 1000.0 if math.isfinite(closure_distance_m) else math.nan
                warmup_free_at_base = (
                    bool(selected_design["feasible"])
                    and float(selected_design["supplemental_warmup_kw"]) <= tolerance_kw
                )
                warmup_free_at_long = (
                    bool(long_distance_row["feasible"])
                    and float(long_distance_row["supplemental_warmup_kw"]) <= tolerance_kw
                )
                rows.append(
                    {
                        "supply_temp_k": float(supply_temp_k),
                        "supply_temp_c": float(supply_temp_k) - 273.15,
                        "fluid": candidate["fluid"],
                        "coolprop_name": candidate["coolprop_name"],
                        "selected_by_screening": is_screening_selected,
                        "screening_score": float(candidate["score"]),
                        "pump_power_kw": float(selected_design["pump_power_kw"]),
                        "pipeline_heat_gain_kw": float(selected_design["heat_gain_kw"]),
                        "supplemental_warmup_kw": float(selected_design["supplemental_warmup_kw"]),
                        "actual_lng_duty_kw": float(selected_design["actual_lng_duty_kw"]),
                        "max_feasible_distance_km": float(pipeline_result["max_feasible_distance_m"]) / 1000.0,
                        "ambient_only_closure_distance_km": closure_distance_km,
                        "warmup_free_at_base_distance": warmup_free_at_base,
                        "warmup_free_at_long_distance": warmup_free_at_long,
                        "base_distance_km": base_distance_m / 1000.0,
                        "long_distance_km": target_distance_m / 1000.0,
                        "long_distance_supplemental_warmup_kw": float(long_distance_row["supplemental_warmup_kw"]),
                        "long_distance_pump_power_kw": float(long_distance_row["pump_power_kw"]),
                        "long_distance_feasible": bool(long_distance_row["feasible"]),
                        "hx_min_pinch_k": float(hx_result["min_pinch_k"]),
                        "status": "feasible",
                        "failure_reason": "",
                    }
                )
            except Exception as exc:  # pragma: no cover
                rows.append(
                    {
                        "supply_temp_k": float(supply_temp_k),
                        "supply_temp_c": float(supply_temp_k) - 273.15,
                        "fluid": candidate["fluid"],
                        "coolprop_name": candidate["coolprop_name"],
                        "selected_by_screening": is_screening_selected,
                        "screening_score": float(candidate["score"]),
                        "pump_power_kw": math.nan,
                        "pipeline_heat_gain_kw": math.nan,
                        "supplemental_warmup_kw": math.nan,
                        "actual_lng_duty_kw": math.nan,
                        "max_feasible_distance_km": math.nan,
                        "ambient_only_closure_distance_km": math.nan,
                        "warmup_free_at_base_distance": False,
                        "warmup_free_at_long_distance": False,
                        "base_distance_km": base_distance_m / 1000.0,
                        "long_distance_km": target_distance_m / 1000.0,
                        "long_distance_supplemental_warmup_kw": math.nan,
                        "long_distance_pump_power_kw": math.nan,
                        "long_distance_feasible": False,
                        "hx_min_pinch_k": math.nan,
                        "status": "failed",
                        "failure_reason": str(exc),
                    }
                )

    frame = pd.DataFrame(rows)
    frame["closure_rank_km"] = frame["ambient_only_closure_distance_km"].fillna(math.inf)
    frame = frame.sort_values(
        ["closure_rank_km", "pump_power_kw", "screening_score"],
        ascending=[True, True, False],
    ).drop(columns=["closure_rank_km"]).reset_index(drop=True)
    frame = add_annualized_columns(frame, "pump_power_kw", baseline["compressor_power_kw"], config)

    feasible_closure = frame[
        (frame["status"] == "feasible") & (frame["ambient_only_closure_distance_km"].notna())
    ].sort_values(["ambient_only_closure_distance_km", "pump_power_kw", "screening_score"], ascending=[True, True, False])

    selected = feasible_closure.iloc[0].to_dict() if not feasible_closure.empty else None
    return {
        "table": frame,
        "selected": selected,
        "has_base_distance_warmup_free_design": bool(
            ((frame["status"] == "feasible") & frame["warmup_free_at_base_distance"]).any()
        ),
        "has_long_distance_warmup_free_design": bool(
            ((frame["status"] == "feasible") & frame["warmup_free_at_long_distance"]).any()
        ),
    }
