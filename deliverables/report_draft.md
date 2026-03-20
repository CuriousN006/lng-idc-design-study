# LNG 냉열 기반 IDC 냉각시스템 설계 연구

> 이 문서는 GitHub Markdown 수식 렌더링을 고려해 `math` 코드 블록과 inline LaTeX 표기를 사용했다.

## 초록

본 연구는 2022년 열시스템디자인 과제를 재현 가능한 코드 기반 설계 연구로 다시 구성한 결과물이다. 대상 IDC의 총 냉방부하는 **13,476.0 kW**로 계산되었고, 이론 최소동력은 **1,215.8 kW**, 기준 R-134a 증기압축 시스템의 압축기 동력은 **4,185.4 kW**로 산정되었다. 이에 비해 LNG 냉열 기반 시스템은 **R-717 (Ammonia)**를 2차 루프 냉각유체로 사용할 때 LNG 기화 duty **18,010.5 kW**, 배관 열유입 **580.4 kW**, 루프 펌프동력 **22.2 kW**의 설계가 가능했다. 그 결과 기준 시스템 대비 전력 절감은 **4,163.2 kW**, 연간 전력 절감은 **36,470.0 MWh/년**, 연간 비용 절감은 **3,831.2 백만원/년**, 연간 회피 배출은 **16,721.5 tCO2/년**으로 평가되었다. 현재 운전점에서의 추정 최대 성립거리는 약 **103.8 km**이며, 35 km 조건은 **성립**으로 판정되었다.

*출처 ID: SRC-001,SRC-004,SRC-005,SRC-006,SRC-007,SRC-008,SRC-010,SRC-013,SRC-014,ASM-020,ASM-032,ASM-033,ASM-034,ASM-035*

## 1. 서론

데이터센터는 상시 운전되는 고발열 시설이며, 냉방 시스템은 전체 전력 수요의 상당 부분을 차지한다. 따라서 데이터센터 냉각을 기계식 압축기 중심으로만 해결하는 접근은 에너지 비용과 전력 인프라 부담을 동시에 키운다. 반면 LNG 기화 과정은 극저온의 냉열을 본질적으로 포함하므로, 이를 적절히 회수하면 대규모 냉방부하를 낮은 동력으로 처리할 수 있다.

이번 재구축의 목표는 단순히 예전 엑셀 파일을 재현하는 것이 아니라, 설계 가정과 출처, 계산식, 민감도 분석, 산출물을 하나의 저장소 안에서 다시 생성할 수 있는 구조로 바꾸는 것이었다. 즉, 결과값만 맞추는 프로젝트가 아니라 왜 그 결과가 나오는지까지 추적 가능한 프로젝트로 재정의했다.

이 보고서가 답하려는 핵심 질문은 다음과 같다.

1. 대상 IDC의 총 냉방부하는 얼마인가?
2. 해당 부하에 대한 이론 최소동력과 기존 증기압축 기준선은 어느 수준인가?
3. LNG와 IDC를 연결하는 2차 루프에는 어떤 냉각유체가 가장 적합한가?
4. LNG 기화기와 장거리 배관을 동시에 만족하는 설계점은 존재하는가?
5. 10 km 기본 설계와 35 km 확장 조건은 어떤 차이를 보이는가?
6. 연간 에너지, 비용, 탄소 효과는 어느 정도인가?

*출처 ID: SRC-001,SRC-009,SRC-011*

## 2. 문제 정의와 입력 조건

과제에서 제시된 기본 경계조건은 랙 수, 랙당 발열, 실내 공기 조건, 냉수 조건, LNG 압력과 온도, 기화기 최소 접근온도, 기본 이송거리와 확장 이송거리로 구성된다. 이 조건들은 [base.toml](../config/base.toml)에 정리되어 있으며, 각 항목에는 원문 출처 또는 가정 ID가 함께 연결되어 있다.

| 항목 | 값 | 출처 ID |
| --- | --- | --- |
| 랙 수 | 1100 racks | SRC-001 |
| 랙당 IT 발열 | 10.0 kW/rack | SRC-001 |
| 실내 공기 조건 | 20.0 °C, RH 50% | SRC-001 |
| 냉수 공급/환수 | 7.0 / 12.0 °C | SRC-001 |
| 외기 조건 | 35.0 °C, RH 70% | SRC-001 |
| LNG 압력/입구온도 | 7.0 MPa, 112.0 K | SRC-001 |
| NG 목표 출구온도 | 283.0 K | SRC-001 |
| 최소 접근온도 | 10.0 K | SRC-001 |
| 기본 이송거리 | 10.0 km | SRC-001 |
| 도전 이송거리 | 35.0 km | SRC-001 |

또한 과제 원문에 직접 주어지지 않는 층고, 틈새바람, 외피 열관류율, 배관 roughness, 단열 두께 스캔 범위 등은 별도의 공학 가정으로 관리했다. 이 가정들은 결과를 임의로 조정하기 위한 숫자가 아니라, 설계 자동화를 위해 반드시 필요한 기본값들이다.

*출처 ID: SRC-001,ASM-001,ASM-007,ASM-014,ASM-015,ASM-019,ASM-020,ASM-024,ASM-025,ASM-027,ASM-028,ASM-029,ASM-033,ASM-034,ASM-035*

## 3. 수학적 모델

본 연구의 계산 체계는 부하 모델, 이론 최소동력, 기준 냉동사이클, 냉각유체 스크리닝, LNG 기화기 상세설계, 장거리 배관 설계, 연간 효과 평가의 7개 모듈로 구성된다. 각 모듈은 하나의 독립 계산기라기보다, 앞 단계의 결과를 다음 단계의 입력으로 넘기는 연속 설계 파이프라인이다.

