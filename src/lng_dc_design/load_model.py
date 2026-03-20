from __future__ import annotations

from dataclasses import dataclass

from .thermo import moist_air_density_kg_per_m3, moist_air_enthalpy_j_per_kg_da


@dataclass(slots=True)
class LoadModelResult:
    breakdown_kw: dict[str, float]
    total_kw: float


def compute_load_model(config: dict) -> LoadModelResult:
    assignment = config["assignment"]
    building = config["building"]
    assumptions = config["load_assumptions"]

    it_kw = assignment["rack_count"] * assignment["it_load_kw_per_rack"]
    floor_area_m2 = building["length_m"] * building["width_m"] * building["active_it_floors"]
    above_ground_height_m = building["above_ground_floors"] * assumptions["floor_height_m"]
    perimeter_m = 2.0 * (building["length_m"] + building["width_m"])
    exterior_wall_area_m2 = perimeter_m * above_ground_height_m
    glazing_area_m2 = exterior_wall_area_m2 * assumptions["glazing_ratio"]
    opaque_wall_area_m2 = exterior_wall_area_m2 - glazing_area_m2
    roof_area_m2 = building["length_m"] * building["width_m"]
    enclosed_volume_m3 = roof_area_m2 * above_ground_height_m

    delta_t_k = assignment["ambient_air_temp_k"] - assignment["room_air_temp_k"]

    lighting_kw = assumptions["lighting_density_w_per_m2"] * floor_area_m2 / 1000.0
    distribution_kw = assumptions["power_distribution_loss_fraction"] * it_kw
    auxiliary_kw = assumptions["auxiliary_service_loss_fraction"] * it_kw
    occupant_kw = assumptions["occupant_count"] * assumptions["occupant_sensible_w"] / 1000.0

    wall_kw = assumptions["wall_u_w_per_m2k"] * opaque_wall_area_m2 * delta_t_k / 1000.0
    roof_kw = assumptions["roof_u_w_per_m2k"] * roof_area_m2 * delta_t_k / 1000.0
    glazing_kw = assumptions["glazing_u_w_per_m2k"] * glazing_area_m2 * delta_t_k / 1000.0
    solar_kw = assumptions["effective_solar_irradiance_w_per_m2"] * assumptions["glazing_shgc"] * glazing_area_m2 / 1000.0

    room_h = moist_air_enthalpy_j_per_kg_da(assignment["room_air_temp_k"], assignment["room_relative_humidity"])
    ambient_h = moist_air_enthalpy_j_per_kg_da(assignment["ambient_air_temp_k"], assignment["ambient_relative_humidity"])
    ambient_density = moist_air_density_kg_per_m3(assignment["ambient_air_temp_k"], assignment["ambient_relative_humidity"])
    infiltration_m3_s = assumptions["infiltration_ach"] * enclosed_volume_m3 / 3600.0
    infiltration_kw = infiltration_m3_s * ambient_density * max(ambient_h - room_h, 0.0) / 1000.0

    breakdown_kw = {
        "IT racks": it_kw,
        "Power distribution losses": distribution_kw,
        "Lighting": lighting_kw,
        "Auxiliary building services": auxiliary_kw,
        "Occupants": occupant_kw,
        "Wall conduction": wall_kw,
        "Roof conduction": roof_kw,
        "Glazing conduction": glazing_kw,
        "Solar gain": solar_kw,
        "Infiltration": infiltration_kw,
    }
    return LoadModelResult(breakdown_kw=breakdown_kw, total_kw=sum(breakdown_kw.values()))
