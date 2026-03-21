from __future__ import annotations

import argparse
from pathlib import Path

from .baseline_vcc import compute_baseline_cycle
from .config import load_config
from .deliverables import build_deliverables, build_presentation, build_report, build_presentation_script
from .fluid_screening import compute_fluid_screening
from .hx_lng_vaporizer import design_lng_vaporizer
from .idc_hx import evaluate_idc_heat_exchange
from .idc_secondary_loop import evaluate_idc_secondary_loop
from .legacy_compare import compare_with_legacy_excel
from .load_model import compute_load_model
from .parallel import default_parallel_enabled_for_command, resolve_parallel_options
from .pipeline_loop import design_pipeline
from .report_assets import write_outputs
from .scenario_study import (
    _merge_fluid_with_pipeline,
    build_distance_scenarios,
    evaluate_ambient_closure_map,
    evaluate_feasible_alternatives,
    evaluate_passive_zero_warmup_search,
    evaluate_supply_temperature_sweep,
    evaluate_zero_warmup_target_search,
)
from .system_eval import evaluate_system
from .thermo import ensure_directory
from .thermo_limit import compute_theoretical_minimum_power
from .uncertainty import evaluate_uncertainty_study
from .validation import validate_run


def run_all(config_path: Path, *, workers: int | None = None, parallel: bool = True) -> dict[str, object]:
    project_root = config_path.resolve().parent.parent
    cfg = load_config(config_path)
    values = cfg.values
    parallel_options = resolve_parallel_options(enabled=parallel, workers=workers)

    load_result = compute_load_model(values)
    minimum_power = compute_theoretical_minimum_power(values, load_result.total_kw)
    baseline = compute_baseline_cycle(values, load_result.total_kw)
    legacy_result = compare_with_legacy_excel(project_root, baseline, minimum_power)
    screening = compute_fluid_screening(values, load_result.total_kw, parallel_options=parallel_options)
    idc_hx_result = evaluate_idc_heat_exchange(values, screening["selected"]["coolprop_name"], load_result.total_kw)
    idc_secondary_loop_result = evaluate_idc_secondary_loop(values, idc_hx_result["chilled_water_mass_flow_kg_s"])
    pipeline_result = design_pipeline(values, screening["selected"], load_result.total_kw)
    hx_result = design_lng_vaporizer(
        values,
        _merge_fluid_with_pipeline(screening["selected"], pipeline_result),
        float(pipeline_result["selected_design"]["actual_lng_duty_kw"]),
    )
    scenario_result = evaluate_feasible_alternatives(values, load_result, baseline, screening, parallel_options=parallel_options)
    distance_scenarios = build_distance_scenarios(values, load_result, baseline, hx_result, pipeline_result)
    supply_temperature_sweep = evaluate_supply_temperature_sweep(values, load_result, baseline, parallel_options=parallel_options)
    ambient_closure_map = evaluate_ambient_closure_map(values, load_result, baseline, parallel_options=parallel_options)
    zero_warmup_target_search = evaluate_zero_warmup_target_search(values, load_result, baseline, parallel_options=parallel_options)
    system_eval = evaluate_system(
        values,
        load_result,
        minimum_power,
        baseline,
        screening,
        idc_hx_result,
        hx_result,
        pipeline_result,
        idc_secondary_loop_result,
        legacy_result,
    )
    validation_messages = validate_run(
        project_root,
        cfg,
        load_result,
        minimum_power,
        baseline,
        screening,
        hx_result,
        pipeline_result,
        idc_secondary_loop_result,
        system_eval,
        zero_warmup_target_search,
    )
    write_outputs(
        project_root,
        config_path,
        load_result,
        minimum_power,
        baseline,
        screening,
        idc_hx_result,
        idc_secondary_loop_result,
        hx_result,
        pipeline_result,
        scenario_result,
        distance_scenarios,
        supply_temperature_sweep,
        ambient_closure_map,
        zero_warmup_target_search,
        system_eval,
        validation_messages,
        legacy_result,
    )
    return {
        "load": load_result,
        "minimum_power": minimum_power,
        "baseline": baseline,
        "legacy": legacy_result,
        "screening": screening,
        "idc_hx": idc_hx_result,
        "idc_secondary_loop": idc_secondary_loop_result,
        "hx": hx_result,
        "pipeline": pipeline_result,
        "scenario": scenario_result,
        "distance_scenarios": distance_scenarios,
        "supply_temperature_sweep": supply_temperature_sweep,
        "ambient_closure_map": ambient_closure_map,
        "zero_warmup_target_search": zero_warmup_target_search,
        "system": system_eval,
        "validation": validation_messages,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="LNG cold-energy IDC design toolkit")
    parser.add_argument("command", choices=["run-all", "screen-fluids", "design-hx", "analyze-pipeline", "analyze-aux-heat", "scenario-study", "explore-passive-heat", "uncertainty-study", "build-report", "build-slides", "build-deliverables", "compare-legacy", "validate"])
    parser.add_argument("--config", required=True, help="Path to TOML configuration file")
    parser.add_argument("--workers", type=int, default=None, help="Override process worker count for parallel commands")
    parser.add_argument("--serial", action="store_true", help="Force serial execution even for commands that default to parallel mode")
    args = parser.parse_args()
    config_path = Path(args.config)
    parallel_enabled = (not args.serial) and (args.workers is not None or default_parallel_enabled_for_command(args.command))
    parallel_options = resolve_parallel_options(enabled=parallel_enabled, workers=args.workers)

    if args.command == "run-all":
        results = run_all(config_path, workers=parallel_options.workers, parallel=parallel_options.enabled)
        print(f"Selected coolant: {results['screening']['selected']['fluid']}")
        print(f"IDC total cooling load: {results['load'].total_kw:,.1f} kW")
        print(f"Baseline power: {results['baseline']['compressor_power_kw']:,.1f} kW")
        print(f"Core LNG system power: {results['system']['core_system_power_kw']:,.1f} kW")
        return 0

    cfg = load_config(config_path)
    values = cfg.values
    load_result = compute_load_model(values)

    if args.command == "screen-fluids":
        screening = compute_fluid_screening(values, load_result.total_kw, parallel_options=parallel_options)
        print(screening["table"].to_string(index=False))
        return 0

    if args.command == "design-hx":
        screening = compute_fluid_screening(values, load_result.total_kw, parallel_options=parallel_options)
        pipeline_result = design_pipeline(values, screening["selected"], load_result.total_kw)
        hx_result = design_lng_vaporizer(
            values,
            _merge_fluid_with_pipeline(screening["selected"], pipeline_result),
            float(pipeline_result["selected_design"]["actual_lng_duty_kw"]),
        )
        print(hx_result["segments"].to_string(index=False))
        print(hx_result["selected_geometry"])
        return 0

    if args.command == "analyze-pipeline":
        screening = compute_fluid_screening(values, load_result.total_kw, parallel_options=parallel_options)
        pipeline_result = design_pipeline(values, screening["selected"], load_result.total_kw)
        print(pipeline_result["sensitivity"].to_string(index=False))
        print(pipeline_result["selected_design"])
        return 0

    if args.command == "analyze-aux-heat":
        results = run_all(config_path, workers=parallel_options.workers, parallel=parallel_options.enabled)
        print(results["system"]["auxiliary_heat_sources"]["table"].to_string(index=False))
        return 0

    if args.command == "scenario-study":
        minimum_power = compute_theoretical_minimum_power(values, load_result.total_kw)
        baseline = compute_baseline_cycle(values, load_result.total_kw)
        screening = compute_fluid_screening(values, load_result.total_kw, parallel_options=parallel_options)
        idc_hx_result = evaluate_idc_heat_exchange(values, screening["selected"]["coolprop_name"], load_result.total_kw)
        idc_secondary_loop_result = evaluate_idc_secondary_loop(values, idc_hx_result["chilled_water_mass_flow_kg_s"])
        pipeline_result = design_pipeline(values, screening["selected"], load_result.total_kw)
        hx_result = design_lng_vaporizer(
            values,
            _merge_fluid_with_pipeline(screening["selected"], pipeline_result),
            float(pipeline_result["selected_design"]["actual_lng_duty_kw"]),
        )
        scenario_result = evaluate_feasible_alternatives(values, load_result, baseline, screening, parallel_options=parallel_options)
        distance_scenarios = build_distance_scenarios(values, load_result, baseline, hx_result, pipeline_result)
        supply_temperature_sweep = evaluate_supply_temperature_sweep(values, load_result, baseline, parallel_options=parallel_options)
        ambient_closure_map = evaluate_ambient_closure_map(values, load_result, baseline, parallel_options=parallel_options)
        zero_warmup_target_search = evaluate_zero_warmup_target_search(values, load_result, baseline, parallel_options=parallel_options)
        print(distance_scenarios.to_string(index=False))
        print()
        print(idc_secondary_loop_result["scan_table"].to_string(index=False))
        print()
        print(supply_temperature_sweep.to_string(index=False))
        print()
        print(ambient_closure_map["table"].to_string(index=False))
        print()
        print(zero_warmup_target_search["table"].to_string(index=False))
        print()
        print(scenario_result["alternatives"].to_string(index=False))
        return 0

    if args.command == "explore-passive-heat":
        passive_search = evaluate_passive_zero_warmup_search(values, parallel_options=parallel_options)
        output_dir = ensure_directory(config_path.resolve().parent.parent / "output")
        output_path = output_dir / "passive_zero_warmup_search.csv"
        passive_search["table"].to_csv(output_path, index=False)
        print(output_path)
        print()
        for scenario_name, distance_map in passive_search["selected_by_scenario"].items():
            print(f"[{scenario_name}]")
            for target_distance_m, result in distance_map.items():
                near_best = result["near_best"]
                warmup_free = result["warmup_free"]
                practical = passive_search["practical_selected_by_scenario"][scenario_name][target_distance_m]
                practical_warmup_free = practical["warmup_free"]
                if warmup_free is not None:
                    print(
                        f"{target_distance_m / 1000.0:.1f} km: warm-up-free design found at "
                        f"{warmup_free['supply_temp_c']:.1f} C / {warmup_free['fluid']}, "
                        f"core power {warmup_free['best_design_pump_power_kw']:.1f} kW"
                    )
                elif near_best is not None:
                    print(
                        f"{target_distance_m / 1000.0:.1f} km: no warm-up-free design, best point "
                        f"{near_best['supply_temp_c']:.1f} C / {near_best['fluid']}, "
                        f"supplemental {near_best['minimum_supplemental_warmup_kw']:.1f} kW"
                    )
                else:
                    print(f"{target_distance_m / 1000.0:.1f} km: no feasible candidate")
                if practical_warmup_free is not None:
                    print(
                        f"  practical filter: retained at {practical_warmup_free['supply_temp_c']:.1f} C / "
                        f"{practical_warmup_free['fluid']}, core power {practical_warmup_free['best_design_pump_power_kw']:.1f} kW"
                    )
                else:
                    print("  practical filter: no warm-up-free design survived")
            print()
        return 0

    if args.command == "uncertainty-study":
        uncertainty_result = evaluate_uncertainty_study(values, parallel_options=parallel_options)
        output_dir = ensure_directory(config_path.resolve().parent.parent / "output")
        samples_path = output_dir / "uncertainty_samples.csv"
        summary_path = output_dir / "uncertainty_summary.csv"
        uncertainty_result["samples"].to_csv(samples_path, index=False)
        uncertainty_result["summary"].to_csv(summary_path, index=False)
        print(samples_path)
        print(summary_path)
        print()
        print(uncertainty_result["summary"].to_string(index=False))
        return 0

    if args.command == "build-report":
        run_all(config_path, workers=parallel_options.workers, parallel=parallel_options.enabled)
        report_path = build_report(config_path.resolve().parent.parent)
        script_path = build_presentation_script(config_path.resolve().parent.parent)
        print(report_path)
        print(script_path)
        return 0

    if args.command == "build-slides":
        run_all(config_path, workers=parallel_options.workers, parallel=parallel_options.enabled)
        presentation_path = build_presentation(config_path.resolve().parent.parent)
        print(presentation_path)
        return 0

    if args.command == "build-deliverables":
        run_all(config_path, workers=parallel_options.workers, parallel=parallel_options.enabled)
        built = build_deliverables(config_path.resolve().parent.parent)
        for path in built.values():
            print(path)
        return 0

    if args.command == "compare-legacy":
        project_root = config_path.resolve().parent.parent
        minimum_power = compute_theoretical_minimum_power(values, load_result.total_kw)
        baseline = compute_baseline_cycle(values, load_result.total_kw)
        legacy_result = compare_with_legacy_excel(project_root, baseline, minimum_power)
        if not legacy_result["available"]:
            print(f"Legacy workbook not found: {legacy_result['path']}")
            return 0
        print(legacy_result["table"].to_string(index=False))
        return 0

    if args.command == "validate":
        results = run_all(config_path, workers=parallel_options.workers, parallel=parallel_options.enabled)
        for message in results["validation"]:
            print(message)
        return 0
    return 1
