from __future__ import annotations

import math
from pathlib import Path

import CoolProp.CoolProp as CP


ATM_PRESSURE_PA = 101_325.0


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def saturation_pressure_water_pa(temperature_k: float) -> float:
    temperature_c = temperature_k - 273.15
    return 610.94 * math.exp((17.625 * temperature_c) / (temperature_c + 243.04))


def humidity_ratio(relative_humidity: float, temperature_k: float, pressure_pa: float = ATM_PRESSURE_PA) -> float:
    p_ws = saturation_pressure_water_pa(temperature_k)
    p_w = relative_humidity * p_ws
    return 0.62198 * p_w / max(pressure_pa - p_w, 1.0)


def moist_air_enthalpy_j_per_kg_da(temperature_k: float, relative_humidity: float) -> float:
    temperature_c = temperature_k - 273.15
    w = humidity_ratio(relative_humidity, temperature_k)
    return 1000.0 * (1.006 * temperature_c + w * (2501.0 + 1.86 * temperature_c))


def moist_air_density_kg_per_m3(temperature_k: float, relative_humidity: float, pressure_pa: float = ATM_PRESSURE_PA) -> float:
    p_ws = saturation_pressure_water_pa(temperature_k)
    p_w = relative_humidity * p_ws
    p_da = pressure_pa - p_w
    r_da = 287.055
    r_v = 461.495
    return p_da / (r_da * temperature_k) + p_w / (r_v * temperature_k)


def log_mean_temperature_difference(delta_t1: float, delta_t2: float) -> float:
    if delta_t1 <= 0.0 or delta_t2 <= 0.0:
        raise ValueError("Temperature differences must remain positive.")
    if abs(delta_t1 - delta_t2) < 1e-9:
        return delta_t1
    return (delta_t1 - delta_t2) / math.log(delta_t1 / delta_t2)


def safe_props(
    output: str,
    *,
    temperature_k: float | None = None,
    pressure_pa: float | None = None,
    enthalpy_j_per_kg: float | None = None,
    entropy_j_per_kgk: float | None = None,
    fluid: str,
) -> float:
    if temperature_k is not None and pressure_pa is not None:
        return float(CP.PropsSI(output, "T", temperature_k, "P", pressure_pa, fluid))
    if enthalpy_j_per_kg is not None and pressure_pa is not None:
        return float(CP.PropsSI(output, "H", enthalpy_j_per_kg, "P", pressure_pa, fluid))
    if entropy_j_per_kgk is not None and pressure_pa is not None:
        return float(CP.PropsSI(output, "S", entropy_j_per_kgk, "P", pressure_pa, fluid))
    raise ValueError("Unsupported state specification.")


def fluid_phase(temperature_k: float, pressure_pa: float, fluid: str) -> str:
    return str(CP.PhaseSI("T", temperature_k, "P", pressure_pa, fluid)).lower()


def darcy_friction_factor(reynolds: float, roughness_m: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        raise ValueError("Reynolds number must be positive.")
    if reynolds < 2300.0:
        return 64.0 / reynolds
    term = (roughness_m / (3.7 * diameter_m)) ** 1.11 + 6.9 / reynolds
    return 1.0 / (-1.8 * math.log10(term)) ** 2


def cylindrical_heat_gain_w_per_length(
    inner_radius_m: float,
    insulation_outer_radius_m: float,
    insulation_k_w_per_mk: float,
    outside_h_w_per_m2k: float,
    ambient_temperature_k: float,
    fluid_temperature_k: float,
) -> float:
    conduction = math.log(insulation_outer_radius_m / inner_radius_m) / (2.0 * math.pi * insulation_k_w_per_mk)
    convection = 1.0 / (2.0 * math.pi * insulation_outer_radius_m * outside_h_w_per_m2k)
    return (ambient_temperature_k - fluid_temperature_k) / (conduction + convection)


def bundle_shell_diameter_m(tube_count: int, pitch_m: float, packing_efficiency: float, clearance_factor: float) -> float:
    cell_area = math.sqrt(3.0) * pitch_m ** 2 / 2.0
    bundle_area = tube_count * cell_area / packing_efficiency
    bundle_diameter = math.sqrt(4.0 * bundle_area / math.pi)
    return bundle_diameter * clearance_factor
