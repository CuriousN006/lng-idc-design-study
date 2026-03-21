from __future__ import annotations

import pandas as pd

from .economics import compute_annual_metrics


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
