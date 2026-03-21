# GitHub GPT-5.4 Pro 코드 리뷰 프롬프트

아래 프롬프트를 GitHub에 연결된 GPT-5.4 Pro 코드 리뷰어에게 그대로 전달하면 된다.

```text
Please do a deep code review of this repository:
https://github.com/CuriousN006/lng-idc-design-study

Context:
- This is a reproducible Python reconstruction of a 2022 undergraduate thermal-system design project: LNG cold-energy based data-center cooling.
- The current version now includes:
  1. mixed-LNG surrogate property modeling,
  2. an IDC secondary chilled-water loop hydraulic model,
  3. hybrid supplemental warm-up scenarios,
  4. CAPEX / NPV / IRR / discounted payback modeling,
  5. source-traceable config values and generated deliverables.
- Recent commits to pay special attention to:
  - ae1e21f Sync deliverables with mixed LNG and project economics
  - 6465eff Add mixed LNG, secondary-loop, and CAPEX modeling
  - c88e19c Add uncertainty study for key design assumptions

Current headline outputs from the repo:
- Selected coolant: R-717 (Ammonia)
- LNG stream model: Peak-shaving LNG surrogate
- IDC total cooling load: about 13,476 kW
- Baseline R-134a compressor power: about 4,185 kW
- LNG external loop pump power: about 22.2 kW
- IDC secondary-loop pump power: about 123.7 kW
- Core LNG system power: about 145.9 kW
- Supplemental warm-up duty: about 3,954 kW
- Core installed CAPEX: about 66.12 billion KRW
- Core-system NPV: about -42.61 billion KRW

How to review:
- Findings first, ordered by severity.
- Focus on bugs, numerical/modeling inconsistencies, thermodynamic mistakes, financial-model mistakes, stale assumptions, source-traceability gaps, and report/deck sync risks.
- Please cite concrete files and line numbers for each finding.
- After findings, add:
  1. open questions / assumptions,
  2. residual risks,
  3. a short summary of what looks solid.

Please review the code as an engineering model, not just as Python style.

Specific review targets:
1. Mixed LNG model
- Check whether the mixed-LNG handling is thermodynamically coherent.
- Verify whether using mixture enthalpy but methane transport-property proxy is acceptable, clearly documented, and consistently applied.
- Look for any hidden pure-methane assumptions that still remain in the LNG-side calculations, reports, or slides.

2. IDC secondary-loop model
- Check whether the equivalent hydraulic model is internally consistent.
- Look for unit mistakes, bad diameter selection logic, unrealistic pressure-drop allocations, or double-counting / undercounting pump power.
- Verify whether the system-level power comparison now consistently includes both the LNG external loop and the IDC secondary loop.

3. CAPEX / financial model
- Review the CAPEX methodology in terms of scaling logic, inflation/indexing, currency conversion, and whether the chosen source mappings are applied consistently.
- Check whether NPV / IRR / discounted payback are implemented correctly.
- Look for cases where negative NPV / undefined IRR could break downstream reporting or interpretation.

4. Energy and warm-up interpretation
- Check whether “supplemental warm-up” is treated consistently across pipeline, hybrid auxiliary heat, annual metrics, report outputs, and slides.
- Verify that the meanings of:
  - LNG loop pump power,
  - IDC secondary-loop pump power,
  - core LNG system power,
  - best-case hybrid total power
  are not mixed up anywhere.

5. Traceability and generated deliverables
- Check whether summary.csv, report_summary.md, report_draft.md, presentation_script.md, and presentation_draft.pptx are consistent with the latest model.
- Look for stale text in docs or deliverables that still reflects older assumptions such as “pure methane only” or “pump-only economic boundary”.
- Verify that newly added SRC/ASM IDs are documented and used appropriately.

6. Test coverage
- Review whether the current smoke tests are enough to protect the new mixed-LNG / secondary-loop / CAPEX logic.
- Suggest the highest-value missing tests, especially around edge cases and regression risks.

If you think the model has conceptual risks rather than outright bugs, call those out explicitly as “model risk” rather than “code bug”.
```

## 사용 팁

- 리뷰 결과를 받으면 `버그`, `모델 리스크`, `문서 불일치`로 다시 분류해서 후속 작업하기 좋다.
- 한 번 더 돌릴 때는 “이번엔 findings 5개만 남겨줘”처럼 범위를 줄이면 더 날카로운 피드백을 받기 쉽다.
