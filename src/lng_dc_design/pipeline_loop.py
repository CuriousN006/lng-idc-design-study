from __future__ import annotations

import math

import CoolProp.CoolProp as CP
import pandas as pd

from .thermo import cylindrical_heat_gain_w_per_length, darcy_friction_factor


def _evaluate_pipeline_case(
    config: dict,
    fluid: str,
    pressure_pa: float,
    required_cooling_kw: float,
    total_lng_duty_kw: float,
    mass_flow_kg_s: float,
    after_idc_temp_k: float,
    minimum_return_to_lng_k: float,
    minimum_line_heat_gain_required_kw: float,
    supply_id_m: float,
    return_id_m: float,
    insulation_thickness_m: float,
    distance_m: float,
) -> dict[str, float | bool]:
    assignment = config["assignment"]
    loop = config["coolant_loop"]
    pipe_cfg = config["pipeline_design"]

    supply_temp_k = loop["supply_temp_k"]
    h_supply = float(CP.PropsSI("H", "T", supply_temp_k, "P", pressure_pa, fluid))
    h_after_idc = float(CP.PropsSI("H", "T", after_idc_temp_k, "P", pressure_pa, fluid))

    supply_avg_temp_k = 0.5 * (supply_temp_k + after_idc_temp_k)
    return_to_lng_temp_k = max(after_idc_temp_k + 1e-3, minimum_return_to_lng_k)
    supplemental_reheat_kw = 0.0
    actual_lng_duty_kw = total_lng_duty_kw

    q_supply = 0.0
    q_return = 0.0
    velocity_supply = 0.0
    velocity_return = 0.0
    supply_rho = 0.0
    return_rho = 0.0
    dp_supply = 0.0
    dp_return = 0.0

    for _ in range(40):
        return_avg_temp_k = 0.5 * (after_idc_temp_k + return_to_lng_temp_k)

        supply_rho = float(CP.PropsSI("D", "T", supply_avg_temp_k, "P", pressure_pa, fluid))
        return_rho = float(CP.PropsSI("D", "T", return_avg_temp_k, "P", pressure_pa, fluid))
        supply_mu = float(CP.PropsSI("V", "T", supply_avg_temp_k, "P", pressure_pa, fluid))
        return_mu = float(CP.PropsSI("V", "T", return_avg_temp_k, "P", pressure_pa, fluid))

        q_supply = mass_flow_kg_s / supply_rho
        q_return = mass_flow_kg_s / return_rho

        area_supply = math.pi * supply_id_m ** 2 / 4.0
        area_return = math.pi * return_id_m ** 2 / 4.0
        velocity_supply = q_supply / area_supply
        velocity_return = q_return / area_return

        reynolds_supply = supply_rho * velocity_supply * supply_id_m / supply_mu
        reynolds_return = return_rho * velocity_return * return_id_m / return_mu

        f_supply = darcy_friction_factor(reynolds_supply, pipe_cfg["pipe_roughness_m"], supply_id_m)
        f_return = darcy_friction_factor(reynolds_return, pipe_cfg["pipe_roughness_m"], return_id_m)

        dp_supply = (
            f_supply * (distance_m / supply_id_m) * supply_rho * velocity_supply ** 2 / 2.0
            + pipe_cfg["minor_loss_k"] * supply_rho * velocity_supply ** 2 / 2.0
        )
        dp_return = (
            f_return * (distance_m / return_id_m) * return_rho * velocity_return ** 2 / 2.0
            + pipe_cfg["minor_loss_k"] * return_rho * velocity_return ** 2 / 2.0
        )

        supply_outer_radius = 0.5 * (supply_id_m + 2.0 * pipe_cfg["pipe_wall_thickness_m"])
        return_outer_radius = 0.5 * (return_id_m + 2.0 * pipe_cfg["pipe_wall_thickness_m"])
        q_supply_w_per_m = cylindrical_heat_gain_w_per_length(
            supply_outer_radius,
            supply_outer_radius + insulation_thickness_m,
            pipe_cfg["insulation_conductivity_w_per_mk"],
            pipe_cfg["outside_h_w_per_m2k"],
            assignment["ambient_air_temp_k"],
            supply_avg_temp_k,
        )
        q_return_w_per_m = cylindrical_heat_gain_w_per_length(
            return_outer_radius,
            return_outer_radius + insulation_thickness_m,
            pipe_cfg["insulation_conductivity_w_per_mk"],
            pipe_cfg["outside_h_w_per_m2k"],
            assignment["ambient_air_temp_k"],
            return_avg_temp_k,
        )
        heat_gain_w = (q_supply_w_per_m + q_return_w_per_m) * distance_m
        heat_gain_kw = heat_gain_w / 1000.0
        supplemental_reheat_kw = max(minimum_line_heat_gain_required_kw - heat_gain_kw, 0.0)
        total_external_heat_kw = heat_gain_kw + supplemental_reheat_kw
        actual_lng_duty_kw = required_cooling_kw + total_external_heat_kw
        new_return_to_lng_temp_k = float(
            CP.PropsSI("T", "H", h_after_idc + total_external_heat_kw * 1000.0 / mass_flow_kg_s, "P", pressure_pa, fluid)
        )
        if abs(new_return_to_lng_temp_k - return_to_lng_temp_k) < 1e-4:
            return_to_lng_temp_k = new_return_to_lng_temp_k
            break
        return_to_lng_temp_k = 0.5 * (return_to_lng_temp_k + new_return_to_lng_temp_k)

    heat_gain_kw = heat_gain_w / 1000.0
    available_cooling_kw = actual_lng_duty_kw - heat_gain_kw - supplemental_reheat_kw
    design_target_margin_kw = total_lng_duty_kw - heat_gain_kw - required_cooling_kw
    pump_power_w = (dp_supply * q_supply + dp_return * q_return) / pipe_cfg["pump_isentropic_efficiency"]
    heat_gain_fraction = heat_gain_kw / max(actual_lng_duty_kw, 1e-9)
    hot_end_margin_k = return_to_lng_temp_k - minimum_return_to_lng_k
    thermal_margin_kw = available_cooling_kw - required_cooling_kw
    actual_utilization_fraction = required_cooling_kw / max(actual_lng_duty_kw, 1e-9)
    return_phase = str(CP.PhaseSI("T", return_to_lng_temp_k, "P", pressure_pa, fluid))
    feasible = (
        velocity_supply <= pipe_cfg["max_liquid_velocity_m_per_s"]
        and velocity_return <= pipe_cfg["max_liquid_velocity_m_per_s"]
        and hot_end_margin_k >= -1e-6
        and "liquid" in return_phase
    )

    return {
        "distance_m": distance_m,
        "insulation_thickness_m": insulation_thickness_m,
        "supply_id_m": supply_id_m,
        "return_id_m": return_id_m,
        "required_mass_flow_kg_s": mass_flow_kg_s,
        "velocity_supply_m_per_s": velocity_supply,
        "velocity_return_m_per_s": velocity_return,
        "dp_supply_kpa": dp_supply / 1000.0,
        "dp_return_kpa": dp_return / 1000.0,
        "heat_gain_kw": heat_gain_kw,
        "heat_gain_fraction": heat_gain_fraction,
        "supplemental_warmup_kw": supplemental_reheat_kw,
        "actual_lng_duty_kw": actual_lng_duty_kw,
        "actual_utilization_fraction": actual_utilization_fraction,
        "pump_power_kw": pump_power_w / 1000.0,
        "available_cooling_kw": available_cooling_kw,
        "thermal_margin_kw": thermal_margin_kw,
        "design_target_margin_kw": design_target_margin_kw,
        "return_to_lng_temp_k": return_to_lng_temp_k,
        "minimum_return_to_lng_k": minimum_return_to_lng_k,
        "hot_end_margin_k": hot_end_margin_k,
        "return_phase": return_phase,
        "meets_utilization_target": design_target_margin_kw >= -1e-6,
        "feasible": feasible,
    }


