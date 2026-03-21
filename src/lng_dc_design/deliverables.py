from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pandas as pd

from .config import load_config
from .load_model import compute_load_model
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


def _parse_assumptions(assumptions_path: Path) -> dict[str, dict[str, str]]:
    entries: dict[str, dict[str, str]] = {}
    for line in assumptions_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ASM-"):
            continue
        parts = [part.strip() for part in line.strip().split("|")[1:-1]]
        if len(parts) < 4:
            continue
        entries[parts[0]] = {
            "assumption": parts[1],
            "value": parts[2],
            "why": parts[3],
        }
    return entries


def _math_block(*lines: str) -> list[str]:
    return ["```math", *lines, "```", ""]


def _source_note(source_ids: str) -> str:
    return f"*출처 ID: {source_ids}*"


def _config_source_id(project_config, dotted_path: str) -> str:
    citation = project_config.citations.get(dotted_path)
    return citation.source_id if citation else "-"


def _format_celsius(temperature_k: float) -> str:
    return f"{temperature_k - 273.15:.1f}"


def _build_report_front_matter(ctx: dict[str, object]) -> list[str]:
    return [
        "# LNG 냉열 기반 IDC 냉각시스템 설계 연구",
        "",
        "> 이 문서는 GitHub Markdown 수식 렌더링을 고려해 `math` 코드 블록과 inline LaTeX 표기를 사용했다.",
        "",
        "## 초록",
        "",
        (
            "본 연구는 2022년 열시스템디자인 과제를 재현 가능한 코드 기반 설계 연구로 다시 구성한 결과물이다. "
            f"대상 IDC의 총 냉방부하는 **{ctx['total_load_kw']} kW**로 계산되었고, "
            f"이론 최소동력은 **{ctx['minimum_power_kw']} kW**, "
            f"기준 R-134a 증기압축 시스템의 압축기 동력은 **{ctx['baseline_power_kw']} kW**로 산정되었다. "
            f"이에 비해 LNG 냉열 기반 시스템은 **{ctx['selected_coolant']}**를 2차 루프 냉각유체로 사용할 때 "
            f"LNG 기화 duty **{ctx['lng_duty_kw']} kW**, 배관 열유입 **{ctx['pipeline_heat_gain_kw']} kW**, "
            f"LNG 순환펌프 **{ctx['lng_loop_pump_kw']} kW**와 IDC 2차 루프 펌프 **{ctx['idc_secondary_pump_kw']} kW**를 포함한 "
            f"핵심 전동부하 **{ctx['core_power_kw']} kW**의 {ctx['base_distance_status']} 설계가 가능했다. "
            f"그 결과 기준 시스템 대비 전력 절감은 **{ctx['power_saving_kw']} kW**, "
            f"연간 전력 절감은 **{ctx['annual_saving_mwh']} MWh/년**, "
            f"연간 비용 절감은 **{ctx['annual_cost_saving_mkrw']} 백만원/년**, "
            f"연간 회피 배출은 **{ctx['annual_avoided_tco2']} tCO2/년**으로 평가되었다. "
            f"대표 혼합 LNG는 **{ctx['lng_stream_model']}**으로 모델링했고, "
            f"10 km 기본안 기준 핵심 설비 CAPEX는 **{ctx['core_capex_bkrw']} 십억원**, NPV는 **{ctx['core_npv_bkrw']} 십억원**으로 추정되었다. "
            f"현재 운전점에서의 추정 최대 하이브리드 성립거리는 약 **{ctx['max_distance_km']} km**, "
            f"기본 LNG duty 기준 최대 성립거리는 약 **{ctx['max_base_distance_km']} km**이며, "
            f"35 km 조건은 **{ctx['long_distance_status']}**으로 판정되었다."
        ),
        "",
        _source_note("SRC-001,SRC-004,SRC-005,SRC-006,SRC-007,SRC-008,SRC-010,SRC-013,SRC-014,SRC-019,SRC-020,SRC-021,SRC-022,SRC-023,SRC-024,SRC-025,ASM-020,ASM-033,ASM-034,ASM-035,ASM-055,ASM-056,ASM-057,ASM-058,ASM-059,ASM-060,ASM-061,ASM-062,ASM-063,ASM-064,ASM-065,ASM-066,ASM-067,ASM-068,ASM-069"),
        "",
        "## 1. 서론",
        "",
        (
            "데이터센터는 상시 운전되는 고발열 시설이며, 냉방 시스템은 전체 전력 수요의 상당 부분을 차지한다. "
            "따라서 데이터센터 냉각을 기계식 압축기 중심으로만 해결하는 접근은 에너지 비용과 전력 인프라 부담을 동시에 키운다. "
            "반면 LNG 기화 과정은 극저온의 냉열을 본질적으로 포함하므로, 이를 적절히 회수하면 대규모 냉방부하를 낮은 동력으로 처리할 수 있다."
        ),
        "",
        (
            "이번 재구축의 목표는 단순히 예전 엑셀 파일을 재현하는 것이 아니라, 설계 가정과 출처, 계산식, 민감도 분석, "
            "산출물을 하나의 저장소 안에서 다시 생성할 수 있는 구조로 바꾸는 것이었다. 즉, 결과값만 맞추는 프로젝트가 아니라 "
            "왜 그 결과가 나오는지까지 추적 가능한 프로젝트로 재정의했다."
        ),
        "",
        "이 보고서가 답하려는 핵심 질문은 다음과 같다.",
        "",
        "1. 대상 IDC의 총 냉방부하는 얼마인가?",
        "2. 해당 부하에 대한 이론 최소동력과 기존 증기압축 기준선은 어느 수준인가?",
        "3. LNG와 IDC를 연결하는 2차 루프에는 어떤 냉각유체가 가장 적합한가?",
        "4. LNG 기화기와 장거리 배관을 동시에 만족하는 설계점은 존재하는가?",
        "5. 10 km 기본 설계와 35 km 확장 조건은 어떤 차이를 보이는가?",
        "6. 연간 에너지, 비용, 탄소 효과는 어느 정도인가?",
        "",
        _source_note("SRC-001,SRC-009,SRC-011"),
        "",
        "## 2. 문제 정의와 입력 조건",
        "",
        (
            "과제에서 제시된 기본 경계조건은 랙 수, 랙당 발열, 실내 공기 조건, 냉수 조건, LNG 압력과 온도, "
            "기화기 최소 접근온도, 기본 이송거리와 확장 이송거리로 구성된다. 이 조건들은 [base.toml](../config/base.toml)에 "
            "정리되어 있으며, 각 항목에는 원문 출처 또는 가정 ID가 함께 연결되어 있다."
        ),
        "",
        str(ctx["input_conditions_md"]),
        "",
        (
            "또한 과제 원문에 직접 주어지지 않는 층고, 틈새바람, 외피 열관류율, 배관 roughness, "
            "단열 두께 스캔 범위 등은 별도의 공학 가정으로 관리했다. 이 가정들은 결과를 임의로 조정하기 위한 숫자가 아니라, "
            "설계 자동화를 위해 반드시 필요한 기본값들이다."
        ),
        "",
        _source_note("SRC-001,ASM-001,ASM-007,ASM-014,ASM-015,ASM-019,ASM-020,ASM-024,ASM-025,ASM-027,ASM-028,ASM-029,ASM-033,ASM-034,ASM-035"),
        "",
        "## 3. 수학적 모델",
        "",
        (
            "본 연구의 계산 체계는 부하 모델, 이론 최소동력, 기준 냉동사이클, 냉각유체 스크리닝, "
            "LNG 기화기 상세설계, 장거리 배관 설계, 연간 효과 평가의 7개 모듈로 구성된다. "
            "각 모듈은 하나의 독립 계산기라기보다, 앞 단계의 결과를 다음 단계의 입력으로 넘기는 연속 설계 파이프라인이다."
        ),
        "",
    ]


