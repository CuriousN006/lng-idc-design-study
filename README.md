# LNG IDC Design

2022년 `LNG 냉열 활용 데이터센터 냉각시스템` 과제를 Python 코드로 재구축한 프로젝트입니다.

## Quick Start

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python -m lng_dc_design run-all --config config/base.toml
python -m unittest discover -s tests
```

## Main Commands

```powershell
python -m lng_dc_design run-all --config config/base.toml
python -m lng_dc_design screen-fluids --config config/base.toml
python -m lng_dc_design design-hx --config config/base.toml
python -m lng_dc_design analyze-pipeline --config config/base.toml
python -m lng_dc_design scenario-study --config config/base.toml
python -m lng_dc_design build-report --config config/base.toml
python -m lng_dc_design build-slides --config config/base.toml
python -m lng_dc_design build-deliverables --config config/base.toml
python -m lng_dc_design compare-legacy --config config/base.toml
python -m lng_dc_design validate --config config/base.toml
```

## Output

- `output/summary.csv`
- `output/fluid_ranking.csv`
- `output/alternative_designs.csv`
- `output/distance_scenarios.csv`
- `output/supply_temperature_sweep.csv`
- `output/annual_summary.csv`
- `output/payback_allowable_capex.csv`
- `output/requirement_traceability.csv`
- `output/source_map.csv`
- `output/report_summary.md`
- `output/figures/*.png`
- `deliverables/report_draft.md`
- `deliverables/presentation_script.md`
- `deliverables/presentation_draft.pptx`
