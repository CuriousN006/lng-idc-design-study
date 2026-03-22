# Engineering Assumptions Registry

문헌에서 직접 주어지지 않은 공학적 기본값은 아래 `ASM-ID`로 추적합니다.

| ID | Assumption | Value | Why It Exists |
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
| ASM-032 | Economic comparison boundary | Baseline compressor power vs core LNG system electric demand (LNG external loop pump + IDC secondary-loop pump) | 기준 증기압축 시스템과 LNG 기반 대안의 핵심 전동부하를 같은 경계에서 비교하기 위한 기본 경제성 경계 |
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
| ASM-043 | Electric resistance auxiliary heater model | 1.00 kWe/kWth, fixed 0 kW | supplemental warm-up을 전기저항 가열로 직접 공급하는 최악 전력 페널티 기준선 |
| ASM-044 | Ambient-air trim heater model | 0.02 kWe/kWth, fixed 15 kW | 저급 외기열을 회수하고 팬/순환펌프 전력만 전기 페널티로 보는 느슨한 보조 가열 시나리오 |
| ASM-045 | Waste-heat recovery loop model | 0.01 kWe/kWth, fixed 10 kW | 인접 폐열원/온배수 루프에서 열을 받아오고 소규모 순환동력만 부담하는 회수형 시나리오 |
| ASM-046 | Heat-pump booster model | 0.25 kWe/kWth, fixed 20 kW | 보조 열원을 적극적으로 끌어올리는 소형 heat pump booster의 유효 전력비를 COP 4 수준으로 근사한 시나리오 |
| ASM-047 | Minimum practical insulation thickness in passive warm-up studies | 0.05 m | 무보조 성립 여부를 보더라도 산업 배관에 최소한의 단열은 남아 있어야 한다는 현실성 필터 |
| ASM-048 | Maximum practical passive-heat fraction of IDC load | 25% of modeled cooling load | 환경에서 과도하게 열을 주워오는 해를 배제하고, 수동 가열이 부하의 일부만 담당하는 범위를 실무형 필터로 두기 위한 기준 |
| ASM-049 | Uncertainty study sample plan | 48 pseudo-random samples, seed 42 | 회귀 가능한 불확실도 탐색을 위해 샘플 수와 난수 시드를 고정 |
| ASM-050 | Ambient-air temperature range in uncertainty study | 305.15-311.15 K | 여름 운전 외기 조건을 중심으로 ±3 K 범위를 주어 장거리 배관과 기준선 민감도를 확인 |
| ASM-051 | IDC-side HX overall-U multiplier range | 0.85-1.15 | 1차 U 추정치의 불확실성을 단순 승수 범위로 반영 |
| ASM-052 | Insulation conductivity multiplier range | 0.85-1.15 | 단열재 성능 편차와 시공 오차를 간략 반영 |
| ASM-053 | Outside convection multiplier range | 0.70-1.30 | 외부 대류계수 상관식과 현장 바람 조건 차이를 단순 승수 범위로 반영 |
| ASM-054 | IDC cooling utilization-fraction range | 0.87-0.93 | 90% 목표 이용률 주변에서 hot-end 제약이 얼마나 민감한지 보기 위한 운전 목표 범위 |
| ASM-055 | Mixed-LNG surrogate label and usage | Peak-shaving LNG surrogate with fixed composition | 한국 수입 LNG의 실제 월별 조성 대신 문헌에 공개된 대표 LNG 조성을 사용해 혼합 LNG 거동을 반영하기 위한 고정 surrogate |
| ASM-056 | Mixed-LNG normalization rule | AFDC peak-shaving composition is renormalized to sum to 1.0 before building the CoolProp mixture string | 공개 표의 반올림 오차를 제거하고 CoolProp 입력에 바로 쓰기 위한 정규화 절차 |
| ASM-057 | Cryogenic LNG vaporizer installation multiplier | 1.60 x generic shell-and-tube installed cost | NETL의 일반 탄소강 열교환기 비용표를 극저온 LNG 기화기 서비스에 맞춰 보수적으로 상향하는 계수 |
| ASM-058 | IDC-side HX installation multiplier | 1.10 x generic shell-and-tube installed cost | IDC측 액체-액체 열교환기는 일반 공정 열교환기와 유사한 설치 수준이지만 compact skid/controls를 반영해 소폭 상향 |
| ASM-059 | Cryogenic pipeline installation multiplier | 1.35 x urban steel distribution pipeline cost | 도심 배관 단가에 극저온 단열, 재킷, 시공 난이도를 반영하는 보수적 승수 |
| ASM-060 | Balance-of-plant fraction for CAPEX | 15% of direct CAPEX | 기초, 제어, 연결 배관, 계장, 시운전 등 직접 장비비 외 통합비를 1차 근사로 반영 |
| ASM-061 | IDC secondary-loop topology | 4 parallel chilled-water distribution circuits | 다층 IDC에서 하나의 거대 단일 루프보다 복수 회로 분배가 현실적이라는 점을 반영한 2차 루프 기본 구조 |
| ASM-062 | IDC secondary-loop equivalent horizontal length | 1.4 x (building length + width) per served floor | 각 층 헤더/분기관을 상세 배관망 없이 등가 길이로 환산하기 위한 1차 근사 |
| ASM-063 | IDC secondary-loop pipe grid and roughness | 0.20-0.45 m diameter, 4.5e-5 m roughness | 대형 chilled-water trunk에 대한 자동 직경 탐색 범위와 탄소강 roughness 기본값 |
| ASM-064 | IDC secondary-loop lumped pressure losses | minor K=18, HX 45 kPa, coil+valve 60 kPa, misc 20 kPa | 상세 단말기/밸브/헤더 모델 대신 분산 손실과 terminal loss를 총합 pressure-drop allowance로 반영 |
| ASM-065 | IDC secondary-loop hydraulic design limits | pump efficiency 75%, max water velocity 2.5 m/s, max total DP 250 kPa | chilled-water 순환계의 보수적 설계 상한을 두어 과도한 직경 축소를 방지 |
| ASM-066 | Project financial life | 20 years | 장거리 배관과 열교환기 중심의 인프라성 설비라는 점을 반영한 평가 기간 |
| ASM-067 | Discount rate for NPV/IRR | 8% | 민간 설비투자 관점의 보수적 nominal discount rate 근사 |
| ASM-068 | O&M and salvage for financial model | annual O&M 2% of CAPEX, salvage 0% | order-of-magnitude 수준의 경제성 평가에서 유지관리와 잔존가치를 단순화하기 위한 금융 가정 |
| ASM-069 | LNG tube-side transport-property proxy | Use pure methane for tube-side viscosity, conductivity, density, and heat capacity while keeping mixture enthalpy for duty partitioning | CoolProp의 극저온 혼합 LNG transport-property flash가 불안정한 구간을 피하면서 혼합 LNG의 엔탈피 기반 효과는 유지하기 위한 절충 |
| ASM-070 | Electric-resistance auxiliary CAPEX model | fixed 0.10 billion KRW + 70,000 KRW/kWth | supplemental warm-up을 전기 히터로 직접 공급하는 최악 시나리오의 간단 장치비 근사 |
| ASM-071 | Ambient-air trim-heater CAPEX model | fixed 0.40 billion KRW + 160,000 KRW/kWth | 외기 열교환기와 팬/보조 순환설비를 포함하는 저급열 회수형 보조 가열 장치비 근사 |
| ASM-072 | Waste-heat recovery CAPEX model | fixed 0.60 billion KRW + 220,000 KRW/kWth | 인접 폐열 루프 연결, 열교환기, 순환펌프를 포함하는 회수형 하이브리드 보조 열원 장치비 근사 |
| ASM-073 | Heat-pump booster CAPEX model | fixed 0.80 billion KRW + 650,000 KRW/kWth | 소형 heat-pump booster와 보조 열교환기/제어기를 포함하는 적극형 보조 열원 장치비 근사 |
| ASM-074 | Electric-resistance auxiliary O&M fraction | 1% of auxiliary CAPEX/year | 전기저항 가열기는 회전기기와 열교환기가 적어 유지관리 부담이 상대적으로 낮다는 가정 |
| ASM-075 | Ambient-air trim-heater O&M fraction | 2% of auxiliary CAPEX/year | 외기 열교환기, 팬, 순환계통의 정기 유지비를 간단 승수로 반영 |
| ASM-076 | Waste-heat recovery auxiliary O&M fraction | 2.5% of auxiliary CAPEX/year | 회수 루프와 추가 열교환기, 펌프 유지관리를 반영한 보수적 O&M 가정 |
| ASM-077 | Heat-pump booster O&M fraction | 3.5% of auxiliary CAPEX/year | 압축기 기반 booster의 상대적으로 높은 정비 부담을 단순 승수로 반영 |
| ASM-078 | LNG transport-proxy sensitivity set | Methane, Ethane, Propane, configured mixture | 혼합 LNG 엔탈피 모델은 유지하되 tube-side transport property proxy 선택이 기화기 면적과 압력강하에 미치는 영향을 bounded sensitivity로 확인하기 위한 비교 세트 |
| ASM-079 | IDC secondary-loop granularity sensitivity set | compact / baseline / conservative / redundant equivalent-network scenarios | 등가 배관망의 헤더 비중, 병렬 회로 수, 단말 손실을 바꿔 2차 루프 펌프동력의 모델 형태 민감도를 확인하기 위한 시나리오 세트 |