def _build_report_model_sections(ctx: dict[str, object]) -> list[str]:
    lines = [
        "### 3.1 냉방부하 모델",
        "",
        (
            "냉방부하 모델은 IT 랙 발열뿐 아니라 전력 분배 손실, 조명, 부대설비, 인체 발열, 외피 전도, 일사, "
            "틈새바람에 의한 외기 유입을 모두 더해 총 냉방부하를 산정한다. 현재 구현은 `load_model.py`에 있으며, "
            "부하를 하나의 lumped load가 아니라 항목별 합산으로 계산한다."
        ),
        "",
    ]
    lines.extend(
        _math_block(
            r"\dot Q_{\mathrm{total}} = \dot Q_{\mathrm{IT}} + \dot Q_{\mathrm{dist}} + \dot Q_{\mathrm{light}} + \dot Q_{\mathrm{aux}} + \dot Q_{\mathrm{occ}} + \dot Q_{\mathrm{wall}} + \dot Q_{\mathrm{roof}} + \dot Q_{\mathrm{glz}} + \dot Q_{\mathrm{sol}} + \dot Q_{\mathrm{inf}}",
            r"\dot Q_{\mathrm{wall}} = U_{\mathrm{wall}} A_{\mathrm{wall}} (T_{\mathrm{amb}} - T_{\mathrm{room}})",
            r"\dot Q_{\mathrm{roof}} = U_{\mathrm{roof}} A_{\mathrm{roof}} (T_{\mathrm{amb}} - T_{\mathrm{room}})",
            r"\dot Q_{\mathrm{glz}} = U_{\mathrm{glz}} A_{\mathrm{glz}} (T_{\mathrm{amb}} - T_{\mathrm{room}})",
            r"\dot Q_{\mathrm{sol}} = I_{\mathrm{eff}} \cdot SHGC \cdot A_{\mathrm{glz}}",
            r"\dot Q_{\mathrm{inf}} = \dot V_{\mathrm{inf}} \rho_{\mathrm{amb}} (h_{\mathrm{amb}} - h_{\mathrm{room}})",
        )
    )
    lines.extend(
        [
            "특히 틈새바람 부하는 외기와 실내의 습공기 엔탈피 차를 사용해 평가했다.",
            "",
        ]
    )
    lines.extend(
        _math_block(
            r"w = 0.62198 \frac{p_w}{p - p_w}",
            r"h = 1000 \left(1.006 T_{^\circ\mathrm{C}} + w \left(2501 + 1.86 T_{^\circ\mathrm{C}}\right)\right)",
        )
    )
    lines.extend(
        [
            str(ctx["load_table_md"]),
            "",
            (
                f"계산 결과 총 냉방부하는 **{ctx['total_load_kw']} kW**였고, 그중 IT 랙과 전력 분배 손실이 가장 큰 비중을 차지했다. "
                "이는 데이터센터 부하의 본질이 전산장비 발열이라는 점과 일치한다."
            ),
            "",
            _source_note(str(ctx["load_source_ids"])),
            "",
            "### 3.2 이론 최소동력",
            "",
            (
                "이론 최소동력은 냉수 평균온도를 저온 열원, 외기온도를 고온 열원으로 두는 이상 카르노 냉동기의 최소 일 입력으로 계산했다. "
                "이는 실제 장치가 달성할 수 없는 절대 하한선이다."
            ),
            "",
        ]
    )
    lines.extend(
        _math_block(
            r"T_L = \frac{T_{\mathrm{cw,s}} + T_{\mathrm{cw,r}}}{2}",
            r"T_H = T_{\mathrm{amb}}",
            r"\dot W_{\min} = \dot Q_L \frac{T_H - T_L}{T_L}",
        )
    )
    lines.extend(
        [
            (
                f"냉수 평균온도는 **{ctx['chilled_mean_c']} °C**, 외기온도는 **{ctx['ambient_c']} °C**로 두었고, "
                f"계산된 이론 최소동력은 **{ctx['minimum_power_kw']} kW**였다."
            ),
            "",
            _source_note(str(ctx["minimum_power_source_ids"])),
            "",
            "### 3.3 기준 R-134a 증기압축 사이클",
            "",
            (
                "기준 시스템은 단순 R-134a 증기압축 사이클로 모델링했다. 증발기와 응축기 접근온도는 각각 10 K, "
                "압축기 등엔트로피 효율은 75%로 두었다."
            ),
            "",
        ]
    )
    lines.extend(
        _math_block(
            r"h_2 = h_1 + \frac{h_{2s} - h_1}{\eta_{\mathrm{is}}}",
            r"\dot m_{\mathrm{ref}} = \frac{\dot Q_L}{h_1 - h_4}",
            r"\dot W_{\mathrm{comp}} = \dot m_{\mathrm{ref}} (h_2 - h_1)",
            r"COP = \frac{\dot Q_L}{\dot W_{\mathrm{comp}}}",
        )
    )
    lines.extend(
        [
            (
                f"이 기준선에서 압축기 동력은 **{ctx['baseline_power_kw']} kW**로 계산되었고, 이는 기존 엑셀 결과 "
                f"**{ctx['legacy_baseline_kw']} kW**와 같은 규모를 보였다."
            ),
            "",
            "![기준 R-134a 사이클 P-h 선도](../output/figures/baseline_cycle_ph.png)",
            "",
            _source_note(str(ctx["baseline_source_ids"])),
            "",
            "### 3.4 냉각유체 스크리닝과 IDC 측 열교환기",
            "",
            (
                "2차 루프 냉각유체 후보는 R-170, R-717, R-744, R-1270, R-290, R-600a, R-1150으로 두었다. "
                "후보는 1 MPa 루프 압력에서 단상 액체 여부, 삼중점 여유, IDC 측 열교환기 성립성, 요구 질량유량과 점도, 안전성 패널티를 기준으로 정렬했다."
            ),
            "",
        ]
    )
    lines.extend(
        _math_block(
            r"T_{\mathrm{after\ IDC}} = T_{\mathrm{cw,r}} - \Delta T_{\min}",
            r"\dot V_{\mathrm{loop}} = \frac{\dot m_{\mathrm{loop}}}{\rho}",
            r"\dot m_{\mathrm{loop}} = \frac{\dot Q_{\mathrm{IDC}}}{h\!\left(T_{\mathrm{after\ IDC}}, P\right) - h\!\left(T_{\mathrm{supply}}, P\right)}",
            r"\phi_{\mathrm{target}} = 0.90",
            r"\dot Q_{\mathrm{LNG,target}} = \frac{\dot Q_{\mathrm{IDC}}}{\phi_{\mathrm{target}}}",
            r"\dot Q_{\mathrm{pipe,max}} = \dot Q_{\mathrm{LNG,target}} - \dot Q_{\mathrm{IDC}}",
            r"T_{\mathrm{return,min}} = T_{\mathrm{NG,out}} + \Delta T_{\min}",
            r"\dot Q_{\mathrm{LNG,min}} = \dot m_{\mathrm{loop}} \left(h\!\left(T_{\mathrm{return,min}}, P\right) - h\!\left(T_{\mathrm{supply}}, P\right)\right)",
            r"\dot Q_{\mathrm{pipe,min}} = \dot Q_{\mathrm{LNG,min}} - \dot Q_{\mathrm{IDC}}",
            r"A_{\mathrm{IDC}} = \frac{\dot Q_{\mathrm{IDC}}}{U_{\mathrm{IDC}}\Delta T_{\mathrm{lm,IDC}}}",
            r"I_{\mathrm{transport}} = \dot m_{\mathrm{loop}} \frac{\mu}{\rho}",
            r"S = 1 - 0.35 m_{\mathrm{norm}} - 0.20 \dot V_{\mathrm{norm}} - 0.10 I_{\mathrm{norm}} - 0.10 \dot Q_{\mathrm{pipe,min,norm}} - 0.05 A_{\mathrm{IDC,norm}} + 0.10 M_{\mathrm{window,norm}} - 0.15 Q_{\mathrm{shortfall,norm}} - P_{\mathrm{safety}} - P_{\mathrm{compat}}",
        )
    )
    lines.extend(
        [
            "즉, 이번 스크리닝은 먼저 IDC 측 열교환기에서 요구 질량유량을 계산한 뒤, 90% 이용률 목표가 허용하는 배관 열유입 상한과 LNG hot-end가 요구하는 최소 환수온도 조건을 함께 계산한다. 이후 그 창(window) 안에 드는 후보를 우선하고, 부족분이 남는 경우에는 supplemental warm-up 요구량으로 별도 추적한다.",
            "",
            str(ctx["alternatives_md"]),
            "",
            (
                f"기본 설계점에서 최상위 유체는 **{ctx['selected_coolant']}**였고, 요구 질량유량은 "
                f"**{ctx['selected_mass_flow']} kg/s**였다. 또한 IDC 측 열교환기의 요구 면적은 **{ctx['idc_hx_area_m2']} m2**, "
                f"IDC 출구 냉각유체 온도는 **{ctx['idc_after_temp_c']} °C**, LNG 입구 환수온도는 **{ctx['idc_return_temp_c']} °C**로 계산되었다."
            ),
            "",
            "![IDC 측 열교환기 온도 프로파일](../output/figures/idc_hx_temperature_profile.png)",
            "",
            "![냉각유체 후보 비교](../output/figures/fluid_ranking.png)",
            "",
            _source_note("SRC-001,SRC-003,SRC-005,SRC-008,ASM-017,ASM-018,ASM-033,ASM-034,ASM-035"),
            "",
            "### 3.5 LNG 기화기 상세설계",
            "",
            (
                "기화기 모델의 핵심은 7 MPa 메탄의 비열이 극저온 영역에서 크게 변하므로, 단일 평균 비열 기반 LMTD 계산만으로는 "
                "정확한 설계를 보장하기 어렵다는 점이다. 따라서 본 코드는 112-190-205-220-283 K의 네 구간으로 나누어 엔탈피 기반 열량을 추적했다."
            ),
            "",
        ]
    )
    lines.extend(
        _math_block(
            r"\dot m_{\mathrm{LNG}} = \frac{\dot Q_{\mathrm{total}}}{h_{\mathrm{NG,out}} - h_{\mathrm{LNG,in}}}",
            r"\dot q_i = \dot m_{\mathrm{LNG}} (h_{i+1} - h_i)",
            r"Nu_t = 0.023 Re_t^{0.8} Pr_t^{0.4}",
            r"j_h = 0.5 \left(1 + \frac{B}{D_s}\right)\left(0.08 Re_s^{0.6821} + 0.7 Re_s^{0.1772}\right)",
            r"h_o = j_h \frac{k_s Pr_s^{1/3}}{D_e}",
            r"U_o^{-1} = \frac{d_o}{d_i h_i} + \frac{d_o \ln(d_o / d_i)}{2 k_w} + \frac{1}{h_o}",
            r"A_{\mathrm{req}} = \sum_i \frac{\dot q_i}{U_{o,i}\Delta T_{\mathrm{lm},i}}",
        )
    )
    lines.extend(
        [
            "기하 형상은 관 길이 6-16 m, 관 수 200-2200개 범위에서 자동 탐색했고, 제공 면적, 유속 제한, 핀치 조건을 동시에 검사했다.",
            "",
            str(ctx["hx_segments_md"]),
            "",
            (
                f"최종 형상은 **관 수 {ctx['hx_tube_count']}개**, **관 길이 {ctx['hx_tube_length_m']} m**, "
                f"**쉘 직경 {ctx['hx_shell_diameter_m']} m**로 정리되었고, 최소 핀치는 **{ctx['hx_min_pinch_k']} K**였다."
            ),
            "",
            "![LNG 기화기 온도 프로파일](../output/figures/hx_temperature_profile.png)",
            "",
            _source_note("SRC-001,SRC-004,SRC-005,SRC-006,SRC-007,ASM-020,ASM-021,ASM-022,ASM-023"),
            "",
            "### 3.6 장거리 배관 모델",
            "",
            (
                "배관 모델은 공급관과 환수관의 압력강하와 열유입을 각각 계산하고, 이를 합쳐 전체 펌프동력과 IDC 도달 냉량을 평가한다. "
                "설계 변수는 공급관 내경, 환수관 내경, 단열 두께다."
            ),
            "",
        ]
    )
    lines.extend(
        _math_block(
            r"Re = \frac{\rho v D}{\mu}",
            r"\Delta P = f \frac{L}{D}\frac{\rho v^2}{2} + K \frac{\rho v^2}{2}",
            r"\dot q' = \frac{T_{\mathrm{amb}} - T_f}{\ln(r_2 / r_1)/(2 \pi k_{\mathrm{ins}}) + 1/(2 \pi r_2 h_o)}",
            r"\dot Q_{\mathrm{pipe}} = (\dot q'_{\mathrm{supply}} + \dot q'_{\mathrm{return}}) L",
            r"\dot W_{\mathrm{pump}} = \frac{\Delta P_{\mathrm{supply}}\dot V_{\mathrm{supply}} + \Delta P_{\mathrm{return}}\dot V_{\mathrm{return}}}{\eta_{\mathrm{pump}}}",
        )
    )
    lines.extend(
        [
            "배관 스캔은 펌프동력과 ambient heat gain을 직접 계산하고, LNG hot-end가 요구하는 최소 환수온도에 못 미치는 경우에는 supplemental warm-up 요구량을 함께 산정한다. 따라서 현재 모델의 장거리 성립성은 단순 열손실이 아니라 `펌프동력 + ambient pickup + 추가 warm-up`의 결합 문제로 읽는다.",
            "",
            str(ctx["pipeline_design_md"]),
            "",
            "![배관 직경 트레이드오프](../output/figures/pipeline_tradeoff.png)",
            "",
            _source_note("SRC-001,ASM-014,ASM-015,ASM-016,ASM-024,ASM-025,ASM-026"),
            "",
            "### 3.7 연간 에너지, 비용, 탄소 모델",
            "",
            (
                "연간화는 데이터센터의 상시 운전을 반영해 8,760시간/년 기준으로 수행했다. "
                "전력요금과 전력 배출계수는 공식 자료를 기준으로 입력했고, 현재 버전에서는 LNG 외부 루프 펌프와 IDC 2차 루프 펌프를 합한 "
                "core LNG system power를 기준 압축기 동력과 비교했다. 또한 설치비, 연간 O&M, 할인율을 포함한 NPV/IRR을 함께 계산했다."
            ),
            "",
        ]
    )
    lines.extend(
        _math_block(
            r"E_{\mathrm{year}} = P \cdot t_{\mathrm{op}} / 1000",
            r"C_{\mathrm{year}} = P \cdot t_{\mathrm{op}} \cdot c_e",
            r"M_{\mathrm{CO_2}} = E_{\mathrm{year}} \cdot EF_{\mathrm{grid}}",
            r"CAPEX_{\mathrm{allow}} = \Delta C_{\mathrm{year}} \cdot N_{\mathrm{payback}}",
            r"CF_{\mathrm{net}} = \Delta C_{\mathrm{year}} - f_{\mathrm{O\&M}} \cdot CAPEX",
            r"NPV = -CAPEX + \sum_{t=1}^{N}\frac{CF_{\mathrm{net}}}{(1+r)^t}",
            r"IRR:\ 0 = -CAPEX + \sum_{t=1}^{N}\frac{CF_{\mathrm{net}}}{(1+IRR)^t}",
        )
    )
    lines.extend(
        [
            _source_note("SRC-013,SRC-014,SRC-021,SRC-022,SRC-023,SRC-024,SRC-025,ASM-030,ASM-031,ASM-057,ASM-058,ASM-059,ASM-060,ASM-061,ASM-062,ASM-063,ASM-064,ASM-065,ASM-066,ASM-067,ASM-068"),
            "",
        ]
    )
    return lines