### 3.1 냉방부하 모델

냉방부하 모델은 IT 랙 발열뿐 아니라 전력 분배 손실, 조명, 부대설비, 인체 발열, 외피 전도, 일사, 틈새바람에 의한 외기 유입을 모두 더해 총 냉방부하를 산정한다. 현재 구현은 `load_model.py`에 있으며, 부하를 하나의 lumped load가 아니라 항목별 합산으로 계산한다.

```math
\dot Q_{\mathrm{total}} = \dot Q_{\mathrm{IT}} + \dot Q_{\mathrm{dist}} + \dot Q_{\mathrm{light}} + \dot Q_{\mathrm{aux}} + \dot Q_{\mathrm{occ}} + \dot Q_{\mathrm{wall}} + \dot Q_{\mathrm{roof}} + \dot Q_{\mathrm{glz}} + \dot Q_{\mathrm{sol}} + \dot Q_{\mathrm{inf}}
\dot Q_{\mathrm{wall}} = U_{\mathrm{wall}} A_{\mathrm{wall}} (T_{\mathrm{amb}} - T_{\mathrm{room}})
\dot Q_{\mathrm{roof}} = U_{\mathrm{roof}} A_{\mathrm{roof}} (T_{\mathrm{amb}} - T_{\mathrm{room}})
\dot Q_{\mathrm{glz}} = U_{\mathrm{glz}} A_{\mathrm{glz}} (T_{\mathrm{amb}} - T_{\mathrm{room}})
\dot Q_{\mathrm{sol}} = I_{\mathrm{eff}} \cdot SHGC \cdot A_{\mathrm{glz}}
\dot Q_{\mathrm{inf}} = \dot V_{\mathrm{inf}} \rho_{\mathrm{amb}} (h_{\mathrm{amb}} - h_{\mathrm{room}})
```

특히 틈새바람 부하는 외기와 실내의 습공기 엔탈피 차를 사용해 평가했다.

```math
w = 0.62198 \frac{p_w}{p - p_w}
h = 1000 \left(1.006 T_{^\circ\mathrm{C}} + w \left(2501 + 1.86 T_{^\circ\mathrm{C}}\right)\right)
```

| 부하 항목 | 열부하 (kW) | 비중 (%) |
| --- | --- | --- |
| IT racks | 11,000.0 | 81.63 |
| Power distribution losses | 880.0 | 6.53 |
| Lighting | 528.0 | 3.92 |
| Auxiliary building services | 220.0 | 1.63 |
| Occupants | 16.5 | 0.12 |
| Wall conduction | 63.5 | 0.47 |
| Roof conduction | 15.0 | 0.11 |
| Glazing conduction | 36.3 | 0.27 |
| Solar gain | 164.6 | 1.22 |
| Infiltration | 552.1 | 4.10 |

계산 결과 총 냉방부하는 **13,476.0 kW**였고, 그중 IT 랙과 전력 분배 손실이 가장 큰 비중을 차지했다. 이는 데이터센터 부하의 본질이 전산장비 발열이라는 점과 일치한다.

*출처 ID: SRC-001,ASM-001,ASM-003,ASM-004,ASM-005,ASM-006,ASM-007,ASM-008,ASM-009,ASM-010,ASM-011*

### 3.2 이론 최소동력

이론 최소동력은 냉수 평균온도를 저온 열원, 외기온도를 고온 열원으로 두는 이상 카르노 냉동기의 최소 일 입력으로 계산했다. 이는 실제 장치가 달성할 수 없는 절대 하한선이다.

```math
T_L = \frac{T_{\mathrm{cw,s}} + T_{\mathrm{cw,r}}}{2}
T_H = T_{\mathrm{amb}}
\dot W_{\min} = \dot Q_L \frac{T_H - T_L}{T_L}
```

냉수 평균온도는 **9.5 °C**, 외기온도는 **35.0 °C**로 두었고, 계산된 이론 최소동력은 **1,215.8 kW**였다.

*출처 ID: SRC-001*

### 3.3 기준 R-134a 증기압축 사이클

기준 시스템은 단순 R-134a 증기압축 사이클로 모델링했다. 증발기와 응축기 접근온도는 각각 10 K, 압축기 등엔트로피 효율은 75%로 두었다.

```math
h_2 = h_1 + \frac{h_{2s} - h_1}{\eta_{\mathrm{is}}}
\dot m_{\mathrm{ref}} = \frac{\dot Q_L}{h_1 - h_4}
\dot W_{\mathrm{comp}} = \dot m_{\mathrm{ref}} (h_2 - h_1)
COP = \frac{\dot Q_L}{\dot W_{\mathrm{comp}}}
```

이 기준선에서 압축기 동력은 **4,185.4 kW**로 계산되었고, 이는 기존 엑셀 결과 **3,994.2 kW**와 같은 규모를 보였다.

![기준 R-134a 사이클 P-h 선도](../output/figures/baseline_cycle_ph.png)

*출처 ID: SRC-001,SRC-004,SRC-005*

### 3.4 냉각유체 스크리닝과 IDC 측 열교환기

2차 루프 냉각유체 후보는 R-170, R-717, R-744, R-1270, R-290, R-600a, R-1150으로 두었다. 후보는 1 MPa 루프 압력에서 단상 액체 여부, 삼중점 여유, IDC 측 열교환기 성립성, 요구 질량유량과 점도, 안전성 패널티를 기준으로 정렬했다.

