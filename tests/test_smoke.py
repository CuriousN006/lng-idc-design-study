from __future__ import annotations

from copy import deepcopy
import unittest
from pathlib import Path

import pandas as pd

from lng_dc_design.baseline_vcc import compute_baseline_cycle
from lng_dc_design.cli import run_all
from lng_dc_design.config import load_config
from lng_dc_design.deliverables import build_deliverables
from lng_dc_design.economics import compute_financial_metrics
from lng_dc_design.fluid_screening import compute_fluid_screening
from lng_dc_design.hx_lng_vaporizer import design_lng_vaporizer
from lng_dc_design.idc_hx import evaluate_idc_heat_exchange
from lng_dc_design.idc_secondary_loop import evaluate_idc_secondary_loop
from lng_dc_design.load_model import compute_load_model
from lng_dc_design.parallel import resolve_parallel_options
from lng_dc_design.pipeline_loop import design_pipeline
from lng_dc_design.scenario_study import (
    _merge_fluid_with_pipeline,
    build_distance_scenarios,
    evaluate_ambient_closure_map,
    evaluate_feasible_alternatives,
    evaluate_passive_zero_warmup_search,
    evaluate_supply_temperature_sweep,
    evaluate_zero_warmup_target_search,
)
from lng_dc_design.system_eval import evaluate_system
from lng_dc_design.thermo_limit import compute_theoretical_minimum_power
from lng_dc_design.uncertainty import evaluate_uncertainty_study


class SmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[1]
        cls.config = load_config(cls.project_root / "config" / "base.toml").values

    def test_end_to_end_modules(self) -> None:
        load_result = compute_load_model(self.config)
        minimum_power = compute_theoretical_minimum_power(self.config, load_result.total_kw)
        baseline = compute_baseline_cycle(self.config, load_result.total_kw)
        screening = compute_fluid_screening(self.config, load_result.total_kw)
        idc_hx_result = evaluate_idc_heat_exchange(
            self.config,
            screening["selected"]["coolprop_name"],
            load_result.total_kw,
        )
        idc_secondary_loop_result = evaluate_idc_secondary_loop(self.config, idc_hx_result["chilled_water_mass_flow_kg_s"])
        pipeline_result = design_pipeline(self.config, screening["selected"], load_result.total_kw)
        hx_result = design_lng_vaporizer(
            self.config,
            _merge_fluid_with_pipeline(screening["selected"], pipeline_result),
            float(pipeline_result["selected_design"]["actual_lng_duty_kw"]),
        )
        scenario_result = evaluate_feasible_alternatives(self.config, load_result, baseline, screening)
        distance_scenarios = build_distance_scenarios(self.config, load_result, baseline, hx_result, pipeline_result)
        supply_temperature_sweep = evaluate_supply_temperature_sweep(self.config, load_result, baseline)
        ambient_closure_map = evaluate_ambient_closure_map(self.config, load_result, baseline)
        zero_warmup_target_search = evaluate_zero_warmup_target_search(self.config, load_result, baseline)
        system_eval = evaluate_system(
            self.config,
            load_result,
            minimum_power,
            baseline,
            screening,
            idc_hx_result,
            hx_result,
            pipeline_result,
            idc_secondary_loop_result,
        )

        self.assertGreater(load_result.total_kw, 11_000.0)
        self.assertGreater(baseline["compressor_power_kw"], minimum_power["minimum_power_kw"])
        self.assertGreater(idc_hx_result["required_area_m2"], 0.0)
        self.assertGreaterEqual(idc_hx_result["min_pinch_k"], self.config["assignment"]["minimum_temperature_approach_k"])
        self.assertGreater(idc_hx_result["coolant_after_idc_temp_k"], self.config["coolant_loop"]["supply_temp_k"])
        self.assertGreater(idc_hx_result["minimum_return_to_lng_k"], idc_hx_result["coolant_after_idc_temp_k"])
        self.assertGreaterEqual(idc_hx_result["minimum_line_heat_gain_required_kw"], 0.0)
        self.assertGreater(float(idc_secondary_loop_result["selected_design"]["pump_power_kw"]), 0.0)
        self.assertGreater(float(idc_secondary_loop_result["selected_design"]["total_pressure_drop_kpa"]), 0.0)
        self.assertIn("idc_hx_area_m2", screening["selected"])
        self.assertIn("HEOS::", str(hx_result["lng_fluid"]))
        self.assertGreaterEqual(
            hx_result["min_pinch_k"] + 1e-6,
            self.config["assignment"]["minimum_temperature_approach_k"],
        )
        self.assertGreaterEqual(system_eval["available_to_idc_kw"], load_result.total_kw)
        self.assertGreaterEqual(
            float(pipeline_result["selected_design"]["return_to_lng_temp_k"]) + 1e-6,
            float(pipeline_result["minimum_return_to_lng_k"]),
        )
        self.assertGreaterEqual(float(pipeline_result["selected_design"]["supplemental_warmup_kw"]), 0.0)
        self.assertFalse(scenario_result["alternatives"].empty)
        self.assertTrue(
            (
                distance_scenarios["pump_power_kw"]
                - distance_scenarios["lng_loop_pump_power_kw"]
                - distance_scenarios["idc_secondary_loop_pump_power_kw"]
            ).abs().max()
            < 1e-6
        )
        base_distance_row = distance_scenarios.loc[
            (distance_scenarios["distance_m"] - float(self.config["assignment"]["pipeline_distance_m"])).abs() < 1e-6
        ].iloc[0]
        self.assertTrue(bool(base_distance_row["hydraulic_feasible"]))
        self.assertTrue(bool(base_distance_row["hybrid_load_satisfied"]))
        self.assertGreater(float(base_distance_row["supplemental_warmup_kw"]), 0.0)
        self.assertLess(float(base_distance_row["base_duty_margin_kw"]), 0.0)
        self.assertFalse(bool(base_distance_row["base_duty_meets_idc_load"]))
        target_distance_m = float(self.config["system_targets"]["long_distance_pipeline_m"])
        self.assertIn(target_distance_m, set(distance_scenarios["distance_m"].tolist()))
        long_distance_row = distance_scenarios.loc[
            (distance_scenarios["distance_m"] - target_distance_m).abs() < 1e-6
        ].iloc[0]
        self.assertTrue(bool(long_distance_row["hydraulic_feasible"]))
        self.assertTrue(bool(long_distance_row["hybrid_load_satisfied"]))
        self.assertGreater(float(long_distance_row["supplemental_warmup_kw"]), 0.0)
        self.assertLess(float(long_distance_row["base_duty_margin_kw"]), 0.0)
        self.assertFalse(bool(long_distance_row["base_duty_meets_idc_load"]))
        self.assertGreaterEqual(len(supply_temperature_sweep), 2)
        self.assertIn("feasible", set(supply_temperature_sweep["status"].tolist()))
        self.assertTrue(
            (
                supply_temperature_sweep["pump_power_kw"]
                - supply_temperature_sweep["lng_loop_pump_power_kw"]
                - supply_temperature_sweep["idc_secondary_loop_pump_power_kw"]
            ).dropna().abs().max()
            < 1e-6
        )
        self.assertFalse(ambient_closure_map["table"].empty)
        self.assertIsNotNone(ambient_closure_map["selected"])
        self.assertGreater(
            float(ambient_closure_map["selected"]["ambient_only_closure_distance_km"]),
            self.config["assignment"]["pipeline_distance_m"] / 1000.0,
        )
        self.assertFalse(zero_warmup_target_search["table"].empty)
        base_search = zero_warmup_target_search["selected_by_distance"][float(self.config["assignment"]["pipeline_distance_m"])]
        long_search = zero_warmup_target_search["selected_by_distance"][float(self.config["system_targets"]["long_distance_pipeline_m"])]
        self.assertIsNone(base_search["warmup_free"])
        self.assertIsNotNone(base_search["near_best"])
        self.assertGreater(float(base_search["near_best"]["minimum_supplemental_warmup_kw"]), 0.0)
        self.assertIsNone(long_search["warmup_free"])
        self.assertIsNotNone(long_search["near_best"])
        self.assertGreater(float(long_search["near_best"]["minimum_supplemental_warmup_kw"]), 0.0)
        self.assertGreater(system_eval["annual"]["cost_saving_krw_per_year"], 0.0)
        self.assertFalse(system_eval["auxiliary_heat_sources"]["table"].empty)
        self.assertIsNotNone(system_eval["auxiliary_heat_sources"]["selected"])
        self.assertGreater(float(system_eval["capex"]["total_capex_krw"]), 0.0)

    def test_build_deliverables(self) -> None:
        run_all(self.project_root / "config" / "base.toml", parallel=False)
        built = build_deliverables(self.project_root)
        self.assertTrue(built["report"].exists())
        self.assertTrue(built["script"].exists())
        self.assertTrue(built["presentation"].exists())
        report_text = built["report"].read_text(encoding="utf-8")
        script_text = built["script"].read_text(encoding="utf-8")
        self.assertNotIn("Baseline compressor power vs LNG loop pump power only", report_text)
        self.assertIn("하이브리드 성립, 기본 LNG duty 불성립", report_text)
        self.assertIn("하이브리드 성립, 기본 LNG duty 불성립", script_text)

    def test_pipeline_thermal_case_extensions(self) -> None:
        load_result = compute_load_model(self.config)
        screening = compute_fluid_screening(self.config, load_result.total_kw)

        baseline_pipeline = design_pipeline(self.config, screening["selected"], load_result.total_kw)
        passive_air_pipeline = design_pipeline(
            self.config,
            screening["selected"],
            load_result.total_kw,
            thermal_case={
                "mode": "air",
                "ambient_air_temp_k": 313.15,
                "wind_speed_m_per_s": 4.0,
                "solar_absorbed_flux_w_per_m2": 300.0,
                "pump_heat_to_fluid_fraction": 0.8,
            },
        )
        buried_pipeline = design_pipeline(
            self.config,
            screening["selected"],
            load_result.total_kw,
            thermal_case={
                "mode": "soil",
                "soil_temperature_k": 298.15,
                "soil_conductivity_w_per_mk": 1.5,
                "burial_depth_m": 1.5,
                "pump_heat_to_fluid_fraction": 0.8,
            },
        )

        self.assertGreaterEqual(
            float(passive_air_pipeline["selected_design"]["heat_gain_kw"]),
            float(baseline_pipeline["selected_design"]["heat_gain_kw"]),
        )
        self.assertGreater(float(passive_air_pipeline["selected_design"]["pump_heat_to_fluid_kw"]), 0.0)
        self.assertEqual(str(buried_pipeline["selected_design"]["thermal_mode"]), "soil")
        self.assertGreater(float(buried_pipeline["selected_design"]["line_heat_gain_kw"]), 0.0)

    def test_passive_zero_warmup_search(self) -> None:
        passive_search = evaluate_passive_zero_warmup_search(self.config)
        self.assertFalse(passive_search["table"].empty)
        self.assertIn("baseline_air", passive_search["selected_by_scenario"])
        self.assertIn("warm_buried_pipe", passive_search["selected_by_scenario"])
        base_distance = float(self.config["assignment"]["pipeline_distance_m"])
        self.assertIsNone(
            passive_search["practical_selected_by_scenario"]["baseline_air"][base_distance]["warmup_free"]
        )

    def test_parallel_consistency(self) -> None:
        load_result = compute_load_model(self.config)
        baseline = compute_baseline_cycle(self.config, load_result.total_kw)
        serial_options = resolve_parallel_options(enabled=False, workers=None)
        parallel_options = resolve_parallel_options(enabled=True, workers=2)

        screening_serial = compute_fluid_screening(self.config, load_result.total_kw, parallel_options=serial_options)
        screening_parallel = compute_fluid_screening(self.config, load_result.total_kw, parallel_options=parallel_options)
        self.assertEqual(screening_serial["selected"]["fluid"], screening_parallel["selected"]["fluid"])
        self.assertAlmostEqual(
            float(screening_serial["selected"]["score"]),
            float(screening_parallel["selected"]["score"]),
            places=9,
        )

        sweep_serial = evaluate_supply_temperature_sweep(
            self.config,
            load_result,
            baseline,
            parallel_options=serial_options,
        ).sort_values("supply_temp_k").reset_index(drop=True)
        sweep_parallel = evaluate_supply_temperature_sweep(
            self.config,
            load_result,
            baseline,
            parallel_options=parallel_options,
        ).sort_values("supply_temp_k").reset_index(drop=True)
        self.assertEqual(
            sweep_serial[["supply_temp_k", "selected_fluid"]].to_dict("records"),
            sweep_parallel[["supply_temp_k", "selected_fluid"]].to_dict("records"),
        )
        for column in ["pump_power_kw", "supplemental_warmup_kw", "max_feasible_distance_km"]:
            for serial_value, parallel_value in zip(sweep_serial[column], sweep_parallel[column], strict=True):
                if pd.isna(serial_value) and pd.isna(parallel_value):
                    continue
                self.assertAlmostEqual(float(serial_value), float(parallel_value), places=6)

    def test_auxiliary_heat_scenarios_rank_monotonically(self) -> None:
        load_result = compute_load_model(self.config)
        minimum_power = compute_theoretical_minimum_power(self.config, load_result.total_kw)
        baseline = compute_baseline_cycle(self.config, load_result.total_kw)
        screening = compute_fluid_screening(self.config, load_result.total_kw)
        idc_hx_result = evaluate_idc_heat_exchange(
            self.config,
            screening["selected"]["coolprop_name"],
            load_result.total_kw,
        )
        idc_secondary_loop_result = evaluate_idc_secondary_loop(self.config, idc_hx_result["chilled_water_mass_flow_kg_s"])
        pipeline_result = design_pipeline(self.config, screening["selected"], load_result.total_kw)
        hx_result = design_lng_vaporizer(
            self.config,
            _merge_fluid_with_pipeline(screening["selected"], pipeline_result),
            float(pipeline_result["selected_design"]["actual_lng_duty_kw"]),
        )
        system_eval = evaluate_system(
            self.config,
            load_result,
            minimum_power,
            baseline,
            screening,
            idc_hx_result,
            hx_result,
            pipeline_result,
            idc_secondary_loop_result,
        )
        aux_table = system_eval["auxiliary_heat_sources"]["table"].set_index("scenario_key")

        self.assertGreater(
            float(aux_table.loc["waste_heat_recovery_loop", "net_power_saving_kw"]),
            float(aux_table.loc["electric_resistance_heater", "net_power_saving_kw"]),
        )
        self.assertGreater(
            float(aux_table.loc["ambient_air_trim_heater", "net_power_saving_kw"]),
            float(aux_table.loc["electric_resistance_heater", "net_power_saving_kw"]),
        )

    def test_uncertainty_study_smoke(self) -> None:
        trial_config = deepcopy(self.config)
        trial_config["uncertainty_analysis"]["sample_count"] = 8
        result = evaluate_uncertainty_study(trial_config)
        self.assertEqual(len(result["samples"]), 8)
        self.assertIn("selected_fluid: most_common", set(result["summary"]["metric"].tolist()))
        self.assertTrue(
            (
                result["samples"]["pump_power_kw"]
                - result["samples"]["lng_loop_pump_power_kw"]
                - result["samples"]["idc_secondary_loop_pump_power_kw"]
            ).abs().max()
            < 1e-6
        )
        self.assertIn("core_system_power_kw: mean", set(result["summary"]["metric"].tolist()))

    def test_discounted_payback_includes_salvage(self) -> None:
        no_salvage_config = deepcopy(self.config)
        no_salvage_config["economic_inputs"]["financial"]["salvage_fraction_of_capex"] = 0.0
        no_salvage_config["economic_inputs"]["financial"]["project_life_years"] = 5
        salvage_config = deepcopy(self.config)
        salvage_config["economic_inputs"]["financial"]["salvage_fraction_of_capex"] = 0.25
        salvage_config["economic_inputs"]["financial"]["project_life_years"] = 5
        no_salvage_metrics = compute_financial_metrics(
            no_salvage_config,
            total_capex_krw=1_000.0,
            annual_cost_saving_krw=230.0,
        )
        metrics = compute_financial_metrics(
            salvage_config,
            total_capex_krw=1_000.0,
            annual_cost_saving_krw=230.0,
        )
        self.assertTrue(pd.isna(no_salvage_metrics["discounted_payback_years"]))
        self.assertFalse(pd.isna(metrics["discounted_payback_years"]))

    def test_idc_secondary_loop_scan_behaviour(self) -> None:
        load_result = compute_load_model(self.config)
        screening = compute_fluid_screening(self.config, load_result.total_kw)
        idc_hx_result = evaluate_idc_heat_exchange(
            self.config,
            screening["selected"]["coolprop_name"],
            load_result.total_kw,
        )
        result = evaluate_idc_secondary_loop(self.config, idc_hx_result["chilled_water_mass_flow_kg_s"])
        ordered = result["scan_table"].sort_values("diameter_m")
        self.assertTrue(ordered["velocity_m_per_s"].is_monotonic_decreasing)
        self.assertTrue(bool(ordered["feasible"].any()))


if __name__ == "__main__":
    unittest.main()
