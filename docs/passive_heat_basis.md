# Passive Heat Basis

이 문서는 `passive_heat_search`에 들어간 숫자들이 `직접 출처에서 온 값인지`, `탐색용 가정인지`를 분리해 기록하는 메모다.

## Purpose

- 무보조 설계 탐색에서 어떤 값이 source-backed인지 명확히 한다.
- source-backed 값과 scenario-envelope 가정을 섞어 쓰더라도, 둘을 혼동하지 않게 한다.
- 향후 시간대별 기상 데이터나 지중온도 모델로 확장할 때 출발점을 남긴다.

## Source-Backed Items

| Item | Value Used | Basis | Source |
| --- | --- | --- | --- |
| Wind-driven outside convection correlation | `h = 5.7 + 3.8 V` | EnergyPlus engineering reference에 실린 외기 표면 대류 상관식 | `SRC-015` |
| Buried-pipe reference burial depth | `1.25 m` | EnergyPlus ground heat exchanger example input | `SRC-016` |
| Buried-pipe reference soil conductivity | `1.08 W/m-K` | EnergyPlus ground heat exchanger example input | `SRC-016` |
| Reference undisturbed ground temperature anchor | `15.5 C` (`288.65 K`) | EnergyPlus `Site:GroundTemperature:Undisturbed` example annual-average ground surface temperature | `SRC-018` |
| Weather-variable provenance | solar irradiance, dry-bulb temperature, wind speed available as time-series weather inputs | NSRDB 공식 데이터 체계 | `SRC-017` |

## Scenario-Envelope Assumptions

아래 값들은 직접 문헌에서 고정된 설계값으로 받아온 것이 아니라, `무보조 해가 존재하는지`를 보기 위한 탐색용 경계조건이다.

| Item | Current Values | Why It Is Still An Assumption | Assumption ID |
| --- | --- | --- | --- |
| Passive search supply-temperature grid | `200-230 K` | 기본 설계점보다 더 넓은 저온 운전 범위를 탐색하기 위한 그리드 | `ASM-037` |
| Passive search diameter grid | `0.075-0.35 m` | 배관 직경 자유도를 넓혀 무보조 해 존재 여부를 확인하기 위한 탐색 범위 | `ASM-038` |
| Passive search insulation grid | `0.00-0.15 m` | 단열 제거까지 포함한 공격적 탐색 범위 | `ASM-039` |
| Wind-speed cases | `0, 2, 4 m/s` | source-backed correlation 위에서 scenario boundary를 정한 값 | `ASM-040` |
| Net absorbed solar flux | `0, 250, 300 W/m2` | 실제 site/weather replay가 아니라 노출 배관의 순흡수 복사열 envelope를 주기 위한 값 | `ASM-041` |
| Pump heat returned to loop | `0.80` | 폐회로에서 펌프동력의 대부분이 결국 유체 열로 돌아온다는 점을 반영한 탐색용 절충값 | `ASM-042` |

## Interpretation Rule

1. `SRC` 기반 값은 모델식 또는 대표 입력의 기술적 근거로 본다.
2. `ASM` 기반 값은 설계 탐색용 envelope로 본다.
3. 따라서 `passive_heat_search` 결과는 `현실 설계 확정안`이 아니라 `이 정도 자유도를 주면 무보조 해가 존재하는가`를 묻는 시나리오 분석으로 읽어야 한다.

## Current Scenarios

| Scenario | What It Means |
| --- | --- |
| `baseline_air` | 기존 35 C 외기만으로 노출 배관이 자연 가열되는지 확인 |
| `summer_air_solar` | 35 C 외기 + 약한 바람 + 순흡수 일사 + 펌프발열 환원을 함께 넣은 exposed-pipe 시나리오 |
| `warm_buried_pipe` | EnergyPlus 예시 기반 buried-pipe 열환경과 펌프발열 환원을 넣은 지중 배관 시나리오 |
| `combined_passive` | 35 C 외기 + 비교적 강한 바람 + 더 큰 순흡수 일사 + 펌프발열 환원을 함께 넣은 공격적 exposed-pipe 시나리오 |

## Next Upgrade

다음 단계에서 source quality를 더 높이려면 아래 순서가 좋다.

1. 실제 후보 지역의 EPW 또는 NSRDB/KMA 시간대별 기상자료를 붙인다.
2. 지중온도는 Kusuda-Achenbach 식으로 계절 위상까지 반영한다.
3. `solar_absorbed_flux`는 `irradiance x absorptivity`로 분해해 재질별로 계산한다.
4. 펌프발열 환원은 펌프/모터/배관의 상세 에너지수지로 대체한다.