```math
T_{\mathrm{after\ IDC}} = T_{\mathrm{cw,r}} - \Delta T_{\min}
\dot V_{\mathrm{loop}} = \frac{\dot m_{\mathrm{loop}}}{\rho}
\dot m_{\mathrm{loop}} = \frac{\dot Q_{\mathrm{IDC}}}{h\!\left(T_{\mathrm{after\ IDC}}, P\right) - h\!\left(T_{\mathrm{supply}}, P\right)}
\phi_{\mathrm{target}} = 0.90
\dot Q_{\mathrm{LNG,target}} = \frac{\dot Q_{\mathrm{IDC}}}{\phi_{\mathrm{target}}}
\dot Q_{\mathrm{pipe,max}} = \dot Q_{\mathrm{LNG,target}} - \dot Q_{\mathrm{IDC}}
T_{\mathrm{return,min}} = T_{\mathrm{NG,out}} + \Delta T_{\min}
\dot Q_{\mathrm{LNG,min}} = \dot m_{\mathrm{loop}} \left(h\!\left(T_{\mathrm{return,min}}, P\right) - h\!\left(T_{\mathrm{supply}}, P\right)\right)
\dot Q_{\mathrm{pipe,min}} = \dot Q_{\mathrm{LNG,min}} - \dot Q_{\mathrm{IDC}}
A_{\mathrm{IDC}} = \frac{\dot Q_{\mathrm{IDC}}}{U_{\mathrm{IDC}}\Delta T_{\mathrm{lm,IDC}}}
I_{\mathrm{transport}} = \dot m_{\mathrm{loop}} \frac{\mu}{\rho}
S = 1 - 0.35 m_{\mathrm{norm}} - 0.20 \dot V_{\mathrm{norm}} - 0.10 I_{\mathrm{norm}} - 0.10 \dot Q_{\mathrm{pipe,min,norm}} - 0.05 A_{\mathrm{IDC,norm}} + 0.10 M_{\mathrm{window,norm}} - 0.15 Q_{\mathrm{shortfall,norm}} - P_{\mathrm{safety}} - P_{\mathrm{compat}}
```

즉, 이번 스크리닝은 먼저 IDC 측 열교환기에서 요구 질량유량을 계산한 뒤, 90% 이용률 목표가 허용하는 배관 열유입 상한과 LNG hot-end가 요구하는 최소 환수온도 조건을 함께 계산한다. 이후 그 창(window) 안에 드는 후보를 우선하고, 부족분이 남는 경우에는 supplemental warm-up 요구량으로 별도 추적한다.

| 유체 | 스크리닝 점수 | 펌프동력 (kW) | 추가 warm-up (kW) | 쉘 직경 (m) | 연간 비용절감 (백만원/년) |
| --- | --- | --- | --- | --- | --- |
| R-717 (Ammonia) | 0.795 | 22.2 | 3,954.0 | 0.792 | 3,831.2 |
| R-290 (Propane) | 0.077 | 220.5 | 4,240.3 | 0.914 | 3,648.6 |
| R-600a (Isobutane) | 0.059 | 235.2 | 4,148.2 | 0.885 | 3,635.1 |

기본 설계점에서 최상위 유체는 **R-717 (Ammonia)**였고, 요구 질량유량은 **54.4 kg/s**였다. 또한 IDC 측 열교환기의 요구 면적은 **567.2 m2**, IDC 출구 냉각유체 온도는 **2.0 °C**, LNG 입구 환수온도는 **19.8 °C**로 계산되었다.

![IDC 측 열교환기 온도 프로파일](../output/figures/idc_hx_temperature_profile.png)

![냉각유체 후보 비교](../output/figures/fluid_ranking.png)

*출처 ID: SRC-001,SRC-003,SRC-005,SRC-008,ASM-017,ASM-018,ASM-033,ASM-034,ASM-035*

### 3.5 LNG 기화기 상세설계

기화기 모델의 핵심은 7 MPa 메탄의 비열이 극저온 영역에서 크게 변하므로, 단일 평균 비열 기반 LMTD 계산만으로는 정확한 설계를 보장하기 어렵다는 점이다. 따라서 본 코드는 112-190-205-220-283 K의 네 구간으로 나누어 엔탈피 기반 열량을 추적했다.

```math
\dot m_{\mathrm{LNG}} = \frac{\dot Q_{\mathrm{total}}}{h_{\mathrm{NG,out}} - h_{\mathrm{LNG,in}}}
\dot q_i = \dot m_{\mathrm{LNG}} (h_{i+1} - h_i)
Nu_t = 0.023 Re_t^{0.8} Pr_t^{0.4}
j_h = 0.5 \left(1 + \frac{B}{D_s}\right)\left(0.08 Re_s^{0.6821} + 0.7 Re_s^{0.1772}\right)
h_o = j_h \frac{k_s Pr_s^{1/3}}{D_e}
U_o^{-1} = \frac{d_o}{d_i h_i} + \frac{d_o \ln(d_o / d_i)}{2 k_w} + \frac{1}{h_o}
A_{\mathrm{req}} = \sum_i \frac{\dot q_i}{U_{o,i}\Delta T_{\mathrm{lm},i}}
```

기하 형상은 관 길이 6-16 m, 관 수 200-2200개 범위에서 자동 탐색했고, 제공 면적, 유속 제한, 핀치 조건을 동시에 검사했다.

| 구간 | 구간 열부하 (kW) | LNG 입구 (K) | LNG 출구 (K) | 냉각유체 입구 (K) | 냉각유체 출구 (K) |
| --- | --- | --- | --- | --- | --- |
| 112-190 K | 7,091.1 | 112.0 | 190.0 | 249.4 | 220.0 |
| 190-205 K | 2,899.6 | 190.0 | 205.0 | 261.2 | 249.4 |
| 205-220 K | 2,929.4 | 205.0 | 220.0 | 272.9 | 261.2 |
| 220-283 K | 5,090.4 | 220.0 | 283.0 | 293.0 | 272.9 |

