from __future__ import annotations

from copy import deepcopy
import math

import pandas as pd

from .baseline_vcc import compute_baseline_cycle
from .economics import add_annualized_columns
from .fluid_screening import compute_fluid_screening
from .hx_lng_vaporizer import design_lng_vaporizer
from .load_model import compute_load_model
from .parallel import ParallelOptions, map_items
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


def evaluate_feasible_alternatives(
    config: dict,
    load_result: object,
    baseline: dict,
    screening: dict,
    parallel_options: ParallelOptions | None = None,
) -> dict[str, object]:
    feasible_candidates = screening["table"][screening["table"]["feasible"]].copy()
    options = parallel_options or SERIAL_PARALLEL_OPTIONS
    rows = map_items(
        _evaluate_feasible_alternative_task,
        [
            {
                "config": config,
                "candidate": candidate.to_dict(),
                "required_cooling_kw": load_result.total_kw,
                "baseline_power_kw": baseline["compressor_power_kw"],
            }
            for _, candidate in feasible_candidates.iterrows()
        ],
        options,
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


def _with_pipeline_distance(config: dict, distance_m: float) -> dict:
    trial = deepcopy(config)
    trial["assignment"]["pipeline_distance_m"] = distance_m
    return trial


def _with_pipeline_search_grid(config: dict, diameter_candidates_m: list[float], insulation_candidates_m: list[float]) -> dict:
    trial = deepcopy(config)
    trial["pipeline_design"]["diameter_candidates_m"] = [float(value) for value in diameter_candidates_m]
    trial["pipeline_design"]["insulation_thickness_candidates_m"] = [float(value) for value in insulation_candidates_m]
    return trial


def _with_environment_overrides(config: dict, thermal_case: dict[str, object]) -> dict:
    trial = deepcopy(config)
    if "ambient_air_temp_k" in thermal_case:
        trial["assignment"]["ambient_air_temp_k"] = float(thermal_case["ambient_air_temp_k"])
    if "ambient_relative_humidity" in thermal_case:
        trial["assignment"]["ambient_relative_humidity"] = float(thermal_case["ambient_relative_humidity"])
    return trial


SERIAL_PARALLEL_OPTIONS = ParallelOptions(enabled=False, workers=1)


def _evaluate_feasible_alternative_task(task: dict[str, object]) -> dict[str, object]:
    config = dict(task["config"])
    candidate = dict(task["candidate"])
    required_cooling_kw = float(task["required_cooling_kw"])
    baseline_power_kw = float(task["baseline_power_kw"])
    try:
        pipeline_result = design_pipeline(config, candidate, required_cooling_kw)
        hx_result = design_lng_vaporizer(
            config,
            _merge_fluid_with_pipeline(candidate, pipeline_result),
            float(pipeline_result["selected_design"]["actual_lng_duty_kw"]),
        )
        selected_pipeline = pipeline_result["selected_design"]
        pump_power_kw = float(selected_pipeline["pump_power_kw"])
        available_cooling_kw = (
            hx_result["required_lng_duty_kw"]
            - float(selected_pipeline["heat_gain_kw"])
            - float(selected_pipeline["supplemental_warmup_kw"])
        )
        return {
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
            "power_saving_kw": baseline_power_kw - pump_power_kw,
            "equivalent_cop": required_cooling_kw / pump_power_kw,
            "design_feasible": available_cooling_kw >= required_cooling_kw - 1e-6,
            "failure_reason": "",
        }
    except Exception as exc:  # pragma: no cover
        return {
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
            "supplemental_warmup_kw": math.nan,
            "pump_power_kw": math.nan,
            "available_cooling_kw": math.nan,
            "power_saving_kw": math.nan,
            "equivalent_cop": math.nan,
            "design_feasible": False,
            "failure_reason": str(exc),
        }


def _evaluate_supply_temperature_sweep_task(task: dict[str, object]) -> dict[str, object]:
    config = dict(task["config"])
    required_cooling_kw = float(task["required_cooling_kw"])
    baseline_power_kw = float(task["baseline_power_kw"])
    supply_temp_k = float(task["supply_temp_k"])
    trial_config = _with_supply_temperature(config, supply_temp_k)
    try:
        screening = compute_fluid_screening(
            trial_config,
            required_cooling_kw,
            parallel_options=SERIAL_PARALLEL_OPTIONS,
        )
        pipeline_result = design_pipeline(trial_config, screening["selected"], required_cooling_kw)
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
        return {
            "supply_temp_k": supply_temp_k,
            "supply_temp_c": supply_temp_k - 273.15,
            "selected_fluid": screening["selected"]["fluid"],
            "screening_score": float(screening["selected"]["score"]),
            "pump_power_kw": float(selected_design["pump_power_kw"]),
            "pipeline_heat_gain_kw": float(selected_design["heat_gain_kw"]),
            "supplemental_warmup_kw": float(selected_design["supplemental_warmup_kw"]),
            "hx_shell_diameter_m": float(hx_result["selected_geometry"]["shell_diameter_m"]),
            "hx_tube_count": int(hx_result["selected_geometry"]["tube_count"]),
            "available_cooling_kw": available_cooling_kw,
            "thermal_margin_kw": available_cooling_kw - required_cooling_kw,
            "power_saving_kw": baseline_power_kw - float(selected_design["pump_power_kw"]),
            "max_feasible_distance_km": float(pipeline_result["max_feasible_distance_m"]) / 1000.0,
            "long_distance_meets_load": bool(long_distance_row["feasible"]),
            "status": "feasible",
            "failure_reason": "",
        }
    except Exception as exc:  # pragma: no cover
        return {
            "supply_temp_k": supply_temp_k,
            "supply_temp_c": supply_temp_k - 273.15,
            "selected_fluid": "",
            "screening_score": math.nan,
            "pump_power_kw": math.nan,
            "pipeline_heat_gain_kw": math.nan,
            "supplemental_warmup_kw": math.nan,
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


def _evaluate_ambient_closure_task(task: dict[str, object]) -> list[dict[str, object]]:
    config = dict(task["config"])
    required_cooling_kw = float(task["required_cooling_kw"])
    supply_temp_k = float(task["supply_temp_k"])
    target_distance_m = float(config["system_targets"]["long_distance_pipeline_m"])
    base_distance_m = float(config["assignment"]["pipeline_distance_m"])
    tolerance_kw = 1e-3

    trial_config = _with_supply_temperature(config, supply_temp_k)
    screening = compute_fluid_screening(
        trial_config,
        required_cooling_kw,
        parallel_options=SERIAL_PARALLEL_OPTIONS,
    )
    feasible_candidates = screening["table"][screening["table"]["feasible"]].copy()

    rows: list[dict[str, object]] = []
    for _, candidate in feasible_candidates.iterrows():
        selected_fluid = candidate.to_dict()
        is_screening_selected = str(candidate["fluid"]) == str(screening["selected"]["fluid"])
        try:
            pipeline_result = design_pipeline(trial_config, selected_fluid, required_cooling_kw)
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
                    "supply_temp_k": supply_temp_k,
                    "supply_temp_c": supply_temp_k - 273.15,
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
                    "supply_temp_k": supply_temp_k,
                    "supply_temp_c": supply_temp_k - 273.15,
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
    return rows


def _evaluate_zero_warmup_target_task(task: dict[str, object]) -> list[dict[str, object]]:
    config = dict(task["config"])
    required_cooling_kw = float(task["required_cooling_kw"])
    target_distance_m = float(task["target_distance_m"])
    supply_temp_k = float(task["supply_temp_k"])
    trial_config = _with_supply_temperature(config, supply_temp_k)
    screening = compute_fluid_screening(
        trial_config,
        required_cooling_kw,
        parallel_options=SERIAL_PARALLEL_OPTIONS,
    )
    feasible_candidates = screening["table"][screening["table"]["feasible"]].copy()
    target_config = _with_pipeline_distance(trial_config, target_distance_m)
    tolerance_kw = 1e-3

    rows: list[dict[str, object]] = []
    for _, candidate in feasible_candidates.iterrows():
        selected_fluid = candidate.to_dict()
        is_screening_selected = str(candidate["fluid"]) == str(screening["selected"]["fluid"])
        try:
            pipeline_result = design_pipeline(target_config, selected_fluid, required_cooling_kw)
            feasible_scan = pipeline_result["scan_table"][pipeline_result["scan_table"]["feasible"]].copy()
            if feasible_scan.empty:
                raise RuntimeError("No feasible pipeline design found for the target distance.")

            min_supplemental_design = feasible_scan.sort_values(
                ["supplemental_warmup_kw", "pump_power_kw", "heat_gain_kw"],
                ascending=[True, True, True],
            ).iloc[0]
            zero_warmup_designs = feasible_scan[
                feasible_scan["supplemental_warmup_kw"] <= tolerance_kw
            ].sort_values(["pump_power_kw", "heat_gain_kw"], ascending=[True, True])
            best_design = zero_warmup_designs.iloc[0] if not zero_warmup_designs.empty else min_supplemental_design

            rows.append(
                {
                    "target_distance_m": target_distance_m,
                    "target_distance_km": target_distance_m / 1000.0,
                    "supply_temp_k": supply_temp_k,
                    "supply_temp_c": supply_temp_k - 273.15,
                    "fluid": candidate["fluid"],
                    "coolprop_name": candidate["coolprop_name"],
                    "selected_by_screening": is_screening_selected,
                    "screening_score": float(candidate["score"]),
                    "zero_warmup_design_found": not zero_warmup_designs.empty,
                    "minimum_supplemental_warmup_kw": float(min_supplemental_design["supplemental_warmup_kw"]),
                    "best_design_pump_power_kw": float(best_design["pump_power_kw"]),
                    "best_design_heat_gain_kw": float(best_design["heat_gain_kw"]),
                    "best_design_supplemental_warmup_kw": float(best_design["supplemental_warmup_kw"]),
                    "best_design_actual_lng_duty_kw": float(best_design["actual_lng_duty_kw"]),
                    "best_design_supply_id_m": float(best_design["supply_id_m"]),
                    "best_design_return_id_m": float(best_design["return_id_m"]),
                    "best_design_insulation_thickness_m": float(best_design["insulation_thickness_m"]),
                    "max_feasible_distance_km": float(pipeline_result["max_feasible_distance_m"]) / 1000.0,
                    "status": "feasible",
                    "failure_reason": "",
                }
            )
        except Exception as exc:  # pragma: no cover
            rows.append(
                {
                    "target_distance_m": target_distance_m,
                    "target_distance_km": target_distance_m / 1000.0,
                    "supply_temp_k": supply_temp_k,
                    "supply_temp_c": supply_temp_k - 273.15,
                    "fluid": candidate["fluid"],
                    "coolprop_name": candidate["coolprop_name"],
                    "selected_by_screening": is_screening_selected,
                    "screening_score": float(candidate["score"]),
                    "zero_warmup_design_found": False,
                    "minimum_supplemental_warmup_kw": math.nan,
                    "best_design_pump_power_kw": math.nan,
                    "best_design_heat_gain_kw": math.nan,
                    "best_design_supplemental_warmup_kw": math.nan,
                    "best_design_actual_lng_duty_kw": math.nan,
                    "best_design_supply_id_m": math.nan,
                    "best_design_return_id_m": math.nan,
                    "best_design_insulation_thickness_m": math.nan,
                    "max_feasible_distance_km": math.nan,
                    "status": "failed",
                    "failure_reason": str(exc),
                }
            )
    return rows


def _evaluate_passive_zero_warmup_task(task: dict[str, object]) -> list[dict[str, object]]:
    config = dict(task["config"])
    scenario_name = str(task["scenario_name"])
    thermal_case = dict(task["thermal_case"])
    target_distance_m = float(task["target_distance_m"])
    supply_temp_k = float(task["supply_temp_k"])
    diameter_candidates_m = list(task["diameter_candidates_m"])
    insulation_candidates_m = list(task["insulation_candidates_m"])
    tolerance_kw = 1e-3

    scenario_config = _with_environment_overrides(config, thermal_case)
    load_result = compute_load_model(scenario_config)
    baseline = compute_baseline_cycle(scenario_config, load_result.total_kw)

    trial_config = _with_supply_temperature(scenario_config, supply_temp_k)
    trial_config = _with_pipeline_distance(trial_config, target_distance_m)
    trial_config = _with_pipeline_search_grid(trial_config, diameter_candidates_m, insulation_candidates_m)
    screening = compute_fluid_screening(
        trial_config,
        load_result.total_kw,
        parallel_options=SERIAL_PARALLEL_OPTIONS,
    )
    feasible_candidates = screening["table"][screening["table"]["feasible"]].copy()

    rows: list[dict[str, object]] = []
    for _, candidate in feasible_candidates.iterrows():
        selected_fluid = candidate.to_dict()
        is_screening_selected = str(candidate["fluid"]) == str(screening["selected"]["fluid"])
        try:
            pipeline_result = design_pipeline(
                trial_config,
                selected_fluid,
                load_result.total_kw,
                thermal_case=thermal_case,
            )
            feasible_scan = pipeline_result["scan_table"][pipeline_result["scan_table"]["feasible"]].copy()
            if feasible_scan.empty:
                raise RuntimeError("No feasible pipeline design found for the configured passive-heat case.")

            min_supplemental_design = feasible_scan.sort_values(
                ["supplemental_warmup_kw", "pump_power_kw", "heat_gain_kw"],
                ascending=[True, True, True],
            ).iloc[0]
            zero_warmup_designs = feasible_scan[
                feasible_scan["supplemental_warmup_kw"] <= tolerance_kw
            ].sort_values(["pump_power_kw", "heat_gain_kw"], ascending=[True, True])
            best_design = zero_warmup_designs.iloc[0] if not zero_warmup_designs.empty else min_supplemental_design

            rows.append(
                {
                    "scenario_name": scenario_name,
                    "thermal_mode": str(thermal_case.get("mode", "air")),
                    "ambient_air_temp_k": float(
                        thermal_case.get("ambient_air_temp_k", scenario_config["assignment"]["ambient_air_temp_k"])
                    ),
                    "wind_speed_m_per_s": float(thermal_case.get("wind_speed_m_per_s", 0.0)),
                    "solar_absorbed_flux_w_per_m2": float(thermal_case.get("solar_absorbed_flux_w_per_m2", 0.0)),
                    "soil_temperature_k": float(
                        thermal_case.get("soil_temperature_k", scenario_config["assignment"]["ambient_air_temp_k"])
                    ),
                    "pump_heat_to_fluid_fraction": float(thermal_case.get("pump_heat_to_fluid_fraction", 0.0)),
                    "target_distance_m": target_distance_m,
                    "target_distance_km": target_distance_m / 1000.0,
                    "required_cooling_kw": float(load_result.total_kw),
                    "baseline_power_kw": float(baseline["compressor_power_kw"]),
                    "supply_temp_k": supply_temp_k,
                    "supply_temp_c": supply_temp_k - 273.15,
                    "fluid": candidate["fluid"],
                    "coolprop_name": candidate["coolprop_name"],
                    "selected_by_screening": is_screening_selected,
                    "screening_score": float(candidate["score"]),
                    "zero_warmup_design_found": not zero_warmup_designs.empty,
                    "minimum_supplemental_warmup_kw": float(min_supplemental_design["supplemental_warmup_kw"]),
                    "best_design_line_heat_gain_kw": float(best_design["line_heat_gain_kw"]),
                    "best_design_pump_heat_to_fluid_kw": float(best_design["pump_heat_to_fluid_kw"]),
                    "best_design_total_heat_gain_kw": float(best_design["heat_gain_kw"]),
                    "best_design_pump_power_kw": float(best_design["pump_power_kw"]),
                    "best_design_supply_id_m": float(best_design["supply_id_m"]),
                    "best_design_return_id_m": float(best_design["return_id_m"]),
                    "best_design_insulation_thickness_m": float(best_design["insulation_thickness_m"]),
                    "best_design_power_saving_kw": float(baseline["compressor_power_kw"]) - float(best_design["pump_power_kw"]),
                    "status": "feasible",
                    "failure_reason": "",
                }
            )
        except Exception as exc:  # pragma: no cover
            rows.append(
                {
                    "scenario_name": scenario_name,
                    "thermal_mode": str(thermal_case.get("mode", "air")),
                    "ambient_air_temp_k": float(
                        thermal_case.get("ambient_air_temp_k", scenario_config["assignment"]["ambient_air_temp_k"])
                    ),
                    "wind_speed_m_per_s": float(thermal_case.get("wind_speed_m_per_s", 0.0)),
                    "solar_absorbed_flux_w_per_m2": float(thermal_case.get("solar_absorbed_flux_w_per_m2", 0.0)),
                    "soil_temperature_k": float(
                        thermal_case.get("soil_temperature_k", scenario_config["assignment"]["ambient_air_temp_k"])
                    ),
                    "pump_heat_to_fluid_fraction": float(thermal_case.get("pump_heat_to_fluid_fraction", 0.0)),
                    "target_distance_m": target_distance_m,
                    "target_distance_km": target_distance_m / 1000.0,
                    "required_cooling_kw": float(load_result.total_kw),
                    "baseline_power_kw": float(baseline["compressor_power_kw"]),
                    "supply_temp_k": supply_temp_k,
                    "supply_temp_c": supply_temp_k - 273.15,
                    "fluid": candidate["fluid"],
                    "coolprop_name": candidate["coolprop_name"],
                    "selected_by_screening": is_screening_selected,
                    "screening_score": float(candidate["score"]),
                    "zero_warmup_design_found": False,
                    "minimum_supplemental_warmup_kw": math.nan,
                    "best_design_line_heat_gain_kw": math.nan,
                    "best_design_pump_heat_to_fluid_kw": math.nan,
                    "best_design_total_heat_gain_kw": math.nan,
                    "best_design_pump_power_kw": math.nan,
                    "best_design_supply_id_m": math.nan,
                    "best_design_return_id_m": math.nan,
                    "best_design_insulation_thickness_m": math.nan,
                    "best_design_power_saving_kw": math.nan,
                    "status": "failed",
                    "failure_reason": str(exc),
                }
            )
    return rows


def _apply_practical_passive_filters(config: dict, frame: pd.DataFrame) -> pd.DataFrame:
    constraints = config.get("practical_passive_constraints", {})
    minimum_insulation_thickness_m = float(constraints.get("minimum_insulation_thickness_m", 0.0))
    maximum_total_heat_gain_fraction_of_load = float(
        constraints.get("maximum_total_heat_gain_fraction_of_load", math.inf)
    )

    output = frame.copy()
    output["best_design_total_heat_gain_fraction_of_load"] = (
        output["best_design_total_heat_gain_kw"] / output["required_cooling_kw"].clip(lower=1e-9)
    )

    practical_flags: list[bool] = []
    practical_failure_reasons: list[str] = []
    for _, row in output.iterrows():
        reasons: list[str] = []
        if row["status"] != "feasible":
            reasons.append("infeasible")
        if float(row["best_design_insulation_thickness_m"]) + 1e-9 < minimum_insulation_thickness_m:
            reasons.append("insulation below practical minimum")
        if float(row["best_design_total_heat_gain_fraction_of_load"]) > maximum_total_heat_gain_fraction_of_load + 1e-9:
            reasons.append("passive heat fraction exceeds practical limit")
        practical_flags.append(not reasons)
        practical_failure_reasons.append("; ".join(reasons))

    output["practical_candidate"] = practical_flags
    output["practical_failure_reasons"] = practical_failure_reasons
    output["practical_zero_warmup_design_found"] = output["zero_warmup_design_found"] & output["practical_candidate"]
    return output


def evaluate_supply_temperature_sweep(
    config: dict,
    load_result: object,
    baseline: dict,
    parallel_options: ParallelOptions | None = None,
) -> pd.DataFrame:
    options = parallel_options or SERIAL_PARALLEL_OPTIONS
    rows = map_items(
        _evaluate_supply_temperature_sweep_task,
        [
            {
                "config": config,
                "required_cooling_kw": load_result.total_kw,
                "baseline_power_kw": baseline["compressor_power_kw"],
                "supply_temp_k": float(supply_temp_k),
            }
            for supply_temp_k in config.get(
                "sensitivity",
                {},
            ).get("coolant_supply_temp_candidates_k", [config["coolant_loop"]["supply_temp_k"]])
        ],
        options,
    )
    return add_annualized_columns(pd.DataFrame(rows).sort_values("supply_temp_k").reset_index(drop=True), "pump_power_kw", baseline["compressor_power_kw"], config)


def evaluate_ambient_closure_map(
    config: dict,
    load_result: object,
    baseline: dict,
    parallel_options: ParallelOptions | None = None,
) -> dict[str, object]:
    target_distance_m = float(config["system_targets"]["long_distance_pipeline_m"])
    base_distance_m = float(config["assignment"]["pipeline_distance_m"])
    options = parallel_options or SERIAL_PARALLEL_OPTIONS
    task_rows = map_items(
        _evaluate_ambient_closure_task,
        [
            {
                "config": config,
                "required_cooling_kw": load_result.total_kw,
                "supply_temp_k": float(supply_temp_k),
            }
            for supply_temp_k in config.get(
                "sensitivity",
                {},
            ).get("coolant_supply_temp_candidates_k", [config["coolant_loop"]["supply_temp_k"]])
        ],
        options,
    )
    rows = [row for batch in task_rows for row in batch]

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


def evaluate_zero_warmup_target_search(
    config: dict,
    load_result: object,
    baseline: dict,
    parallel_options: ParallelOptions | None = None,
) -> dict[str, object]:
    target_distances_m = sorted(
        {
            float(config["assignment"]["pipeline_distance_m"]),
            float(config["system_targets"]["long_distance_pipeline_m"]),
        }
    )
    options = parallel_options or SERIAL_PARALLEL_OPTIONS
    task_rows = map_items(
        _evaluate_zero_warmup_target_task,
        [
            {
                "config": config,
                "required_cooling_kw": load_result.total_kw,
                "target_distance_m": float(target_distance_m),
                "supply_temp_k": float(supply_temp_k),
            }
            for target_distance_m in target_distances_m
            for supply_temp_k in config.get(
                "sensitivity",
                {},
            ).get("coolant_supply_temp_candidates_k", [config["coolant_loop"]["supply_temp_k"]])
        ],
        options,
    )
    rows = [row for batch in task_rows for row in batch]

    frame = pd.DataFrame(rows).sort_values(
        ["target_distance_m", "minimum_supplemental_warmup_kw", "best_design_pump_power_kw", "screening_score"],
        ascending=[True, True, True, False],
    ).reset_index(drop=True)
    frame = add_annualized_columns(frame, "best_design_pump_power_kw", baseline["compressor_power_kw"], config)

    selected_by_distance: dict[float, dict[str, object] | None] = {}
    for target_distance_m in target_distances_m:
        distance_rows = frame[
            (frame["status"] == "feasible") & ((frame["target_distance_m"] - target_distance_m).abs() < 1e-6)
        ].copy()
        zero_rows = distance_rows[distance_rows["zero_warmup_design_found"]].sort_values(
            ["best_design_pump_power_kw", "minimum_supplemental_warmup_kw", "screening_score"],
            ascending=[True, True, False],
        )
        near_best = distance_rows.sort_values(
            ["minimum_supplemental_warmup_kw", "best_design_pump_power_kw", "screening_score"],
            ascending=[True, True, False],
        )
        selected_by_distance[target_distance_m] = {
            "warmup_free": zero_rows.iloc[0].to_dict() if not zero_rows.empty else None,
            "near_best": near_best.iloc[0].to_dict() if not near_best.empty else None,
        }

    return {
        "table": frame,
        "selected_by_distance": selected_by_distance,
    }


def evaluate_passive_zero_warmup_search(
    config: dict,
    parallel_options: ParallelOptions | None = None,
) -> dict[str, object]:
    search_cfg = config.get("passive_heat_search", {})
    scenarios = list(search_cfg.get("scenarios", []))
    if not scenarios:
        raise RuntimeError("No passive heat-search scenarios were configured.")

    target_distances_m = sorted(
        {
            float(config["assignment"]["pipeline_distance_m"]),
            float(config["system_targets"]["long_distance_pipeline_m"]),
        }
    )
    supply_temp_candidates_k = list(
        search_cfg.get("supply_temp_candidates_k", [config["coolant_loop"]["supply_temp_k"]])
    )
    diameter_candidates_m = list(
        search_cfg.get("diameter_candidates_m", config["pipeline_design"]["diameter_candidates_m"])
    )
    insulation_candidates_m = list(
        search_cfg.get(
            "insulation_thickness_candidates_m",
            config["pipeline_design"]["insulation_thickness_candidates_m"],
        )
    )

    options = parallel_options or SERIAL_PARALLEL_OPTIONS
    task_rows = map_items(
        _evaluate_passive_zero_warmup_task,
        [
            {
                "config": config,
                "scenario_name": str(scenario.get("name", "unnamed")),
                "thermal_case": {key: value for key, value in scenario.items() if key != "name"},
                "target_distance_m": float(target_distance_m),
                "supply_temp_k": float(supply_temp_k),
                "diameter_candidates_m": diameter_candidates_m,
                "insulation_candidates_m": insulation_candidates_m,
            }
            for scenario in scenarios
            for target_distance_m in target_distances_m
            for supply_temp_k in supply_temp_candidates_k
        ],
        options,
    )
    rows = [row for batch in task_rows for row in batch]

    frame = pd.DataFrame(rows).sort_values(
        ["scenario_name", "target_distance_m", "minimum_supplemental_warmup_kw", "best_design_pump_power_kw", "screening_score"],
        ascending=[True, True, True, True, False],
    ).reset_index(drop=True)
    frame = _apply_practical_passive_filters(config, frame)

    selected_by_scenario: dict[str, dict[float, dict[str, object] | None]] = {}
    practical_selected_by_scenario: dict[str, dict[float, dict[str, object] | None]] = {}
    for scenario_name in sorted(frame["scenario_name"].dropna().unique()):
        selected_by_scenario[scenario_name] = {}
        practical_selected_by_scenario[scenario_name] = {}
        scenario_rows = frame[(frame["scenario_name"] == scenario_name) & (frame["status"] == "feasible")].copy()
        practical_rows = scenario_rows[scenario_rows["practical_candidate"]].copy()
        for target_distance_m in target_distances_m:
            distance_rows = scenario_rows[(scenario_rows["target_distance_m"] - target_distance_m).abs() < 1e-6].copy()
            zero_rows = distance_rows[distance_rows["zero_warmup_design_found"]].sort_values(
                ["best_design_pump_power_kw", "minimum_supplemental_warmup_kw", "screening_score"],
                ascending=[True, True, False],
            )
            near_best = distance_rows.sort_values(
                ["minimum_supplemental_warmup_kw", "best_design_pump_power_kw", "screening_score"],
                ascending=[True, True, False],
            )
            selected_by_scenario[scenario_name][target_distance_m] = {
                "warmup_free": zero_rows.iloc[0].to_dict() if not zero_rows.empty else None,
                "near_best": near_best.iloc[0].to_dict() if not near_best.empty else None,
            }
            practical_distance_rows = practical_rows[(practical_rows["target_distance_m"] - target_distance_m).abs() < 1e-6].copy()
            practical_zero_rows = practical_distance_rows[
                practical_distance_rows["practical_zero_warmup_design_found"]
            ].sort_values(
                ["best_design_pump_power_kw", "minimum_supplemental_warmup_kw", "screening_score"],
                ascending=[True, True, False],
            )
            practical_near_best = practical_distance_rows.sort_values(
                ["minimum_supplemental_warmup_kw", "best_design_pump_power_kw", "screening_score"],
                ascending=[True, True, False],
            )
            practical_selected_by_scenario[scenario_name][target_distance_m] = {
                "warmup_free": practical_zero_rows.iloc[0].to_dict() if not practical_zero_rows.empty else None,
                "near_best": practical_near_best.iloc[0].to_dict() if not practical_near_best.empty else None,
            }

    return {
        "table": frame,
        "selected_by_scenario": selected_by_scenario,
        "practical_selected_by_scenario": practical_selected_by_scenario,
    }
