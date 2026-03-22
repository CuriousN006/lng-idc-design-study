from __future__ import annotations

import math

import pandas as pd

from .thermo import (
    darcy_friction_factor,
    buried_pipe_heat_gain_w_per_length,
    exposed_pipe_heat_gain_w_per_length,
    outside_h_from_wind_speed,
    phase_si,
    props_si,
)


def _resolve_thermal_case(config: dict, thermal_case: dict[str, float | str] | None) -> dict[str, float | str]:
    assignment = config["assignment"]
    pipe_cfg = config["pipeline_design"]
    resolved: dict[str, float | str] = {
        "mode": "air",
        "ambient_air_temp_k": float(assignment["ambient_air_temp_k"]),
        "outside_h_w_per_m2k": float(pipe_cfg["outside_h_w_per_m2k"]),
        "wind_speed_m_per_s": 0.0,
        "solar_absorbed_flux_w_per_m2": 0.0,
        "soil_temperature_k": float(assignment["ambient_air_temp_k"]),
        "soil_conductivity_w_per_mk": 1.5,
        "burial_depth_m": 1.5,
        "pump_heat_to_fluid_fraction": 0.0,
    }
    if thermal_case:
        resolved.update(thermal_case)
    if "wind_speed_m_per_s" in resolved:
        resolved["outside_h_w_per_m2k"] = outside_h_from_wind_speed(
            float(resolved["wind_speed_m_per_s"]),
            float(resolved["outside_h_w_per_m2k"]),
        )
    return resolved


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
    thermal_case: dict[str, float | str] | None = None,
) -> dict[str, float | bool]:
    assignment = config["assignment"]
    loop = config["coolant_loop"]
    pipe_cfg = config["pipeline_design"]
    thermal = _resolve_thermal_case(config, thermal_case)

    supply_temp_k = loop["supply_temp_k"]
    h_supply = props_si("H", "T", supply_temp_k, "P", pressure_pa, fluid)
    h_after_idc = props_si("H", "T", after_idc_temp_k, "P", pressure_pa, fluid)

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
    line_heat_gain_kw = 0.0
    pump_heat_to_fluid_kw = 0.0

    for _ in range(40):
        return_avg_temp_k = 0.5 * (after_idc_temp_k + return_to_lng_temp_k)

        supply_rho = props_si("D", "T", supply_avg_temp_k, "P", pressure_pa, fluid)
        return_rho = props_si("D", "T", return_avg_temp_k, "P", pressure_pa, fluid)
        supply_mu = props_si("V", "T", supply_avg_temp_k, "P", pressure_pa, fluid)
        return_mu = props_si("V", "T", return_avg_temp_k, "P", pressure_pa, fluid)

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
        if str(thermal["mode"]).lower() == "soil":
            q_supply_w_per_m = buried_pipe_heat_gain_w_per_length(
                supply_outer_radius,
                supply_outer_radius + insulation_thickness_m,
                pipe_cfg["insulation_conductivity_w_per_mk"],
                float(thermal["soil_conductivity_w_per_mk"]),
                float(thermal["burial_depth_m"]),
                float(thermal["soil_temperature_k"]),
                supply_avg_temp_k,
            )
            q_return_w_per_m = buried_pipe_heat_gain_w_per_length(
                return_outer_radius,
                return_outer_radius + insulation_thickness_m,
                pipe_cfg["insulation_conductivity_w_per_mk"],
                float(thermal["soil_conductivity_w_per_mk"]),
                float(thermal["burial_depth_m"]),
                float(thermal["soil_temperature_k"]),
                return_avg_temp_k,
            )
        else:
            q_supply_w_per_m = exposed_pipe_heat_gain_w_per_length(
                supply_outer_radius,
                supply_outer_radius + insulation_thickness_m,
                pipe_cfg["insulation_conductivity_w_per_mk"],
                float(thermal["outside_h_w_per_m2k"]),
                float(thermal["ambient_air_temp_k"]),
                supply_avg_temp_k,
                float(thermal["solar_absorbed_flux_w_per_m2"]),
            )
            q_return_w_per_m = exposed_pipe_heat_gain_w_per_length(
                return_outer_radius,
                return_outer_radius + insulation_thickness_m,
                pipe_cfg["insulation_conductivity_w_per_mk"],
                float(thermal["outside_h_w_per_m2k"]),
                float(thermal["ambient_air_temp_k"]),
                return_avg_temp_k,
                float(thermal["solar_absorbed_flux_w_per_m2"]),
            )
        line_heat_gain_w = (q_supply_w_per_m + q_return_w_per_m) * distance_m
        line_heat_gain_kw = line_heat_gain_w / 1000.0
        pump_power_w = (dp_supply * q_supply + dp_return * q_return) / pipe_cfg["pump_isentropic_efficiency"]
        pump_heat_to_fluid_kw = float(thermal["pump_heat_to_fluid_fraction"]) * pump_power_w / 1000.0
        heat_gain_kw = line_heat_gain_kw + pump_heat_to_fluid_kw
        supplemental_reheat_kw = max(minimum_line_heat_gain_required_kw - heat_gain_kw, 0.0)
        total_external_heat_kw = heat_gain_kw + supplemental_reheat_kw
        actual_lng_duty_kw = required_cooling_kw + total_external_heat_kw
        new_return_to_lng_temp_k = props_si(
            "T",
            "H",
            h_after_idc + total_external_heat_kw * 1000.0 / mass_flow_kg_s,
            "P",
            pressure_pa,
            fluid,
        )
        if abs(new_return_to_lng_temp_k - return_to_lng_temp_k) < 1e-4:
            return_to_lng_temp_k = new_return_to_lng_temp_k
            break
        return_to_lng_temp_k = 0.5 * (return_to_lng_temp_k + new_return_to_lng_temp_k)

    pump_power_w = (dp_supply * q_supply + dp_return * q_return) / pipe_cfg["pump_isentropic_efficiency"]
    tolerance_kw = 1e-6
    base_duty_available_cooling_kw = total_lng_duty_kw - heat_gain_kw - supplemental_reheat_kw
    hybrid_available_cooling_kw = actual_lng_duty_kw - heat_gain_kw - supplemental_reheat_kw
    available_cooling_kw = hybrid_available_cooling_kw
    design_target_margin_kw = total_lng_duty_kw - heat_gain_kw - required_cooling_kw
    heat_gain_fraction = heat_gain_kw / max(actual_lng_duty_kw, 1e-9)
    hot_end_margin_k = return_to_lng_temp_k - minimum_return_to_lng_k
    base_duty_margin_kw = base_duty_available_cooling_kw - required_cooling_kw
    thermal_margin_kw = hybrid_available_cooling_kw - required_cooling_kw
    hybrid_heat_balance_error_kw = thermal_margin_kw
    actual_utilization_fraction = required_cooling_kw / max(actual_lng_duty_kw, 1e-9)
    return_phase = phase_si("T", return_to_lng_temp_k, "P", pressure_pa, fluid)
    hydraulic_feasible = (
        velocity_supply <= pipe_cfg["max_liquid_velocity_m_per_s"]
        and velocity_return <= pipe_cfg["max_liquid_velocity_m_per_s"]
        and hot_end_margin_k >= -1e-6
        and "liquid" in return_phase
    )
    requires_supplemental_warmup = supplemental_reheat_kw > tolerance_kw
    within_design_lng_duty = actual_lng_duty_kw <= total_lng_duty_kw + tolerance_kw
    base_duty_meets_idc_load = hydraulic_feasible and base_duty_margin_kw >= -tolerance_kw
    hybrid_operation_feasible = hydraulic_feasible
    hybrid_load_satisfied = hybrid_operation_feasible

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
        "line_heat_gain_kw": line_heat_gain_kw,
        "pump_heat_to_fluid_kw": pump_heat_to_fluid_kw,
        "heat_gain_kw": heat_gain_kw,
        "heat_gain_fraction": heat_gain_fraction,
        "supplemental_warmup_kw": supplemental_reheat_kw,
        "requires_supplemental_warmup": requires_supplemental_warmup,
        "base_lng_duty_kw": total_lng_duty_kw,
        "hybrid_requested_lng_duty_kw": actual_lng_duty_kw,
        "actual_lng_duty_kw": actual_lng_duty_kw,
        "actual_utilization_fraction": actual_utilization_fraction,
        "pump_power_kw": pump_power_w / 1000.0,
        "available_cooling_kw": available_cooling_kw,
        "hybrid_available_cooling_kw": hybrid_available_cooling_kw,
        "base_duty_available_cooling_kw": base_duty_available_cooling_kw,
        "thermal_margin_kw": thermal_margin_kw,
        "hybrid_heat_balance_error_kw": hybrid_heat_balance_error_kw,
        "base_duty_margin_kw": base_duty_margin_kw,
        "design_target_margin_kw": design_target_margin_kw,
        "return_to_lng_temp_k": return_to_lng_temp_k,
        "minimum_return_to_lng_k": minimum_return_to_lng_k,
        "hot_end_margin_k": hot_end_margin_k,
        "return_phase": return_phase,
        "meets_utilization_target": within_design_lng_duty,
        "within_design_lng_duty": within_design_lng_duty,
        "base_duty_meets_idc_load": base_duty_meets_idc_load,
        "hybrid_operation_feasible": hybrid_operation_feasible,
        "hybrid_load_satisfied": hybrid_load_satisfied,
        "hydraulic_feasible": hydraulic_feasible,
        "feasible": hydraulic_feasible,
        "thermal_mode": str(thermal["mode"]),
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
    thermal_case: dict[str, float | str] | None = None,
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
        thermal_case,
    )

    while bool(upper_case["hydraulic_feasible"]) and upper < 250_000.0:
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
            thermal_case,
        )

    if bool(upper_case["hydraulic_feasible"]):
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
            thermal_case,
        )
        if bool(mid_case["hydraulic_feasible"]):
            lower = mid
        else:
            upper = mid
    return lower