def _estimate_max_feasible_distance(
    config: dict,
    fluid: str,
    pressure_pa: float,
    required_cooling_kw: float,
    total_lng_duty_kw: float,
    mass_flow_kg_s: float,
    after_idc_temp_k: float,
    minimum_return_to_lng_k: float,
    minimum_line_heat_gain_required_kw: float,
    selected: dict[str, float],
) -> float:
    lower = 0.0
    upper = max(
        config["assignment"]["pipeline_distance_m"],
        config["system_targets"]["long_distance_pipeline_m"],
    )

    upper_case = _evaluate_pipeline_case(
        config,
        fluid,
        pressure_pa,
        required_cooling_kw,
        total_lng_duty_kw,
        mass_flow_kg_s,
        after_idc_temp_k,
        minimum_return_to_lng_k,
        minimum_line_heat_gain_required_kw,
        selected["supply_id_m"],
        selected["return_id_m"],
        selected["insulation_thickness_m"],
        upper,
    )

    while bool(upper_case["feasible"]) and upper < 250_000.0:
        lower = upper
        upper *= 1.5
        upper_case = _evaluate_pipeline_case(
            config,
            fluid,
            pressure_pa,
            required_cooling_kw,
            total_lng_duty_kw,
            mass_flow_kg_s,
            after_idc_temp_k,
            minimum_return_to_lng_k,
            minimum_line_heat_gain_required_kw,
            selected["supply_id_m"],
            selected["return_id_m"],
            selected["insulation_thickness_m"],
            upper,
        )

    if bool(upper_case["feasible"]):
        return upper

    for _ in range(25):
        mid = 0.5 * (lower + upper)
        mid_case = _evaluate_pipeline_case(
            config,
            fluid,
            pressure_pa,
            required_cooling_kw,
            total_lng_duty_kw,
            mass_flow_kg_s,
            after_idc_temp_k,
            minimum_return_to_lng_k,
            minimum_line_heat_gain_required_kw,
            selected["supply_id_m"],
            selected["return_id_m"],
            selected["insulation_thickness_m"],
            mid,
        )
        if bool(mid_case["feasible"]):
            lower = mid
        else:
            upper = mid
    return lower


