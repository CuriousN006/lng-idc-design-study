from __future__ import annotations

from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .thermo import ensure_directory


def _dataframe_to_markdown(frame: pd.DataFrame) -> str:
    headers = list(frame.columns)
    divider = ["---"] * len(headers)
    rows = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(divider) + " |",
    ]
    for _, row in frame.iterrows():
        rows.append("| " + " | ".join(str(row[column]) for column in headers) + " |")
    return "\n".join(rows)


def _save_load_breakdown(output_dir: Path, load_result: object) -> None:
    fig, ax = plt.subplots(figsize=(11, 5))
    labels = list(load_result.breakdown_kw.keys())
    values = list(load_result.breakdown_kw.values())
    ax.bar(labels, values, color="#2e6f95")
    ax.set_ylabel("Load (kW)")
    ax.set_title("IDC Cooling Load Breakdown")
    ax.tick_params(axis="x", rotation=45, labelsize=9)
    fig.tight_layout()
    fig.savefig(output_dir / "load_breakdown.png", dpi=180)
    plt.close(fig)


def _save_fluid_ranking(output_dir: Path, ranking: pd.DataFrame) -> None:
    feasible = ranking[ranking["feasible"]].copy()
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(feasible["required_mass_flow_kg_s"], feasible["score"], color="#6b8e23")
    for _, row in feasible.iterrows():
        ax.annotate(row["fluid"], (row["required_mass_flow_kg_s"], row["score"]), fontsize=8)
    ax.set_xlabel("Required coolant mass flow (kg/s)")
    ax.set_ylabel("Composite screening score")
    ax.set_title("Coolant Screening Ranking")
    fig.tight_layout()
    fig.savefig(output_dir / "fluid_ranking.png", dpi=180)
    plt.close(fig)


def _save_baseline_cycle(output_dir: Path, baseline: dict) -> None:
    fig, ax = plt.subplots(figsize=(7, 5))
    points = baseline["cycle_points"]
    ordered = points.set_index("state").loc[[1, 2, 3, 4, 1]].reset_index()
    ax.plot(ordered["enthalpy_kj_per_kg"], ordered["pressure_kpa"], marker="o", color="#8b0000")
    for _, row in points.iterrows():
        ax.annotate(f"{int(row['state'])}", (row["enthalpy_kj_per_kg"], row["pressure_kpa"]), fontsize=9)
    ax.set_xlabel("Enthalpy (kJ/kg)")
    ax.set_ylabel("Pressure (kPa)")
    ax.set_title("Baseline R-134a P-h Cycle")
    ax.set_yscale("log")
    fig.tight_layout()
    fig.savefig(output_dir / "baseline_cycle_ph.png", dpi=180)
    plt.close(fig)


def _save_hx_profile(output_dir: Path, hx_result: dict) -> None:
    cold_bounds = hx_result["cold_boundaries_k"]
    hot_bounds = hx_result["hot_boundaries_k"]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(range(len(cold_bounds)), cold_bounds, marker="o", label="Methane / NG")
    ax.plot(range(len(hot_bounds)), hot_bounds, marker="s", label=hx_result["selected_fluid"])
    ax.set_xticks(range(len(cold_bounds)))
    ax.set_xticklabels([f"B{i}" for i in range(len(cold_bounds))])
    ax.set_ylabel("Temperature (K)")
    ax.set_title("LNG Vaporizer Temperature Profile")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "hx_temperature_profile.png", dpi=180)
    plt.close(fig)


def _save_idc_hx_profile(output_dir: Path, idc_hx_result: dict) -> None:
    profile = idc_hx_result["profile"]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(profile["location"], profile["chilled_water_temp_k"], marker="o", label="Chilled water")
    ax.plot(profile["location"], profile["coolant_temp_k"], marker="s", label=idc_hx_result["fluid"])
    ax.set_ylabel("Temperature (K)")
    ax.set_title("IDC-side Heat Exchanger Temperature Profile")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "idc_hx_temperature_profile.png", dpi=180)
    plt.close(fig)