def _estimate_max_base_duty_distance(
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
    thermal_case: dict[str, float | str] | None = None,
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
        thermal_case,
    )

    while bool(upper_case["base_duty_meets_idc_load"]) and upper < 250_000.0:
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
            thermal_case,
        )

    if bool(upper_case["base_duty_meets_idc_load"]):
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
            thermal_case,
        )
        if bool(mid_case["base_duty_meets_idc_load"]):
            lower = mid
        else:
            upper = mid
    return lower


def _estimate_ambient_only_closure_distance(
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
    max_feasible_distance_m: float,
    tolerance_kw: float = 1e-3,
    thermal_case: dict[str, float | str] | None = None,
) -> float:
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
        max_feasible_distance_m,
        thermal_case,
    )
    if (not bool(upper_case["hydraulic_feasible"])) or float(upper_case["supplemental_warmup_kw"]) > tolerance_kw:
        return math.nan

    lower_case = _evaluate_pipeline_case(
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
        0.0,
        thermal_case,
    )
    if bool(lower_case["hydraulic_feasible"]) and float(lower_case["supplemental_warmup_kw"]) <= tolerance_kw:
        return 0.0

    lower = 0.0
    upper = max_feasible_distance_m
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
            thermal_case,
        )
        if bool(mid_case["hydraulic_feasible"]) and float(mid_case["supplemental_warmup_kw"]) <= tolerance_kw:
            upper = mid
        else:
            lower = mid
    return upper