최종 형상은 **관 수 600개**, **관 길이 14.0 m**, **쉘 직경 0.792 m**로 정리되었고, 최소 핀치는 **10.0 K**였다.

![LNG 기화기 온도 프로파일](../output/figures/hx_temperature_profile.png)

*출처 ID: SRC-001,SRC-004,SRC-005,SRC-006,SRC-007,ASM-020,ASM-021,ASM-022,ASM-023*

### 3.6 장거리 배관 모델

배관 모델은 공급관과 환수관의 압력강하와 열유입을 각각 계산하고, 이를 합쳐 전체 펌프동력과 IDC 도달 냉량을 평가한다. 설계 변수는 공급관 내경, 환수관 내경, 단열 두께다.

```math
Re = \frac{\rho v D}{\mu}
\Delta P = f \frac{L}{D}\frac{\rho v^2}{2} + K \frac{\rho v^2}{2}
\dot q' = \frac{T_{\mathrm{amb}} - T_f}{\ln(r_2 / r_1)/(2 \pi k_{\mathrm{ins}}) + 1/(2 \pi r_2 h_o)}
\dot Q_{\mathrm{pipe}} = (\dot q'_{\mathrm{supply}} + \dot q'_{\mathrm{return}}) L
\dot W_{\mathrm{pump}} = \frac{\Delta P_{\mathrm{supply}}\dot V_{\mathrm{supply}} + \Delta P_{\mathrm{return}}\dot V_{\mathrm{return}}}{\eta_{\mathrm{pump}}}
```

배관 스캔은 펌프동력과 ambient heat gain을 직접 계산하고, LNG hot-end가 요구하는 최소 환수온도에 못 미치는 경우에는 supplemental warm-up 요구량을 함께 산정한다. 따라서 현재 모델의 장거리 성립성은 단순 열손실이 아니라 `펌프동력 + ambient pickup + 추가 warm-up`의 결합 문제로 읽는다.

| 설계 변수 | 값 |
| --- | --- |
| 공급관 내경 | 0.350 m |
| 환수관 내경 | 0.350 m |
| 단열 두께 | 0.050 m |
| 배관 열유입 | 580.4 kW |
| 추가 warm-up | 3,954.0 kW |
| 루프 펌프동력 | 22.2 kW |
| 공급관 속도 | 0.840 m/s |
| 환수관 속도 | 0.906 m/s |
| 공급관 압력강하 | 96.5 kPa |
| 환수관 압력강하 | 101.3 kPa |

![배관 직경 트레이드오프](../output/figures/pipeline_tradeoff.png)

*출처 ID: SRC-001,ASM-014,ASM-015,ASM-016,ASM-024,ASM-025,ASM-026*

### 3.7 연간 에너지, 비용, 탄소 모델

연간화는 데이터센터의 상시 운전을 반영해 8,760시간/년 기준으로 수행했다. 전력요금과 전력 배출계수는 공식 자료를 기준으로 입력했으며, v1에서는 기준 압축기 동력과 LNG 루프 펌프동력만을 비교 경계로 삼았다.

```math
E_{\mathrm{year}} = P \cdot t_{\mathrm{op}} / 1000
C_{\mathrm{year}} = P \cdot t_{\mathrm{op}} \cdot c_e
M_{\mathrm{CO_2}} = E_{\mathrm{year}} \cdot EF_{\mathrm{grid}}
CAPEX_{\mathrm{allow}} = \Delta C_{\mathrm{year}} \cdot N_{\mathrm{payback}}
```

*출처 ID: SRC-013,SRC-014,ASM-030,ASM-031,ASM-032*

## 4. 결과

### 4.1 전체 성능 요약

| 항목 | 값 |
| --- | --- |
| 총 냉방부하 | 13,476.0 kW |
| 이론 최소동력 | 1,215.8 kW |
| 기준 압축기 동력 | 4,185.4 kW |
| 선정 냉각유체 | R-717 (Ammonia) |
| IDC 측 HX 면적 | 567.2 m2 |
| IDC 출구 냉각유체 온도 | 2.0 °C |
| LNG 유입 환수온도 | 19.8 °C |
| LNG 기화 duty | 18,010.5 kW |
| 배관 열유입 | 580.4 kW |
| 추가 warm-up | 3,954.0 kW |
| IDC 도달 가능 냉량 | 13,476.0 kW |
| 루프 펌프동력 | 22.2 kW |
| 등가 냉각 COP | 607.7 |
| 기준 대비 절감 동력 | 4,163.2 kW |

가장 먼저 눈에 띄는 결과는 **607.7**에 달하는 등가 냉각 COP다. 이 값은 동일 냉방부하를 처리하기 위해 요구되는 전력의 크기가 얼마나 줄었는지를 보여준다.

![시스템 소비동력 비교](../output/figures/system_power_comparison.png)

### 4.2 냉각유체 선정 결과

후보군 비교 결과, 기본안은 **R-717 (Ammonia)**로 결정되었다. 이는 루프 질량유량, IDC 측 HX 면적 **567.2 m2**, 장거리 배관 동력, 기화기 형상, 환경성, 안전성 패널티를 동시에 고려한 결과다.

| 유체 | 스크리닝 점수 | 펌프동력 (kW) | 추가 warm-up (kW) | 쉘 직경 (m) | 연간 비용절감 (백만원/년) |
| --- | --- | --- | --- | --- | --- |
| R-717 (Ammonia) | 0.795 | 22.2 | 3,954.0 | 0.792 | 3,831.2 |
| R-290 (Propane) | 0.077 | 220.5 | 4,240.3 | 0.914 | 3,648.6 |
| R-600a (Isobutane) | 0.059 | 235.2 | 4,148.2 | 0.885 | 3,635.1 |

