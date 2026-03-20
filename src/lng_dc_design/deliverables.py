from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pandas as pd

from .thermo import ensure_directory


def _summary_map(output_dir: Path) -> dict[str, dict[str, str]]:
    frame = pd.read_csv(output_dir / "summary.csv")
    return {
        str(row["metric"]): {
            "value": row["value"],
            "unit": row["unit"],
            "source_ids": row["source_ids"],
        }
        for _, row in frame.iterrows()
    }


def _format_number(value: float, digits: int = 1) -> str:
    if pd.isna(value):
        return "-"
    return f"{float(value):,.{digits}f}"


def _parse_sources(sources_path: Path) -> dict[str, dict[str, str]]:
    entries: dict[str, dict[str, str]] = {}
    for line in sources_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| SRC-"):
            continue
        parts = [part.strip() for part in line.strip().split("|")[1:-1]]
        if len(parts) < 6:
            continue
        entries[parts[0]] = {
            "title": parts[1],
            "link_or_path": parts[2],
            "type": parts[3],
            "used_values": parts[4],
            "used_in": parts[5],
        }
    return entries


def _markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows = [header, divider]
    for _, row in frame[columns].iterrows():
        rows.append("| " + " | ".join(str(row[column]) for column in columns) + " |")
    return "\n".join(rows)