def design_pipeline(
    config: dict,
    selected_fluid: dict,
    required_cooling_kw: float,
    thermal_case: dict[str, float | str] | None = None,
) -> dict[str, object]:
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
                    thermal_case,
                )
                rows.append(row)

    frame = pd.DataFrame(rows).sort_values(
        [
            "base_duty_meets_idc_load",
            "feasible",
            "requires_supplemental_warmup",
            "supplemental_warmup_kw",
            "pump_power_kw",
            "heat_gain_kw",
        ],
        ascending=[False, False, True, True, True, True],
    )
    if not bool(frame["feasible"].any()):
        raise RuntimeError("No feasible pipeline design found in search grid.")
    selected_hybrid = frame[frame["feasible"]].iloc[0].to_dict()
    base_duty_designs = frame[frame["base_duty_meets_idc_load"]]
    selected_base_duty = base_duty_designs.iloc[0].to_dict() if not base_duty_designs.empty else None
    selected = selected_base_duty or selected_hybrid

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
                thermal_case,
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
        thermal_case,
    )
    ambient_only_closure_distance_m = _estimate_ambient_only_closure_distance(
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
        max_feasible_distance_m,
        thermal_case=thermal_case,
    )
    max_base_duty_distance_m = _estimate_max_base_duty_distance(
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
        thermal_case,
    )

    return {
        "scan_table": frame.reset_index(drop=True),
        "selected_design": selected,
        "selected_hybrid_design": selected_hybrid,
        "selected_base_duty_design": selected_base_duty,
        "sensitivity": sensitivity,
        "target_heat_gain_kw": total_lng_duty_kw - required_cooling_kw,
        "base_distance_m": config["assignment"]["pipeline_distance_m"],
        "max_feasible_distance_m": max_feasible_distance_m,
        "max_base_duty_distance_m": max_base_duty_distance_m,
        "ambient_only_closure_distance_m": ambient_only_closure_distance_m,
        "after_idc_temp_k": after_idc_temp_k,
        "return_to_lng_temp_k": float(selected["return_to_lng_temp_k"]),
        "minimum_return_to_lng_k": minimum_return_to_lng_k,
        "minimum_line_heat_gain_required_kw": minimum_line_heat_gain_required_kw,
    }
