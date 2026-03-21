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
