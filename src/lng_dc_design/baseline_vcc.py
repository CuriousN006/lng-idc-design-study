from __future__ import annotations

import CoolProp.CoolProp as CP
import pandas as pd


def compute_baseline_cycle(config: dict, total_cooling_kw: float) -> dict[str, object]:
    baseline = config["baseline_cycle"]
    assignment = config["assignment"]
    fluid = baseline["fluid"]

    evaporating_temp_k = assignment["chilled_water_supply_temp_k"] - baseline["evaporator_approach_k"]
    condensing_temp_k = assignment["ambient_air_temp_k"] + baseline["condenser_approach_k"]
    compressor_eta = baseline["compressor_isentropic_efficiency"]

    p_low = float(CP.PropsSI("P", "T", evaporating_temp_k, "Q", 1.0, fluid))
    p_high = float(CP.PropsSI("P", "T", condensing_temp_k, "Q", 0.0, fluid))

    h1 = float(CP.PropsSI("H", "T", evaporating_temp_k, "Q", 1.0, fluid))
    s1 = float(CP.PropsSI("S", "T", evaporating_temp_k, "Q", 1.0, fluid))
    h2s = float(CP.PropsSI("H", "P", p_high, "S", s1, fluid))
    h2 = h1 + (h2s - h1) / compressor_eta
    h3 = float(CP.PropsSI("H", "T", condensing_temp_k, "Q", 0.0, fluid))
    h4 = h3

    q_evap_j_per_kg = h1 - h4
    q_cond_j_per_kg = h2 - h3
    work_j_per_kg = h2 - h1

    mass_flow_kg_s = total_cooling_kw * 1000.0 / q_evap_j_per_kg
    compressor_power_kw = mass_flow_kg_s * work_j_per_kg / 1000.0
    condenser_heat_kw = mass_flow_kg_s * q_cond_j_per_kg / 1000.0
    cop = total_cooling_kw / compressor_power_kw

    points = pd.DataFrame(
        [
            {"state": 1, "pressure_kpa": p_low / 1000.0, "enthalpy_kj_per_kg": h1 / 1000.0},
            {"state": 2, "pressure_kpa": p_high / 1000.0, "enthalpy_kj_per_kg": h2 / 1000.0},
            {"state": 3, "pressure_kpa": p_high / 1000.0, "enthalpy_kj_per_kg": h3 / 1000.0},
            {"state": 4, "pressure_kpa": p_low / 1000.0, "enthalpy_kj_per_kg": h4 / 1000.0},
        ]
    )

    return {
        "fluid": fluid,
        "evaporating_temp_k": evaporating_temp_k,
        "condensing_temp_k": condensing_temp_k,
        "mass_flow_kg_s": mass_flow_kg_s,
        "compressor_power_kw": compressor_power_kw,
        "condenser_heat_kw": condenser_heat_kw,
        "cop": cop,
        "cycle_points": points,
    }