### 4.3 LNG 기화기 결과

LNG 기화기 설계는 네 구간 모두에서 양의 핀치를 유지했고, 최소값은 **10.0 K**였다. 최종적으로 LNG는 **112.0 K**에서 **283.0 K**까지 가열된다.

| 구간 | 구간 열부하 (kW) | LNG 입구 (K) | LNG 출구 (K) | 냉각유체 입구 (K) | 냉각유체 출구 (K) |
| --- | --- | --- | --- | --- | --- |
| 112-190 K | 7,091.1 | 112.0 | 190.0 | 249.4 | 220.0 |
| 190-205 K | 2,899.6 | 190.0 | 205.0 | 261.2 | 249.4 |
| 205-220 K | 2,929.4 | 205.0 | 220.0 | 272.9 | 261.2 |
| 220-283 K | 5,090.4 | 220.0 | 283.0 | 293.0 | 272.9 |

### 4.4 배관 설계와 거리 민감도

배관 기본안은 공급관과 환수관 모두 **0.350 m** 내경을 사용하고, 단열 두께는 **0.050 m**로 결정되었다.

| 거리 (km) | 펌프동력 (kW) | 열유입 (kW) | 추가 warm-up (kW) | 열여유 (kW) | IDC 부하 충족 |
| --- | --- | --- | --- | --- | --- |
| 5.0 | 11.4 | 290.2 | 4,244.2 | 0.0 | 예 |
| 10.0 | 22.2 | 580.4 | 3,954.0 | 0.0 | 예 |
| 15.0 | 33.0 | 870.7 | 3,663.8 | 0.0 | 예 |
| 20.0 | 43.8 | 1,160.9 | 3,373.6 | 0.0 | 예 |
| 25.0 | 54.6 | 1,451.1 | 3,083.4 | -0.0 | 예 |
| 30.0 | 65.4 | 1,741.3 | 2,793.2 | 0.0 | 예 |
| 35.0 | 76.2 | 2,031.5 | 2,502.9 | 0.0 | 예 |

![거리 민감도](../output/figures/pipeline_distance_sensitivity.png)

거리 증가에 따라 열유입이 거의 선형적으로 증가하면서, 현재 운전점에서의 추정 최대 편도 성립거리는 **103.8 km**로 나타났다. 따라서 **35 km** 조건은 기본안의 단순 확장만으로는 **성립 판정**을 받는다.

### 4.5 공급온도 민감도와 35 km 해석

| 공급온도 (°C) | 선정 유체 | 펌프동력 (kW) | 최대 성립거리 (km) | 35 km 충족 | 상태 |
| --- | --- | --- | --- | --- | --- |
| -63.1 | R-717 (Ammonia) | 13.7 | 83.2 | 예 | 성립 |
| -58.1 | R-717 (Ammonia) | 17.2 | 92.5 | 예 | 성립 |
| -53.1 | R-717 (Ammonia) | 22.2 | 103.8 | 예 | 성립 |
| -48.1 | R-717 (Ammonia) | 29.2 | 117.5 | 예 | 성립 |
| -43.1 | R-717 (Ammonia) | 39.7 | 134.4 | 예 | 성립 |
| -38.1 | R-717 (Ammonia) | 55.9 | 155.9 | 예 | 성립 |
| -33.1 | R-717 (Ammonia) | 82.6 | 183.8 | 예 | 성립 |

![공급온도 민감도](../output/figures/supply_temperature_sensitivity.png)

공급온도 스윕 결과, 펌프동력 최소점은 **-63.1 °C**이며 이때도 기본 유체는 **R-717 (Ammonia)**로 유지된다. 현재 기본안 자체가 **35 km** 조건을 이미 만족하므로, 공급온도 스윕은 복구 목적이 아니라 추가 여유와 펌프동력 변화의 trade-off를 읽기 위한 분석으로 해석된다.

### 4.6 추가 warm-up 제거 가능성

| 공급온도 (°C) | 유체 | 기본안 추가 warm-up (kW) | 무보조 성립거리 (km) | 35 km 무보조 성립 | 기본 스크리닝 선정 |
| --- | --- | --- | --- | --- | --- |
| -63.1 | R-717 (Ammonia) | 3,240.3 | 62.7 | 아니오 | 예 |
| -63.1 | R-600a (Isobutane) | 3,427.3 | 65.8 | 아니오 | 아니오 |
| -63.1 | R-290 (Propane) | 3,508.3 | 67.1 | 아니오 | 아니오 |
| -58.1 | R-717 (Ammonia) | 3,569.0 | 69.7 | 아니오 | 예 |
| -58.1 | R-600a (Isobutane) | 3,759.3 | 72.9 | 아니오 | 아니오 |
| -58.1 | R-290 (Propane) | 3,845.6 | 74.4 | 아니오 | 아니오 |
| -53.1 | R-717 (Ammonia) | 3,954.0 | 78.1 | 아니오 | 예 |
| -53.1 | R-600a (Isobutane) | 4,148.2 | 81.5 | 아니오 | 아니오 |

![무보조 warm-up 성립거리 맵](../output/figures/ambient_closure_map.png)

현재 탐색 범위에서 가장 이른 무보조 warm-up 성립점은 **-63.1 °C / R-717 (Ammonia)** 조합이며, ambient heat gain만으로 LNG hot-end를 만족시키려면 최소 **62.7 km**의 편도 거리가 필요했다. 이때의 루프 펌프동력은 **13.7 kW**였다.

