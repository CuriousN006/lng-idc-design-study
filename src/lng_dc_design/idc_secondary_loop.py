from __future__ import annotations

import math

import pandas as pd

from .thermo import darcy_friction_factor, props_si


def _equivalent_distribution_length_m(config: dict) -> float:
    building = config["building"]
    load_assumptions = config["load_assumptions"]
    loop_cfg = config["idc_secondary_loop"]

    parallel_circuits = max(int(loop_cfg["parallel_circuits"]), 1)
    active_floors = float(building["active_it_floors"]) / parallel_circuits
    floor_height_m = float(load_assumptions["floor_height_m"])
    length_m = float(building["length_m"])
    width_m = float(building["width_m"])
    horizontal_factor = float(loop_cfg["horizontal_distribution_length_factor"])

    riser_length_m = 2.0 * active_floors * floor_height_m
    horizontal_length_m = active_floors * horizontal_factor * (length_m + width_m)
    return riser_length_m + horizontal_length_m


def evaluate_idc_secondary_loop(
    config: dict,
    chilled_water_mass_flow_kg_s: float,
) -> dict[str, object]:
    assignment = config["assignment"]
    loop_cfg = config["idc_secondary_loop"]

    supply_temp_k = float(assignment["chilled_water_supply_temp_k"])
    return_temp_k = float(assignment["chilled_water_return_temp_k"])
    mean_temp_k = 0.5 * (supply_temp_k + return_temp_k)
    pressure_pa = 101_325.0
    fluid = "Water"

    density = props_si("D", "T", mean_temp_k, "P", pressure_pa, fluid)
    viscosity = props_si("V", "T", mean_temp_k, "P", pressure_pa, fluid)
    total_volumetric_flow_m3_s = chilled_water_mass_flow_kg_s / density
    parallel_circuits = max(int(loop_cfg["parallel_circuits"]), 1)
    volumetric_flow_m3_s = total_volumetric_flow_m3_s / parallel_circuits
    equivalent_length_m = _equivalent_distribution_length_m(config)

    rows: list[dict[str, float | bool]] = []
    for diameter_m in loop_cfg["diameter_candidates_m"]:
        cross_section_area_m2 = math.pi * diameter_m ** 2 / 4.0
        velocity_m_per_s = volumetric_flow_m3_s / cross_section_area_m2
        reynolds = density * velocity_m_per_s * diameter_m / viscosity
        friction_factor = darcy_friction_factor(reynolds, loop_cfg["pipe_roughness_m"], diameter_m)
        pipe_dp_pa = friction_factor * (equivalent_length_m / diameter_m) * density * velocity_m_per_s ** 2 / 2.0
        minor_dp_pa = loop_cfg["minor_loss_k"] * density * velocity_m_per_s ** 2 / 2.0
        terminal_dp_pa = (
            loop_cfg["idc_hx_pressure_drop_kpa"]
            + loop_cfg["coil_and_valve_pressure_drop_kpa"]
            + loop_cfg["miscellaneous_pressure_drop_kpa"]
        ) * 1000.0
        total_dp_pa = pipe_dp_pa + minor_dp_pa + terminal_dp_pa
        pump_power_kw = total_dp_pa * volumetric_flow_m3_s / loop_cfg["pump_efficiency"] / 1000.0 * parallel_circuits
        feasible = (
            velocity_m_per_s <= loop_cfg["max_water_velocity_m_per_s"]
            and total_dp_pa / 1000.0 <= loop_cfg["max_total_pressure_drop_kpa"]
        )
        rows.append(
            {
                "diameter_m": float(diameter_m),
                "equivalent_length_m": equivalent_length_m,
                "parallel_circuits": parallel_circuits,
                "total_volumetric_flow_m3_s": total_volumetric_flow_m3_s,
                "volumetric_flow_m3_s": volumetric_flow_m3_s,
                "velocity_m_per_s": velocity_m_per_s,
                "reynolds": reynolds,
                "pipe_pressure_drop_kpa": pipe_dp_pa / 1000.0,
                "minor_pressure_drop_kpa": minor_dp_pa / 1000.0,
                "terminal_pressure_drop_kpa": terminal_dp_pa / 1000.0,
                "total_pressure_drop_kpa": total_dp_pa / 1000.0,
                "pump_power_kw": pump_power_kw,
                "feasible": feasible,
            }
        )

    scan_table = pd.DataFrame(rows).sort_values(
        ["feasible", "pump_power_kw", "diameter_m"],
        ascending=[False, True, True],
    ).reset_index(drop=True)
    if not bool(scan_table["feasible"].any()):
        raise RuntimeError("No feasible IDC secondary-loop diameter satisfied the configured velocity and pressure-drop limits.")

    selected_design = scan_table[scan_table["feasible"]].iloc[0].to_dict()
    return {
        "selected_design": selected_design,
        "scan_table": scan_table,
        "equivalent_length_m": equivalent_length_m,
        "density_kg_per_m3": density,
        "viscosity_pa_s": viscosity,
        "volumetric_flow_m3_s": total_volumetric_flow_m3_s,
        "per_circuit_volumetric_flow_m3_s": volumetric_flow_m3_s,
        "parallel_circuits": parallel_circuits,
    }
