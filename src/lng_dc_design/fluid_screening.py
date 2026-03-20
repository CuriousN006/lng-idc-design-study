from __future__ import annotations

import math

import CoolProp.CoolProp as CP
import pandas as pd

from .thermo import fluid_phase, safe_props


def compute_fluid_screening(config: dict, required_cooling_kw: float) -> dict[str, object]:
    loop = config["coolant_loop"]
    candidates = config["coolant_candidates"]

    total_lng_duty_kw = required_cooling_kw / config["system_targets"]["idc_cooling_utilization_fraction"]
    supply_k = loop["supply_temp_k"]
    after_idc_k = loop["after_idc_temp_k"]
    return_to_lng_k = loop["return_to_lng_temp_k"]
    pressure_pa = loop["pressure_mpa"] * 1_000_000.0

    rows: list[dict[str, object]] = []
    for key, metadata in candidates.items():
        fluid = metadata["coolprop_name"]
        row: dict[str, object] = {"key": key, "fluid": metadata["display_name"], "coolprop_name": fluid}
        try:
            triple_k = float(CP.PropsSI("Ttriple", fluid))
            phase_supply = fluid_phase(supply_k, pressure_pa, fluid)
            phase_return = fluid_phase(return_to_lng_k, pressure_pa, fluid)
            reference_t = 0.5 * (supply_k + return_to_lng_k)
            cp = safe_props("C", temperature_k=reference_t, pressure_pa=pressure_pa, fluid=fluid)
            rho = safe_props("D", temperature_k=reference_t, pressure_pa=pressure_pa, fluid=fluid)
            mu = safe_props("V", temperature_k=reference_t, pressure_pa=pressure_pa, fluid=fluid)
            k_cond = safe_props("L", temperature_k=reference_t, pressure_pa=pressure_pa, fluid=fluid)

            feasible = "liquid" in phase_supply and "liquid" in phase_return and supply_k >= triple_k + 10.0
            if not feasible:
                reason = f"Loop phase incompatible: supply={phase_supply}, return={phase_return}, triple={triple_k:.1f} K"
            else:
                reason = "Feasible single-phase liquid loop"

            delta_t_idc = after_idc_k - supply_k
            mass_flow = total_lng_duty_kw * 1000.0 / max(cp * delta_t_idc, 1.0)
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
    feasible["score"] = (
        1.0
        - 0.45 * feasible["mass_norm"]
        - 0.30 * feasible["vol_norm"]
        - 0.15 * feasible["visc_norm"]
        - feasible["penalty"]
    )
    feasible = feasible.sort_values("score", ascending=False)
    merged = frame.merge(feasible[["key", "score"]], on="key", how="left")
    return {
        "table": merged.sort_values(["feasible", "score"], ascending=[False, False]).reset_index(drop=True),
        "selected": feasible.iloc[0].to_dict(),
        "total_lng_duty_kw": total_lng_duty_kw,
    }
