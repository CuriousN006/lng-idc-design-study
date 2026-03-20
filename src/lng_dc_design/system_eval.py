from __future__ import annotations

import pandas as pd

from .economics import compute_annual_metrics


def evaluate_system(
    config: dict,
    load_result: object,
    minimum_power: dict,
    baseline: dict,
    screening: dict,
    hx_result: dict,
    pipeline_result: dict,
    legacy_result: dict | None = None,
) -> dict[str, object]:
    pipeline = pipeline_result["selected_design"]
    q_load_kw = load_result.total_kw
    q_lng_kw = hx_result["required_lng_duty_kw"]
    q_env_kw = pipeline["heat_gain_kw"]
    available_to_idc_kw = q_lng_kw - q_env_kw
    pump_kw = pipeline["pump_power_kw"]
    equivalent_cop = q_load_kw / pump_kw
    power_saving_kw = baseline["compressor_power_kw"] - pump_kw
    annual_metrics = compute_annual_metrics(config, baseline["compressor_power_kw"], pump_kw)

    rows = [
            {"metric": "IDC total cooling load", "value": q_load_kw, "unit": "kW", "source_ids": "SRC-001,ASM-001,ASM-003,ASM-004,ASM-005,ASM-006,ASM-007,ASM-008,ASM-009,ASM-010,ASM-011"},
            {"metric": "Theoretical minimum power", "value": minimum_power["minimum_power_kw"], "unit": "kW", "source_ids": "SRC-001"},
            {"metric": "Baseline R-134a compressor power", "value": baseline["compressor_power_kw"], "unit": "kW", "source_ids": "SRC-001,SRC-004,SRC-005"},
            {"metric": "Selected coolant", "value": screening["selected"]["fluid"], "unit": "-", "source_ids": "SRC-003,SRC-008,ASM-017,ASM-018,ASM-019"},
            {"metric": "LNG vaporizer duty", "value": q_lng_kw, "unit": "kW", "source_ids": "SRC-001,SRC-004,SRC-005,SRC-006,SRC-007"},
            {"metric": "Pipeline heat gain", "value": q_env_kw, "unit": "kW", "source_ids": "SRC-001,ASM-014,ASM-015,ASM-016"},
            {"metric": "Available cooling at IDC", "value": available_to_idc_kw, "unit": "kW", "source_ids": "SRC-001,ASM-014,ASM-015,ASM-016"},
            {"metric": "LNG system pump power", "value": pump_kw, "unit": "kW", "source_ids": "SRC-001,ASM-014,ASM-015,ASM-016"},
            {"metric": "Equivalent cooling COP", "value": equivalent_cop, "unit": "-", "source_ids": "SRC-001,SRC-004,SRC-005"},
            {"metric": "Baseline-to-LNG power saving", "value": power_saving_kw, "unit": "kW", "source_ids": "SRC-001,SRC-004,SRC-005"},
            {"metric": "Annual baseline electricity use", "value": annual_metrics["baseline_energy_mwh_per_year"], "unit": "MWh/year", "source_ids": "SRC-013,ASM-030,ASM-032"},
            {"metric": "Annual LNG electricity use", "value": annual_metrics["lng_energy_mwh_per_year"], "unit": "MWh/year", "source_ids": "SRC-013,ASM-030,ASM-032"},
            {"metric": "Annual electricity saving", "value": annual_metrics["energy_saving_mwh_per_year"], "unit": "MWh/year", "source_ids": "SRC-013,ASM-030,ASM-032"},
            {"metric": "Annual electricity cost saving", "value": annual_metrics["cost_saving_krw_per_year"], "unit": "KRW/year", "source_ids": "SRC-013,ASM-030,ASM-032"},
            {"metric": "Annual avoided indirect emissions", "value": annual_metrics["avoided_emissions_tco2_per_year"], "unit": "tCO2/year", "source_ids": "SRC-013,SRC-014,ASM-030,ASM-032"},
        ]
    for _, row in annual_metrics["payback_table"].iterrows():
        rows.append(
            {
                "metric": f"Allowable incremental CAPEX at {int(row['payback_years'])}-year payback",
                "value": row["allowable_incremental_capex_krw"],
                "unit": "KRW",
                "source_ids": "SRC-013,ASM-030,ASM-031,ASM-032",
            }
        )
    if legacy_result and legacy_result.get("available"):
        rows.extend(
            [
                {"metric": "Legacy Excel theoretical minimum power", "value": legacy_result["legacy_wmin_kw"], "unit": "kW", "source_ids": "SRC-010"},
                {"metric": "Legacy Excel baseline compressor power", "value": legacy_result["legacy_baseline_power_kw"], "unit": "kW", "source_ids": "SRC-010"},
                {
                    "metric": "Current vs legacy baseline power delta",
                    "value": baseline["compressor_power_kw"] - legacy_result["legacy_baseline_power_kw"],
                    "unit": "kW",
                    "source_ids": "SRC-001,SRC-004,SRC-005,SRC-010",
                },
            ]
        )
    summary = pd.DataFrame(rows)
    return {
        "summary": summary,
        "available_to_idc_kw": available_to_idc_kw,
        "pump_power_kw": pump_kw,
        "equivalent_cop": equivalent_cop,
        "power_saving_kw": power_saving_kw,
        "annual": annual_metrics,
    }