def build_report(project_root: Path) -> Path:
    output_dir = project_root / "output"
    deliverables_dir = ensure_directory(project_root / "deliverables")
    summary = _summary_map(output_dir)
    alternatives = pd.read_csv(output_dir / "alternative_designs.csv")
    distance = pd.read_csv(output_dir / "distance_scenarios.csv")
    temperature = pd.read_csv(output_dir / "supply_temperature_sweep.csv")
    annual = pd.read_csv(output_dir / "annual_summary.csv")
    payback = pd.read_csv(output_dir / "payback_allowable_capex.csv")
    legacy = pd.read_csv(output_dir / "legacy_comparison.csv")
    sources = _parse_sources(project_root / "docs" / "sources.md")

    selected_alternative = alternatives.iloc[0]
    long_distance = distance.sort_values("distance_km").iloc[-1]
    best_temp = temperature[temperature["status"] == "feasible"].sort_values("pump_power_kw").iloc[0]
    annual_report = annual.copy()
    annual_report["value"] = annual_report.apply(
        lambda row: _format_number(float(row["value"]) / 1_000_000.0)
        if row["metric"] == "Electricity cost saving"
        else _format_number(float(row["value"])),
        axis=1,
    )

    report_path = deliverables_dir / "report_draft.md"
    report_lines = [
        "# LNG Cold-Energy Based IDC Cooling System Design Study",
        "",
        "## Abstract",
        "",
        (
            "This report reconstructs the 2022 thermal system design project as a reproducible Python-based study for a "
            "large-scale internet data center cooled by LNG cold energy. The final design delivers a modeled cooling load of "
            f"**{_format_number(float(summary['IDC total cooling load']['value']))} kW** while reducing the reference "
            f"R-134a compressor power requirement from **{_format_number(float(summary['Baseline R-134a compressor power']['value']))} kW** "
            f"to an LNG loop pumping demand of **{_format_number(float(summary['LNG system pump power']['value']))} kW**. "
            f"The selected coolant is **{summary['Selected coolant']['value']}**, the LNG vaporizer pinch constraint is "
            f"held at **10.0 K**, and the estimated annual electricity saving is "
            f"**{_format_number(float(summary['Annual electricity saving']['value']))} MWh/year**."
        ),
        "",
        "## 1. Problem Definition",
        "",
        "The project objective is to use LNG cold energy to replace a conventional mechanical cooling load in a data center while satisfying the original assignment constraints on room conditions, chilled-water conditions, vaporizer duty, and pipeline distance.",
        "",
        "Key questions addressed in this study are:",
        "",
        "- What is the total cooling load of the target IDC?",
        "- What is the theoretical lower bound on power consumption?",
        "- How does a conventional R-134a reference cycle compare with an LNG-assisted system?",
        "- Which coolant is most suitable for the LNG-to-IDC secondary loop?",
        "- Is the system still feasible when the transport distance increases from 10 km to 35 km?",
        "- What are the annual energy, cost, and carbon implications?",
        "",
        "## 2. Design Basis",
        "",
        "- Assignment-derived design basis is recorded in [base.toml](../config/base.toml).",
        "- Full source registry is recorded in [sources.md](../docs/sources.md).",
        "- Engineering assumptions are recorded in [assumptions.md](../docs/assumptions.md).",
        "",
        "Core basis values:",
        "",
        f"- IDC total cooling load: **{_format_number(float(summary['IDC total cooling load']['value']))} kW**",
        f"- LNG / NG duty requirement: **{_format_number(float(summary['LNG vaporizer duty']['value']))} kW**",
        f"- Baseline R-134a compressor power: **{_format_number(float(summary['Baseline R-134a compressor power']['value']))} kW**",
        f"- Selected coolant: **{summary['Selected coolant']['value']}**",
        "",
        "## 3. Modeling Approach",
        "",
        "The codebase separates the project into load calculation, theoretical minimum power, baseline vapor-compression benchmarking, coolant screening, LNG vaporizer design, long-distance pipeline design, sensitivity studies, and annualized impact analysis.",
        "",
        "Main analysis outputs are generated by the following figures:",
        "",
        "![Load Breakdown](../output/figures/load_breakdown.png)",
        "",
        "![Baseline Cycle](../output/figures/baseline_cycle_ph.png)",
        "",
        "![Coolant Ranking](../output/figures/fluid_ranking.png)",
        "",
        "![HX Profile](../output/figures/hx_temperature_profile.png)",
        "",
        "![Pipeline Tradeoff](../output/figures/pipeline_tradeoff.png)",
        "",
        "## 4. Main Results",
        "",
        _markdown_table(
            pd.DataFrame(
                [
                    {"Metric": "Cooling load", "Value": f"{_format_number(float(summary['IDC total cooling load']['value']))} kW"},
                    {"Metric": "Theoretical minimum power", "Value": f"{_format_number(float(summary['Theoretical minimum power']['value']))} kW"},
                    {"Metric": "Baseline R-134a power", "Value": f"{_format_number(float(summary['Baseline R-134a compressor power']['value']))} kW"},
                    {"Metric": "Selected coolant", "Value": summary["Selected coolant"]["value"]},
                    {"Metric": "LNG loop pump power", "Value": f"{_format_number(float(summary['LNG system pump power']['value']))} kW"},
                    {"Metric": "Power saving", "Value": f"{_format_number(float(summary['Baseline-to-LNG power saving']['value']))} kW"},
                ]
            ),
            ["Metric", "Value"],
        ),
        "",
        "### 4.1 Coolant Selection",
        "",
        _markdown_table(
            alternatives.assign(
                screening_score=alternatives["screening_score"].map(lambda x: _format_number(x, 3)),
                pump_power_kw=alternatives["pump_power_kw"].map(_format_number),
                hx_shell_diameter_m=alternatives["hx_shell_diameter_m"].map(lambda x: _format_number(x, 3)),
                annual_cost_saving_krw=alternatives["annual_cost_saving_krw"].map(lambda x: _format_number(x / 1_000_000.0)),
            ),
            ["fluid", "screening_score", "pump_power_kw", "hx_shell_diameter_m", "annual_cost_saving_krw"],
        ),
        "",
        "The base-case optimum is **"
        f"{selected_alternative['fluid']}**, which minimizes loop pumping demand while preserving a feasible LNG vaporizer and pipeline design.",
        "",
        "### 4.2 Distance Sensitivity",
        "",
        _markdown_table(
            distance.assign(
                distance_km=distance["distance_km"].map(_format_number),
                pump_power_kw=distance["pump_power_kw"].map(_format_number),
                heat_gain_kw=distance["heat_gain_kw"].map(_format_number),
                thermal_margin_kw=distance["thermal_margin_kw"].map(_format_number),
            ),
            ["distance_km", "pump_power_kw", "heat_gain_kw", "thermal_margin_kw", "meets_idc_load"],
        ),
        "",
        "![Distance Sensitivity](../output/figures/pipeline_distance_sensitivity.png)",
        "",
        (
            f"The long-distance case at **{_format_number(long_distance['distance_km'])} km** is "
            f"**{'feasible' if bool(long_distance['meets_idc_load']) else 'not feasible'}** under the current duty margin. "
            f"The estimated maximum feasible one-way distance for the selected design is about "
            f"**{_format_number(distance['max_feasible_distance_m'].iloc[0] / 1000.0)} km**."
        ),
        "",
        "### 4.3 Supply Temperature Sensitivity",
        "",
        _markdown_table(
            temperature.assign(
                supply_temp_c=temperature["supply_temp_c"].map(_format_number),
                pump_power_kw=temperature["pump_power_kw"].map(_format_number),
                max_feasible_distance_km=temperature["max_feasible_distance_km"].map(_format_number),
            ),
            ["supply_temp_c", "selected_fluid", "pump_power_kw", "max_feasible_distance_km", "long_distance_meets_load", "status"],
        ),
        "",
        "![Supply Temperature Sensitivity](../output/figures/supply_temperature_sensitivity.png)",
        "",
        (
            f"The best pump-power point in the temperature sweep is **{_format_number(best_temp['supply_temp_c'])} C**, "
            f"which retains **{best_temp['selected_fluid']}** as the preferred fluid. "
            f"A warmer supply temperature of **-43.1 C** makes the 35 km case feasible, but only after switching to **R-600a** "
            f"and accepting a much larger pumping demand."
        ),
        "",
        "### 4.4 Annual Impact",
        "",
        _markdown_table(annual_report, ["metric", "value", "unit"]),
        "",
        "![Annual Impact](../output/figures/annual_impact_comparison.png)",
        "",
        "Allowable additional investment based on simple payback targets:",
        "",
        _markdown_table(
            payback.assign(
                allowable_incremental_capex_krw=payback["allowable_incremental_capex_krw"].map(lambda x: f"{_format_number(x / 1_000_000.0)} million KRW")
            ),
            ["payback_years", "allowable_incremental_capex_krw"],
        ),
        "",
        "## 5. Comparison with Legacy Excel Work",
        "",
        _markdown_table(
            legacy.assign(
                legacy_value_kw=legacy["legacy_value_kw"].map(_format_number),
                current_value_kw=legacy["current_value_kw"].map(_format_number),
                difference_kw=legacy["difference_kw"].map(_format_number),
                difference_percent=legacy["difference_percent"].map(lambda x: _format_number(x, 2)),
            ),
            ["metric", "legacy_value_kw", "current_value_kw", "difference_kw", "difference_percent"],
        ),
        "",
        "The recreated Python workflow is consistent with the historical spreadsheet at the system level, while making the assumptions, source traceability, and scenario studies explicit.",
        "",
        "## 6. Discussion",
        "",
        "- The base 10 km system is feasible with a large power reduction relative to the baseline compressor load.",
        "- The 35 km case is not feasible at the current duty margin for the base design point, which is itself a useful design conclusion rather than a failure.",
        "- A temperature-level shift can extend feasible distance, but it may require a different coolant and a higher loop pumping penalty.",
        "- The annualized economics are strong under the current boundary definition, but the comparison currently excludes detailed auxiliary equipment, maintenance, financing, and LNG infrastructure CAPEX.",
        "",
        "## 7. Limitations",
        "",
        "- LNG is modeled as pure methane in v1.",
        "- The IDC-side distribution network is simplified into a cooling-duty boundary rather than a full hydraulic network.",
        "- The economic comparison boundary is limited to baseline compressor power versus LNG loop pump power.",
        "- Detailed mechanical design checks such as stress, materials procurement, and controls integration are outside the present scope.",
        "",
        "## 8. Conclusion",
        "",
        (
            "The reconstructed project shows that an LNG cold-energy cooling concept can strongly reduce the modeled electrical demand of the reference data-center cooling system at the 10 km design point. "
            "The selected base design uses ammonia in the secondary loop, a shell-and-tube LNG vaporizer, and a 0.35 m supply/return pipeline pair. "
            "The design is energy-efficient, economically attractive under the present boundary, and transparent enough to support further report refinement and presentation work."
        ),
        "",
        "## References",
        "",
    ]
    for source_id in ["SRC-001", "SRC-004", "SRC-005", "SRC-006", "SRC-007", "SRC-008", "SRC-009", "SRC-010", "SRC-011", "SRC-012", "SRC-013", "SRC-014"]:
        if source_id in sources:
            entry = sources[source_id]
            report_lines.append(f"- **{source_id}** {entry['title']}. {entry['link_or_path']}")
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    return report_path