def _build_report_result_sections(ctx: dict[str, object]) -> list[str]:
    return [
        "## 4. 결과",
        "",
        "### 4.1 전체 성능 요약",
        "",
        str(ctx["performance_summary_md"]),
        "",
        (
            f"가장 먼저 눈에 띄는 결과는 **{ctx['equivalent_cop']}**에 달하는 등가 냉각 COP다. "
            "이 값은 동일 냉방부하를 처리하기 위해 요구되는 전력의 크기가 얼마나 줄었는지를 보여준다."
        ),
        "",
        "![시스템 소비동력 비교](../output/figures/system_power_comparison.png)",
        "",
        "### 4.2 냉각유체 선정 결과",
        "",
        (
            f"후보군 비교 결과, 기본안은 **{ctx['selected_coolant']}**로 결정되었다. "
            f"이는 루프 질량유량, IDC 측 HX 면적 **{ctx['idc_hx_area_m2']} m2**, 장거리 배관 동력, 기화기 형상, 환경성, 안전성 패널티를 동시에 고려한 결과다."
        ),
        "",
        str(ctx["alternatives_md"]),
        "",
        "### 4.3 LNG 기화기 결과",
        "",
        (
            f"LNG 기화기 설계는 네 구간 모두에서 양의 핀치를 유지했고, 최소값은 **{ctx['hx_min_pinch_k']} K**였다. "
            f"최종적으로 LNG는 **{ctx['lng_inlet_k']} K**에서 **{ctx['ng_outlet_k']} K**까지 가열된다."
        ),
        "",
        str(ctx["hx_segments_md"]),
        "",
        "### 4.4 배관 설계와 거리 민감도",
        "",
        (
            f"배관 기본안은 공급관과 환수관 모두 **{ctx['pipeline_id_m']} m** 내경을 사용하고, "
            f"단열 두께는 **{ctx['pipeline_insulation_m']} m**로 결정되었다."
        ),
        "",
        str(ctx["distance_md"]),
        "",
        "![거리 민감도](../output/figures/pipeline_distance_sensitivity.png)",
        "",
        (
            f"거리 증가에 따라 열유입이 거의 선형적으로 증가하면서, 현재 운전점에서의 추정 최대 편도 성립거리는 **{ctx['max_distance_km']} km**로 나타났다. "
            f"따라서 **{ctx['long_distance_km']} km** 조건은 기본안의 단순 확장만으로는 **{ctx['long_distance_status']} 판정**을 받는다."
        ),
        "",
        "### 4.5 공급온도 민감도와 35 km 해석",
        "",
        str(ctx["temperature_md"]),
        "",
        "![공급온도 민감도](../output/figures/supply_temperature_sensitivity.png)",
        "",
        (
            f"공급온도 스윕 결과, 펌프동력 최소점은 **{ctx['best_supply_temp_c']} °C**이며 이때도 "
            f"기본 유체는 **{ctx['best_supply_fluid']}**로 유지된다. {ctx['recover_35km_text']}"
        ),
        "",
        "### 4.6 추가 warm-up 제거 가능성",
        "",
        str(ctx["closure_md"]),
        "",
        "![무보조 warm-up 성립거리 맵](../output/figures/ambient_closure_map.png)",
        "",
        (
            f"현재 탐색 범위에서 가장 이른 무보조 warm-up 성립점은 **{ctx['best_closure_temp_c']} °C / "
            f"{ctx['best_closure_fluid']}** 조합이며, ambient heat gain만으로 LNG hot-end를 만족시키려면 "
            f"최소 **{ctx['best_closure_distance_km']} km**의 편도 거리가 필요했다. "
            f"이때의 루프 펌프동력은 **{ctx['best_closure_pump_kw']} kW**였다."
        ),
        "",
        str(ctx["closure_interpretation_text"]),
        "",
        str(ctx["practical_passive_text"]),
        "",
        "### 4.7 연간 효과와 경제성",
        "",
        str(ctx["annual_md"]),
        "",
        "![연간 효과](../output/figures/annual_impact_comparison.png)",
        "",
        str(ctx["payback_md"]),
        "",
        (
            f"현재 비교 경계에서 LNG 시스템은 연간 **{ctx['annual_saving_mwh']} MWh/년**의 전력을 줄이고, "
            f"연간 **{ctx['annual_cost_saving_mkrw']} 백만원/년**의 전기요금을 절감하며, "
            f"연간 **{ctx['annual_avoided_tco2']} tCO2/년**의 간접배출을 회피한다."
        ),
        "",
        str(ctx["auxiliary_heat_text"]),
        "",
        "### 4.8 기존 엑셀 결과와 비교",
        "",
        str(ctx["legacy_md"]),
        "",
        "## 5. 논의",
        "",
        (
            "첫째, 10 km 기본 설계는 기술적으로 성립할 뿐 아니라 에너지 절감 측면에서도 매우 유리하다. "
            "기준 압축기 시스템이 수 MW급 전력을 요구하는 반면, LNG 냉열 기반 루프는 수십 kW 수준의 펌프동력으로 동일한 냉방부하를 처리할 수 있었다."
        ),
        "",
        (
            "둘째, 이번 프로젝트의 진짜 설계 통찰은 35 km 조건의 판정이 운전점과 열수지 가정에 따라 달라질 만큼 민감하다는 사실이다. "
            f"이번 결과는 현재 기본안의 경계가 약 **{ctx['max_distance_km']} km**라는 점을 정량적으로 보여준다. {ctx['long_distance_discussion']}"
        ),
        "",
        (ctx["long_distance_extension_text"]),
        "",
        (
            f"넷째, 추가 warm-up을 완전히 제거하는 관점에서 보면 현재 **{ctx['base_distance_km']} km** 기본거리는 "
            "아직 충분한 ambient pickup을 제공하지 못한다. 따라서 현 기본안은 순수 LNG 냉열 단독안이라기보다, "
            "LNG hot-end 조건을 맞추기 위한 보조 열원 또는 더 긴 배관거리의 도움을 받는 하이브리드 운전점으로 읽는 편이 더 정확하다."
        ),
        "",
        (ctx["practical_passive_text"]),
        "",
        (
            "다섯째, 혼합 LNG와 IDC 2차 루프를 포함하면 설계의 물리적 설명력은 높아지지만, 동시에 외부 장거리 배관 CAPEX가 매우 크게 드러난다. "
            "즉 에너지 측면의 장점과 인프라 투자 부담을 분리해서 읽어야 한다."
        ),
        "",
        (ctx["auxiliary_heat_text"]),
        "",
        "## 6. 한계와 향후 확장",
        "",
        "- LNG 엔탈피 계산은 혼합 LNG surrogate를 쓰지만, 극저온 transport property는 메탄 proxy를 사용했다.",
        "- IDC 2차 루프는 등가 배관망과 lumped terminal loss로 모델링했으므로 floor-by-floor 배관 상세도는 아직 없다.",
        "- 기화기 설계는 열역학과 형상 스캔 중심이며, 응력과 제작성의 상세 검토는 아직 별도 단계가 필요하다.",
        "- 경제성은 core-system CAPEX와 단순 O&M까지 확장했지만, 보조 열원별 추가 CAPEX와 site-specific 공사비는 아직 별도 단계가 필요하다.",
        "- 냉각유체 스코어는 휴리스틱 성격이 있으므로, 안전/규제/재료 호환성 검토로 후속 보정이 필요하다.",
        "",
        "## 7. 결론",
        "",
        (
            f"본 연구는 총 **{ctx['total_load_kw']} kW**의 IDC 냉방부하를 대상으로, LNG 냉열 기반 냉각 시스템이 "
            f"10 km 기본 설계점에서 **{ctx['base_distance_conclusion_text']}**. 선정된 기본안은 **{ctx['selected_coolant']}**를 2차 루프 유체로 사용하고, "
            f"기화기 duty **{ctx['lng_duty_kw']} kW**, core system power **{ctx['core_power_kw']} kW**, "
            f"배관 열유입 **{ctx['pipeline_heat_gain_kw']} kW**의 수준에서 IDC 부하를 충족한다. "
            f"현재 경계는 약 **{ctx['max_distance_km']} km**이며, 35 km 조건은 **{ctx['long_distance_status']} 판정**으로 정리되었다."
        ),
        "",
        "## 부록 A. 출처 레지스트리",
        "",
        str(ctx["source_registry_md"]),
        "",
        "## 부록 B. 공학 가정 레지스트리",
        "",
        str(ctx["assumption_registry_md"]),
        "",
        "## 참고문헌",
        "",
    ]