def _save_hx_geometry_scan(output_dir: Path, hx_result: dict) -> None:
    frame = hx_result["geometry_candidates"]
    feasible = frame[frame["feasible"]]
    fig, ax = plt.subplots(figsize=(8, 5))
    scatter = ax.scatter(feasible["tube_count"], feasible["tube_length_m"], c=feasible["shell_diameter_m"], cmap="plasma")
    ax.set_xlabel("Tube count")
    ax.set_ylabel("Tube length (m)")
    ax.set_title("Feasible LNG Vaporizer Geometry Scan")
    colorbar = fig.colorbar(scatter, ax=ax)
    colorbar.set_label("Shell diameter (m)")
    fig.tight_layout()
    fig.savefig(output_dir / "hx_geometry_scan.png", dpi=180)
    plt.close(fig)


def _save_pipeline_tradeoff(output_dir: Path, pipeline_result: dict) -> None:
    frame = pipeline_result["scan_table"]
    feasible = frame[frame["feasible"]]
    fig, ax = plt.subplots(figsize=(8, 5))
    scatter = ax.scatter(feasible["pump_power_kw"], feasible["heat_gain_fraction"], c=feasible["supply_id_m"], cmap="viridis")
    ax.set_xlabel("Pump power (kW)")
    ax.set_ylabel("Heat gain fraction")
    ax.set_title("Pipeline Trade-off Scan")
    colorbar = fig.colorbar(scatter, ax=ax)
    colorbar.set_label("Supply ID (m)")
    fig.tight_layout()
    fig.savefig(output_dir / "pipeline_tradeoff.png", dpi=180)
    plt.close(fig)


def _save_pipeline_distance_sensitivity(output_dir: Path, pipeline_result: dict) -> None:
    frame = pipeline_result["sensitivity"]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(frame["distance_m"] / 1000.0, frame["pump_power_kw"], marker="o", label="Pump power")
    ax.plot(frame["distance_m"] / 1000.0, frame["heat_gain_kw"], marker="s", label="Heat gain")
    ax.set_xlabel("Distance (km)")
    ax.set_ylabel("kW")
    ax.set_title("Distance Sensitivity")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "pipeline_distance_sensitivity.png", dpi=180)
    plt.close(fig)


def _save_power_comparison(output_dir: Path, baseline: dict, system_eval: dict) -> None:
    fig, ax = plt.subplots(figsize=(7, 5))
    labels = ["Baseline VCC", "LNG loop"]
    values = [baseline["compressor_power_kw"], system_eval["pump_power_kw"]]
    ax.bar(labels, values, color=["#aa4a44", "#3a7ca5"])
    ax.set_ylabel("Power (kW)")
    ax.set_title("Power Demand Comparison")
    fig.tight_layout()
    fig.savefig(output_dir / "system_power_comparison.png", dpi=180)
    plt.close(fig)


def _save_legacy_comparison(output_dir: Path, legacy_result: dict | None) -> None:
    if not legacy_result or not legacy_result.get("available"):
        return
    frame = legacy_result["table"]
    fig, ax = plt.subplots(figsize=(8, 5))
    x = range(len(frame))
    width = 0.35
    ax.bar([i - width / 2 for i in x], frame["legacy_value_kw"], width=width, label="Legacy Excel")
    ax.bar([i + width / 2 for i in x], frame["current_value_kw"], width=width, label="Current Python")
    ax.set_xticks(list(x))
    ax.set_xticklabels(frame["metric"], rotation=10)
    ax.set_ylabel("kW")
    ax.set_title("Legacy Excel vs Current Python")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "legacy_comparison.png", dpi=180)
    plt.close(fig)


def _save_alternative_designs(output_dir: Path, scenario_result: dict) -> None:
    frame = scenario_result["alternatives"]
    feasible = frame[frame["design_feasible"]].copy()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(feasible["fluid"], feasible["pump_power_kw"], color="#4f6d7a")
    ax.set_ylabel("Pump power (kW)")
    ax.set_title("Feasible Coolant Alternatives")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(output_dir / "alternative_designs.png", dpi=180)
    plt.close(fig)


