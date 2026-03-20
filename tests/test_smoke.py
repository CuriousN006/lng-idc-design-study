from __future__ import annotations

import unittest
from pathlib import Path

from lng_dc_design.baseline_vcc import compute_baseline_cycle
from lng_dc_design.cli import run_all
from lng_dc_design.config import load_config
from lng_dc_design.deliverables import build_deliverables
from lng_dc_design.fluid_screening import compute_fluid_screening
from lng_dc_design.hx_lng_vaporizer import design_lng_vaporizer
from lng_dc_design.load_model import compute_load_model
from lng_dc_design.pipeline_loop import design_pipeline
from lng_dc_design.scenario_study import build_distance_scenarios, evaluate_feasible_alternatives, evaluate_supply_temperature_sweep
from lng_dc_design.system_eval import evaluate_system
from lng_dc_design.thermo_limit import compute_theoretical_minimum_power


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
        hx_result = design_lng_vaporizer(self.config, screening["selected"], screening["total_lng_duty_kw"])
        pipeline_result = design_pipeline(self.config, screening["selected"], load_result.total_kw, hx_result)
        scenario_result = evaluate_feasible_alternatives(self.config, load_result, baseline, screening)
        distance_scenarios = build_distance_scenarios(self.config, load_result, baseline, hx_result, pipeline_result)
        supply_temperature_sweep = evaluate_supply_temperature_sweep(self.config, load_result, baseline)
        system_eval = evaluate_system(self.config, load_result, minimum_power, baseline, screening, hx_result, pipeline_result)

        self.assertGreater(load_result.total_kw, 11_000.0)
        self.assertGreater(baseline["compressor_power_kw"], minimum_power["minimum_power_kw"])
        self.assertGreaterEqual(hx_result["min_pinch_k"], self.config["assignment"]["minimum_temperature_approach_k"])
        self.assertGreaterEqual(system_eval["available_to_idc_kw"], load_result.total_kw)
        self.assertFalse(scenario_result["alternatives"].empty)
        self.assertTrue(bool(distance_scenarios.iloc[0]["meets_idc_load"]))
        self.assertIn(False, set(distance_scenarios["meets_idc_load"].tolist()))
        self.assertGreaterEqual(len(supply_temperature_sweep), 2)
        self.assertIn("feasible", set(supply_temperature_sweep["status"].tolist()))
        self.assertGreater(system_eval["annual"]["cost_saving_krw_per_year"], 0.0)

    def test_build_deliverables(self) -> None:
        run_all(self.project_root / "config" / "base.toml")
        built = build_deliverables(self.project_root)
        self.assertTrue(built["report"].exists())
        self.assertTrue(built["script"].exists())
        self.assertTrue(built["presentation"].exists())


if __name__ == "__main__":
    unittest.main()
