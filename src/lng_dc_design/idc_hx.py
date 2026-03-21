from __future__ import annotations

import pandas as pd

from .thermo import fluid_phase, log_mean_temperature_difference, props_si


def evaluate_idc_heat_exchange(
    config: dict,
    fluid: str,
    required_cooling_kw: float,
) -> dict[str, object]:
    assignment = config["assignment"]
    loop = config["coolant_loop"]
    idc_hx = config["idc_hx"]

    pressure_pa = loop["pressure_mpa"] * 1_000_000.0
    supply_temp_k = loop["supply_temp_k"]
    chilled_supply_k = assignment["chilled_water_supply_temp_k"]
    chilled_return_k = assignment["chilled_water_return_temp_k"]
    minimum_approach_k = assignment["minimum_temperature_approach_k"]
    utilization_target_fraction = config["system_targets"]["idc_cooling_utilization_fraction"]
    minimum_return_to_lng_k = assignment["ng_outlet_temp_k"] + minimum_approach_k

    coolant_after_idc_temp_k = chilled_return_k - minimum_approach_k
    if coolant_after_idc_temp_k <= supply_temp_k:
        raise RuntimeError("IDC heat exchanger target outlet is not above the coolant supply temperature.")
    if minimum_return_to_lng_k <= coolant_after_idc_temp_k:
        raise RuntimeError("Required LNG hot-end return temperature must exceed the IDC outlet temperature.")

    h_supply = props_si("H", "T", supply_temp_k, "P", pressure_pa, fluid)
    h_after_idc = props_si("H", "T", coolant_after_idc_temp_k, "P", pressure_pa, fluid)
    coolant_mass_flow_kg_s = required_cooling_kw * 1000.0 / max(h_after_idc - h_supply, 1.0)

    h_minimum_return = props_si("H", "T", minimum_return_to_lng_k, "P", pressure_pa, fluid)
    minimum_lng_duty_kw = coolant_mass_flow_kg_s * (h_minimum_return - h_supply) / 1000.0
    minimum_line_heat_gain_required_kw = max(minimum_lng_duty_kw - required_cooling_kw, 0.0)
    design_lng_duty_kw = required_cooling_kw / utilization_target_fraction
    line_heat_gain_budget_kw = design_lng_duty_kw - required_cooling_kw
    minimum_hot_end_utilization_fraction = required_cooling_kw / max(minimum_lng_duty_kw, 1e-9)

    chilled_water_cp = idc_hx["chilled_water_cp_j_per_kgk"]
    chilled_water_mass_flow_kg_s = required_cooling_kw * 1000.0 / (
        chilled_water_cp * (chilled_return_k - chilled_supply_k)
    )

    delta_t_hot_end_k = chilled_return_k - coolant_after_idc_temp_k
    delta_t_cold_end_k = chilled_supply_k - supply_temp_k
    lmtd_k = log_mean_temperature_difference(delta_t_hot_end_k, delta_t_cold_end_k)
    required_area_m2 = required_cooling_kw * 1000.0 / (idc_hx["overall_u_w_per_m2k"] * lmtd_k)

    supply_phase = fluid_phase(supply_temp_k, pressure_pa, fluid)
    after_idc_phase = fluid_phase(coolant_after_idc_temp_k, pressure_pa, fluid)
    minimum_return_phase = fluid_phase(minimum_return_to_lng_k, pressure_pa, fluid)
    reference_t = 0.5 * (supply_temp_k + coolant_after_idc_temp_k)
    reference_density = props_si("D", "T", reference_t, "P", pressure_pa, fluid)
    reference_cp = props_si("C", "T", reference_t, "P", pressure_pa, fluid)
    reference_viscosity = props_si("V", "T", reference_t, "P", pressure_pa, fluid)
    reference_conductivity = props_si("L", "T", reference_t, "P", pressure_pa, fluid)

    profile = pd.DataFrame(
        [
            {
                "location": "cold end",
                "chilled_water_temp_k": chilled_supply_k,
                "coolant_temp_k": supply_temp_k,
                "delta_t_k": delta_t_cold_end_k,
            },
            {
                "location": "hot end",
                "chilled_water_temp_k": chilled_return_k,
                "coolant_temp_k": coolant_after_idc_temp_k,
                "delta_t_k": delta_t_hot_end_k,
            },
        ]
    )

    return {
        "fluid": fluid,
        "required_cooling_kw": required_cooling_kw,
        "utilization_target_fraction": utilization_target_fraction,
        "design_lng_duty_kw": design_lng_duty_kw,
        "total_lng_duty_kw": design_lng_duty_kw,
        "line_heat_gain_budget_kw": line_heat_gain_budget_kw,
        "minimum_return_to_lng_k": minimum_return_to_lng_k,
        "minimum_lng_duty_kw": minimum_lng_duty_kw,
        "minimum_line_heat_gain_required_kw": minimum_line_heat_gain_required_kw,
        "minimum_hot_end_utilization_fraction": minimum_hot_end_utilization_fraction,
        "supply_temp_k": supply_temp_k,
        "coolant_after_idc_temp_k": coolant_after_idc_temp_k,
        "coolant_mass_flow_kg_s": coolant_mass_flow_kg_s,
        "chilled_water_mass_flow_kg_s": chilled_water_mass_flow_kg_s,
        "min_pinch_k": min(delta_t_hot_end_k, delta_t_cold_end_k),
        "lmtd_k": lmtd_k,
        "required_area_m2": required_area_m2,
        "supply_phase": supply_phase,
        "after_idc_phase": after_idc_phase,
        "minimum_return_phase": minimum_return_phase,
        "reference_density_kg_per_m3": reference_density,
        "reference_cp_j_per_kgk": reference_cp,
        "reference_viscosity_pa_s": reference_viscosity,
        "reference_conductivity_w_per_mk": reference_conductivity,
        "profile": profile,
    }
