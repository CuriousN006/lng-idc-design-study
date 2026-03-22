from __future__ import annotations

import math

import pandas as pd

from .hx_lng_vaporizer import design_lng_vaporizer
from .scenario_study import _merge_fluid_with_pipeline


def evaluate_lng_transport_sensitivity(
    config: dict,
    screening: dict,
    pipeline_result: dict,
) -> dict[str, object]:
    sensitivity_cfg = config.get("lng_transport_sensitivity", {})
    proxy_options = list(sensitivity_cfg.get("proxy_options", []))
    if not proxy_options:
        raise RuntimeError("No LNG transport sensitivity proxy options were configured.")

    required_lng_duty_kw = float(pipeline_result["selected_design"]["actual_lng_duty_kw"])
    merged_fluid = _merge_fluid_with_pipeline(screening["selected"], pipeline_result)
    reference_proxy = str(config.get("lng_mixture", {}).get("transport_property_proxy", "Methane"))

    rows: list[dict[str, object]] = []
    for proxy_option in proxy_options:
        proxy_key = str(proxy_option)
        try:
            hx_result = design_lng_vaporizer(
                config,
                merged_fluid,
                required_lng_duty_kw,
                transport_property_proxy_override=proxy_key,
            )
            selected_geometry = hx_result["selected_geometry"]
            rows.append(
                {
                    "proxy_key": proxy_key,
                    "proxy_label": str(hx_result["lng_transport_label"]),
                    "status": "feasible",
                    "tube_count": int(selected_geometry["tube_count"]),
                    "tube_length_m": float(selected_geometry["tube_length_m"]),
                    "shell_diameter_m": float(selected_geometry["shell_diameter_m"]),
                    "required_area_m2": float(selected_geometry["required_area_m2"]),
                    "provided_area_m2": float(selected_geometry["provided_area_m2"]),
                    "tube_pressure_drop_kpa": float(selected_geometry["tube_pressure_drop_kpa"]),
                    "shell_pressure_drop_kpa": float(selected_geometry["shell_pressure_drop_kpa"]),
                    "min_pinch_k": float(hx_result["min_pinch_k"]),
                    "failure_reason": "",
                    "is_reference": proxy_key == reference_proxy,
                }
            )
        except Exception as exc:  # pragma: no cover - dependent on CoolProp mixture support
            rows.append(
                {
                    "proxy_key": proxy_key,
                    "proxy_label": proxy_key,
                    "status": "failed",
                    "tube_count": math.nan,
                    "tube_length_m": math.nan,
                    "shell_diameter_m": math.nan,
                    "required_area_m2": math.nan,
                    "provided_area_m2": math.nan,
                    "tube_pressure_drop_kpa": math.nan,
                    "shell_pressure_drop_kpa": math.nan,
                    "min_pinch_k": math.nan,
                    "failure_reason": str(exc),
                    "is_reference": proxy_key == reference_proxy,
                }
            )

    table = pd.DataFrame(rows)
    reference_rows = table[(table["status"] == "feasible") & (table["proxy_key"] == reference_proxy)]
    reference = reference_rows.iloc[0].to_dict() if not reference_rows.empty else None

    if reference is not None:
        for column in ["required_area_m2", "tube_pressure_drop_kpa", "shell_pressure_drop_kpa"]:
            baseline = float(reference[column])
            if abs(baseline) < 1e-12:
                table[f"{column}_delta_pct"] = math.nan
            else:
                table[f"{column}_delta_pct"] = (table[column] - baseline) / baseline * 100.0
    else:
        for column in ["required_area_m2", "tube_pressure_drop_kpa", "shell_pressure_drop_kpa"]:
            table[f"{column}_delta_pct"] = math.nan

    feasible = table[table["status"] == "feasible"].copy()
    selected = None
    if not feasible.empty:
        selected = feasible.sort_values(
            ["required_area_m2", "tube_pressure_drop_kpa", "shell_pressure_drop_kpa"],
            ascending=[True, True, True],
        ).iloc[0].to_dict()

    return {
        "table": table.sort_values(["status", "required_area_m2", "proxy_label"], ascending=[True, True, True]).reset_index(drop=True),
        "reference": reference,
        "selected": selected,
    }
