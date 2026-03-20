# LNG 냉열 기반 IDC 냉각시스템 설계 연구

## 초록

본 보고서는 2022년 열시스템디자인 과제를 재현 가능한 Python 기반 설계 연구로 다시 구성한 결과다. LNG 냉열을 활용한 최종 설계는 **13,476.0 kW**의 IDC 냉방부하를 만족하면서, 기준 R-134a 압축기 동력 **4,185.4 kW**를 LNG 루프 펌프동력 **13.1 kW** 수준으로 대체한다. 선정된 냉각유체는 **R-717 (Ammonia)**이며, LNG 기화기 최소 핀치는 **10.0 K**로 유지했고, 예상 연간 전력 절감량은 **36,549.0 MWh/년**이다.

## 1. 문제 정의

본 프로젝트의 목적은 LNG 냉열을 이용해 데이터센터의 기존 기계식 냉방부하를 대체하되, 과제에서 제시한 실내 조건, 냉수 조건, 기화기 duty, 배관 이송거리 제약을 동시에 만족하는 설계를 도출하는 것이다.

이 연구가 답하려는 핵심 질문은 다음과 같다.

- 대상 IDC의 총 냉방부하는 얼마인가?
- 요구 조건에서 이론 최소동력은 어느 수준인가?
- 기존 R-134a 기준 시스템과 LNG 보조 시스템은 어떻게 비교되는가?
- LNG와 IDC 사이 2차 루프에 가장 적합한 냉각유체는 무엇인가?
- 이송거리가 10 km에서 35 km로 증가해도 시스템이 성립하는가?
- 연간 전력, 비용, 탄소 효과는 어느 정도인가?

## 2. 설계 기준

- 과제 기반 입력값은 [base.toml](../config/base.toml)에 기록했다.
- 전체 출처 레지스트리는 [sources.md](../docs/sources.md)에 정리했다.
- 공학적 가정은 [assumptions.md](../docs/assumptions.md)에 따로 남겼다.

핵심 입력값은 다음과 같다.

- IDC 총 냉방부하: **13,476.0 kW**
- LNG / NG 기화 duty: **14,973.3 kW**
- 기준 R-134a 압축기 동력: **4,185.4 kW**
- 선정 냉각유체: **R-717 (Ammonia)**

## 3. 모델링 방법

코드는 부하 계산, 이론 최소동력, 기준 증기압축 사이클, 냉각유체 스크리닝, LNG 기화기 설계, 장거리 배관 설계, 민감도 분석, 연간 효과 계산으로 나누어 구성했다.

주요 결과는 아래 그림들로 요약된다.

![부하 구성](../output/figures/load_breakdown.png)

![기준 사이클](../output/figures/baseline_cycle_ph.png)

![냉각유체 순위](../output/figures/fluid_ranking.png)

![열교환기 온도 프로파일](../output/figures/hx_temperature_profile.png)

![배관 트레이드오프](../output/figures/pipeline_tradeoff.png)

## 4. 주요 결과

| 항목 | 값 |
| --- | --- |
| 냉방부하 | 13,476.0 kW |
| 이론 최소동력 | 1,215.8 kW |
| 기준 R-134a 동력 | 4,185.4 kW |
| 선정 냉각유체 | R-717 (Ammonia) |
| LNG 루프 펌프동력 | 13.1 kW |
| 전력 절감 | 4,172.3 kW |

### 4.1 냉각유체 선정

| 유체 | 스크리닝 점수 | 펌프동력 (kW) | 쉘 직경 (m) | 연간 비용절감 (백만원/년) |
| --- | --- | --- | --- | --- |
| R-717 (Ammonia) | 0.720 | 13.1 | 0.723 | 3,839.5 |
| R-290 (Propane) | 0.147 | 124.9 | 0.758 | 3,736.6 |
| R-600a (Isobutane) | -0.027 | 134.5 | 0.758 | 3,727.8 |

기본 설계점에서 최적 유체는 **R-717 (Ammonia)**였으며, 이는 LNG 기화기와 장거리 배관 설계를 모두 만족하는 범위 안에서 루프 펌프동력을 최소화했다.

### 4.2 거리 민감도

| 거리 (km) | 펌프동력 (kW) | 열유입 (kW) | 열여유 (kW) | IDC 부하 충족 |
| --- | --- | --- | --- | --- |
| 5.0 | 6.4 | 253.0 | 1,244.3 | 예 |
| 10.0 | 12.8 | 506.0 | 991.3 | 예 |
| 15.0 | 19.2 | 759.1 | 738.3 | 예 |
| 20.0 | 25.6 | 1,012.1 | 485.3 | 예 |
| 25.0 | 32.1 | 1,265.1 | 232.2 | 예 |
| 30.0 | 38.5 | 1,518.1 | -20.8 | 아니오 |
| 35.0 | 44.9 | 1,771.1 | -273.8 | 아니오 |