현재 탐색 범위에서는 10 km와 35 km 모두 ambient heat gain만으로 LNG hot-end를 만족시키지 못했고, 가장 빠른 무보조 성립거리도 **62.7 km**였다. 따라서 현재 추가 warm-up 항은 단순 수치 보정이 아니라, 물리적으로 의미 있는 보조 열원 요구량으로 해석하는 편이 맞다.

### 4.7 연간 효과와 경제성

| 항목 | 값 | 단위 |
| --- | --- | --- |
| 기준 시스템 전력사용 | 36,664.2 | MWh/년 |
| LNG 시스템 전력사용 | 194.3 | MWh/년 |
| 전력 절감 | 36,470.0 | MWh/년 |
| 전력요금 절감 | 3,831.2 | 백만원/년 |
| 회피 간접배출 | 16,721.5 | tCO2/년 |

![연간 효과](../output/figures/annual_impact_comparison.png)

| 회수기간 (년) | 허용 추가 투자비 (백만원) |
| --- | --- |
| 3 | 11,493.5 |
| 5 | 19,155.8 |
| 7 | 26,818.2 |
| 10 | 38,311.7 |

현재 비교 경계에서 LNG 시스템은 연간 **36,470.0 MWh/년**의 전력을 줄이고, 연간 **3,831.2 백만원/년**의 전기요금을 절감하며, 연간 **16,721.5 tCO2/년**의 간접배출을 회피한다.

### 4.8 기존 엑셀 결과와 비교

| 항목 | 기존 엑셀 (kW) | 현재 코드 (kW) | 차이 (kW) | 차이율 (%) |
| --- | --- | --- | --- | --- |
| 이론 최소동력 | 1,272.2 | 1,215.8 | -56.5 | -4.44 |
| 기준 압축기 동력 | 3,994.2 | 4,185.4 | 191.2 | 4.79 |

## 5. 논의

첫째, 10 km 기본 설계는 기술적으로 성립할 뿐 아니라 에너지 절감 측면에서도 매우 유리하다. 기준 압축기 시스템이 수 MW급 전력을 요구하는 반면, LNG 냉열 기반 루프는 수십 kW 수준의 펌프동력으로 동일한 냉방부하를 처리할 수 있었다.

둘째, 이번 프로젝트의 진짜 설계 통찰은 35 km 조건의 판정이 운전점과 열수지 가정에 따라 달라질 만큼 민감하다는 사실이다. 이번 결과는 현재 기본안의 경계가 약 **103.8 km**라는 점을 정량적으로 보여준다. 특히 현재 기본안 자체가 **35 km** 조건도 이미 충족한다는 점은, 기존 프로젝트의 보수적 duty 가정이 실제보다 제한적이었을 가능성을 보여준다.

셋째, 이번 모델에서는 35 km가 별도 운전점 변경 없이도 성립했다. 즉, IDC 측 HX 제약과 LNG hot-end 제약을 동시에 반영한 뒤 총 duty를 다시 계산하면, 장거리 조건의 해석이 기존보다 훨씬 완화될 수 있음을 확인했다.

넷째, 추가 warm-up을 완전히 제거하는 관점에서 보면 현재 **10.0 km** 기본거리는 아직 충분한 ambient pickup을 제공하지 못한다. 따라서 현 기본안은 순수 LNG 냉열 단독안이라기보다, LNG hot-end 조건을 맞추기 위한 보조 열원 또는 더 긴 배관거리의 도움을 받는 하이브리드 운전점으로 읽는 편이 더 정확하다.

다섯째, 등가 COP와 연간 절감량은 매우 크지만, 현 단계의 경제성 경계는 압축기 동력 대 펌프동력 비교에 한정되어 있다.

## 6. 한계와 향후 확장

- LNG는 v1에서 순수 메탄으로 가정했다.
- IDC 측 분배 네트워크는 전체 유압망이 아니라 냉방 duty 경계조건으로 단순화했다.
- 기화기 설계는 열역학과 형상 스캔 중심이며, 응력과 제작성의 상세 검토는 아직 별도 단계가 필요하다.
- 경제성은 핵심 동력 비교 범위에 한정되므로 전체 CAPEX/OPEX 분석으로 확장되어야 한다.
- 냉각유체 스코어는 휴리스틱 성격이 있으므로, 안전/규제/재료 호환성 검토로 후속 보정이 필요하다.

## 7. 결론

본 연구는 총 **13,476.0 kW**의 IDC 냉방부하를 대상으로, LNG 냉열 기반 냉각 시스템이 10 km 기본 설계점에서 충분히 성립함을 보였다. 선정된 기본안은 **R-717 (Ammonia)**를 2차 루프 유체로 사용하고, 기화기 duty **18,010.5 kW**, 루프 펌프동력 **22.2 kW**, 배관 열유입 **580.4 kW**의 수준에서 IDC 부하를 충족한다. 현재 경계는 약 **103.8 km**이며, 35 km 조건은 **성립 판정**으로 정리되었다.

## 부록 A. 출처 레지스트리