def build_report(project_root: Path) -> Path:
    output_dir = project_root / "output"
    deliverables_dir = ensure_directory(project_root / "deliverables")
    project_config = load_config(project_root / "config" / "base.toml")
    config = project_config.values
    load_result = compute_load_model(config)
    summary = _summary_map(output_dir)
    alternatives = pd.read_csv(output_dir / "alternative_designs.csv")
    distance = pd.read_csv(output_dir / "distance_scenarios.csv")
    temperature = pd.read_csv(output_dir / "supply_temperature_sweep.csv")
    ambient_closure = pd.read_csv(output_dir / "ambient_closure_map.csv")
    annual = pd.read_csv(output_dir / "annual_summary.csv")
    auxiliary_heat = pd.read_csv(output_dir / "auxiliary_heat_sources.csv")
    payback = pd.read_csv(output_dir / "payback_allowable_capex.csv")
    legacy = pd.read_csv(output_dir / "legacy_comparison.csv")
    hx_segments = pd.read_csv(output_dir / "hx_segments.csv")
    pipeline_scan = pd.read_csv(output_dir / "pipeline_scan_top200.csv")
    passive_zero_warmup = pd.read_csv(output_dir / "passive_zero_warmup_search.csv")
    sources = _parse_sources(project_root / "docs" / "sources.md")
    assumptions = _parse_assumptions(project_root / "docs" / "assumptions.md")

    selected_alternative = alternatives.iloc[0]
    selected_pipeline = pipeline_scan.iloc[0]
    base_distance = distance.sort_values("distance_km").iloc[0]
    long_distance = distance.sort_values("distance_km").iloc[-1]
    base_distance_base_ok = bool(base_distance["base_duty_meets_idc_load"])
    base_distance_hybrid_ok = bool(base_distance["hybrid_load_satisfied"])
    long_distance_base_ok = bool(long_distance["base_duty_meets_idc_load"])
    long_distance_hybrid_ok = bool(long_distance["hybrid_load_satisfied"])
    long_distance_requires_supp = bool(long_distance["requires_supplemental_warmup"])
    best_temp = temperature[temperature["status"] == "feasible"].sort_values("pump_power_kw").iloc[0]
    feasible_closure = ambient_closure[ambient_closure["status"] == "feasible"].copy()
    closure_candidates = feasible_closure[feasible_closure["ambient_only_closure_distance_km"].notna()].sort_values(
        ["ambient_only_closure_distance_km", "pump_power_kw", "screening_score"],
        ascending=[True, True, False],
    )
    best_closure = closure_candidates.iloc[0] if not closure_candidates.empty else None
    base_warmup_free = feasible_closure[feasible_closure["warmup_free_at_base_distance"] == True]
    long_warmup_free = feasible_closure[feasible_closure["warmup_free_at_long_distance"] == True]
    recover_35km = temperature[
        (temperature["status"] == "feasible") & (temperature["long_distance_base_duty_meets_load"] == True)
    ].sort_values("pump_power_kw")
    best_auxiliary = auxiliary_heat.sort_values("net_power_saving_kw", ascending=False).iloc[0]
    practical_passive = passive_zero_warmup[passive_zero_warmup["practical_zero_warmup_design_found"] == True].copy()

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
            "Core system power (kW)": alternatives["pump_power_kw"].map(_format_number),
            "추가 warm-up (kW)": alternatives["supplemental_warmup_kw"].map(_format_number),
            "쉘 직경 (m)": alternatives["hx_shell_diameter_m"].map(lambda x: _format_number(x, 3)),
            "연간 비용절감 (백만원/년)": alternatives["annual_cost_saving_krw"].map(
                lambda x: _format_number(x / 1_000_000.0)
            ),
        }
    )
    distance_table = pd.DataFrame(
        {
            "거리 (km)": distance["distance_km"].map(_format_number),
            "Core system power (kW)": distance["pump_power_kw"].map(_format_number),
            "열유입 (kW)": distance["heat_gain_kw"].map(_format_number),
            "추가 warm-up (kW)": distance["supplemental_warmup_kw"].map(_format_number),
            "기본 duty 여유 (kW)": distance["base_duty_margin_kw"].map(_format_number),
            "하이브리드 성립": distance["hybrid_load_satisfied"].map(lambda x: "예" if bool(x) else "아니오"),
            "기본 duty 충족": distance["base_duty_meets_idc_load"].map(lambda x: "예" if bool(x) else "아니오"),
        }
    )
    temperature_table = pd.DataFrame(
        {
            "공급온도 (°C)": temperature["supply_temp_c"].map(_format_number),
            "선정 유체": temperature["selected_fluid"].fillna("-"),
            "Core system power (kW)": temperature["pump_power_kw"].map(_format_number),
            "최대 하이브리드 성립거리 (km)": temperature["max_feasible_distance_km"].map(_format_number),
            "최대 기본 duty 성립거리 (km)": temperature["max_base_duty_distance_km"].map(_format_number),
            "35 km 기본 duty 충족": temperature["long_distance_base_duty_meets_load"].map(lambda x: "예" if bool(x) else "아니오"),
            "상태": temperature["status"].replace({"feasible": "성립", "failed": "실패"}),
        }
    )
    closure_table = pd.DataFrame(
        {
            "공급온도 (°C)": closure_candidates["supply_temp_c"].map(_format_number),
            "유체": closure_candidates["fluid"],
            "기본안 추가 warm-up (kW)": closure_candidates["supplemental_warmup_kw"].map(_format_number),
            "무보조 성립거리 (km)": closure_candidates["ambient_only_closure_distance_km"].map(_format_number),
            "35 km 무보조 성립": closure_candidates["warmup_free_at_long_distance"].map(lambda x: "예" if bool(x) else "아니오"),
            "기본 스크리닝 선정": closure_candidates["selected_by_screening"].map(lambda x: "예" if bool(x) else "아니오"),
        }
    ).head(8)
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
    load_table = pd.DataFrame(
        [
            {
                "부하 항목": name,
                "열부하 (kW)": _format_number(value),
                "비중 (%)": _format_number(100.0 * value / load_result.total_kw, 2),
            }
            for name, value in load_result.breakdown_kw.items()
        ]
    )
    input_conditions_table = pd.DataFrame(
        [
            {
                "항목": "랙 수",
                "값": f"{config['assignment']['rack_count']:.0f} racks",
                "출처 ID": _config_source_id(project_config, "assignment.rack_count"),
            },
            {
                "항목": "랙당 IT 발열",
                "값": f"{config['assignment']['it_load_kw_per_rack']:.1f} kW/rack",
                "출처 ID": _config_source_id(project_config, "assignment.it_load_kw_per_rack"),
            },
            {
                "항목": "실내 공기 조건",
                "값": f"{_format_celsius(config['assignment']['room_air_temp_k'])} °C, RH {config['assignment']['room_relative_humidity'] * 100:.0f}%",
                "출처 ID": _config_source_id(project_config, "assignment.room_air_temp_k"),
            },
            {
                "항목": "냉수 공급/환수",
                "값": f"{_format_celsius(config['assignment']['chilled_water_supply_temp_k'])} / {_format_celsius(config['assignment']['chilled_water_return_temp_k'])} °C",
                "출처 ID": _config_source_id(project_config, "assignment.chilled_water_supply_temp_k"),
            },
            {
                "항목": "외기 조건",
                "값": f"{_format_celsius(config['assignment']['ambient_air_temp_k'])} °C, RH {config['assignment']['ambient_relative_humidity'] * 100:.0f}%",
                "출처 ID": _config_source_id(project_config, "assignment.ambient_air_temp_k"),
            },
            {
                "항목": "LNG 압력/입구온도",
                "값": f"{config['assignment']['lng_pressure_mpa']:.1f} MPa, {config['assignment']['lng_inlet_temp_k']:.1f} K",
                "출처 ID": _config_source_id(project_config, "assignment.lng_pressure_mpa"),
            },
            {
                "항목": "NG 목표 출구온도",
                "값": f"{config['assignment']['ng_outlet_temp_k']:.1f} K",
                "출처 ID": _config_source_id(project_config, "assignment.ng_outlet_temp_k"),
            },
            {
                "항목": "최소 접근온도",
                "값": f"{config['assignment']['minimum_temperature_approach_k']:.1f} K",
                "출처 ID": _config_source_id(project_config, "assignment.minimum_temperature_approach_k"),
            },
            {
                "항목": "기본 이송거리",
                "값": f"{config['assignment']['pipeline_distance_m'] / 1000.0:.1f} km",
                "출처 ID": _config_source_id(project_config, "assignment.pipeline_distance_m"),
            },
            {
                "항목": "도전 이송거리",
                "값": f"{config['system_targets']['long_distance_pipeline_m'] / 1000.0:.1f} km",
                "출처 ID": _config_source_id(project_config, "system_targets.long_distance_pipeline_m"),
            },
        ]
    )

    load_table_md = _markdown_table(load_table, ["부하 항목", "열부하 (kW)", "비중 (%)"])
    input_conditions_md = _markdown_table(input_conditions_table, ["항목", "값", "출처 ID"])
    alternatives_md = _markdown_table(alternatives_table, ["유체", "스크리닝 점수", "Core system power (kW)", "추가 warm-up (kW)", "쉘 직경 (m)", "연간 비용절감 (백만원/년)"])
    distance_md = _markdown_table(distance_table, ["거리 (km)", "Core system power (kW)", "열유입 (kW)", "추가 warm-up (kW)", "기본 duty 여유 (kW)", "하이브리드 성립", "기본 duty 충족"])
    temperature_md = _markdown_table(temperature_table, ["공급온도 (°C)", "선정 유체", "Core system power (kW)", "최대 하이브리드 성립거리 (km)", "최대 기본 duty 성립거리 (km)", "35 km 기본 duty 충족", "상태"])
    closure_md = _markdown_table(
        closure_table,
        ["공급온도 (°C)", "유체", "기본안 추가 warm-up (kW)", "무보조 성립거리 (km)", "35 km 무보조 성립", "기본 스크리닝 선정"],
    )
    annual_md = _markdown_table(annual_report, ["항목", "값", "단위"])
    payback_md = _markdown_table(
        payback.assign(
            **{
                "회수기간 (년)": payback["payback_years"],
                "허용 추가 투자비 (백만원)": payback["allowable_incremental_capex_krw"].map(
                    lambda x: _format_number(x / 1_000_000.0)
                ),
            }
        ),
        ["회수기간 (년)", "허용 추가 투자비 (백만원)"],
    )
    legacy_md = _markdown_table(legacy_table, ["항목", "기존 엑셀 (kW)", "현재 코드 (kW)", "차이 (kW)", "차이율 (%)"])
    hx_segments_md = _markdown_table(
        pd.DataFrame(
            {
                "구간": hx_segments["segment"],
                "구간 열부하 (kW)": hx_segments["q_kw"].map(_format_number),
                "LNG 입구 (K)": hx_segments["lng_in_k"].map(_format_number),
                "LNG 출구 (K)": hx_segments["lng_out_k"].map(_format_number),
                "냉각유체 입구 (K)": hx_segments["coolant_in_k"].map(_format_number),
                "냉각유체 출구 (K)": hx_segments["coolant_out_k"].map(_format_number),
            }
        ),
        ["구간", "구간 열부하 (kW)", "LNG 입구 (K)", "LNG 출구 (K)", "냉각유체 입구 (K)", "냉각유체 출구 (K)"],
    )
    pipeline_design_md = _markdown_table(
        pd.DataFrame(
            [
                {"설계 변수": "공급관 내경", "값": f"{selected_alternative['pipeline_supply_id_m']:.3f} m"},
                {"설계 변수": "환수관 내경", "값": f"{selected_alternative['pipeline_return_id_m']:.3f} m"},
                {"설계 변수": "단열 두께", "값": f"{selected_alternative['pipeline_insulation_thickness_m']:.3f} m"},
                {"설계 변수": "배관 열유입", "값": f"{_format_number(selected_alternative['pipeline_heat_gain_kw'])} kW"},
                {"설계 변수": "추가 warm-up", "값": f"{_format_number(selected_alternative['supplemental_warmup_kw'])} kW"},
                {"설계 변수": "LNG 외부 루프 펌프동력", "값": f"{_format_number(selected_alternative['lng_loop_pump_power_kw'])} kW"},
                {"설계 변수": "Core system power", "값": f"{_format_number(selected_alternative['pump_power_kw'])} kW"},
                {"설계 변수": "공급관 속도", "값": f"{_format_number(selected_pipeline['velocity_supply_m_per_s'], 3)} m/s"},
                {"설계 변수": "환수관 속도", "값": f"{_format_number(selected_pipeline['velocity_return_m_per_s'], 3)} m/s"},
                {"설계 변수": "공급관 압력강하", "값": f"{_format_number(selected_pipeline['dp_supply_kpa'])} kPa"},
                {"설계 변수": "환수관 압력강하", "값": f"{_format_number(selected_pipeline['dp_return_kpa'])} kPa"},
            ]
        ),
        ["설계 변수", "값"],
    )
    performance_summary_md = _markdown_table(
        pd.DataFrame(
            [
                {"항목": "총 냉방부하", "값": f"{_format_number(float(summary['IDC total cooling load']['value']))} kW"},
                {"항목": "이론 최소동력", "값": f"{_format_number(float(summary['Theoretical minimum power']['value']))} kW"},
                {"항목": "기준 압축기 동력", "값": f"{_format_number(float(summary['Baseline R-134a compressor power']['value']))} kW"},
                {"항목": "선정 냉각유체", "값": str(summary["Selected coolant"]["value"])},
                {"항목": "IDC 측 HX 면적", "값": f"{_format_number(float(summary['IDC-side HX required area']['value']))} m2"},
                {"항목": "IDC 출구 냉각유체 온도", "값": f"{_format_celsius(float(summary['IDC coolant outlet temperature']['value']))} °C"},
                {"항목": "LNG 유입 환수온도", "값": f"{_format_celsius(float(summary['IDC loop return temperature at LNG inlet']['value']))} °C"},
                {"항목": "LNG 기화 duty", "값": f"{_format_number(float(summary['LNG vaporizer duty']['value']))} kW"},
                {"항목": "배관 열유입", "값": f"{_format_number(float(summary['Pipeline heat gain']['value']))} kW"},
                {"항목": "추가 warm-up", "값": f"{_format_number(float(summary['Supplemental warm-up duty']['value']))} kW"},
                {"항목": "IDC 도달 가능 냉량", "값": f"{_format_number(float(summary['Available cooling at IDC']['value']))} kW"},
                {"항목": "LNG 외부 루프 펌프동력", "값": f"{_format_number(float(summary['LNG system pump power']['value']))} kW"},
                {"항목": "IDC 2차 루프 펌프동력", "값": f"{_format_number(float(summary['IDC secondary-loop pump power']['value']))} kW"},
                {"항목": "Core system power", "값": f"{_format_number(float(summary['Core LNG system power']['value']))} kW"},
                {"항목": "Core installed CAPEX", "값": f"{_format_number(float(summary['Core installed CAPEX']['value']) / 1_000_000_000.0, 2)} 십억원"},
                {"항목": "Core-system NPV", "값": f"{_format_number(float(summary['Core-system NPV']['value']) / 1_000_000_000.0, 2)} 십억원"},
                {"항목": "등가 냉각 COP", "값": _format_number(float(summary['Equivalent cooling COP']['value']), 1)},
                {"항목": "기준 대비 절감 동력", "값": f"{_format_number(float(summary['Baseline-to-LNG power saving']['value']))} kW"},
            ]
        ),
        ["항목", "값"],
    )
    source_registry_md = _markdown_table(
        pd.DataFrame(
            [
                {"ID": source_id, "제목": entry["title"], "형식": entry["type"], "주요 사용값": entry["used_values"]}
                for source_id, entry in sorted(sources.items())
            ]
        ),
        ["ID", "제목", "형식", "주요 사용값"],
    )
    assumption_registry_md = _markdown_table(
        pd.DataFrame(
            [
                {"ID": assumption_id, "가정": entry["assumption"], "값": entry["value"], "설정 이유": entry["why"]}
                for assumption_id, entry in sorted(assumptions.items())
            ]
        ),
        ["ID", "가정", "값", "설정 이유"],
    )

    if long_distance_base_ok:
        recover_35km_text = (
            f"현재 기본안 자체가 **{int(long_distance['distance_km'])} km** 조건을 기본 LNG duty 경계 안에서 이미 만족하므로, "
            "공급온도 스윕은 복구 목적이 아니라 추가 여유와 펌프동력 변화의 trade-off를 읽기 위한 분석으로 해석된다."
        )
    elif not recover_35km.empty:
        recover_row = recover_35km.iloc[0]
        recover_35km_text = (
            f"추가로, 공급온도를 **{recover_row['supply_temp_c']:.1f} °C**까지 높이면 "
            f"**{recover_row['selected_fluid']}**를 사용해 35 km 조건을 회복할 수 있었으나, "
            f"그때의 펌프동력은 **{_format_number(recover_row['pump_power_kw'])} kW**로 크게 상승했다."
        )
    else:
        recover_35km_text = "공급온도 스윕 범위 안에서는 35 km 기본 LNG duty 조건을 만족하는 운전점이 발견되지 않았다."

    if long_distance_base_ok:
        long_distance_discussion = (
            f"특히 현재 기본안 자체가 **{int(long_distance['distance_km'])} km** 조건도 이미 충족한다는 점은, "
            "기존 프로젝트의 보수적 duty 가정이 실제보다 제한적이었을 가능성을 보여준다."
        )
        long_distance_extension_text = (
            "셋째, 이번 모델에서는 35 km가 별도 운전점 변경 없이도 기본 LNG duty 경계 안에서 성립했다. "
            "즉, IDC 측 HX 제약과 LNG hot-end 제약을 동시에 반영한 뒤에도 기본안의 거리 여유가 남는다는 뜻이다."
        )
    elif long_distance_hybrid_ok:
        long_distance_discussion = (
            f"특히 **{int(long_distance['distance_km'])} km** 조건은 유압과 액상 유지 관점에서는 아직 해가 존재하지만, "
            "기본 LNG duty만으로는 IDC 부하와 hot-end 요구를 동시에 닫지 못해 supplemental warm-up이 필요하다."
        )
        long_distance_extension_text = (
            "셋째, 이번 모델에서 35 km는 '완전 불성립'이 아니라 하이브리드 운전에서는 성립하지만 기본 LNG duty 경계에서는 불성립하는 조건이다. "
            "따라서 장거리 확장성은 존재하지만, 그 의미를 순수 LNG 냉열 단독 성립으로 읽어서는 안 된다."
        )
    else:
        long_distance_discussion = (
            f"특히 **{int(long_distance['distance_km'])} km** 조건이 아직 불성립이라는 사실은, "
            "장거리 설계가 열유입 여유와 루프 온도 수준에 매우 민감함을 보여준다."
        )
        long_distance_extension_text = (
            "셋째, 35 km는 절대 불가능한 조건이 아니라 기본안의 단순 연장으로는 불가능한 조건이다. "
            "즉, 운전점과 유체 선택을 바꾸면 회복 가능할 수도 있지만, 그 대가로 펌프동력과 설계 복잡성이 증가한다."
        )

    if best_closure is not None and base_warmup_free.empty and long_warmup_free.empty:
        closure_interpretation_text = (
            f"현재 탐색 범위에서는 10 km와 35 km 모두 ambient heat gain만으로 LNG hot-end를 만족시키지 못했고, "
            f"가장 빠른 무보조 성립거리도 **{_format_number(best_closure['ambient_only_closure_distance_km'])} km**였다. "
            "따라서 현재 추가 warm-up 항은 단순 수치 보정이 아니라, 물리적으로 의미 있는 보조 열원 요구량으로 해석하는 편이 맞다."
        )
    elif best_closure is not None and base_warmup_free.empty:
        best_long = long_warmup_free.sort_values(["pump_power_kw", "ambient_only_closure_distance_km"]).iloc[0]
        closure_interpretation_text = (
            f"10 km 기본안에서는 무보조 운전점이 없지만, **{_format_number(best_long['supply_temp_c'])} °C / {best_long['fluid']}** "
            "조합은 35 km 거리에서 추가 warm-up 없이도 성립한다. 즉 장거리망은 오히려 hot-end 제약 완화에 유리할 수 있다."
        )
    elif not base_warmup_free.empty:
        best_base = base_warmup_free.sort_values(["pump_power_kw", "ambient_only_closure_distance_km"]).iloc[0]
        closure_interpretation_text = (
            f"현재 탐색 범위 안에서도 **{_format_number(best_base['supply_temp_c'])} °C / {best_base['fluid']}** 조합은 "
            "기본 10 km 거리에서 추가 warm-up 없이 성립한다. 따라서 보조 열원 항은 기본안 선택의 결과이지 절대적인 필수조건은 아니다."
        )
    else:
        closure_interpretation_text = "현재 탐색 범위에서는 무보조 warm-up 성립거리 해석을 위한 추가 후보가 충분하지 않았다."

    if practical_passive.empty:
        practical_passive_text = (
            "다만 공격적 passive heat 탐색에서 형식적으로 warm-up-free 점이 몇 개 나타나더라도, "
            "최소 단열 두께 50 mm와 passive heat 의존도 25% 이하라는 현실성 필터를 적용하면 "
            "현재는 **실무적으로 남는 무보조 해가 없었다**. 즉 무보조 성립은 가능성의 증거이지, 바로 채택 가능한 설계의 증거는 아니다."
        )
    else:
        best_practical_passive = practical_passive.sort_values(
            ["best_design_pump_power_kw", "minimum_supplemental_warmup_kw"]
        ).iloc[0]
        practical_passive_text = (
            f"현실성 필터를 거친 뒤에도 **{_format_number(best_practical_passive['target_distance_km'])} km / "
            f"{_format_number(best_practical_passive['supply_temp_c'])} °C / {best_practical_passive['fluid']}** "
            "조합은 무보조 성립점으로 남았다. 따라서 향후에는 이 practical warm-up-free 해를 중심으로 설계를 다시 좁혀볼 가치가 있다."
        )

    auxiliary_heat_text = (
        f"보조 열원이 완전히 사라지지 않는다면, 현재 구성된 하이브리드 시나리오 중에서는 "
        f"**{best_auxiliary['scenario_label']}**가 가장 유리했다. 이 경우 총 시스템 동력은 "
        f"**{_format_number(best_auxiliary['total_system_power_kw'])} kW**이고, 기준선 대비 순절감은 "
        f"**{_format_number(best_auxiliary['net_power_saving_kw'])} kW**다."
    )

    ctx: dict[str, object] = {
        "input_conditions_md": input_conditions_md,
        "load_table_md": load_table_md,
        "alternatives_md": alternatives_md,
        "distance_md": distance_md,
        "temperature_md": temperature_md,
        "closure_md": closure_md,
        "annual_md": annual_md,
        "payback_md": payback_md,
        "legacy_md": legacy_md,
        "hx_segments_md": hx_segments_md,
        "pipeline_design_md": pipeline_design_md,
        "performance_summary_md": performance_summary_md,
        "source_registry_md": source_registry_md,
        "assumption_registry_md": assumption_registry_md,
        "total_load_kw": _format_number(float(summary["IDC total cooling load"]["value"])),
        "minimum_power_kw": _format_number(float(summary["Theoretical minimum power"]["value"])),
        "baseline_power_kw": _format_number(float(summary["Baseline R-134a compressor power"]["value"])),
        "selected_coolant": str(summary["Selected coolant"]["value"]),
        "lng_stream_model": str(summary["LNG stream model"]["value"]),
        "lng_duty_kw": _format_number(float(summary["LNG vaporizer duty"]["value"])),
        "pipeline_heat_gain_kw": _format_number(float(summary["Pipeline heat gain"]["value"])),
        "pump_power_kw": _format_number(float(summary["LNG system pump power"]["value"])),
        "lng_loop_pump_kw": _format_number(float(summary["LNG system pump power"]["value"])),
        "idc_secondary_pump_kw": _format_number(float(summary["IDC secondary-loop pump power"]["value"])),
        "core_power_kw": _format_number(float(summary["Core LNG system power"]["value"])),
        "power_saving_kw": _format_number(float(summary["Baseline-to-LNG power saving"]["value"])),
        "annual_saving_mwh": _format_number(float(summary["Annual electricity saving"]["value"])),
        "annual_cost_saving_mkrw": _format_number(float(summary["Annual electricity cost saving"]["value"]) / 1_000_000.0),
        "annual_avoided_tco2": _format_number(float(summary["Annual avoided indirect emissions"]["value"])),
        "core_capex_bkrw": _format_number(float(summary["Core installed CAPEX"]["value"]) / 1_000_000_000.0, 2),
        "core_npv_bkrw": _format_number(float(summary["Core-system NPV"]["value"]) / 1_000_000_000.0, 2),
        "equivalent_cop": _format_number(float(summary["Equivalent cooling COP"]["value"]), 1),
        "base_distance_km": _format_number(config["assignment"]["pipeline_distance_m"] / 1000.0),
        "base_distance_status": (
            "기본 LNG duty 기준"
            if base_distance_base_ok
            else "supplemental warm-up을 포함한 하이브리드 운전 기준"
            if base_distance_hybrid_ok
            else "하이브리드까지 포함해도 불성립한"
        ),
        "base_distance_conclusion_text": (
            "기본 LNG duty 기준으로 성립함을 보였다"
            if base_distance_base_ok
            else "supplemental warm-up을 포함한 하이브리드 운전 기준으로 성립함을 보였다"
            if base_distance_hybrid_ok
            else "하이브리드까지 포함해도 성립하지 않음을 보였다"
        ),
        "max_distance_km": _format_number(distance["max_feasible_distance_m"].iloc[0] / 1000.0),
        "max_base_distance_km": _format_number(distance["max_base_duty_distance_m"].iloc[0] / 1000.0),
        "idc_hx_area_m2": _format_number(float(summary["IDC-side HX required area"]["value"])),
        "idc_after_temp_c": _format_celsius(float(summary["IDC coolant outlet temperature"]["value"])),
        "idc_return_temp_c": _format_celsius(float(summary["IDC loop return temperature at LNG inlet"]["value"])),
        "chilled_mean_c": _format_celsius(0.5 * (config["assignment"]["chilled_water_supply_temp_k"] + config["assignment"]["chilled_water_return_temp_k"])),
        "ambient_c": _format_celsius(config["assignment"]["ambient_air_temp_k"]),
        "load_source_ids": summary["IDC total cooling load"]["source_ids"],
        "minimum_power_source_ids": summary["Theoretical minimum power"]["source_ids"],
        "baseline_source_ids": summary["Baseline R-134a compressor power"]["source_ids"],
        "legacy_baseline_kw": legacy_table.iloc[1]["기존 엑셀 (kW)"],
        "selected_mass_flow": _format_number(selected_alternative["required_mass_flow_kg_s"]),
        "hx_tube_count": int(selected_alternative["hx_tube_count"]),
        "hx_tube_length_m": _format_number(selected_alternative["hx_tube_length_m"]),
        "hx_shell_diameter_m": _format_number(selected_alternative["hx_shell_diameter_m"], 3),
        "hx_min_pinch_k": _format_number(selected_alternative["hx_min_pinch_k"]),
        "pipeline_id_m": f"{selected_alternative['pipeline_supply_id_m']:.3f}",
        "pipeline_insulation_m": f"{selected_alternative['pipeline_insulation_thickness_m']:.3f}",
        "lng_inlet_k": f"{config['assignment']['lng_inlet_temp_k']:.1f}",
        "ng_outlet_k": f"{config['assignment']['ng_outlet_temp_k']:.1f}",
        "long_distance_km": int(long_distance["distance_km"]),
        "long_distance_status": (
            "기본 LNG duty 성립"
            if long_distance_base_ok
            else "하이브리드 성립, 기본 LNG duty 불성립"
            if long_distance_hybrid_ok
            else "하이브리드까지 포함해 불성립"
        ),
        "long_distance_discussion": long_distance_discussion,
        "long_distance_extension_text": long_distance_extension_text,
        "best_supply_temp_c": _format_number(best_temp["supply_temp_c"]),
        "best_supply_fluid": best_temp["selected_fluid"],
        "recover_35km_text": recover_35km_text,
        "best_closure_temp_c": _format_number(best_closure["supply_temp_c"]) if best_closure is not None else "-",
        "best_closure_fluid": best_closure["fluid"] if best_closure is not None else "-",
        "best_closure_distance_km": _format_number(best_closure["ambient_only_closure_distance_km"]) if best_closure is not None else "-",
        "best_closure_pump_kw": _format_number(best_closure["pump_power_kw"]) if best_closure is not None else "-",
        "closure_interpretation_text": closure_interpretation_text,
        "practical_passive_text": practical_passive_text,
        "auxiliary_heat_text": auxiliary_heat_text,
    }

    report_path = deliverables_dir / "report_draft.md"
    report_lines: list[str] = []
    report_lines.extend(_build_report_front_matter(ctx))
    report_lines.extend(_build_report_model_sections(ctx))
    report_lines.extend(_build_report_result_sections(ctx))
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
    auxiliary_heat = pd.read_csv(output_dir / "auxiliary_heat_sources.csv")
    passive_zero_warmup = pd.read_csv(output_dir / "passive_zero_warmup_search.csv")
    selected_alternative = alternatives.iloc[0]
    base_distance = distance.sort_values("distance_km").iloc[0]
    long_distance = distance.sort_values("distance_km").iloc[-1]
    base_distance_base_ok = bool(base_distance["base_duty_meets_idc_load"])
    base_distance_hybrid_ok = bool(base_distance["hybrid_load_satisfied"])
    long_distance_base_ok = bool(long_distance["base_duty_meets_idc_load"])
    long_distance_hybrid_ok = bool(long_distance["hybrid_load_satisfied"])
    high_temp = temperature[
        (temperature["status"] == "feasible") & (temperature["long_distance_base_duty_meets_load"] == True)
    ].head(1)
    best_auxiliary = auxiliary_heat.sort_values("net_power_saving_kw", ascending=False).iloc[0]
    practical_passive = passive_zero_warmup[passive_zero_warmup["practical_zero_warmup_design_found"] == True].copy()
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
        f"- 추정 최대 하이브리드 편도 성립거리는 약 {_format_number(distance['max_feasible_distance_m'].iloc[0] / 1000.0)} km다.",
        f"- 기본 LNG duty 기준 최대 편도 성립거리는 약 {_format_number(distance['max_base_duty_distance_m'].iloc[0] / 1000.0)} km다.",
        f"- 따라서 현재 설계점에서 {int(long_distance['distance_km'])} km 조건은 {'기본 LNG duty까지 성립' if long_distance_base_ok else '하이브리드 성립, 기본 LNG duty 불성립' if long_distance_hybrid_ok else '하이브리드까지 포함해 불성립'}이라고 정리한다.",
        "",
        "## 슬라이드 14. 순환 배관 설계 - 공급온도 민감도",
        "- 공급온도를 높이면 성립거리는 늘어나지만, 유체 선택과 펌프동력이 같이 바뀐다고 설명한다.",
        "- 공격적 passive heat 탐색에선 무보조 점이 나오더라도, 현실성 필터를 거치면 현재는 채택 가능한 무보조 해가 남지 않는다고 덧붙인다.",
        "",
        "## 슬라이드 15. 열역학/경제성 평가 - 소비동력 비교",
        f"- 이론 최소동력은 {_format_number(float(summary['Theoretical minimum power']['value']))} kW다.",
        f"- 기준 R-134a 압축기 동력은 {_format_number(float(summary['Baseline R-134a compressor power']['value']))} kW다.",
        f"- LNG 외부 루프 펌프는 {_format_number(float(summary['LNG system pump power']['value']))} kW, IDC 2차 루프 펌프는 {_format_number(float(summary['IDC secondary-loop pump power']['value']))} kW이며, 합산 core system power는 {_format_number(float(summary['Core LNG system power']['value']))} kW라고 설명한다.",
        f"- 만약 보조 열원이 남는다면, 현재 시나리오 중 최선은 {best_auxiliary['scenario_label']}이고 총 시스템 동력은 {_format_number(best_auxiliary['total_system_power_kw'])} kW라고 설명한다.",
        "",
        "## 슬라이드 16. 열역학/경제성 평가 - 연간 효과와 회수기간",
        f"- 연간 전력 절감량은 {_format_number(annual_map['Electricity saving']['value'])} MWh/년이다.",
        f"- 연간 전력요금 절감은 {_format_number(annual_map['Electricity cost saving']['value'] / 1_000_000.0)} 백만원/년 수준이다.",
        f"- 연간 회피 간접배출은 {_format_number(annual_map['Avoided indirect emissions']['value'])} tCO2/년이다.",
        f"- 다만 core installed CAPEX는 {_format_number(float(summary['Core installed CAPEX']['value']) / 1_000_000_000.0, 2)} 십억원, NPV는 {_format_number(float(summary['Core-system NPV']['value']) / 1_000_000_000.0, 2)} 십억원으로 현재는 투자 부담이 크다고 덧붙인다.",
        "",
        "## 슬라이드 17. 추가 고려 사항 - 확장 과제",
        "- 혼합 LNG surrogate, IDC 2차 루프, 장거리 조건의 제어 전략과 보조 열원 CAPEX가 후속 과제라고 정리한다.",
        f"- 현재 기본안에서 {int(long_distance['distance_km'])} km 조건은 {'기본 LNG duty까지 이미 성립' if long_distance_base_ok else '하이브리드는 성립하지만 기본 LNG duty는 아직 불성립' if long_distance_hybrid_ok else '하이브리드까지 포함해 아직 불성립'}이라고 정리하고, 그 이유를 IDC 측 HX와 총 duty 관점에서 설명한다.",
        "",
        "## 슬라이드 18. 추가 고려 사항 - 출처 체계와 재현성",
        "- config, sources, assumptions, output, deliverables가 하나의 저장소 안에서 연결된 구조라고 설명한다.",
        "- 질의응답에서 수치와 가정을 바로 추적할 수 있다는 점이 이번 재구축의 장점이라고 말한다.",
        "",
        "## 슬라이드 19. 결론",
        f"- 10 km 기본안은 {'기본 LNG duty 기준으로' if base_distance_base_ok else 'supplemental warm-up을 포함한 하이브리드 운전 기준으로' if base_distance_hybrid_ok else '하이브리드까지 포함해도'} 기술적으로 {'성립한다고' if base_distance_hybrid_ok else '불성립한다고'} 결론낸다.",
        f"- 동시에 {int(long_distance['distance_km'])} km 조건은 현재 기본안에서 {'기본 LNG duty까지 성립' if long_distance_base_ok else '하이브리드 성립, 기본 LNG duty 불성립' if long_distance_hybrid_ok else '하이브리드까지 포함해 불성립'}이며, 추정 최대 하이브리드 편도 성립거리는 약 {_format_number(distance['max_feasible_distance_m'].iloc[0] / 1000.0)} km라고 정리한다.",
    ]
    if (not long_distance_base_ok) and (not high_temp.empty):
        row = high_temp.iloc[0]
        script_lines.insert(
            script_lines.index("## 슬라이드 15. 열역학/경제성 평가 - 소비동력 비교") - 1,
            f"- 공급온도 {row['supply_temp_c']:.1f} °C에서는 {row['selected_fluid']}로 35 km 기본 LNG duty 조건을 복구할 수 있다는 점도 함께 언급한다.",
        )
    script_lines.extend(
        [
            (
                "- 현실성 필터 결과 "
                + ("채택 가능한 무보조 해가 남는다고 설명한다." if not practical_passive.empty else "채택 가능한 무보조 해는 아직 없다고 정리한다.")
            ),
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
