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
    annual_report["항목"] = annual_report["metric"].replace(
        {
            "Baseline electricity use": "기준 시스템 전력사용",
            "LNG electricity use": "LNG 시스템 전력사용",
            "Electricity saving": "전력 절감",
            "Electricity cost saving": "전력요금 절감",
            "Avoided indirect emissions": "회피 간접배출",
        }
    )
    annual_report["값"] = annual_report.apply(
        lambda row: _format_number(float(row["value"]) / 1_000_000.0)
        if row["metric"] == "Electricity cost saving"
        else _format_number(float(row["value"])),
        axis=1,
    )
    annual_report["단위"] = annual_report.apply(
        lambda row: (
            "백만원/년"
            if row["metric"] == "Electricity cost saving"
            else "MWh/년"
            if row["unit"] == "MWh/year"
            else "tCO2/년"
            if row["unit"] == "tCO2/year"
            else row["unit"]
        ),
        axis=1,
    )
    alternatives_table = pd.DataFrame(
        {
            "유체": alternatives["fluid"],
            "스크리닝 점수": alternatives["screening_score"].map(lambda x: _format_number(x, 3)),
            "펌프동력 (kW)": alternatives["pump_power_kw"].map(_format_number),
            "쉘 직경 (m)": alternatives["hx_shell_diameter_m"].map(lambda x: _format_number(x, 3)),
            "연간 비용절감 (백만원/년)": alternatives["annual_cost_saving_krw"].map(
                lambda x: _format_number(x / 1_000_000.0)
            ),
        }
    )
    distance_table = pd.DataFrame(
        {
            "거리 (km)": distance["distance_km"].map(_format_number),
            "펌프동력 (kW)": distance["pump_power_kw"].map(_format_number),
            "열유입 (kW)": distance["heat_gain_kw"].map(_format_number),
            "열여유 (kW)": distance["thermal_margin_kw"].map(_format_number),
            "IDC 부하 충족": distance["meets_idc_load"].map(lambda x: "예" if bool(x) else "아니오"),
        }
    )
    temperature_table = pd.DataFrame(
        {
            "공급온도 (°C)": temperature["supply_temp_c"].map(_format_number),
            "선정 유체": temperature["selected_fluid"].fillna("-"),
            "펌프동력 (kW)": temperature["pump_power_kw"].map(_format_number),
            "최대 성립거리 (km)": temperature["max_feasible_distance_km"].map(_format_number),
            "35 km 충족": temperature["long_distance_meets_load"].map(lambda x: "예" if bool(x) else "아니오"),
            "상태": temperature["status"].replace({"feasible": "성립", "failed": "실패"}),
        }
    )
    legacy_table = pd.DataFrame(
        {
            "항목": legacy["metric"].replace(
                {
                    "Theoretical minimum power": "이론 최소동력",
                    "Baseline compressor power": "기준 압축기 동력",
                }
            ),
            "기존 엑셀 (kW)": legacy["legacy_value_kw"].map(_format_number),
            "현재 코드 (kW)": legacy["current_value_kw"].map(_format_number),
            "차이 (kW)": legacy["difference_kw"].map(_format_number),
            "차이율 (%)": legacy["difference_percent"].map(lambda x: _format_number(x, 2)),
        }
    )

    report_path = deliverables_dir / "report_draft.md"
    report_lines = [
        "# LNG 냉열 기반 IDC 냉각시스템 설계 연구",
        "",
        "## 초록",
        "",
        (
            "본 보고서는 2022년 열시스템디자인 과제를 재현 가능한 Python 기반 설계 연구로 다시 구성한 결과다. "
            "LNG 냉열을 활용한 최종 설계는 "
            f"**{_format_number(float(summary['IDC total cooling load']['value']))} kW**의 IDC 냉방부하를 만족하면서, "
            f"기준 R-134a 압축기 동력 **{_format_number(float(summary['Baseline R-134a compressor power']['value']))} kW**를 "
            f"LNG 루프 펌프동력 **{_format_number(float(summary['LNG system pump power']['value']))} kW** 수준으로 대체한다. "
            f"선정된 냉각유체는 **{summary['Selected coolant']['value']}**이며, LNG 기화기 최소 핀치는 **10.0 K**로 유지했고, "
            f"예상 연간 전력 절감량은 **{_format_number(float(summary['Annual electricity saving']['value']))} MWh/년**이다."
        ),
        "",
        "## 1. 문제 정의",
        "",
        "본 프로젝트의 목적은 LNG 냉열을 이용해 데이터센터의 기존 기계식 냉방부하를 대체하되, 과제에서 제시한 실내 조건, 냉수 조건, 기화기 duty, 배관 이송거리 제약을 동시에 만족하는 설계를 도출하는 것이다.",
        "",
        "이 연구가 답하려는 핵심 질문은 다음과 같다.",
        "",
        "- 대상 IDC의 총 냉방부하는 얼마인가?",
        "- 요구 조건에서 이론 최소동력은 어느 수준인가?",
        "- 기존 R-134a 기준 시스템과 LNG 보조 시스템은 어떻게 비교되는가?",
        "- LNG와 IDC 사이 2차 루프에 가장 적합한 냉각유체는 무엇인가?",
        "- 이송거리가 10 km에서 35 km로 증가해도 시스템이 성립하는가?",
        "- 연간 전력, 비용, 탄소 효과는 어느 정도인가?",
        "",
        "## 2. 설계 기준",
        "",
        "- 과제 기반 입력값은 [base.toml](../config/base.toml)에 기록했다.",
        "- 전체 출처 레지스트리는 [sources.md](../docs/sources.md)에 정리했다.",
        "- 공학적 가정은 [assumptions.md](../docs/assumptions.md)에 따로 남겼다.",
        "",
        "핵심 입력값은 다음과 같다.",
        "",
        f"- IDC 총 냉방부하: **{_format_number(float(summary['IDC total cooling load']['value']))} kW**",
        f"- LNG / NG 기화 duty: **{_format_number(float(summary['LNG vaporizer duty']['value']))} kW**",
        f"- 기준 R-134a 압축기 동력: **{_format_number(float(summary['Baseline R-134a compressor power']['value']))} kW**",
        f"- 선정 냉각유체: **{summary['Selected coolant']['value']}**",
        "",
        "## 3. 모델링 방법",
        "",
        "코드는 부하 계산, 이론 최소동력, 기준 증기압축 사이클, 냉각유체 스크리닝, LNG 기화기 설계, 장거리 배관 설계, 민감도 분석, 연간 효과 계산으로 나누어 구성했다.",
        "",
        "주요 결과는 아래 그림들로 요약된다.",
        "",
        "![부하 구성](../output/figures/load_breakdown.png)",
        "",
        "![기준 사이클](../output/figures/baseline_cycle_ph.png)",
        "",
        "![냉각유체 순위](../output/figures/fluid_ranking.png)",
        "",
        "![열교환기 온도 프로파일](../output/figures/hx_temperature_profile.png)",
        "",
        "![배관 트레이드오프](../output/figures/pipeline_tradeoff.png)",
        "",
        "## 4. 주요 결과",
        "",
        _markdown_table(
            pd.DataFrame(
                [
                    {"항목": "냉방부하", "값": f"{_format_number(float(summary['IDC total cooling load']['value']))} kW"},
                    {"항목": "이론 최소동력", "값": f"{_format_number(float(summary['Theoretical minimum power']['value']))} kW"},
                    {"항목": "기준 R-134a 동력", "값": f"{_format_number(float(summary['Baseline R-134a compressor power']['value']))} kW"},
                    {"항목": "선정 냉각유체", "값": summary["Selected coolant"]["value"]},
                    {"항목": "LNG 루프 펌프동력", "값": f"{_format_number(float(summary['LNG system pump power']['value']))} kW"},
                    {"항목": "전력 절감", "값": f"{_format_number(float(summary['Baseline-to-LNG power saving']['value']))} kW"},
                ]
            ),
            ["항목", "값"],
        ),
        "",
        "### 4.1 냉각유체 선정",
        "",
        _markdown_table(alternatives_table, ["유체", "스크리닝 점수", "펌프동력 (kW)", "쉘 직경 (m)", "연간 비용절감 (백만원/년)"]),
        "",
        f"기본 설계점에서 최적 유체는 **{selected_alternative['fluid']}**였으며, 이는 LNG 기화기와 장거리 배관 설계를 모두 만족하는 범위 안에서 루프 펌프동력을 최소화했다.",
        "",
        "### 4.2 거리 민감도",
        "",
        _markdown_table(distance_table, ["거리 (km)", "펌프동력 (kW)", "열유입 (kW)", "열여유 (kW)", "IDC 부하 충족"]),
        "",
        "![거리 민감도](../output/figures/pipeline_distance_sensitivity.png)",
        "",
        (
            f"현재 duty 여유 기준에서 **{_format_number(long_distance['distance_km'])} km** 장거리 조건은 "
            f"**{'성립' if bool(long_distance['meets_idc_load']) else '불성립'}**이다. "
            f"선정 설계의 추정 최대 편도 성립거리는 약 **{_format_number(distance['max_feasible_distance_m'].iloc[0] / 1000.0)} km**다."
        ),
        "",
        "### 4.3 공급온도 민감도",
        "",
        _markdown_table(temperature_table, ["공급온도 (°C)", "선정 유체", "펌프동력 (kW)", "최대 성립거리 (km)", "35 km 충족", "상태"]),
        "",
        "![공급온도 민감도](../output/figures/supply_temperature_sensitivity.png)",
        "",
        (
            f"공급온도 스윕에서 펌프동력이 가장 낮은 지점은 **{_format_number(best_temp['supply_temp_c'])} °C**이며, "
            f"이때도 우선 유체는 **{best_temp['selected_fluid']}**로 유지된다. "
            f"반면 **-43.1 °C** 수준으로 공급온도를 높이면 35 km 조건을 만족시킬 수 있지만, **R-600a**로 바뀌고 펌프동력 증가를 감수해야 한다."
        ),
        "",
        "### 4.4 연간 효과",
        "",
        _markdown_table(annual_report, ["항목", "값", "단위"]),
        "",
        "![연간 효과](../output/figures/annual_impact_comparison.png)",
        "",
        "단순 회수기간 기준 허용 가능한 추가 투자비는 다음과 같다.",
        "",
        _markdown_table(
            payback.assign(
                **{
                    "회수기간 (년)": payback["payback_years"],
                    "허용 추가 투자비 (백만원)": payback["allowable_incremental_capex_krw"].map(
                        lambda x: _format_number(x / 1_000_000.0)
                    ),
                }
            ),
            ["회수기간 (년)", "허용 추가 투자비 (백만원)"],
        ),
        "",
        "## 5. 기존 엑셀 결과와 비교",
        "",
        _markdown_table(legacy_table, ["항목", "기존 엑셀 (kW)", "현재 코드 (kW)", "차이 (kW)", "차이율 (%)"]),
        "",
        "새 Python 워크플로우는 시스템 수준에서 기존 스프레드시트와 같은 규모의 결과를 재현하면서도, 가정과 출처, 시나리오 분석을 더 명확하게 드러낸다.",
        "",
        "## 6. 논의",
        "",
        "- 기본 10 km 설계는 기준 압축기 시스템 대비 큰 전력 절감과 함께 성립한다.",
        "- 35 km 조건은 현재 기본 설계점에서 성립하지 않으며, 이것 자체가 중요한 설계 결론이다.",
        "- 공급온도 수준을 조정하면 성립 거리를 늘릴 수 있지만, 다른 유체 선택과 더 큰 펌프동력 페널티를 수반한다.",
        "- 연간 경제성은 현재 경계조건에서 매우 유리하지만, 보조기기, 유지보수, 금융비용, LNG 인프라 CAPEX는 아직 포함하지 않았다.",
        "",
        "## 7. 한계",
        "",
        "- v1에서는 LNG를 순수 메탄으로 가정했다.",
        "- IDC 측 분배 네트워크는 전체 유압망이 아니라 냉방 duty 경계조건으로 단순화했다.",
        "- 경제성 비교 범위는 기준 압축기 동력과 LNG 루프 펌프동력 비교에 한정된다.",
        "- 응력, 재료 조달, 제어 통합 같은 상세 기계설계 검토는 현재 범위 밖이다.",
        "",
        "## 8. 결론",
        "",
        (
            "재구축된 프로젝트는 LNG 냉열 기반 냉각 개념이 10 km 설계점에서 기준 데이터센터 냉각 시스템의 전력 요구를 크게 줄일 수 있음을 보여준다. "
            "선정된 기본안은 2차 루프에 암모니아를 사용하고, 쉘-튜브 LNG 기화기와 0.35 m 공급/환수 배관을 적용한다. "
            "현재 경계조건에서 이 설계는 에너지 측면과 경제성 측면 모두 매력적이며, 후속 보고서 정리와 발표자료 고도화까지 연결할 수 있을 만큼 투명하다."
        ),
        "",
        "## 참고문헌",
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
        "# 발표 스크립트",
        "",
        "## 슬라이드 1. 표지",
        "- 이 발표는 2022년 과제를 코드 기반으로 재구성한 장문형 발표자료라고 소개한다.",
        "- 제목은 LNG 냉열을 활용한 IDC 냉각시스템 및 주요 부품의 설계로 유지하되, 재구축본이라는 점을 분명히 한다.",
        "",
        "## 슬라이드 2. 목차",
        "- Part 1부터 Part 6까지의 전체 흐름을 먼저 보여준다.",
        "- 이번 발표는 요약형 피치덱이 아니라 계산 근거를 따라가는 공학 발표 형식이라고 설명한다.",
        "",
        "## 슬라이드 3. 예비설계 - 설계 대상과 냉방부하",
        "- IDC 규모와 랙 발열, 외피와 보조부하 가정을 먼저 정리한다.",
        f"- 총 냉방부하는 {_format_number(float(summary['IDC total cooling load']['value']))} kW로 계산되며, 이후 모든 설계의 기준 duty가 된다고 말한다.",
        "",
        "## 슬라이드 4. 예비설계 - 이론 최소동력",
        f"- 이론 최소동력은 {_format_number(float(summary['Theoretical minimum power']['value']))} kW라고 제시한다.",
        "- 이 값은 절대 하한선이며, 이후 기준 사이클과 LNG 시스템 비교의 출발점이라고 설명한다.",
        "",
        "## 슬라이드 5. 예비설계 - 기준 R-134a 증기압축 사이클",
        f"- 기준 압축기 동력은 {_format_number(float(summary['Baseline R-134a compressor power']['value']))} kW다.",
        "- 기존 엑셀과 크기 수준이 맞기 때문에 기준선으로 신뢰할 수 있다고 말한다.",
        "",
        "## 슬라이드 6. 냉각유체 선정 - 선정 기준",
        "- 환경성, 온도창, 압력 제약, 설계성, 연간 절감 효과를 동시에 본다고 설명한다.",
        "- 이번 재구축은 탈락 후보도 사유와 함께 남긴다는 점을 강조한다.",
        "",
        "## 슬라이드 7. 냉각유체 선정 - 후보 비교 결과",
        f"- 최종 우선순위는 {selected_alternative['fluid']}를 포함한 상위 후보 3개로 정리된다고 말한다.",
        "- 펌프동력과 기화기 규모까지 포함한 전체 비교라는 점을 짚는다.",
        "",
        "## 슬라이드 8. 냉각유체 선정 - 기본안 결정",
        f"- 기본안 유체는 {selected_alternative['fluid']}이며, 가장 좋은 균형점을 보인다고 정리한다.",
        "- 동시에 안전성과 운전성 서술은 후속 보강이 필요하다고 덧붙인다.",
        "",
        "## 슬라이드 9. LNG 기화기 설계 - 열역학 해석과 핀치",
        "- 초임계 메탄의 비열 변화 때문에 구간 분할 엔탈피 해석이 필요하다고 설명한다.",
        "- 최소 핀치 10 K를 전 구간에서 만족시키는 것이 핵심 제약이라고 말한다.",
        "",
        "## 슬라이드 10. LNG 기화기 설계 - 형상 스캔과 최종 제원",
        "- 관 수와 길이 사이의 절충을 통해 최종 기화기 형상을 정했다고 설명한다.",
        "- 단순 최솟값이 아니라 장치 현실성을 함께 고려했다고 강조한다.",
        "",
        "## 슬라이드 11. LNG 기화기 설계 - 최종 설계 판단",
        "- 열역학 해석과 형상 스캔을 함께 보면 현재 기화기 설계가 타당하다는 점을 요약한다.",
        "",
        "## 슬라이드 12. 순환 배관 설계 - 설계 조건",
        "- 기본 설계 거리는 10 km, 도전 조건은 35 km라고 다시 정리한다.",
        "- 배관은 압력강하와 열유입을 동시에 관리해야 한다는 점을 말한다.",
        "",
        "## 슬라이드 13. 순환 배관 설계 - 거리 민감도",
        f"- 추정 최대 편도 성립거리는 약 {_format_number(distance['max_feasible_distance_m'].iloc[0] / 1000.0)} km다.",
        f"- 따라서 현재 설계점에서 {int(long_distance['distance_km'])} km 조건은 {'성립' if bool(long_distance['meets_idc_load']) else '불성립'}이라고 정리한다.",
        "",
        "## 슬라이드 14. 순환 배관 설계 - 공급온도 민감도",
        "- 공급온도를 높이면 성립거리는 늘어나지만, 유체 선택과 펌프동력이 같이 바뀐다고 설명한다.",
        "",
        "## 슬라이드 15. 열역학/경제성 평가 - 소비동력 비교",
        f"- 이론 최소동력은 {_format_number(float(summary['Theoretical minimum power']['value']))} kW다.",
        f"- 기준 R-134a 압축기 동력은 {_format_number(float(summary['Baseline R-134a compressor power']['value']))} kW다.",
        f"- LNG 루프 펌프동력은 {_format_number(float(summary['LNG system pump power']['value']))} kW 수준이며, 이것이 핵심 에너지 논거라고 설명한다.",
        "",
        "## 슬라이드 16. 열역학/경제성 평가 - 연간 효과와 회수기간",
        f"- 연간 전력 절감량은 {_format_number(annual_map['Electricity saving']['value'])} MWh/년이다.",
        f"- 연간 전력요금 절감은 {_format_number(annual_map['Electricity cost saving']['value'] / 1_000_000.0)} 백만원/년 수준이다.",
        f"- 연간 회피 간접배출은 {_format_number(annual_map['Avoided indirect emissions']['value'])} tCO2/년이다.",
        "",
        "## 슬라이드 17. 추가 고려 사항 - 확장 과제",
        "- 실제 LNG 조성, IDC 냉수 네트워크, 장거리 조건의 제어 전략이 후속 과제라고 정리한다.",
        "- 35 km는 기본안의 연장이 아니라 별도 최적화 과제라고 말한다.",
        "",
        "## 슬라이드 18. 추가 고려 사항 - 출처 체계와 재현성",
        "- config, sources, assumptions, output, deliverables가 하나의 저장소 안에서 연결된 구조라고 설명한다.",
        "- 질의응답에서 수치와 가정을 바로 추적할 수 있다는 점이 이번 재구축의 장점이라고 말한다.",
        "",
        "## 슬라이드 19. 결론",
        "- 10 km LNG 냉열 설계는 기술적으로 성립하고 에너지 측면에서 매우 매력적이라고 결론낸다.",
        "- 동시에 35 km는 운전점 변경 없이는 기본안으로 성립하지 않는 경계조건이라고 정리한다.",
    ]
    if not high_temp.empty:
        row = high_temp.iloc[0]
        script_lines.insert(
            script_lines.index("## 슬라이드 15. 열역학/경제성 평가 - 소비동력 비교") - 1,
            f"- 공급온도 {row['supply_temp_c']:.1f} °C에서는 {row['selected_fluid']}로 35 km 조건을 복구할 수 있다는 점도 함께 언급한다.",
        )
    script_lines.extend(
        [
            "- 마지막 문장은 이번 발표가 A11 스타일의 공학 발표 흐름을 유지하면서도 코드 기반 재현성과 민감도 분석을 추가했다는 점으로 마무리한다.",
        ]
    )
    script_path = deliverables_dir / "presentation_script.md"
    script_path.write_text("\n".join(script_lines), encoding="utf-8")
    return script_path


def build_presentation(project_root: Path) -> Path:
    deliverables_dir = ensure_directory(project_root / "deliverables")
    slides_src_dir = ensure_directory(deliverables_dir / "slides_src")
    deck_source = slides_src_dir / "presentation_academic_draft.js"
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