| ID | 제목 | 형식 | 주요 사용값 |
| --- | --- | --- | --- |
| SRC-001 | 2022 열시스템 디자인 학기말 프로젝트 | Local assignment PDF | IDC 운전조건, 랙 부하, 냉수 조건, LNG 조건, 튜브 규격, 거리, 최소 온도차 |
| SRC-003 | Properties of Refrigerants | Local technical PDF | 냉매 후보군의 열역학/안전 참고 |
| SRC-004 | NIST REFPROP Overview | Official web | 물성 계산의 기준 참고 |
| SRC-005 | CoolProp High-Level API | Official web | 실제 코드 물성 엔진 |
| SRC-006 | TEMA 10th Edition | Local technical standard | 쉘-튜브 열교환기 nomenclature and sizing context |
| SRC-007 | Heat Exchanger Data Book | Local technical handbook | LMTD, Kern method, shell-side sizing context |
| SRC-008 | Refrigerants Environmental Data | Local technical PDF | GWP / ODP for candidate fluids |
| SRC-009 | KOGAS LNG Cold Energy Business | Official web | LNG 냉열 사업과 전력 수요 완화 배경 |
| SRC-010 | 2022 legacy heat exchanger design workbook | Local legacy workbook | 기존 팀의 Wmin, 기존 R-134a 압축기 동력 비교 기준 |
| SRC-011 | ASHRAE Thermal Guidelines Reference Card | Official PDF | 데이터센터 권장 운전 온도/환경 범위의 공식 배경 자료 |
| SRC-012 | NIST Chemistry WebBook Methane Entry | Official web | 메탄 물성/기초 식별 정보 보조 출처 |
| SRC-013 | KEA EG-TIPS standard energy saving project information | Official web | 산업용 전력 단가 105.05원/kWh, 전력 배출계수 0.4585 tCO2/MWh |
| SRC-014 | GIR 2024 approved electricity emission factor announcement | Official web | 2024 승인 전력배출계수 공고의 공식 확인 경로 |
| SRC-015 | EnergyPlus Engineering Reference | Official PDF | 외기 대류계수의 wind-speed correlation `h_c = 5.7 + 3.8 V_z` |
| SRC-016 | EnergyPlus Ground Heat Exchanger example page | Official web | buried pipe example inputs including burial depth 1.25 m and soil thermal conductivity 1.08 W/m-K |
| SRC-017 | NREL NSRDB documentation | Official web | 태양복사(GHI)·기온·풍속이 시간해상도 기상 입력으로 제공된다는 공식 데이터 체계 |
| SRC-018 | EnergyPlus Site:GroundTemperature:Undisturbed documentation | Official web | Kusuda-Achenbach 기반 지중온도 입력 구조와 example annual-average ground surface temperature 15.5 C |

## 부록 B. 공학 가정 레지스트리

| ID | 가정 | 값 | 설정 이유 |
| --- | --- | --- | --- |
| ASM-001 | Above-ground floor height | 4.0 m | 대형 IDC 층고의 보수적 기본값 |
| ASM-002 | Glazing ratio | 10% of exterior wall area | 창면적이 제한된 IDC 외피 가정 |
| ASM-003 | Lighting density | 12 W/m2 | 24/7 운영 시설의 보수적 실내 조명 부하 |
| ASM-004 | Power distribution loss fraction | 8% of IT load | UPS/PDU 손실 반영 |
| ASM-005 | Auxiliary service loss fraction | 2% of IT load | 승강기, 소방, BMS 등 부대설비 반영 |
| ASM-006 | Occupancy model | 220 persons, 75 W sensible each | 상주/점검 인력의 보수적 내부발열 |
| ASM-007 | Infiltration rate | 0.15 ACH | 밀폐성이 높은 IDC의 보수적 틈새 공기 유입 |
| ASM-008 | Wall U-value | 0.35 W/m2-K | 단열 외피 가정 |
| ASM-009 | Roof U-value | 0.25 W/m2-K | 지붕 단열 가정 |
| ASM-010 | Glazing U-value | 1.8 W/m2-K | 복층 glazing 수준의 보수적 값 |
| ASM-011 | Effective solar model | 350 W/m2 and SHGC 0.35 | 간략한 복사 열획득 모델 |
| ASM-012 | Tube bundle packing efficiency and pitch basis | 0.90 efficiency, 25.4 mm pitch | 단순 bundle sizing 근사 |
| ASM-013 | Shell clearance factor | 1.15 | bundle diameter to shell ID margin |
| ASM-014 | Insulation model | k = 0.028 W/m-K, outside h = 8 W/m2-K | 장거리 배관의 보수적 단열/외기전달 모델 |
| ASM-015 | Pipe roughness | 4.5e-5 m | 탄소강 배관 roughness 기본값 |
| ASM-016 | Minor loss coefficient | K = 10 per line | 밸브/엘보/헤더 등 lumped loss |
| ASM-017 | Fluid safety penalties | candidate-specific heuristic penalties | 독성/가연성 차이를 ranking에 반영 |
| ASM-018 | Material compatibility penalties | candidate-specific heuristic penalties | 암모니아/재질 호환성 차이를 ranking에 반영 |
| ASM-019 | Coolant loop temperature fallback | 220 K supply, 286 K after IDC, 293 K return to LNG | 기존 2022 엑셀 해석을 보존하기 위한 fallback 온도 세트이며, 현재는 동적 IDC 열교환기 계산이 우선 적용됨 |
| ASM-020 | LNG vaporizer segmentation | 112-190-205-220-283 K | 비열 급변 영역을 반영하는 4구간 모델 |
| ASM-021 | Baffle spacing | 0.30 m | 기존 계산 흔적과 textbook scale의 절충 |
| ASM-022 | Tube wall conductivity | 16 W/m-K | 금속관의 대표 열전도율 |
| ASM-023 | HX search grid | tube length 6-16 m, 200-2200 tubes | 설계 자동 탐색 범위 |
| ASM-024 | Pipeline diameter search grid | 0.10-0.35 m | 속도/압력강하 trade-off 탐색 범위 |
| ASM-025 | Insulation thickness search grid | 0.05-0.15 m | 열유입 trade-off 탐색 범위 |
| ASM-026 | Pipe wall thickness | 8 mm | 대구경 산업 배관의 단순 기본값 |
| ASM-027 | Distance sensitivity sweep grid | 5-35 km in 5 km steps | 기본 10 km와 장거리 한계 사이의 경향 확인 |
| ASM-028 | Coolant supply-temperature sweep grid | 210-240 K | 설계점 주변과 저온측 여유를 함께 보기 위한 운전 온도 민감도 확인 |
| ASM-029 | Supply-temperature sweep method | Only supply temperature is perturbed, and the IDC-side HX is re-solved at each sweep point | 운전 온도 수준 변화를 보되, 부하측 열교환기와 환수온도는 매번 다시 맞추는 물리 결합형 sweep 규칙 |
| ASM-030 | Annual operating hours | 8,760 h/year | 데이터센터의 연중 상시 운전을 반영한 연간화 기준 |
| ASM-031 | Simple payback targets | 3, 5, 7, 10 years | 추가 투자 허용범위를 빠르게 읽기 위한 경제성 지표 |
| ASM-032 | Economic comparison boundary | Baseline compressor power vs LNG loop pump power only | 냉각 시스템 핵심 동력 비교이며, 상세 O&M/보조기기/금융비용은 v1 범위 밖 |
| ASM-033 | IDC-side HX overall U | 850 W/m2-K | 액체-액체 열교환기의 1차 설계용 보수적 overall U 기본값 |
| ASM-034 | Chilled-water specific heat | 4,180 J/kg-K | 7/12°C 단상 냉수의 대표 비열값 |
| ASM-035 | IDC-side HX model structure | Counterflow 2-point pinch model with 7/12°C chilled water and minimum approach constraint | IDC 부하측 열교환기와 2차 루프를 전체 네트워크 없이도 물리적으로 연결하기 위한 최소 모델 |
| ASM-036 | Ambient-only closure criterion | First feasible one-way distance where supplemental warm-up falls below 1e-3 kW | 추가 warm-up이 필요 없는 설계점을 정량적으로 찾기 위한 판정 기준 |
| ASM-037 | Passive heat-search supply-temperature grid | 200-230 K in 5 K steps | 기본 설계점보다 더 저온까지 내려가며 무보조 성립 가능성을 확인하기 위한 확장 sweep |
| ASM-038 | Passive heat-search diameter grid | 0.075-0.35 m | 자연 열유입을 활용하는 공격적 배관 탐색에서 직경 제약을 더 넓게 보기 위한 확장 범위 |
| ASM-039 | Passive heat-search insulation grid | 0.00-0.15 m | 무보조 성립을 위해 의도적으로 단열을 줄이는 극단 설계까지 확인하기 위한 탐색 범위 |
| ASM-040 | Passive heat-search wind-speed cases | 0, 2, 4 m/s | `SRC-015`의 wind-based outside convection correlation 위에서 자연대류, 약한 바람, 비교적 강한 바람의 탐색용 경계조건을 주기 위한 시나리오 값 |
| ASM-041 | Passive heat-search net absorbed solar flux | 0, 250, 300 W/m2 | `SRC-017`의 태양복사/기상 데이터 체계 위에서 노출 배관이 받는 순흡수 열유속의 탐색용 envelope를 주기 위한 값이며, 현 단계에서는 site-specific weather replay가 아니라 scenario study용 |
| ASM-042 | Pump heat returned to loop in passive scenarios | 80% of pump power | 폐회로에서 펌프 소비동력의 대부분이 결국 루프 열로 환원된다는 점을 반영한 탐색용 상한 가정이며, 상세 기기 열수지 없이 과도한 100% 귀속을 피하기 위한 보수적 절충값 |