def _save_supply_temperature_sweep(output_dir: Path, supply_temperature_sweep: pd.DataFrame) -> None:
    feasible = supply_temperature_sweep[supply_temperature_sweep["status"] == "feasible"].copy()
    fig, ax1 = plt.subplots(figsize=(9, 5))
    ax1.plot(feasible["supply_temp_c"], feasible["pump_power_kw"], marker="o", color="#8b1e3f", label="Pump power")
    ax1.set_xlabel("Coolant supply temperature (C)")
    ax1.set_ylabel("Pump power (kW)", color="#8b1e3f")
    ax1.tick_params(axis="y", labelcolor="#8b1e3f")

    ax2 = ax1.twinx()
    ax2.plot(feasible["supply_temp_c"], feasible["max_feasible_distance_km"], marker="s", color="#1d7874", label="Max feasible distance")
    ax2.set_ylabel("Max feasible distance (km)", color="#1d7874")
    ax2.tick_params(axis="y", labelcolor="#1d7874")
    ax1.set_title("Supply Temperature Sensitivity")
    fig.tight_layout()
    fig.savefig(output_dir / "supply_temperature_sensitivity.png", dpi=180)
    plt.close(fig)


def _save_annual_impact(output_dir: Path, annual_metrics: dict) -> None:
    labels = ["Electricity use", "Electricity cost", "Indirect emissions"]
    baseline_values = [
        annual_metrics["baseline_energy_mwh_per_year"],
        annual_metrics["baseline_cost_krw_per_year"] / 1_000_000.0,
        annual_metrics["baseline_emissions_tco2_per_year"],
    ]
    lng_values = [
        annual_metrics["lng_energy_mwh_per_year"],
        annual_metrics["lng_cost_krw_per_year"] / 1_000_000.0,
        annual_metrics["lng_emissions_tco2_per_year"],
    ]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for idx, ax in enumerate(axes):
        ax.bar(["Baseline", "LNG"], [baseline_values[idx], lng_values[idx]], color=["#8b0000", "#2e8b57"])
        ax.set_title(labels[idx])
    axes[0].set_ylabel("Annualized value")
    fig.tight_layout()
    fig.savefig(output_dir / "annual_impact_comparison.png", dpi=180)
    plt.close(fig)


def _build_requirement_traceability(system_eval: dict) -> pd.DataFrame:
    source_map = {row["metric"]: row["source_ids"] for _, row in system_eval["summary"].iterrows()}
    return pd.DataFrame(
        [
            {
                "requirement": "IDC total cooling-load calculation",
                "status": "Complete",
                "evidence_metric": "IDC total cooling load",
                "primary_output": "output/summary.csv; output/figures/load_breakdown.png",
                "source_ids": source_map["IDC total cooling load"],
            },
            {
                "requirement": "Theoretical minimum power estimate",
                "status": "Complete",
                "evidence_metric": "Theoretical minimum power",
                "primary_output": "output/summary.csv",
                "source_ids": source_map["Theoretical minimum power"],
            },
            {
                "requirement": "Baseline R-134a cycle benchmark",
                "status": "Complete",
                "evidence_metric": "Baseline R-134a compressor power",
                "primary_output": "output/summary.csv; output/figures/baseline_cycle_ph.png",
                "source_ids": source_map["Baseline R-134a compressor power"],
            },
            {
                "requirement": "Coolant candidate screening and selection",
                "status": "Complete",
                "evidence_metric": "Selected coolant",
                "primary_output": "output/fluid_ranking.csv; output/figures/fluid_ranking.png; output/alternative_designs.csv",
                "source_ids": source_map["Selected coolant"],
            },
            {
                "requirement": "IDC-side interface heat exchanger model",
                "status": "Complete",
                "evidence_metric": "IDC-side HX required area",
                "primary_output": "output/idc_hx_profile.csv; output/figures/idc_hx_temperature_profile.png; output/summary.csv",
                "source_ids": source_map["IDC-side HX required area"],
            },
            {
                "requirement": "Shell-and-tube LNG vaporizer design",
                "status": "Complete",
                "evidence_metric": "LNG vaporizer duty",
                "primary_output": "output/hx_segments.csv; output/hx_geometry_candidates_top100.csv; output/figures/hx_temperature_profile.png",
                "source_ids": source_map["LNG vaporizer duty"],
            },
            {
                "requirement": "10 km coolant pipeline design",
                "status": "Complete",
                "evidence_metric": "LNG system pump power",
                "primary_output": "output/summary.csv; output/pipeline_scan_top200.csv; output/figures/pipeline_tradeoff.png",
                "source_ids": source_map["LNG system pump power"],
            },
            {
                "requirement": "Long-distance pipeline sensitivity (35 km)",
                "status": "Complete",
                "evidence_metric": "Available cooling at IDC",
                "primary_output": "output/distance_scenarios.csv; output/pipeline_sensitivity.csv; output/figures/pipeline_distance_sensitivity.png",
                "source_ids": source_map["Available cooling at IDC"],
            },
            {
                "requirement": "Power-saving assessment versus legacy and baseline",
                "status": "Complete",
                "evidence_metric": "Baseline-to-LNG power saving",
                "primary_output": "output/summary.csv; output/legacy_comparison.csv; output/figures/system_power_comparison.png",
                "source_ids": source_map["Baseline-to-LNG power saving"],
            },
        ]
    )