def build_presentation_script(project_root: Path) -> Path:
    output_dir = project_root / "output"
    deliverables_dir = ensure_directory(project_root / "deliverables")
    summary = _summary_map(output_dir)
    alternatives = pd.read_csv(output_dir / "alternative_designs.csv")
    distance = pd.read_csv(output_dir / "distance_scenarios.csv")
    temperature = pd.read_csv(output_dir / "supply_temperature_sweep.csv")
    annual = pd.read_csv(output_dir / "annual_summary.csv")
    selected_alternative = alternatives.iloc[0]
    long_distance = distance.sort_values("distance_km").iloc[-1]
    high_temp = temperature[(temperature["status"] == "feasible") & (temperature["long_distance_meets_load"] == True)].head(1)
    annual_map = {
        str(row["metric"]): {
            "value": float(row["value"]),
            "unit": str(row["unit"]),
        }
        for _, row in annual.iterrows()
    }

    script_lines = [
        "# Presentation Script",
        "",
        "## Slide 1. Title and Core Message",
        "- Open with the design question: can LNG cold energy replace a conventional data-center cooling duty?",
        "- Emphasize that the project is now a reproducible, code-based engineering study rather than a one-off spreadsheet.",
        f"- Highlight the three anchor numbers immediately: cooling load {_format_number(float(summary['IDC total cooling load']['value']))} kW, baseline compressor power {_format_number(float(summary['Baseline R-134a compressor power']['value']))} kW, LNG pump power {_format_number(float(summary['LNG system pump power']['value']))} kW.",
        "",
        "## Slide 2. Design Question and Basis",
        "- Frame the assignment constraints before showing any design result.",
        "- Use the modeled cooling load and the transport-distance requirement as the two hardest assignment constraints.",
        "- Call out that sources and assumptions are explicitly tracked inside the project repository.",
        "",
        "## Slide 3. System Concept",
        "- Explain the architecture in one sentence: LNG cold energy chills a secondary loop, and that loop transports duty to the IDC.",
        "- Mention the two design bottlenecks: vaporizer pinch and long-distance transport penalty.",
        f"- State the current base-case fluid choice: {summary['Selected coolant']['value']}.",
        "",
        "## Slide 4. Benchmark Against the Reference Cycle",
        f"- Theoretical minimum power is {_format_number(float(summary['Theoretical minimum power']['value']))} kW.",
        f"- Reference R-134a compressor power is {_format_number(float(summary['Baseline R-134a compressor power']['value']))} kW.",
        f"- The modeled LNG loop pump demand is only {_format_number(float(summary['LNG system pump power']['value']))} kW, which defines the main energy argument.",
        "",
        "## Slide 5. Coolant Selection",
        f"- Present {selected_alternative['fluid']} as the base-case winner, not as an arbitrary choice but as the best trade-off in the modeled ranking.",
        "- Explain that the screening compares feasibility, pumping demand, heat-exchanger scale, and downstream annual benefit.",
        "- Position propane and isobutane as useful alternatives rather than discarded options.",
        "",
        "## Slide 6. Transport-Distance Constraint",
        f"- State the base result clearly: maximum feasible one-way distance is about {_format_number(distance['max_feasible_distance_m'].iloc[0] / 1000.0)} km.",
        f"- Therefore the {int(long_distance['distance_km'])} km case is {'feasible' if bool(long_distance['meets_idc_load']) else 'not feasible'} at the current design point.",
        "- Use this as a design insight, not as a failure: transport distance is the real system constraint after the base 10 km case closes.",
        "",
        "## Slide 7. Temperature Trade-off",
        "- Explain that a warmer supply temperature increases transport feasibility but also changes the fluid preference and pumping penalty.",
        "- Show that recovering 35 km is possible only by moving the operating point, not by assuming the base design magically stretches that far.",
        "",
        "## Slide 8. Annual Impact",
        f"- Annual electricity saving is {_format_number(annual_map['Electricity saving']['value'])} {annual_map['Electricity saving']['unit']}.",
        f"- Annual electricity cost saving is {_format_number(annual_map['Electricity cost saving']['value'] / 1_000_000.0)} million KRW/year.",
        f"- Annual avoided indirect emissions are {_format_number(annual_map['Avoided indirect emissions']['value'])} {annual_map['Avoided indirect emissions']['unit']}.",
        "",
        "## Slide 9. Recommendation",
        "- Close with a decision statement: the 10 km LNG cold-energy design is technically feasible and strongly attractive on an energy basis.",
        "- Say explicitly that 35 km requires a changed operating point and should be treated as a design extension, not the base promise.",
    ]
    if not high_temp.empty:
        row = high_temp.iloc[0]
        script_lines.insert(
            script_lines.index("## Slide 8. Annual Impact") - 1,
            f"- Mention the recovery point explicitly: at {row['supply_temp_c']:.1f} C supply temperature, the design becomes feasible at 35 km with {row['selected_fluid']}.",
        )
    script_lines.extend(
        [
            "- End by positioning the project as a reusable design study with traceable sources, assumptions, and scenarios.",
        ]
    )
    script_path = deliverables_dir / "presentation_script.md"
    script_path.write_text("\n".join(script_lines), encoding="utf-8")
    return script_path


