from __future__ import annotations

from copy import deepcopy
import random

import pandas as pd

from .baseline_vcc import compute_baseline_cycle
from .fluid_screening import compute_fluid_screening
from .idc_secondary_loop import evaluate_idc_secondary_loop
from .load_model import compute_load_model
from .parallel import ParallelOptions, map_items
from .pipeline_loop import design_pipeline


SERIAL_PARALLEL_OPTIONS = ParallelOptions(enabled=False, workers=1)


def _idc_secondary_loop_pump_power_kw(config: dict, required_cooling_kw: float) -> float:
    assignment = config["assignment"]
    idc_hx = config["idc_hx"]
    chilled_delta_t_k = float(assignment["chilled_water_return_temp_k"]) - float(assignment["chilled_water_supply_temp_k"])
    chilled_water_mass_flow_kg_s = required_cooling_kw * 1000.0 / (
        float(idc_hx["chilled_water_cp_j_per_kgk"]) * chilled_delta_t_k
    )
    idc_secondary_loop_result = evaluate_idc_secondary_loop(config, chilled_water_mass_flow_kg_s)
    return float(idc_secondary_loop_result["selected_design"]["pump_power_kw"])


def _with_uncertainty_sample(config: dict, sample: dict[str, float]) -> dict:
    trial = deepcopy(config)
    trial["assignment"]["ambient_air_temp_k"] = sample["ambient_air_temp_k"]
    trial["idc_hx"]["overall_u_w_per_m2k"] = config["idc_hx"]["overall_u_w_per_m2k"] * sample["overall_u_multiplier"]
    trial["pipeline_design"]["insulation_conductivity_w_per_mk"] = (
        config["pipeline_design"]["insulation_conductivity_w_per_mk"] * sample["insulation_conductivity_multiplier"]
    )
    trial["pipeline_design"]["outside_h_w_per_m2k"] = (
        config["pipeline_design"]["outside_h_w_per_m2k"] * sample["outside_h_multiplier"]
    )
    trial["system_targets"]["idc_cooling_utilization_fraction"] = sample["utilization_fraction"]
    return trial


def _evaluate_uncertainty_sample(task: dict[str, object]) -> dict[str, object]:
    base_config = dict(task["config"])
    sample = dict(task["sample"])
    trial_config = _with_uncertainty_sample(base_config, sample)
    load_result = compute_load_model(trial_config)
    baseline = compute_baseline_cycle(trial_config, load_result.total_kw)
    screening = compute_fluid_screening(
        trial_config,
        load_result.total_kw,
        parallel_options=SERIAL_PARALLEL_OPTIONS,
    )
    pipeline_result = design_pipeline(trial_config, screening["selected"], load_result.total_kw)
    selected_design = pipeline_result["selected_design"]
    lng_loop_pump_power_kw = float(selected_design["pump_power_kw"])
    idc_secondary_loop_pump_kw = _idc_secondary_loop_pump_power_kw(trial_config, load_result.total_kw)
    core_system_power_kw = lng_loop_pump_power_kw + idc_secondary_loop_pump_kw
    return {
        "sample_id": int(sample["sample_id"]),
        "ambient_air_temp_k": float(sample["ambient_air_temp_k"]),
        "overall_u_multiplier": float(sample["overall_u_multiplier"]),
        "insulation_conductivity_multiplier": float(sample["insulation_conductivity_multiplier"]),
        "outside_h_multiplier": float(sample["outside_h_multiplier"]),
        "utilization_fraction": float(sample["utilization_fraction"]),
        "selected_fluid": str(screening["selected"]["fluid"]),
        "screening_score": float(screening["selected"]["score"]),
        "baseline_power_kw": float(baseline["compressor_power_kw"]),
        "pump_power_kw": core_system_power_kw,
        "lng_loop_pump_power_kw": lng_loop_pump_power_kw,
        "idc_secondary_loop_pump_power_kw": idc_secondary_loop_pump_kw,
        "core_system_power_kw": core_system_power_kw,
        "supplemental_warmup_kw": float(selected_design["supplemental_warmup_kw"]),
        "heat_gain_kw": float(selected_design["heat_gain_kw"]),
        "max_feasible_distance_km": float(pipeline_result["max_feasible_distance_m"]) / 1000.0,
    }


def evaluate_uncertainty_study(
    config: dict,
    parallel_options: ParallelOptions | None = None,
) -> dict[str, object]:
    study_cfg = config.get("uncertainty_analysis", {})
    sample_count = int(study_cfg.get("sample_count", 0))
    if sample_count <= 0:
        raise RuntimeError("uncertainty_analysis.sample_count must be positive.")

    rng = random.Random(int(study_cfg.get("seed", 42)))
    samples: list[dict[str, float]] = []
    for sample_id in range(sample_count):
        samples.append(
            {
                "sample_id": float(sample_id),
                "ambient_air_temp_k": rng.uniform(*study_cfg["ambient_air_temp_range_k"]),
                "overall_u_multiplier": rng.uniform(*study_cfg["overall_u_multiplier_range"]),
                "insulation_conductivity_multiplier": rng.uniform(*study_cfg["insulation_conductivity_multiplier_range"]),
                "outside_h_multiplier": rng.uniform(*study_cfg["outside_h_multiplier_range"]),
                "utilization_fraction": rng.uniform(*study_cfg["utilization_fraction_range"]),
            }
        )

    options = parallel_options or SERIAL_PARALLEL_OPTIONS
    rows = map_items(
        _evaluate_uncertainty_sample,
        [{"config": config, "sample": sample} for sample in samples],
        options,
    )
    frame = pd.DataFrame(rows).sort_values("sample_id").reset_index(drop=True)

    summary_rows = []
    for column in [
        "baseline_power_kw",
        "lng_loop_pump_power_kw",
        "idc_secondary_loop_pump_power_kw",
        "core_system_power_kw",
        "supplemental_warmup_kw",
        "heat_gain_kw",
        "max_feasible_distance_km",
    ]:
        summary_rows.extend(
            [
                {"metric": f"{column}: mean", "value": float(frame[column].mean())},
                {"metric": f"{column}: p10", "value": float(frame[column].quantile(0.10))},
                {"metric": f"{column}: p50", "value": float(frame[column].quantile(0.50))},
                {"metric": f"{column}: p90", "value": float(frame[column].quantile(0.90))},
            ]
        )
    summary_rows.append(
        {
            "metric": "selected_fluid: most_common",
            "value": str(frame["selected_fluid"].mode().iloc[0]),
        }
    )
    summary_rows.append(
        {
            "metric": "selected_fluid: stability_fraction",
            "value": float(frame["selected_fluid"].value_counts(normalize=True).iloc[0]),
        }
    )

    return {
        "samples": frame,
        "summary": pd.DataFrame(summary_rows),
    }
