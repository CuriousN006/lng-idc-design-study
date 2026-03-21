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

`build-slides`와 `build-deliverables`는 로컬 `deliverables/slides_src/`의 PptxGenJS 소스를 사용합니다.  
Node.js가 설치되어 있으면 첫 실행 시 `node_modules/`가 해당 폴더 안에 자동으로 생성됩니다.

## Main Commands

```powershell
python -m lng_dc_design run-all --config config/base.toml
python -m lng_dc_design screen-fluids --config config/base.toml
python -m lng_dc_design design-hx --config config/base.toml
python -m lng_dc_design analyze-pipeline --config config/base.toml
python -m lng_dc_design analyze-aux-heat --config config/base.toml
python -m lng_dc_design scenario-study --config config/base.toml
python -m lng_dc_design explore-passive-heat --config config/base.toml
python -m lng_dc_design uncertainty-study --config config/base.toml
python -m lng_dc_design build-report --config config/base.toml
python -m lng_dc_design build-slides --config config/base.toml
python -m lng_dc_design build-deliverables --config config/base.toml
python -m lng_dc_design compare-legacy --config config/base.toml
python -m lng_dc_design validate --config config/base.toml
```

병렬 실행이 필요하면 `--workers N`을 붙일 수 있습니다. 현재 기준으로는 `explore-passive-heat`처럼 큰 탐색에서 병렬화 이득이 크고, `run-all`이나 `validate`는 물성 캐시 이후 직렬이 더 빠를 수 있습니다.

## Output

- `output/summary.csv`
- `output/fluid_ranking.csv`
- `output/alternative_designs.csv`
- `output/distance_scenarios.csv`
- `output/supply_temperature_sweep.csv`
- `output/annual_summary.csv`
- `output/auxiliary_heat_sources.csv`
- `output/uncertainty_samples.csv`
- `output/uncertainty_summary.csv`
- `output/payback_allowable_capex.csv`
- `output/requirement_traceability.csv`
- `output/source_map.csv`
- `output/report_summary.md`
- `output/figures/*.png`
- `deliverables/report_draft.md`
- `deliverables/presentation_script.md`
- `deliverables/presentation_draft.pptx`
- `deliverables/slides_src/presentation_draft.js`