def design_pipeline(config: dict, selected_fluid: dict, required_cooling_kw: float) -> dict[str, object]:
    loop = config["coolant_loop"]
    pipe_cfg = config["pipeline_design"]
    pressure_pa = loop["pressure_mpa"] * 1_000_000.0
    fluid = selected_fluid["coolprop_name"]

    mass_flow_kg_s = float(selected_fluid["required_mass_flow_kg_s"])
    total_lng_duty_kw = float(selected_fluid["total_lng_duty_kw"])
    after_idc_temp_k = float(selected_fluid["after_idc_temp_k"])
    minimum_return_to_lng_k = float(selected_fluid["minimum_return_to_lng_k"])
    minimum_line_heat_gain_required_kw = float(selected_fluid["minimum_line_heat_gain_required_kw"])

    rows: list[dict[str, float | bool]] = []
    for insulation_thickness_m in pipe_cfg["insulation_thickness_candidates_m"]:
        for supply_id_m in pipe_cfg["diameter_candidates_m"]:
            for return_id_m in pipe_cfg["diameter_candidates_m"]:
                row = _evaluate_pipeline_case(
                    config,
                    fluid,
                    pressure_pa,
                    required_cooling_kw,
                    total_lng_duty_kw,
                    mass_flow_kg_s,
                    after_idc_temp_k,
                    minimum_return_to_lng_k,
                    minimum_line_heat_gain_required_kw,
                    supply_id_m,
                    return_id_m,
                    insulation_thickness_m,
                    config["assignment"]["pipeline_distance_m"],
                )
                rows.append(row)

    frame = pd.DataFrame(rows).sort_values(
        ["feasible", "pump_power_kw", "supplemental_warmup_kw", "heat_gain_kw"],
        ascending=[False, True, True, True],
    )
    if not bool(frame["feasible"].any()):
        raise RuntimeError("No feasible pipeline design found in search grid.")
    selected = frame[frame["feasible"]].iloc[0].to_dict()

    distance_candidates = config.get("sensitivity", {}).get(
        "distance_candidates_m",
        [config["assignment"]["pipeline_distance_m"], config["system_targets"]["long_distance_pipeline_m"]],
    )
    sensitivity = pd.DataFrame(
        [
            _evaluate_pipeline_case(
                config,
                fluid,
                pressure_pa,
                required_cooling_kw,
                total_lng_duty_kw,
                mass_flow_kg_s,
                after_idc_temp_k,
                minimum_return_to_lng_k,
                minimum_line_heat_gain_required_kw,
                float(selected["supply_id_m"]),
                float(selected["return_id_m"]),
                float(selected["insulation_thickness_m"]),
                float(distance_m),
            )
            for distance_m in distance_candidates
        ]
    ).sort_values("distance_m").reset_index(drop=True)

    max_feasible_distance_m = _estimate_max_feasible_distance(
        config,
        fluid,
        pressure_pa,
        required_cooling_kw,
        total_lng_duty_kw,
        mass_flow_kg_s,
        after_idc_temp_k,
        minimum_return_to_lng_k,
        minimum_line_heat_gain_required_kw,
        selected,
    )

    return {
        "scan_table": frame.reset_index(drop=True),
        "selected_design": selected,
        "sensitivity": sensitivity,
        "target_heat_gain_kw": total_lng_duty_kw - required_cooling_kw,
        "base_distance_m": config["assignment"]["pipeline_distance_m"],
        "max_feasible_distance_m": max_feasible_distance_m,
        "after_idc_temp_k": after_idc_temp_k,
        "return_to_lng_temp_k": float(selected["return_to_lng_temp_k"]),
        "minimum_return_to_lng_k": minimum_return_to_lng_k,
        "minimum_line_heat_gain_required_kw": minimum_line_heat_gain_required_kw,
    }