## 참고문헌

- **SRC-001** 2022 열시스템 디자인 학기말 프로젝트. `references/local/2022_assignment_lng_idc.pdf`
- **SRC-004** NIST REFPROP Overview. [REFPROP](https://www.nist.gov/srd/refprop), `references/web/nist_refprop.html`
- **SRC-005** CoolProp High-Level API. [High-Level API](https://coolprop.org/coolprop/HighLevelAPI.html), `references/web/coolprop_high_level_api.html`
- **SRC-006** TEMA 10th Edition. `references/local/TEMA-10th-Edition-2019.pdf`
- **SRC-007** Heat Exchanger Data Book. `references/local/heat_exchanger_data_book.pdf`
- **SRC-008** Refrigerants Environmental Data. `references/local/refrigerants_environmental_data.pdf`
- **SRC-009** KOGAS LNG Cold Energy Business. [KOGAS](https://www.kogas.or.kr/site/eng/1030703000000), `references/web/kogas_lng_cold_energy_business.html`
- **SRC-010** 2022 legacy heat exchanger design workbook. `references/local/legacy_heat_exchanger_design.xlsx`
- **SRC-011** ASHRAE Thermal Guidelines Reference Card. [ASHRAE Thermal Guidelines](https://www.ashrae.org/file%20library/technical%20resources/bookstore/supplemental%20files/therm-gdlns-5th-r-e-refcard.pdf), `references/web/ashrae_thermal_guidelines_refcard.pdf`
- **SRC-012** NIST Chemistry WebBook Methane Entry. [NIST Methane](https://webbook.nist.gov/cgi/cbook.cgi?Name=CH4), `references/web/nist_methane_webbook.html`
- **SRC-013** KEA EG-TIPS standard energy saving project information. [KEA EG-TIPS](https://tips.energy.or.kr/purpose/standard_info.do), `references/web/kea_standard_info.html`
- **SRC-014** GIR 2024 approved electricity emission factor announcement. [GIR electricity factor](https://www.gir.go.kr/home/board/read.do?boardId=82&boardMasterId=2&menuId=36&pagerOffset=30&maxPageItems=10&maxIndexPages=10&searchKey=&searchValue=)