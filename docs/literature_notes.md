# Literature Notes

외부 자료는 아래 원칙으로 사용합니다.

- 설계 입력값의 1차 원천은 과제 PDF와 공식 기술자료입니다.
- 코드 런타임 물성은 `CoolProp`을 사용하되, 물성 출처 계보는 `NIST REFPROP`와 NIST 자료를 함께 기록합니다.
- 뉴스/홍보성 자료는 배경 설명에만 쓰고, 설계 수치는 공식/기술 문헌으로 다시 받습니다.

## Current External Source Roles

| Source ID | Role in Project | Notes |
| --- | --- | --- |
| SRC-004 | 물성 계보 문서화 | REFPROP 자체를 직접 호출하지는 않지만, 산업 표준 계보를 기록 |
| SRC-005 | 실제 런타임 물성 엔진 | 코드 구현에서 직접 사용하는 API 문서 |
| SRC-009 | LNG 냉열 활용 배경 | 데이터센터와 LNG 냉열 사업 맥락 설명용 |
| SRC-011 | 데이터센터 운전 환경 공식 배경 | 향후 운영 범위 적합성 점검에 사용할 수 있음 |
| SRC-012 | 메탄 공식 참조 보조 자료 | LNG를 순수 메탄으로 둔 v1 가정의 보조 문헌 |
| SRC-013 | 연간 경제성 입력값 | 산업용 전력 단가와 전력 배출계수의 코드 입력 출처 |
| SRC-014 | 전력 배출계수 공고 경로 | 탄소지표의 공공기관 확인 경로 |

## Next Literature Upgrades

- 배관 및 단열에 대해 KGS 또는 ASME 계열의 공개 기술 자료를 추가 확보
- 데이터센터 환경 조건에 대해 ASHRAE 권고 범위를 코드의 옵션 제약으로 반영
- LNG 조성 혼합물 확장 시 KOGAS 또는 peer-reviewed LNG composition source 추가