def write_outputs(
    project_root: Path,
    config_path: Path,
    load_result: object,
    minimum_power: dict,
    baseline: dict,
    screening: dict,
    idc_hx_result: dict,
    hx_result: dict,
    pipeline_result: dict,
    scenario_result: dict,
    distance_scenarios: pd.DataFrame,
    supply_temperature_sweep: pd.DataFrame,
    system_eval: dict,
    validation_messages: list[str],
    legacy_result: dict | None = None,
) -> None:
    output_dir = ensure_directory(project_root / "output")
    figure_dir = ensure_directory(output_dir / "figures")

    system_eval["summary"].to_csv(output_dir / "summary.csv", index=False)
    screening["table"].to_csv(output_dir / "fluid_ranking.csv", index=False)
    system_eval["summary"][["metric", "source_ids"]].to_csv(output_dir / "source_map.csv", index=False)
    baseline["cycle_points"].to_csv(output_dir / "baseline_cycle_points.csv", index=False)
    idc_hx_result["profile"].to_csv(output_dir / "idc_hx_profile.csv", index=False)
    hx_result["segments"].to_csv(output_dir / "hx_segments.csv", index=False)
    hx_result["geometry_candidates"].head(100).to_csv(output_dir / "hx_geometry_candidates_top100.csv", index=False)
    pipeline_result["scan_table"].head(200).to_csv(output_dir / "pipeline_scan_top200.csv", index=False)
    pipeline_result["sensitivity"].to_csv(output_dir / "pipeline_sensitivity.csv", index=False)
    scenario_result["alternatives"].to_csv(output_dir / "alternative_designs.csv", index=False)
    distance_scenarios.to_csv(output_dir / "distance_scenarios.csv", index=False)
    supply_temperature_sweep.to_csv(output_dir / "supply_temperature_sweep.csv", index=False)
    requirement_traceability = _build_requirement_traceability(system_eval)
    requirement_traceability.to_csv(output_dir / "requirement_traceability.csv", index=False)
    annual_summary = pd.DataFrame(
        [
            {"metric": "Baseline electricity use", "value": system_eval["annual"]["baseline_energy_mwh_per_year"], "unit": "MWh/year"},
            {"metric": "LNG electricity use", "value": system_eval["annual"]["lng_energy_mwh_per_year"], "unit": "MWh/year"},
            {"metric": "Electricity saving", "value": system_eval["annual"]["energy_saving_mwh_per_year"], "unit": "MWh/year"},
            {"metric": "Electricity cost saving", "value": system_eval["annual"]["cost_saving_krw_per_year"], "unit": "KRW/year"},
            {"metric": "Avoided indirect emissions", "value": system_eval["annual"]["avoided_emissions_tco2_per_year"], "unit": "tCO2/year"},
        ]
    )
    annual_summary.to_csv(output_dir / "annual_summary.csv", index=False)
    system_eval["annual"]["payback_table"].to_csv(output_dir / "payback_allowable_capex.csv", index=False)
    if legacy_result and legacy_result.get("available"):
        legacy_result["table"].to_csv(output_dir / "legacy_comparison.csv", index=False)

    _save_load_breakdown(figure_dir, load_result)
    _save_fluid_ranking(figure_dir, screening["table"])
    _save_baseline_cycle(figure_dir, baseline)
    _save_idc_hx_profile(figure_dir, idc_hx_result)
    _save_hx_profile(figure_dir, hx_result)
    _save_hx_geometry_scan(figure_dir, hx_result)
    _save_pipeline_tradeoff(figure_dir, pipeline_result)
    _save_pipeline_distance_sensitivity(figure_dir, pipeline_result)
    _save_power_comparison(figure_dir, baseline, system_eval)
    _save_legacy_comparison(figure_dir, legacy_result)
    _save_alternative_designs(figure_dir, scenario_result)
    _save_supply_temperature_sweep(figure_dir, supply_temperature_sweep)
    _save_annual_impact(figure_dir, system_eval["annual"])

    base_distance_index = (distance_scenarios["distance_m"] - float(pipeline_result["base_distance_m"])).abs().idxmin()
    base_distance_row = distance_scenarios.loc[base_distance_index]
    long_distance_row = distance_scenarios.sort_values("distance_m").iloc[-1]
    feasible_supply_sweep = supply_temperature_sweep[supply_temperature_sweep["status"] == "feasible"].sort_values("pump_power_kw")
    best_supply_row = feasible_supply_sweep.iloc[0] if not feasible_supply_sweep.empty else None
    report_lines = [
        "# LNG Cold-Energy IDC Cooling System Summary",
        "",
        f"- Run date: {date.today().isoformat()}",
        f"- Config: `{config_path}`",
        f"- Selected coolant: **{screening['selected']['fluid']}**",
        f"- Total cooling load: **{load_result.total_kw:,.1f} kW**",
        f"- Theoretical minimum power: **{minimum_power['minimum_power_kw']:,.1f} kW**",
        f"- Baseline R-134a power: **{baseline['compressor_power_kw']:,.1f} kW**",
        f"- LNG loop pump power: **{system_eval['pump_power_kw']:,.1f} kW**",
        f"- Baseline-to-LNG saving: **{system_eval['power_saving_kw']:,.1f} kW**",
        f"- Minimum LNG vaporizer pinch: **{hx_result['min_pinch_k']:.2f} K**",
        "",
        "## Key Design Selections",
        "",
        f"- Selected coolant score: **{screening['selected']['score']:.3f}**",
        f"- IDC-side HX required area: **{idc_hx_result['required_area_m2']:,.1f} m2**",
        f"- IDC-side HX minimum pinch: **{idc_hx_result['min_pinch_k']:.2f} K**",
        f"- IDC outlet coolant temperature: **{idc_hx_result['coolant_after_idc_temp_k']:.2f} K**",
        f"- LNG-inlet return temperature: **{hx_result['return_to_lng_temp_k']:.2f} K**",
        f"- LNG vaporizer geometry: **{int(hx_result['selected_geometry']['tube_count'])} tubes x {hx_result['selected_geometry']['tube_length_m']:.1f} m**",
        f"- LNG vaporizer shell diameter: **{hx_result['selected_geometry']['shell_diameter_m']:.3f} m**",
        f"- Pipeline IDs: **supply {pipeline_result['selected_design']['supply_id_m']:.3f} m / return {pipeline_result['selected_design']['return_id_m']:.3f} m**",
        f"- Selected insulation thickness: **{pipeline_result['selected_design']['insulation_thickness_m']:.3f} m**",
        f"- Supplemental warm-up duty: **{pipeline_result['selected_design']['supplemental_warmup_kw']:.1f} kW**",
        "",
        "## Scenario Notes",
        "",
        f"- Base case distance: **{base_distance_row['distance_km']:.1f} km**",
        f"- Long-distance check: **{long_distance_row['distance_km']:.1f} km**",
        f"- Long-distance pump power: **{long_distance_row['pump_power_kw']:,.1f} kW**",
        f"- Long-distance heat gain: **{long_distance_row['heat_gain_kw']:,.1f} kW**",
        f"- Long-distance supplemental warm-up: **{long_distance_row['supplemental_warmup_kw']:,.1f} kW**",
        f"- Long-distance load satisfied: **{bool(long_distance_row['meets_idc_load'])}**",
        f"- Long-distance interpretation: **{'Feasible' if bool(long_distance_row['meets_idc_load']) else 'Infeasible under current duty margin'}**",
        f"- Estimated maximum feasible one-way distance: **{pipeline_result['max_feasible_distance_m'] / 1000.0:,.1f} km**",
        "",
        "## Annual Impact",
        "",
        f"- Annual electricity saving: **{system_eval['annual']['energy_saving_mwh_per_year']:,.1f} MWh/year**",
        f"- Annual electricity cost saving: **{system_eval['annual']['cost_saving_krw_per_year'] / 1_000_000.0:,.1f} million KRW/year**",
        f"- Annual avoided indirect emissions: **{system_eval['annual']['avoided_emissions_tco2_per_year']:,.1f} tCO2/year**",
        f"- Allowable incremental CAPEX at 5-year payback: **{system_eval['annual']['payback_table'].set_index('payback_years').loc[5, 'allowable_incremental_capex_krw'] / 1_000_000.0:,.1f} million KRW**",
        "- Economic boundary: **baseline compressor power vs LNG loop pump power only**",
        "",
        "## Temperature Sensitivity",
        "",
    ]
    if best_supply_row is not None:
        report_lines.extend(
            [
                f"- Best sweep point by pump power: **{best_supply_row['supply_temp_c']:.1f} C** with **{best_supply_row['selected_fluid']}**",
                f"- Pump power at best sweep point: **{best_supply_row['pump_power_kw']:,.1f} kW**",
                f"- Estimated max feasible distance at best sweep point: **{best_supply_row['max_feasible_distance_km']:,.1f} km**",
            ]
        )
    else:
        report_lines.append("- No feasible supply-temperature sweep point was found in the configured range.")
    report_lines.extend(
        [
        "",
        "## Alternative Coolants",
        "",
        ]
    )
    for _, row in scenario_result["alternatives"].iterrows():
        report_lines.append(
            f"- {row['fluid']}: pump **{row['pump_power_kw']:,.1f} kW**, warm-up **{row.get('supplemental_warmup_kw', 0.0):,.1f} kW**, shell **{row['hx_shell_diameter_m']:.3f} m**, feasible design **{bool(row['design_feasible'])}**"
        )
    if legacy_result and legacy_result.get("available"):
        report_lines.extend(
            [
                "",
                "## Legacy Comparison",
                "",
                f"- Legacy workbook: `{legacy_result['path']}`",
                f"- Legacy minimum power: **{legacy_result['legacy_wmin_kw']:,.1f} kW**",
                f"- Legacy baseline compressor power: **{legacy_result['legacy_baseline_power_kw']:,.1f} kW**",
                "",
            ]
        )
    report_lines.extend(
        [
            "## Validation",
            "",
        ]
    )
    report_lines.extend([f"- {message}" for message in validation_messages])
    report_lines.extend(
        [
            "",
            "## Generated Files",
            "",
            "- `output/summary.csv`",
            "- `output/fluid_ranking.csv`",
            "- `output/alternative_designs.csv`",
            "- `output/distance_scenarios.csv`",
            "- `output/supply_temperature_sweep.csv`",
            "- `output/annual_summary.csv`",
            "- `output/payback_allowable_capex.csv`",
            "- `output/requirement_traceability.csv`",
            "- `output/source_map.csv`",
            "- `output/idc_hx_profile.csv`",
            "- `output/hx_segments.csv`",
            "- `output/pipeline_sensitivity.csv`",
            "- `output/figures/*.png`",
            "",
            "## Requirement Traceability",
            "",
        ]
    )
    for _, row in requirement_traceability.iterrows():
        report_lines.append(f"- {row['requirement']}: {row['status']} ({row['primary_output']})")
    report_lines.extend(
        [
            "",
            "## Source Appendix",
            "",
        ]
    )
    for _, row in system_eval["summary"].iterrows():
        report_lines.append(f"- {row['metric']}: {row['source_ids']}")
    (output_dir / "report_summary.md").write_text("\n".join(report_lines), encoding="utf-8")
    (output_dir / "requirement_traceability.md").write_text(_dataframe_to_markdown(requirement_traceability), encoding="utf-8")