![거리 민감도](../output/figures/pipeline_distance_sensitivity.png)

현재 duty 여유 기준에서 **35.0 km** 장거리 조건은 **불성립**이다. 선정 설계의 추정 최대 편도 성립거리는 약 **29.6 km**다.

### 4.3 공급온도 민감도

| 공급온도 (°C) | 선정 유체 | 펌프동력 (kW) | 최대 성립거리 (km) | 35 km 충족 | 상태 |
| --- | --- | --- | --- | --- | --- |
| -58.1 | - | - | - | 아니오 | 실패 |
| -53.1 | R-717 (Ammonia) | 13.1 | 29.6 | 아니오 | 성립 |
| -48.1 | R-717 (Ammonia) | 13.2 | 34.2 | 아니오 | 성립 |
| -43.1 | R-600a (Isobutane) | 130.4 | 40.6 | 예 | 성립 |

![공급온도 민감도](../output/figures/supply_temperature_sensitivity.png)

공급온도 스윕에서 펌프동력이 가장 낮은 지점은 **-53.1 °C**이며, 이때도 우선 유체는 **R-717 (Ammonia)**로 유지된다. 반면 **-43.1 °C** 수준으로 공급온도를 높이면 35 km 조건을 만족시킬 수 있지만, **R-600a**로 바뀌고 펌프동력 증가를 감수해야 한다.

### 4.4 연간 효과

| 항목 | 값 | 단위 |
| --- | --- | --- |
| 기준 시스템 전력사용 | 36,664.2 | MWh/년 |
| LNG 시스템 전력사용 | 115.2 | MWh/년 |
| 전력 절감 | 36,549.0 | MWh/년 |
| 전력요금 절감 | 3,839.5 | 백만원/년 |
| 회피 간접배출 | 16,757.7 | tCO2/년 |

![연간 효과](../output/figures/annual_impact_comparison.png)

단순 회수기간 기준 허용 가능한 추가 투자비는 다음과 같다.

| 회수기간 (년) | 허용 추가 투자비 (백만원) |
| --- | --- |
| 3 | 11,518.4 |
| 5 | 19,197.4 |
| 7 | 26,876.3 |
| 10 | 38,394.8 |

## 5. 기존 엑셀 결과와 비교

| 항목 | 기존 엑셀 (kW) | 현재 코드 (kW) | 차이 (kW) | 차이율 (%) |
| --- | --- | --- | --- | --- |
| 이론 최소동력 | 1,272.2 | 1,215.8 | -56.5 | -4.44 |
| 기준 압축기 동력 | 3,994.2 | 4,185.4 | 191.2 | 4.79 |

새 Python 워크플로우는 시스템 수준에서 기존 스프레드시트와 같은 규모의 결과를 재현하면서도, 가정과 출처, 시나리오 분석을 더 명확하게 드러낸다.

## 6. 논의

- 기본 10 km 설계는 기준 압축기 시스템 대비 큰 전력 절감과 함께 성립한다.
- 35 km 조건은 현재 기본 설계점에서 성립하지 않으며, 이것 자체가 중요한 설계 결론이다.
- 공급온도 수준을 조정하면 성립 거리를 늘릴 수 있지만, 다른 유체 선택과 더 큰 펌프동력 페널티를 수반한다.
- 연간 경제성은 현재 경계조건에서 매우 유리하지만, 보조기기, 유지보수, 금융비용, LNG 인프라 CAPEX는 아직 포함하지 않았다.

## 7. 한계

- v1에서는 LNG를 순수 메탄으로 가정했다.
- IDC 측 분배 네트워크는 전체 유압망이 아니라 냉방 duty 경계조건으로 단순화했다.
- 경제성 비교 범위는 기준 압축기 동력과 LNG 루프 펌프동력 비교에 한정된다.
- 응력, 재료 조달, 제어 통합 같은 상세 기계설계 검토는 현재 범위 밖이다.

## 8. 결론

재구축된 프로젝트는 LNG 냉열 기반 냉각 개념이 10 km 설계점에서 기준 데이터센터 냉각 시스템의 전력 요구를 크게 줄일 수 있음을 보여준다. 선정된 기본안은 2차 루프에 암모니아를 사용하고, 쉘-튜브 LNG 기화기와 0.35 m 공급/환수 배관을 적용한다. 현재 경계조건에서 이 설계는 에너지 측면과 경제성 측면 모두 매력적이며, 후속 보고서 정리와 발표자료 고도화까지 연결할 수 있을 만큼 투명하다.

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