from __future__ import annotations

import re
from pathlib import Path


ID_PATTERN = re.compile(r"\b(?:SRC|ASM)-\d{3}\b")


def _extract_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return set(ID_PATTERN.findall(path.read_text(encoding="utf-8")))


def validate_run(project_root: Path, config, load_result, minimum_power, baseline, screening, hx_result, pipeline_result, system_eval) -> list[str]:
    messages: list[str] = []

    if not config.citations:
        raise AssertionError("No config citations were loaded from the TOML file.")
    messages.append(f"Loaded {len(config.citations)} citation-tagged config values from the TOML file.")

    summary_ids = set()
    for source_ids in system_eval["summary"]["source_ids"]:
        summary_ids.update(token.strip() for token in str(source_ids).split(","))

    documented_ids = _extract_ids(project_root / "docs" / "sources.md") | _extract_ids(project_root / "docs" / "assumptions.md")
    config_ids = {node.source_id for node in config.citations.values()}
    undocumented_config_ids = sorted(identifier for identifier in config_ids if identifier not in documented_ids)
    if undocumented_config_ids:
        raise AssertionError(f"Config source IDs missing from documentation: {undocumented_config_ids}")
    messages.append("All citation-tagged config values map to documented SRC/ASM entries.")

    missing = sorted(identifier for identifier in summary_ids if identifier and identifier not in documented_ids)
    if missing:
        raise AssertionError(f"Undocumented source IDs found: {missing}")
    messages.append("All summary source IDs are documented in docs/sources.md or docs/assumptions.md.")

    if hx_result["min_pinch_k"] < config.values["assignment"]["minimum_temperature_approach_k"] - 1e-6:
        raise AssertionError("Minimum LNG vaporizer pinch constraint violated.")
    messages.append(f"LNG vaporizer pinch check passed at {hx_result['min_pinch_k']:.2f} K.")

    if system_eval["available_to_idc_kw"] < load_result.total_kw:
        raise AssertionError("Available cooling at IDC is lower than the modeled cooling load.")
    messages.append("LNG loop delivers at least the modeled IDC cooling load.")

    if baseline["compressor_power_kw"] <= minimum_power["minimum_power_kw"]:
        raise AssertionError("Baseline vapor compression power should exceed the theoretical minimum.")
    messages.append("Baseline R-134a power remains above the Carnot minimum, as expected.")

    pipe_scan = pipeline_result["scan_table"].sort_values("supply_id_m")
    mean_by_diameter = pipe_scan.groupby("supply_id_m", as_index=False)["dp_supply_kpa"].mean()
    if not mean_by_diameter["dp_supply_kpa"].is_monotonic_decreasing:
        raise AssertionError("Pipeline pressure drop is not monotonically decreasing with larger supply diameter.")
    messages.append("Pipeline pressure drop decreases with increasing supply diameter.")

    heat_by_insulation = pipeline_result["scan_table"].groupby("insulation_thickness_m", as_index=False)["heat_gain_kw"].mean()
    if not heat_by_insulation.sort_values("insulation_thickness_m")["heat_gain_kw"].is_monotonic_decreasing:
        raise AssertionError("Pipeline heat gain is not monotonically decreasing with thicker insulation.")
    messages.append("Pipeline heat gain decreases with thicker insulation.")

    long_distance = pipeline_result["sensitivity"].sort_values("distance_m").iloc[-1]
    available_long_distance_kw = hx_result["required_lng_duty_kw"] - float(long_distance["heat_gain_kw"])
    if available_long_distance_kw >= load_result.total_kw:
        messages.append("Long-distance pipeline case still satisfies the IDC load.")
    else:
        messages.append("Long-distance pipeline case is infeasible at the current duty margin because heat gain exceeds the available buffer.")
    messages.append(f"Estimated maximum feasible one-way pipeline distance is about {pipeline_result['max_feasible_distance_m'] / 1000.0:.1f} km.")

    feasible_fluids = screening["table"][screening["table"]["feasible"]]
    if feasible_fluids.empty:
        raise AssertionError("No feasible fluids survived the screening stage.")
    messages.append(f"{len(feasible_fluids)} feasible coolant candidate(s) remained after screening.")

    annual = system_eval["annual"]
    if annual["cost_saving_krw_per_year"] <= 0.0:
        raise AssertionError("Annual electricity cost saving should be positive for the selected LNG design.")
    if annual["avoided_emissions_tco2_per_year"] <= 0.0:
        raise AssertionError("Annual avoided emissions should be positive for the selected LNG design.")
    messages.append("Annualized cost saving and avoided emissions are both positive.")
    return messages
