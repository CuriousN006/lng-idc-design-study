from __future__ import annotations

import pandas as pd

from .auxiliary_heat import add_auxiliary_economics, evaluate_auxiliary_heat_sources
from .capex import estimate_capex
from .economics import compute_annual_metrics, compute_financial_metrics


def evaluate_system(
    config: dict,
    load_result: object,
    minimum_power: dict,
    baseline: dict,
    screening: dict,
    idc_hx_result: dict,
    hx_result: dict,
    pipeline_result: dict,
    idc_secondary_loop_result: dict,
    legacy_result: dict | None = None,
) -> dict[str, object]:
    pipeline = pipeline_result["selected_design"]
    q_load_kw = load_result.total_kw
    q_lng_kw = hx_result["required_lng_duty_kw"]
    q_env_kw = pipeline["heat_gain_kw"]
    q_supplemental_kw = float(pipeline.get("supplemental_warmup_kw", 0.0))
    idc_after_k = float(hx_result["after_idc_temp_k"])
    return_to_lng_k = float(hx_result["return_to_lng_temp_k"])
    idc_hx_area_m2 = float(screening["selected"]["idc_hx_area_m2"])
    idc_hx_min_pinch_k = float(screening["selected"]["idc_hx_min_pinch_k"])
    available_to_idc_kw = q_lng_kw - q_env_kw - q_supplemental_kw
    lng_loop_pump_kw = float(pipeline["pump_power_kw"])
    idc_secondary_pump_kw = float(idc_secondary_loop_result["selected_design"]["pump_power_kw"])
    core_system_power_kw = lng_loop_pump_kw + idc_secondary_pump_kw
    equivalent_cop = q_load_kw / core_system_power_kw
    power_saving_kw = baseline["compressor_power_kw"] - core_system_power_kw
    annual_metrics = compute_annual_metrics(config, baseline["compressor_power_kw"], core_system_power_kw)
    auxiliary_heat_sources = evaluate_auxiliary_heat_sources(
        config,
        baseline["compressor_power_kw"],
        pipeline_result,
        core_system_power_kw,
    )
    capex = estimate_capex(config, idc_hx_result, hx_result, pipeline_result, idc_secondary_loop_result)
    auxiliary_heat_sources = add_auxiliary_economics(config, auxiliary_heat_sources, capex["total_capex_krw"])
    financial_core = compute_financial_metrics(config, capex["total_capex_krw"], annual_metrics["cost_saving_krw_per_year"])
    best_hybrid = auxiliary_heat_sources["selected"]
    best_financial_hybrid = auxiliary_heat_sources["selected_financial"]
    financial_best_hybrid = (
        {
            "annual_om_cost_krw_per_year": float(best_financial_hybrid["total_annual_om_cost_krw"]),
            "net_annual_cashflow_krw_per_year": float(best_financial_hybrid["annual_cost_saving_krw_per_year"]) - float(best_financial_hybrid["total_annual_om_cost_krw"]),
            "simple_payback_years": float(best_financial_hybrid["simple_payback_years"]),
            "discounted_payback_years": float(best_financial_hybrid["discounted_payback_years"]),
            "npv_krw": float(best_financial_hybrid["npv_krw"]),
            "irr_fraction": float(best_financial_hybrid["irr_fraction"]),
        }
        if best_financial_hybrid is not None
        else compute_financial_metrics(config, capex["total_capex_krw"], annual_metrics["cost_saving_krw_per_year"])
    )

    rows = [
            {"metric": "IDC total cooling load", "value": q_load_kw, "unit": "kW", "source_ids": "SRC-001,ASM-001,ASM-003,ASM-004,ASM-005,ASM-006,ASM-007,ASM-008,ASM-009,ASM-010,ASM-011"},
            {"metric": "Theoretical minimum power", "value": minimum_power["minimum_power_kw"], "unit": "kW", "source_ids": "SRC-001"},
            {"metric": "Baseline R-134a compressor power", "value": baseline["compressor_power_kw"], "unit": "kW", "source_ids": "SRC-001,SRC-004,SRC-005"},
            {"metric": "Selected coolant", "value": screening["selected"]["fluid"], "unit": "-", "source_ids": "SRC-001,SRC-003,SRC-005,SRC-008,ASM-017,ASM-018,ASM-033,ASM-034,ASM-035"},
            {"metric": "LNG stream model", "value": hx_result["lng_mixture_label"], "unit": "-", "source_ids": "SRC-019,SRC-020,ASM-055,ASM-056,ASM-069"},
            {"metric": "IDC coolant outlet temperature", "value": idc_after_k, "unit": "K", "source_ids": "SRC-001,ASM-035"},
            {"metric": "IDC loop return temperature at LNG inlet", "value": return_to_lng_k, "unit": "K", "source_ids": "SRC-001,SRC-005,ASM-035"},
            {"metric": "IDC-side HX required area", "value": idc_hx_area_m2, "unit": "m2", "source_ids": "SRC-001,ASM-033,ASM-034,ASM-035"},
            {"metric": "IDC-side HX minimum pinch", "value": idc_hx_min_pinch_k, "unit": "K", "source_ids": "SRC-001,ASM-035"},
            {"metric": "LNG vaporizer duty", "value": q_lng_kw, "unit": "kW", "source_ids": "SRC-001,SRC-004,SRC-005,SRC-006,SRC-007"},
            {"metric": "Pipeline heat gain", "value": q_env_kw, "unit": "kW", "source_ids": "SRC-001,ASM-014,ASM-015,ASM-016"},
            {"metric": "Supplemental warm-up duty", "value": q_supplemental_kw, "unit": "kW", "source_ids": "SRC-001,SRC-005,ASM-035"},
            {"metric": "IDC secondary-loop pump power", "value": idc_secondary_pump_kw, "unit": "kW", "source_ids": "SRC-001,ASM-061,ASM-062,ASM-063,ASM-064,ASM-065"},
            {"metric": "IDC secondary-loop selected diameter", "value": float(idc_secondary_loop_result["selected_design"]["diameter_m"]), "unit": "m", "source_ids": "SRC-001,ASM-061,ASM-062,ASM-063,ASM-064,ASM-065"},
            {"metric": "IDC secondary-loop total pressure drop", "value": float(idc_secondary_loop_result["selected_design"]["total_pressure_drop_kpa"]), "unit": "kPa", "source_ids": "SRC-001,ASM-061,ASM-062,ASM-063,ASM-064,ASM-065"},
            {
                "metric": "Best-case hybrid auxiliary source",
                "value": auxiliary_heat_sources["selected"]["scenario_label"] if auxiliary_heat_sources["selected"] else "-",
                "unit": "-",
                "source_ids": "ASM-043,ASM-044,ASM-045,ASM-046",
            },
            {
                "metric": "Best-financial hybrid auxiliary source",
                "value": auxiliary_heat_sources["selected_financial"]["scenario_label"] if auxiliary_heat_sources["selected_financial"] else "-",
                "unit": "-",
                "source_ids": "ASM-043,ASM-044,ASM-045,ASM-046,ASM-070,ASM-071,ASM-072,ASM-073,ASM-074,ASM-075,ASM-076,ASM-077",
            },
            {
                "metric": "Best-case hybrid total power",
                "value": auxiliary_heat_sources["selected"]["total_system_power_kw"] if auxiliary_heat_sources["selected"] else core_system_power_kw,
                "unit": "kW",
                "source_ids": "SRC-001,SRC-013,ASM-032,ASM-043,ASM-044,ASM-045,ASM-046,ASM-061,ASM-062,ASM-063,ASM-064,ASM-065",
            },
            {
                "metric": "Best-case hybrid installed CAPEX",
                "value": auxiliary_heat_sources["selected"]["total_installed_capex_krw"] if auxiliary_heat_sources["selected"] else capex["total_capex_krw"],
                "unit": "KRW",
                "source_ids": "SRC-021,SRC-022,SRC-023,SRC-024,SRC-025,ASM-057,ASM-058,ASM-059,ASM-060,ASM-070,ASM-071,ASM-072,ASM-073",
            },
            {
                "metric": "Best-financial hybrid NPV",
                "value": auxiliary_heat_sources["selected_financial"]["npv_krw"] if auxiliary_heat_sources["selected_financial"] else financial_core["npv_krw"],
                "unit": "KRW",
                "source_ids": "SRC-013,ASM-066,ASM-067,ASM-068,SRC-021,SRC-022,SRC-023,SRC-024,SRC-025,ASM-057,ASM-058,ASM-059,ASM-060,ASM-070,ASM-071,ASM-072,ASM-073,ASM-074,ASM-075,ASM-076,ASM-077",
            },
            {"metric": "Available cooling at IDC", "value": available_to_idc_kw, "unit": "kW", "source_ids": "SRC-001,SRC-005,ASM-014,ASM-015,ASM-016,ASM-035"},
            {"metric": "LNG system pump power", "value": lng_loop_pump_kw, "unit": "kW", "source_ids": "SRC-001,ASM-014,ASM-015,ASM-016"},
            {"metric": "Core LNG system power", "value": core_system_power_kw, "unit": "kW", "source_ids": "SRC-001,ASM-014,ASM-015,ASM-016,ASM-061,ASM-062,ASM-063,ASM-064,ASM-065"},
            {"metric": "Equivalent cooling COP", "value": equivalent_cop, "unit": "-", "source_ids": "SRC-001,SRC-004,SRC-005"},
            {"metric": "Baseline-to-LNG power saving", "value": power_saving_kw, "unit": "kW", "source_ids": "SRC-001,SRC-004,SRC-005"},
            {"metric": "Annual baseline electricity use", "value": annual_metrics["baseline_energy_mwh_per_year"], "unit": "MWh/year", "source_ids": "SRC-013,ASM-030"},
            {"metric": "Annual LNG electricity use", "value": annual_metrics["lng_energy_mwh_per_year"], "unit": "MWh/year", "source_ids": "SRC-013,ASM-030,ASM-061,ASM-062,ASM-063,ASM-064,ASM-065"},
            {"metric": "Annual electricity saving", "value": annual_metrics["energy_saving_mwh_per_year"], "unit": "MWh/year", "source_ids": "SRC-013,ASM-030,ASM-061,ASM-062,ASM-063,ASM-064,ASM-065"},
            {"metric": "Annual electricity cost saving", "value": annual_metrics["cost_saving_krw_per_year"], "unit": "KRW/year", "source_ids": "SRC-013,ASM-030,ASM-061,ASM-062,ASM-063,ASM-064,ASM-065"},
            {"metric": "Annual avoided indirect emissions", "value": annual_metrics["avoided_emissions_tco2_per_year"], "unit": "tCO2/year", "source_ids": "SRC-013,SRC-014,ASM-030,ASM-061,ASM-062,ASM-063,ASM-064,ASM-065"},
            {"metric": "Core installed CAPEX", "value": capex["total_capex_krw"], "unit": "KRW", "source_ids": "SRC-021,SRC-022,SRC-023,SRC-024,SRC-025,ASM-057,ASM-058,ASM-059,ASM-060"},
            {"metric": "Core annual O&M", "value": financial_core["annual_om_cost_krw_per_year"], "unit": "KRW/year", "source_ids": "ASM-066,ASM-067,ASM-068"},
            {"metric": "Core-system NPV", "value": financial_core["npv_krw"], "unit": "KRW", "source_ids": "SRC-013,ASM-066,ASM-067,ASM-068,SRC-021,SRC-022,SRC-023,SRC-024,SRC-025,ASM-057,ASM-058,ASM-059,ASM-060"},
            {"metric": "Core-system IRR", "value": financial_core["irr_fraction"], "unit": "-", "source_ids": "SRC-013,ASM-066,ASM-067,ASM-068,SRC-021,SRC-022,SRC-023,SRC-024,SRC-025,ASM-057,ASM-058,ASM-059,ASM-060"},
            {"metric": "Core-system discounted payback", "value": financial_core["discounted_payback_years"], "unit": "years", "source_ids": "SRC-013,ASM-066,ASM-067,ASM-068,SRC-021,SRC-022,SRC-023,SRC-024,SRC-025,ASM-057,ASM-058,ASM-059,ASM-060"},
        ]
    for _, row in annual_metrics["payback_table"].iterrows():
        rows.append(
            {
                "metric": f"Allowable incremental CAPEX at {int(row['payback_years'])}-year payback",
                "value": row["allowable_incremental_capex_krw"],
                "unit": "KRW",
                "source_ids": "SRC-013,ASM-030,ASM-031,ASM-061,ASM-062,ASM-063,ASM-064,ASM-065",
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
        "pump_power_kw": core_system_power_kw,
        "equivalent_cop": equivalent_cop,
        "power_saving_kw": power_saving_kw,
        "annual": annual_metrics,
        "auxiliary_heat_sources": auxiliary_heat_sources,
        "capex": capex,
        "financial_core": financial_core,
        "financial_best_hybrid": financial_best_hybrid,
        "best_financial_hybrid": best_financial_hybrid,
        "core_system_power_kw": core_system_power_kw,
        "lng_loop_pump_kw": lng_loop_pump_kw,
        "idc_secondary_pump_kw": idc_secondary_pump_kw,
    }
