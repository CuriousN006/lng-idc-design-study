from __future__ import annotations

import math

import pandas as pd

from .lng_mixture import build_lng_mixture_definition
from .thermo import bundle_shell_diameter_m, log_mean_temperature_difference, props_si


def _tube_pressure_drop(length_m: float, diameter_i_m: float, velocity: float, rho: float, mu: float) -> float:
    reynolds = max(rho * velocity * diameter_i_m / mu, 1.0)
    if reynolds < 2300.0:
        friction = 64.0 / reynolds
    else:
        friction = 0.3164 * reynolds ** -0.25
    return friction * (length_m / diameter_i_m) * rho * velocity ** 2 / 2.0


def design_lng_vaporizer(
    config: dict,
    selected_fluid: dict,
    required_lng_duty_kw: float,
    *,
    transport_property_proxy_override: str | None = None,
) -> dict[str, object]:
    assignment = config["assignment"]
    hx_cfg = config["hx_design"]
    loop = config["coolant_loop"]

    fluid = selected_fluid["coolprop_name"]
    pressure_pa = loop["pressure_mpa"] * 1_000_000.0
    lng_pressure_pa = assignment["lng_pressure_mpa"] * 1_000_000.0
    cold_bounds = hx_cfg["segment_boundaries_k"]
    lng_mixture = build_lng_mixture_definition(config)
    lng_fluid = lng_mixture.coolprop_string
    if transport_property_proxy_override == "configured_mixture":
        lng_transport_fluid = lng_fluid
        lng_transport_label = f"{lng_mixture.label} transport"
    elif transport_property_proxy_override is not None:
        lng_transport_fluid = str(transport_property_proxy_override)
        lng_transport_label = str(transport_property_proxy_override)
    else:
        lng_transport_fluid = str(config.get("lng_mixture", {}).get("transport_property_proxy", lng_fluid))
        lng_transport_label = str(config.get("lng_mixture", {}).get("transport_property_proxy", lng_fluid))

    h_lng = [props_si("H", "T", temp_k, "P", lng_pressure_pa, lng_fluid) for temp_k in cold_bounds]
    q_total_w = required_lng_duty_kw * 1000.0
    m_lng = q_total_w / (h_lng[-1] - h_lng[0])
    q_segments = [m_lng * (h_lng[i + 1] - h_lng[i]) for i in range(len(cold_bounds) - 1)]

    return_to_lng_temp_k = float(selected_fluid.get("return_to_lng_temp_k", loop["return_to_lng_temp_k"]))
    after_idc_temp_k = float(selected_fluid.get("after_idc_temp_k", loop["after_idc_temp_k"]))

    h_hot_in = props_si("H", "T", return_to_lng_temp_k, "P", pressure_pa, fluid)
    h_hot_out = props_si("H", "T", loop["supply_temp_k"], "P", pressure_pa, fluid)
    m_hot = float(selected_fluid.get("required_mass_flow_kg_s", q_total_w / max(h_hot_in - h_hot_out, 1.0)))

    hot_at_boundaries = [0.0] * len(cold_bounds)
    hot_at_boundaries[-1] = return_to_lng_temp_k
    current_h = h_hot_in
    for segment_idx in range(len(q_segments) - 1, -1, -1):
        current_h -= q_segments[segment_idx] / m_hot
        hot_at_boundaries[segment_idx] = props_si("T", "H", current_h, "P", pressure_pa, fluid)

    pinch_values = [hot - cold for hot, cold in zip(hot_at_boundaries, cold_bounds)]
    min_pinch = min(pinch_values)

    outer_diameter_m = assignment["tube_outer_diameter_m"]
    wall_thickness_m = assignment["tube_wall_thickness_m"]
    inner_diameter_m = outer_diameter_m - 2.0 * wall_thickness_m
    pitch_m = hx_cfg["tube_pitch_m"]
    k_wall = hx_cfg["tube_wall_conductivity_w_per_mk"]
    baffle_spacing_m = hx_cfg["baffle_spacing_m"]
    packing_efficiency = hx_cfg["tube_packing_efficiency"]
    clearance_factor = hx_cfg["shell_clearance_factor"]

    candidate_rows: list[dict[str, float]] = []
    for length_m in hx_cfg["tube_length_candidates_m"]:
        for tube_count in range(hx_cfg["tube_count_min"], hx_cfg["tube_count_max"] + 1, hx_cfg["tube_count_step"]):
            shell_diameter_m = bundle_shell_diameter_m(tube_count, pitch_m, packing_efficiency, clearance_factor)
            provided_area_m2 = tube_count * math.pi * outer_diameter_m * length_m

            required_area_m2 = 0.0
            tube_velocity_max = 0.0
            shell_velocity_max = 0.0
            tube_dp_pa = 0.0
            shell_dp_pa = 0.0

            for idx, q_segment in enumerate(q_segments):
                cold_in = cold_bounds[idx]
                cold_out = cold_bounds[idx + 1]
                hot_in = hot_at_boundaries[idx + 1]
                hot_out = hot_at_boundaries[idx]

                lng_mean_t = 0.5 * (cold_in + cold_out)
                hot_mean_t = 0.5 * (hot_in + hot_out)

                mu_tube = props_si("V", "T", lng_mean_t, "P", lng_pressure_pa, lng_transport_fluid)
                k_tube = props_si("L", "T", lng_mean_t, "P", lng_pressure_pa, lng_transport_fluid)
                cp_tube = props_si("C", "T", lng_mean_t, "P", lng_pressure_pa, lng_transport_fluid)
                rho_tube = props_si("D", "T", lng_mean_t, "P", lng_pressure_pa, lng_transport_fluid)

                mu_shell = props_si("V", "T", hot_mean_t, "P", pressure_pa, fluid)
                k_shell = props_si("L", "T", hot_mean_t, "P", pressure_pa, fluid)
                cp_shell = props_si("C", "T", hot_mean_t, "P", pressure_pa, fluid)
                rho_shell = props_si("D", "T", hot_mean_t, "P", pressure_pa, fluid)

                tube_area = tube_count * math.pi * inner_diameter_m ** 2 / 4.0
                tube_velocity = m_lng / (rho_tube * tube_area)
                reynolds_tube = rho_tube * tube_velocity * inner_diameter_m / mu_tube
                prandtl_tube = cp_tube * mu_tube / k_tube
                nusselt_tube = 0.023 * reynolds_tube ** 0.8 * prandtl_tube ** 0.4
                hi = nusselt_tube * k_tube / inner_diameter_m

                equivalent_diameter = 1.10 / outer_diameter_m * (pitch_m ** 2 - 0.917 * outer_diameter_m ** 2)
                shell_area = (pitch_m - outer_diameter_m) * shell_diameter_m * baffle_spacing_m / pitch_m
                shell_mass_velocity = m_hot / shell_area
                shell_velocity = shell_mass_velocity / rho_shell
                reynolds_shell = shell_mass_velocity * equivalent_diameter / mu_shell
                prandtl_shell = cp_shell * mu_shell / k_shell
                j_h = 0.5 * (1.0 + baffle_spacing_m / shell_diameter_m) * (0.08 * reynolds_shell ** 0.6821 + 0.7 * reynolds_shell ** 0.1772)
                ho = j_h * k_shell * prandtl_shell ** (1.0 / 3.0) / equivalent_diameter

                uo = 1.0 / (
                    outer_diameter_m / (inner_diameter_m * hi)
                    + outer_diameter_m * math.log(outer_diameter_m / inner_diameter_m) / (2.0 * k_wall)
                    + 1.0 / ho
                )
                lmtd = log_mean_temperature_difference(hot_in - cold_out, hot_out - cold_in)
                required_area_m2 += q_segment / (uo * lmtd)

                tube_dp_pa += _tube_pressure_drop(length_m, inner_diameter_m, tube_velocity, rho_tube, mu_tube)
                shell_dp_pa += 0.20 * (length_m / max(baffle_spacing_m, 1e-6)) * rho_shell * shell_velocity ** 2
                tube_velocity_max = max(tube_velocity_max, tube_velocity)
                shell_velocity_max = max(shell_velocity_max, shell_velocity)

            feasible = (
                provided_area_m2 >= required_area_m2
                and tube_velocity_max <= hx_cfg["max_liquid_velocity_m_per_s"]
                and shell_velocity_max <= hx_cfg["max_liquid_velocity_m_per_s"]
                and min_pinch >= assignment["minimum_temperature_approach_k"] - 1e-6
            )
            candidate_rows.append(
                {
                    "tube_length_m": length_m,
                    "tube_count": tube_count,
                    "shell_diameter_m": shell_diameter_m,
                    "provided_area_m2": provided_area_m2,
                    "required_area_m2": required_area_m2,
                    "tube_velocity_max_m_per_s": tube_velocity_max,
                    "shell_velocity_max_m_per_s": shell_velocity_max,
                    "tube_pressure_drop_kpa": tube_dp_pa / 1000.0,
                    "shell_pressure_drop_kpa": shell_dp_pa / 1000.0,
                    "feasible": feasible,
                }
            )

    candidates = pd.DataFrame(candidate_rows).sort_values(
        ["feasible", "shell_diameter_m", "tube_count", "tube_length_m"], ascending=[False, True, True, True]
    )
    if not bool(candidates["feasible"].any()):
        raise RuntimeError("No feasible LNG vaporizer geometry found in search grid.")
    selected_geometry = candidates[candidates["feasible"]].iloc[0].to_dict()

    segment_frame = pd.DataFrame(
        [
            {
                "segment": f"{cold_bounds[idx]:.0f}-{cold_bounds[idx + 1]:.0f} K",
                "q_kw": q_segments[idx] / 1000.0,
                "lng_in_k": cold_bounds[idx],
                "lng_out_k": cold_bounds[idx + 1],
                "coolant_in_k": hot_at_boundaries[idx + 1],
                "coolant_out_k": hot_at_boundaries[idx],
            }
            for idx in range(len(q_segments))
        ]
    )

    return {
        "selected_fluid": fluid,
        "lng_mixture_label": lng_mixture.label,
        "lng_fluid": lng_fluid,
        "lng_transport_fluid": lng_transport_fluid,
        "lng_transport_label": lng_transport_label,
        "lng_normalized_components": lng_mixture.normalized_components,
        "required_lng_duty_kw": required_lng_duty_kw,
        "m_lng_kg_s": m_lng,
        "m_coolant_kg_s": m_hot,
        "hot_boundaries_k": hot_at_boundaries,
        "cold_boundaries_k": cold_bounds,
        "after_idc_temp_k": after_idc_temp_k,
        "return_to_lng_temp_k": return_to_lng_temp_k,
        "pinch_values_k": pinch_values,
        "min_pinch_k": min_pinch,
        "geometry_candidates": candidates,
        "selected_geometry": selected_geometry,
        "segments": segment_frame,
    }
