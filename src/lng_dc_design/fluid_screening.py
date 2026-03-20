from __future__ import annotations

import math

import CoolProp.CoolProp as CP
import pandas as pd

from .idc_hx import evaluate_idc_heat_exchange
from .thermo import fluid_phase


def compute_fluid_screening(config: dict, required_cooling_kw: float) -> dict[str, object]:
    loop = config["coolant_loop"]
    candidates = config["coolant_candidates"]
    utilization_target_fraction = config["system_targets"]["idc_cooling_utilization_fraction"]
    supply_k = loop["supply_temp_k"]
    pressure_pa = loop["pressure_mpa"] * 1_000_000.0

    rows: list[dict[str, object]] = []
    for key, metadata in candidates.items():
        fluid = metadata["coolprop_name"]
        row: dict[str, object] = {"key": key, "fluid": metadata["display_name"], "coolprop_name": fluid}
        try:
            triple_k = float(CP.PropsSI("Ttriple", fluid))
            idc_hx_result = evaluate_idc_heat_exchange(config, fluid, required_cooling_kw)
            phase_supply = fluid_phase(supply_k, pressure_pa, fluid)
            phase_after_idc = str(idc_hx_result["after_idc_phase"])
            phase_return = str(idc_hx_result["minimum_return_phase"])
            cp = float(idc_hx_result["reference_cp_j_per_kgk"])
            rho = float(idc_hx_result["reference_density_kg_per_m3"])
            mu = float(idc_hx_result["reference_viscosity_pa_s"])
            k_cond = float(idc_hx_result["reference_conductivity_w_per_mk"])

            feasible = (
                "liquid" in phase_supply
                and "liquid" in phase_after_idc
                and "liquid" in phase_return
                and supply_k >= triple_k + 10.0
                and float(idc_hx_result["min_pinch_k"]) >= config["assignment"]["minimum_temperature_approach_k"] - 1e-6
            )
            if not feasible:
                reason = (
                    f"Loop phase incompatible: supply={phase_supply}, after_idc={phase_after_idc}, "
                    f"return={phase_return}, triple={triple_k:.1f} K"
                )
            elif float(idc_hx_result["minimum_line_heat_gain_required_kw"]) > float(idc_hx_result["line_heat_gain_budget_kw"]) + 1e-6:
                reason = (
                    "Feasible loop, but the LNG hot-end minimum return requirement exceeds the "
                    f"{utilization_target_fraction:.0%} utilization target and needs supplemental warm-up."
                )
            else:
                reason = "Feasible single-phase liquid loop with IDC-side HX and a valid line-heat window"

            mass_flow = float(idc_hx_result["coolant_mass_flow_kg_s"])
            volumetric_flow = mass_flow / rho
            transport_index = mass_flow * mu / rho
            penalty = metadata["safety_penalty"] + metadata["compatibility_penalty"] + 0.05 * min(metadata["gwp"] / 1000.0, 1.0)

            row.update(
                {
                    "feasible": feasible,
                    "reason": reason,
                    "cp_j_per_kgk": cp,
                    "density_kg_per_m3": rho,
                    "viscosity_pa_s": mu,
                    "conductivity_w_per_mk": k_cond,
                    "required_mass_flow_kg_s": mass_flow,
                    "volumetric_flow_m3_s": volumetric_flow,
                    "transport_index": transport_index,
                    "gwp": metadata["gwp"],
                    "odp": metadata["odp"],
                    "penalty": penalty,
                    "after_idc_temp_k": float(idc_hx_result["coolant_after_idc_temp_k"]),
                    "minimum_return_to_lng_k": float(idc_hx_result["minimum_return_to_lng_k"]),
                    "total_lng_duty_kw": float(idc_hx_result["total_lng_duty_kw"]),
                    "line_heat_gain_budget_kw": float(idc_hx_result["line_heat_gain_budget_kw"]),
                    "minimum_lng_duty_kw": float(idc_hx_result["minimum_lng_duty_kw"]),
                    "minimum_line_heat_gain_required_kw": float(idc_hx_result["minimum_line_heat_gain_required_kw"]),
                    "minimum_hot_end_utilization_fraction": float(idc_hx_result["minimum_hot_end_utilization_fraction"]),
                    "utilization_target_fraction": float(idc_hx_result["utilization_target_fraction"]),
                    "target_shortfall_kw": max(
                        float(idc_hx_result["minimum_lng_duty_kw"]) - float(idc_hx_result["design_lng_duty_kw"]),
                        0.0,
                    ),
                    "meets_utilization_target": float(idc_hx_result["minimum_lng_duty_kw"]) <= float(idc_hx_result["design_lng_duty_kw"]) + 1e-6,
                    "idc_hx_area_m2": float(idc_hx_result["required_area_m2"]),
                    "idc_hx_min_pinch_k": float(idc_hx_result["min_pinch_k"]),
                    "idc_chilled_water_mass_flow_kg_s": float(idc_hx_result["chilled_water_mass_flow_kg_s"]),
                }
            )
        except Exception as exc:  # pragma: no cover
            row.update(
                {
                    "feasible": False,
                    "reason": f"CoolProp error: {exc}",
                    "cp_j_per_kgk": math.nan,
                    "density_kg_per_m3": math.nan,
                    "viscosity_pa_s": math.nan,
                    "conductivity_w_per_mk": math.nan,
                    "required_mass_flow_kg_s": math.nan,
                    "volumetric_flow_m3_s": math.nan,
                    "transport_index": math.nan,
                    "gwp": metadata["gwp"],
                    "odp": metadata["odp"],
                    "penalty": math.nan,
                    "after_idc_temp_k": math.nan,
                    "minimum_return_to_lng_k": math.nan,
                    "total_lng_duty_kw": math.nan,
                    "line_heat_gain_budget_kw": math.nan,
                    "minimum_lng_duty_kw": math.nan,
                    "minimum_line_heat_gain_required_kw": math.nan,
                    "minimum_hot_end_utilization_fraction": math.nan,
                    "utilization_target_fraction": utilization_target_fraction,
                    "target_shortfall_kw": math.nan,
                    "meets_utilization_target": False,
                    "idc_hx_area_m2": math.nan,
                    "idc_hx_min_pinch_k": math.nan,
                    "idc_chilled_water_mass_flow_kg_s": math.nan,
                }
            )
        rows.append(row)

    frame = pd.DataFrame(rows)
    feasible = frame[frame["feasible"]].copy()
    if feasible.empty:
        raise RuntimeError("No feasible coolant candidates were found.")

    def normalize(series: pd.Series) -> pd.Series:
        span = series.max() - series.min()
        if span < 1e-12:
            return pd.Series(0.5, index=series.index)
        return (series - series.min()) / span

    feasible["mass_norm"] = normalize(feasible["required_mass_flow_kg_s"])
    feasible["vol_norm"] = normalize(feasible["volumetric_flow_m3_s"])
    feasible["visc_norm"] = normalize(feasible["transport_index"])
    feasible["hot_end_norm"] = normalize(feasible["minimum_line_heat_gain_required_kw"])
    feasible["area_norm"] = normalize(feasible["idc_hx_area_m2"])
    feasible["window_margin_kw"] = feasible["line_heat_gain_budget_kw"] - feasible["minimum_line_heat_gain_required_kw"]
    feasible["window_margin_norm"] = normalize(feasible["window_margin_kw"])
    feasible["target_shortfall_norm"] = normalize(feasible["target_shortfall_kw"])
    feasible["score"] = (
        1.0
        - 0.35 * feasible["mass_norm"]
        - 0.20 * feasible["vol_norm"]
        - 0.10 * feasible["visc_norm"]
        - 0.10 * feasible["hot_end_norm"]
        - 0.05 * feasible["area_norm"]
        + 0.10 * feasible["window_margin_norm"]
        - 0.15 * feasible["target_shortfall_norm"]
        - feasible["penalty"]
    )
    feasible = feasible.sort_values("score", ascending=False)
    merged = frame.merge(feasible[["key", "score"]], on="key", how="left")
    selected = feasible.iloc[0].to_dict()
    return {
        "table": merged.sort_values(["feasible", "score"], ascending=[False, False]).reset_index(drop=True),
        "selected": selected,
        "total_lng_duty_kw": float(selected["total_lng_duty_kw"]),
    }
