from __future__ import annotations

import math

import CoolProp.CoolProp as CP
import pandas as pd

from .thermo import cylindrical_heat_gain_w_per_length, darcy_friction_factor


def design_pipeline(config: dict, selected_fluid: dict, required_cooling_kw: float, hx_result: dict) -> dict[str, object]:
    assignment = config["assignment"]
    loop = config["coolant_loop"]
    pipe_cfg = config["pipeline_design"]
    pressure_pa = loop["pressure_mpa"] * 1_000_000.0
    fluid = selected_fluid["coolprop_name"]

    mass_flow = hx_result["m_coolant_kg_s"]
    q_total_w = hx_result["required_lng_duty_kw"] * 1000.0
    q_target_env_w = q_total_w - required_cooling_kw * 1000.0

    supply_avg_temp_k = 0.5 * (loop["supply_temp_k"] + loop["after_idc_temp_k"])
    return_avg_temp_k = 0.5 * (loop["after_idc_temp_k"] + loop["return_to_lng_temp_k"])
    supply_rho = float(CP.PropsSI("D", "T", supply_avg_temp_k, "P", pressure_pa, fluid))
    return_rho = float(CP.PropsSI("D", "T", return_avg_temp_k, "P", pressure_pa, fluid))
    supply_mu = float(CP.PropsSI("V", "T", supply_avg_temp_k, "P", pressure_pa, fluid))
    return_mu = float(CP.PropsSI("V", "T", return_avg_temp_k, "P", pressure_pa, fluid))

    rows: list[dict[str, float]] = []
    for insulation_thickness_m in pipe_cfg["insulation_thickness_candidates_m"]:
        for supply_id_m in pipe_cfg["diameter_candidates_m"]:
            for return_id_m in pipe_cfg["diameter_candidates_m"]:
                q_supply = mass_flow / supply_rho
                q_return = mass_flow / return_rho

                area_supply = math.pi * supply_id_m ** 2 / 4.0
                area_return = math.pi * return_id_m ** 2 / 4.0
                velocity_supply = q_supply / area_supply
                velocity_return = q_return / area_return

                reynolds_supply = supply_rho * velocity_supply * supply_id_m / supply_mu
                reynolds_return = return_rho * velocity_return * return_id_m / return_mu

                f_supply = darcy_friction_factor(reynolds_supply, pipe_cfg["pipe_roughness_m"], supply_id_m)
                f_return = darcy_friction_factor(reynolds_return, pipe_cfg["pipe_roughness_m"], return_id_m)

                dp_supply = (
                    f_supply * (assignment["pipeline_distance_m"] / supply_id_m) * supply_rho * velocity_supply ** 2 / 2.0
                    + pipe_cfg["minor_loss_k"] * supply_rho * velocity_supply ** 2 / 2.0
                )
                dp_return = (
                    f_return * (assignment["pipeline_distance_m"] / return_id_m) * return_rho * velocity_return ** 2 / 2.0
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
                heat_gain_w = (q_supply_w_per_m + q_return_w_per_m) * assignment["pipeline_distance_m"]
                pump_power_w = (dp_supply * q_supply + dp_return * q_return) / pipe_cfg["pump_isentropic_efficiency"]
                heat_gain_fraction = heat_gain_w / q_total_w

                feasible = (
                    velocity_supply <= pipe_cfg["max_liquid_velocity_m_per_s"]
                    and velocity_return <= pipe_cfg["max_liquid_velocity_m_per_s"]
                )
                rows.append(
                    {
                        "insulation_thickness_m": insulation_thickness_m,
                        "supply_id_m": supply_id_m,
                        "return_id_m": return_id_m,
                        "velocity_supply_m_per_s": velocity_supply,
                        "velocity_return_m_per_s": velocity_return,
                        "dp_supply_kpa": dp_supply / 1000.0,
                        "dp_return_kpa": dp_return / 1000.0,
                        "heat_gain_kw": heat_gain_w / 1000.0,
                        "heat_gain_fraction": heat_gain_fraction,
                        "pump_power_kw": pump_power_w / 1000.0,
                        "objective": abs(heat_gain_w - q_target_env_w) / 1000.0 + pump_power_w / 2000.0,
                        "feasible": feasible,
                    }
                )

    frame = pd.DataFrame(rows).sort_values(["feasible", "objective", "pump_power_kw"], ascending=[False, True, True])
    if not bool(frame["feasible"].any()):
        raise RuntimeError("No feasible pipeline design found in search grid.")
    selected = frame[frame["feasible"]].iloc[0].to_dict()

    def evaluate_distance(distance_m: float) -> dict[str, float]:
        q_supply = mass_flow / supply_rho
        q_return = mass_flow / return_rho
        area_supply = math.pi * selected["supply_id_m"] ** 2 / 4.0
        area_return = math.pi * selected["return_id_m"] ** 2 / 4.0
        velocity_supply = q_supply / area_supply
        velocity_return = q_return / area_return
        f_supply = darcy_friction_factor(supply_rho * velocity_supply * selected["supply_id_m"] / supply_mu, pipe_cfg["pipe_roughness_m"], selected["supply_id_m"])
        f_return = darcy_friction_factor(return_rho * velocity_return * selected["return_id_m"] / return_mu, pipe_cfg["pipe_roughness_m"], selected["return_id_m"])
        dp_supply = f_supply * (distance_m / selected["supply_id_m"]) * supply_rho * velocity_supply ** 2 / 2.0
        dp_return = f_return * (distance_m / selected["return_id_m"]) * return_rho * velocity_return ** 2 / 2.0
        heat_gain_kw = (selected["heat_gain_kw"] / assignment["pipeline_distance_m"]) * distance_m
        pump_kw = (dp_supply * q_supply + dp_return * q_return) / pipe_cfg["pump_isentropic_efficiency"] / 1000.0
        return {
            "distance_m": distance_m,
            "heat_gain_kw": heat_gain_kw,
            "heat_gain_fraction": heat_gain_kw / (q_total_w / 1000.0),
            "pump_power_kw": pump_kw,
        }

    distance_candidates = config.get("sensitivity", {}).get(
        "distance_candidates_m",
        [assignment["pipeline_distance_m"], config["system_targets"]["long_distance_pipeline_m"]],
    )
    sensitivity = pd.DataFrame([evaluate_distance(distance_m) for distance_m in distance_candidates]).sort_values("distance_m").reset_index(drop=True)
    thermal_buffer_kw = hx_result["required_lng_duty_kw"] - required_cooling_kw
    base_heat_gain_kw = selected["heat_gain_kw"]
    max_feasible_distance_m = (
        assignment["pipeline_distance_m"] * thermal_buffer_kw / base_heat_gain_kw
        if base_heat_gain_kw > 1e-12
        else float("inf")
    )
    return {
        "scan_table": frame.reset_index(drop=True),
        "selected_design": selected,
        "sensitivity": sensitivity,
        "target_heat_gain_kw": q_target_env_w / 1000.0,
        "base_distance_m": assignment["pipeline_distance_m"],
        "max_feasible_distance_m": max_feasible_distance_m,
    }
