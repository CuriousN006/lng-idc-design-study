from __future__ import annotations

import pandas as pd

from .economics import compute_annual_metrics, compute_financial_metrics


def evaluate_auxiliary_heat_sources(
    config: dict,
    baseline_power_kw: float,
    pipeline_result: dict,
    core_system_power_kw: float,
) -> dict[str, object]:
    selected_design = pipeline_result["selected_design"]
    supplemental_warmup_kw = float(selected_design.get("supplemental_warmup_kw", 0.0))
    source_config = config.get("auxiliary_heat_sources", {})

    rows: list[dict[str, object]] = []
    for key, metadata in source_config.items():
        electric_intensity = float(metadata["electric_intensity_kw_per_kwth"])
        fixed_parasitic_kw = float(metadata.get("fixed_parasitic_kw", 0.0))
        auxiliary_power_kw = supplemental_warmup_kw * electric_intensity + fixed_parasitic_kw
        total_system_power_kw = core_system_power_kw + auxiliary_power_kw
        annual_metrics = compute_annual_metrics(config, baseline_power_kw, total_system_power_kw)
        rows.append(
            {
                "scenario_key": key,
                "scenario_label": str(metadata.get("label", key)),
                "description": str(metadata.get("description", "")),
                "electric_intensity_kw_per_kwth": electric_intensity,
                "fixed_parasitic_kw": fixed_parasitic_kw,
                "supplemental_warmup_kw": supplemental_warmup_kw,
                "auxiliary_power_kw": auxiliary_power_kw,
                "core_system_power_kw": core_system_power_kw,
                "total_system_power_kw": total_system_power_kw,
                "net_power_saving_kw": baseline_power_kw - total_system_power_kw,
                "annual_energy_saving_mwh_per_year": annual_metrics["energy_saving_mwh_per_year"],
                "annual_cost_saving_krw_per_year": annual_metrics["cost_saving_krw_per_year"],
                "annual_avoided_emissions_tco2_per_year": annual_metrics["avoided_emissions_tco2_per_year"],
            }
        )

    table = pd.DataFrame(rows).sort_values(
        ["net_power_saving_kw", "annual_cost_saving_krw_per_year"],
        ascending=[False, False],
    ).reset_index(drop=True)

    return {
        "table": table,
        "selected": table.iloc[0].to_dict() if not table.empty else None,
    }


def add_auxiliary_economics(
    config: dict,
    auxiliary_heat_sources: dict[str, object],
    core_capex_krw: float,
) -> dict[str, object]:
    table = auxiliary_heat_sources["table"].copy()
    if table.empty:
        return {
            "table": table,
            "selected": None,
            "selected_financial": None,
        }

    source_config = config.get("auxiliary_heat_sources", {})
    financial_cfg = config["economic_inputs"]["financial"]
    core_om_fraction = float(financial_cfg["annual_om_fraction_of_capex"])
    core_annual_om_cost_krw = core_capex_krw * core_om_fraction

    rows: list[dict[str, object]] = []
    for _, row in table.iterrows():
        metadata = source_config[str(row["scenario_key"])]
        auxiliary_capex_krw = (
            float(metadata["capex_fixed_krw"])
            + float(metadata["capex_variable_krw_per_kwth"]) * float(row["supplemental_warmup_kw"])
        )
        auxiliary_om_fraction = float(metadata["annual_om_fraction_of_aux_capex"])
        auxiliary_annual_om_cost_krw = auxiliary_capex_krw * auxiliary_om_fraction
        total_installed_capex_krw = core_capex_krw + auxiliary_capex_krw
        total_annual_om_cost_krw = core_annual_om_cost_krw + auxiliary_annual_om_cost_krw
        financial_metrics = compute_financial_metrics(
            config,
            total_installed_capex_krw,
            float(row["annual_cost_saving_krw_per_year"]),
            annual_om_cost_krw_override=total_annual_om_cost_krw,
        )
        enriched = row.to_dict()
        enriched.update(
            {
                "core_capex_krw": core_capex_krw,
                "auxiliary_capex_krw": auxiliary_capex_krw,
                "total_installed_capex_krw": total_installed_capex_krw,
                "core_annual_om_cost_krw": core_annual_om_cost_krw,
                "auxiliary_annual_om_cost_krw": auxiliary_annual_om_cost_krw,
                "total_annual_om_cost_krw": total_annual_om_cost_krw,
                "npv_krw": financial_metrics["npv_krw"],
                "irr_fraction": financial_metrics["irr_fraction"],
                "discounted_payback_years": financial_metrics["discounted_payback_years"],
                "simple_payback_years": financial_metrics["simple_payback_years"],
                "source_ids": str(metadata.get("source_ids", "")),
            }
        )
        rows.append(enriched)

    enriched_table = pd.DataFrame(rows).sort_values(
        ["net_power_saving_kw", "annual_cost_saving_krw_per_year"],
        ascending=[False, False],
    ).reset_index(drop=True)
    financial_table = enriched_table.sort_values(
        ["npv_krw", "annual_cost_saving_krw_per_year"],
        ascending=[False, False],
    ).reset_index(drop=True)
    return {
        "table": enriched_table,
        "selected": enriched_table.iloc[0].to_dict() if not enriched_table.empty else None,
        "selected_financial": financial_table.iloc[0].to_dict() if not financial_table.empty else None,
    }
