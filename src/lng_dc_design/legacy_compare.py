from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import load_workbook


def compare_with_legacy_excel(project_root: Path, baseline: dict, minimum_power: dict) -> dict[str, object]:
    legacy_path = project_root / "references" / "local" / "legacy_heat_exchanger_design.xlsx"
    if not legacy_path.exists():
        return {
            "available": False,
            "path": str(legacy_path),
            "table": pd.DataFrame(),
        }

    workbook = load_workbook(legacy_path, data_only=True, read_only=True)
    sheet = workbook["기존 증기압축 사이클"]
    legacy_wmin_mw = float(sheet["B3"].value)
    legacy_power_mw = float(sheet["C3"].value)

    table = pd.DataFrame(
        [
            {
                "metric": "Theoretical minimum power",
                "legacy_value_kw": legacy_wmin_mw * 1000.0,
                "current_value_kw": minimum_power["minimum_power_kw"],
                "difference_kw": minimum_power["minimum_power_kw"] - legacy_wmin_mw * 1000.0,
                "difference_percent": 100.0 * (minimum_power["minimum_power_kw"] - legacy_wmin_mw * 1000.0) / (legacy_wmin_mw * 1000.0),
            },
            {
                "metric": "Baseline compressor power",
                "legacy_value_kw": legacy_power_mw * 1000.0,
                "current_value_kw": baseline["compressor_power_kw"],
                "difference_kw": baseline["compressor_power_kw"] - legacy_power_mw * 1000.0,
                "difference_percent": 100.0 * (baseline["compressor_power_kw"] - legacy_power_mw * 1000.0) / (legacy_power_mw * 1000.0),
            },
        ]
    )
    return {
        "available": True,
        "path": str(legacy_path),
        "table": table,
        "legacy_wmin_kw": legacy_wmin_mw * 1000.0,
        "legacy_baseline_power_kw": legacy_power_mw * 1000.0,
    }
