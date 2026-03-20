# Source Registry

모든 외부 수치와 설계 기준은 아래 `SRC-ID`로 추적합니다. 접근일은 구현일 기준 `2026-03-20`입니다.

| ID | Title | Link or Local Path | Type | Used Values | Used In |
| --- | --- | --- | --- | --- | --- |
| SRC-001 | 2022 열시스템 디자인 학기말 프로젝트 | `references/local/2022_assignment_lng_idc.pdf` | Local assignment PDF | IDC 운전조건, 랙 부하, 냉수 조건, LNG 조건, 튜브 규격, 거리, 최소 온도차 | `config/base.toml`, load model, baseline cycle, HX, pipeline |
| SRC-003 | Properties of Refrigerants | `references/local/properties_of_refrigerants.pdf` | Local technical PDF | 냉매 후보군의 열역학/안전 참고 | coolant screening rationale |
| SRC-004 | NIST REFPROP Overview | [REFPROP](https://www.nist.gov/srd/refprop), `references/web/nist_refprop.html` | Official web | 물성 계산의 기준 참고 | documentation, report background |
| SRC-005 | CoolProp High-Level API | [High-Level API](https://coolprop.org/coolprop/HighLevelAPI.html), `references/web/coolprop_high_level_api.html` | Official web | 실제 코드 물성 엔진 | runtime property evaluation |
| SRC-006 | TEMA 10th Edition | `references/local/TEMA-10th-Edition-2019.pdf` | Local technical standard | 쉘-튜브 열교환기 nomenclature and sizing context | HX documentation |
| SRC-007 | Heat Exchanger Data Book | `references/local/heat_exchanger_data_book.pdf` | Local technical handbook | LMTD, Kern method, shell-side sizing context | HX correlations |
| SRC-008 | Refrigerants Environmental Data | `references/local/refrigerants_environmental_data.pdf` | Local technical PDF | GWP / ODP for candidate fluids | coolant screening metadata |
| SRC-009 | KOGAS LNG Cold Energy Business | [KOGAS](https://www.kogas.or.kr/site/eng/1030703000000), `references/web/kogas_lng_cold_energy_business.html` | Official web | LNG 냉열 사업과 전력 수요 완화 배경 | source appendix, project context |
| SRC-010 | 2022 legacy heat exchanger design workbook | `references/local/legacy_heat_exchanger_design.xlsx` | Local legacy workbook | 기존 팀의 Wmin, 기존 R-134a 압축기 동력 비교 기준 | legacy comparison output |
| SRC-011 | ASHRAE Thermal Guidelines Reference Card | [ASHRAE Thermal Guidelines](https://www.ashrae.org/file%20library/technical%20resources/bookstore/supplemental%20files/therm-gdlns-5th-r-e-refcard.pdf), `references/web/ashrae_thermal_guidelines_refcard.pdf` | Official PDF | 데이터센터 권장 운전 온도/환경 범위의 공식 배경 자료 | literature registry, future operating-envelope checks |
| SRC-012 | NIST Chemistry WebBook Methane Entry | [NIST Methane](https://webbook.nist.gov/cgi/cbook.cgi?Name=CH4), `references/web/nist_methane_webbook.html` | Official web | 메탄 물성/기초 식별 정보 보조 출처 | literature registry, methane documentation notes |
| SRC-013 | KEA EG-TIPS standard energy saving project information | [KEA EG-TIPS](https://tips.energy.or.kr/purpose/standard_info.do), `references/web/kea_standard_info.html` | Official web | 산업용 전력 단가 105.05원/kWh, 전력 배출계수 0.4585 tCO2/MWh | annual energy, cost, and carbon metrics |
| SRC-014 | GIR 2024 approved electricity emission factor announcement | [GIR electricity factor](https://www.gir.go.kr/home/board/read.do?boardId=82&boardMasterId=2&menuId=36&pagerOffset=30&maxPageItems=10&maxIndexPages=10&searchKey=&searchValue=) | Official web | 2024 승인 전력배출계수 공고의 공식 확인 경로 | source corroboration for carbon metrics |

## Notes

- HTML 페이지는 캐시 보관이 필수는 아니므로 URL과 접근일을 기록하고, 필요 시 `references/web/`에 스냅샷을 추가합니다.
- 로컬 제공 PDF는 원본의 작업용 사본을 `references/local/`에 둡니다.
