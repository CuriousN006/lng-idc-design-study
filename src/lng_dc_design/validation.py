from __future__ import annotations

import math
import re
from pathlib import Path


ID_PATTERN = re.compile(r"\b(?:SRC|ASM)-\d{3}\b")


def _extract_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return set(ID_PATTERN.findall(path.read_text(encoding="utf-8")))


def validate_run(
    project_root: Path,
    config,
    load_result,
    minimum_power,
    baseline,
    screening,
    hx_result,
    pipeline_result,
    idc_secondary_loop_result,
    system_eval,
    zero_warmup_target_search: dict | None = None,
) -> list[str]:
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

    idc_pinch = float(screening["selected"]["idc_hx_min_pinch_k"])
    if idc_pinch < config.values["assignment"]["minimum_temperature_approach_k"] - 1e-6:
        raise AssertionError("IDC-side heat exchanger pinch constraint violated.")
    messages.append(f"IDC-side heat exchanger pinch check passed at {idc_pinch:.2f} K.")

    supply_temp_k = float(config.values["coolant_loop"]["supply_temp_k"])
    after_idc_temp_k = float(hx_result["after_idc_temp_k"])
    return_to_lng_temp_k = float(hx_result["return_to_lng_temp_k"])
    if not (supply_temp_k < after_idc_temp_k < return_to_lng_temp_k):
        raise AssertionError("Coolant temperatures across the IDC-side heat exchanger are not monotonically increasing.")
    messages.append("IDC-side coolant temperatures increase monotonically from LNG outlet to IDC outlet and back to the LNG inlet.")

    if float(screening["selected"]["idc_hx_area_m2"]) <= 0.0:
        raise AssertionError("IDC-side heat exchanger required area must be positive.")
    messages.append("IDC-side heat exchanger sizing returned a positive required area.")

    secondary_scan = idc_secondary_loop_result["scan_table"].sort_values("diameter_m")
    if not secondary_scan["velocity_m_per_s"].is_monotonic_decreasing:
        raise AssertionError("IDC secondary-loop velocity should decrease as diameter increases.")
    messages.append("IDC secondary-loop velocity decreases with increasing loop diameter.")

    feasible_secondary = secondary_scan[secondary_scan["feasible"]]
    if feasible_secondary.empty:
        raise AssertionError("No feasible IDC secondary-loop design was found.")
    messages.append(
        f"IDC secondary-loop selected {float(idc_secondary_loop_result['selected_design']['diameter_m']):.3f} m at "
        f"{float(idc_secondary_loop_result['selected_design']['pump_power_kw']):.1f} kW."
    )

    utilization_target = float(config.values["system_targets"]["idc_cooling_utilization_fraction"])
    if float(screening["selected"]["minimum_hot_end_utilization_fraction"]) < utilization_target - 1e-6:
        messages.append("Configured utilization target is more aggressive than the selected coolant can satisfy at the LNG hot end; supplemental warm-up is required.")
    else:
        messages.append("Selected coolant satisfies the hot-end minimum return condition within the configured utilization target.")

    if system_eval["available_to_idc_kw"] < load_result.total_kw:
        raise AssertionError("Available cooling at IDC is lower than the modeled cooling load.")
    messages.append("LNG loop delivers at least the modeled IDC cooling load.")

    if float(pipeline_result["selected_design"]["return_to_lng_temp_k"]) < float(pipeline_result["minimum_return_to_lng_k"]) - 1e-6:
        raise AssertionError("Selected pipeline design does not warm the return stream enough for the LNG hot-end constraint.")
    messages.append("Selected pipeline design satisfies the LNG hot-end return temperature requirement.")

    if float(pipeline_result["selected_design"]["supplemental_warmup_kw"]) > 1e-6:
        messages.append(f"Selected pipeline still needs {pipeline_result['selected_design']['supplemental_warmup_kw']:.1f} kW of supplemental warm-up to hit the LNG hot-end requirement.")
    else:
        messages.append("Selected pipeline meets the LNG hot-end requirement using ambient pickup alone.")

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

    target_distance = float(config.values["system_targets"]["long_distance_pipeline_m"])
    long_distance_rows = pipeline_result["sensitivity"].loc[
        (pipeline_result["sensitivity"]["distance_m"] - target_distance).abs() < 1e-6
    ]
    if long_distance_rows.empty:
        raise AssertionError(f"Configured long-distance checkpoint {target_distance:.1f} m is missing from the sensitivity table.")
    long_distance = long_distance_rows.iloc[0]
    available_long_distance_kw = float(long_distance["available_cooling_kw"])
    if bool(long_distance["feasible"]) and available_long_distance_kw >= load_result.total_kw - 1e-6:
        messages.append("Long-distance pipeline case still satisfies the IDC load.")
    else:
        messages.append("Long-distance pipeline case is infeasible at the current duty margin because heat gain exceeds the available buffer.")
    messages.append(f"Estimated maximum feasible one-way pipeline distance is about {pipeline_result['max_feasible_distance_m'] / 1000.0:.1f} km.")
    ambient_only_closure_distance_m = float(pipeline_result.get("ambient_only_closure_distance_m", math.nan))
    if math.isfinite(ambient_only_closure_distance_m):
        messages.append(
            f"Ambient-only closure occurs near {ambient_only_closure_distance_m / 1000.0:.1f} km, so shorter distances still require supplemental warm-up under the current hot-end constraint."
        )
    else:
        messages.append("No feasible ambient-only closure point was found before the selected pipeline loses feasibility.")

    if zero_warmup_target_search:
        base_distance = float(config.values["assignment"]["pipeline_distance_m"])
        long_distance_target = float(config.values["system_targets"]["long_distance_pipeline_m"])
        base_search = zero_warmup_target_search["selected_by_distance"].get(base_distance)
        long_search = zero_warmup_target_search["selected_by_distance"].get(long_distance_target)
        if base_search and base_search["warmup_free"] is None and base_search["near_best"] is not None:
            messages.append(
                f"No warm-up-free design was found at the {base_distance / 1000.0:.1f} km target; the best grid point still needs {base_search['near_best']['minimum_supplemental_warmup_kw']:.1f} kW."
            )
        if long_search and long_search["warmup_free"] is None and long_search["near_best"] is not None:
            messages.append(
                f"No warm-up-free design was found at the {long_distance_target / 1000.0:.1f} km target; the best grid point still needs {long_search['near_best']['minimum_supplemental_warmup_kw']:.1f} kW."
            )

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

    if float(system_eval["capex"]["total_capex_krw"]) <= 0.0:
        raise AssertionError("Core installed CAPEX must be positive.")
    messages.append(
        f"Core installed CAPEX estimated at {float(system_eval['capex']['total_capex_krw']) / 1_000_000_000.0:.2f} billion KRW."
    )

    messages.append(
        f"Core-system discounted payback estimate is {system_eval['financial_core']['discounted_payback_years'] if not math.isnan(float(system_eval['financial_core']['discounted_payback_years'])) else 'not reached within project life'}."
    )

    auxiliary_heat_sources = system_eval.get("auxiliary_heat_sources", {}).get("table")
    if auxiliary_heat_sources is None or auxiliary_heat_sources.empty:
        raise AssertionError("Auxiliary heat-source scenario table should not be empty.")
    best_auxiliary = system_eval["auxiliary_heat_sources"]["selected"]
    if best_auxiliary is None:
        raise AssertionError("A best auxiliary heat-source scenario should be selected.")
    messages.append(
        f"Configured hybrid warm-up scenarios rank {best_auxiliary['scenario_label']} best at {best_auxiliary['total_system_power_kw']:.1f} kW total power."
    )
    return messages