def build_presentation(project_root: Path) -> Path:
    deliverables_dir = ensure_directory(project_root / "deliverables")
    slides_src_dir = ensure_directory(deliverables_dir / "slides_src")
    deck_source = slides_src_dir / "presentation_draft.js"
    package_json = slides_src_dir / "package.json"
    node_modules_dir = slides_src_dir / "node_modules"
    npm_executable = "npm.cmd" if os.name == "nt" else "npm"
    node_executable = "node.exe" if os.name == "nt" else "node"

    if not deck_source.exists():
        raise FileNotFoundError(f"Missing slide source: {deck_source}")
    if not package_json.exists():
        raise FileNotFoundError(f"Missing slide package manifest: {package_json}")

    if not node_modules_dir.exists():
        subprocess.run([npm_executable, "install"], cwd=slides_src_dir, check=True)

    subprocess.run([node_executable, str(deck_source)], cwd=slides_src_dir, check=True)

    pptx_path = deliverables_dir / "presentation_draft.pptx"
    if not pptx_path.exists():
        raise FileNotFoundError(f"Slide build did not produce {pptx_path}")
    return pptx_path


def build_deliverables(project_root: Path) -> dict[str, Path]:
    report_path = build_report(project_root)
    script_path = build_presentation_script(project_root)
    presentation_path = build_presentation(project_root)
    return {
        "report": report_path,
        "script": script_path,
        "presentation": presentation_path,
    }
