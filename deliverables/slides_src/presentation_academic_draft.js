"use strict";

const path = require("path");
const fs = require("fs");
const PptxGenJS = require("pptxgenjs");
const { imageSizingContain } = require("./pptxgenjs_helpers/image");
const {
  warnIfSlideHasOverlaps,
  warnIfSlideElementsOutOfBounds,
} = require("./pptxgenjs_helpers/layout");

const pptx = new PptxGenJS();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "OpenAI Codex";
pptx.company = "OpenAI";
pptx.subject = "LNG 냉열 기반 IDC 냉각시스템 장표";
pptx.title = "LNG 냉열 기반 IDC 냉각시스템 발표자료";
pptx.lang = "ko-KR";
pptx.theme = {
  headFontFace: "Malgun Gothic",
  bodyFontFace: "Malgun Gothic",
  lang: "ko-KR",
};

const colors = {
  teal: "2C6273",
  ink: "2C3842",
  gray: "6C7680",
  light: "EEF2F4",
  mid: "D6DEE3",
  white: "FFFFFF",
  gold: "C89B3C",
  green: "2F7D58",
  red: "A55349",
  blue: "4F88B8",
};

const figuresDir = path.resolve(__dirname, "..", "..", "output", "figures");
const outputDir = path.resolve(__dirname, "..", "..", "output");
const outputFile = path.resolve(__dirname, "..", "presentation_draft.pptx");

function requireFigure(fileName) {
  const filePath = path.join(figuresDir, fileName);
  if (!fs.existsSync(filePath)) {
    throw new Error(`Missing figure: ${filePath}`);
  }
  return filePath;
}

function parseCsvLine(line) {
  const values = [];
  let current = "";
  let inQuotes = false;
  for (let idx = 0; idx < line.length; idx += 1) {
    const ch = line[idx];
    if (ch === '"') {
      if (inQuotes && line[idx + 1] === '"') {
        current += '"';
        idx += 1;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (ch === "," && !inQuotes) {
      values.push(current);
      current = "";
    } else {
      current += ch;
    }
  }
  values.push(current);
  return values;
}

function readCsv(fileName) {
  const filePath = path.join(outputDir, fileName);
  const text = fs.readFileSync(filePath, "utf8").replace(/^\uFEFF/, "").trim();
  const lines = text.split(/\r?\n/);
  const headers = parseCsvLine(lines[0]);
  return lines.slice(1).map((line) => {
    const values = parseCsvLine(line);
    return Object.fromEntries(headers.map((header, idx) => [header, values[idx] ?? ""]));
  });
}

function toNumber(value) {
  return Number(value);
}

function toBool(value) {
  return String(value).toLowerCase() === "true";
}

function selectDistanceRow(rows, targetDistanceM) {
  if (!rows.length) {
    return null;
  }
  let bestRow = rows[0];
  let bestDelta = Math.abs(toNumber(bestRow.distance_m) - targetDistanceM);
  for (const row of rows.slice(1)) {
    const delta = Math.abs(toNumber(row.distance_m) - targetDistanceM);
    if (delta < bestDelta) {
      bestRow = row;
      bestDelta = delta;
    }
  }
  return bestRow;
}

function formatNumber(value, digits = 1) {
  return Number(value).toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

const summaryRows = readCsv("summary.csv");
const summary = Object.fromEntries(summaryRows.map((row) => [row.metric, row]));
const distanceRows = readCsv("distance_scenarios.csv");
const supplyRows = readCsv("supply_temperature_sweep.csv");
const annualRows = readCsv("annual_summary.csv");
const alternativeRows = readCsv("alternative_designs.csv");
const auxiliaryHeatRows = readCsv("auxiliary_heat_sources.csv");
const transportRows = readCsv("lng_transport_sensitivity.csv");
const idcGranularityRows = readCsv("idc_secondary_granularity.csv");
const passiveHeatRows = readCsv("passive_zero_warmup_search.csv");

const baseDistanceTargetM = Number(process.env.LNG_IDC_BASE_DISTANCE_M || "10000");
const longDistanceTargetM = Number(process.env.LNG_IDC_LONG_DISTANCE_M || "35000");
const baseDistance = selectDistanceRow(distanceRows, baseDistanceTargetM) || distanceRows[0];
const baseDistanceBaseDutyMeetsLoad = toBool(baseDistance.base_duty_meets_idc_load);
const baseDistanceHybridSatisfied = toBool(baseDistance.hybrid_operation_feasible || baseDistance.hybrid_load_satisfied);
const baseDistanceRequiresSupplementalWarmup = toBool(baseDistance.requires_supplemental_warmup);
const longDistance = selectDistanceRow(distanceRows, longDistanceTargetM) || distanceRows[distanceRows.length - 1];
const longDistanceKm = toNumber(longDistance.distance_km);
const longDistanceBaseDutyMeetsLoad = toBool(longDistance.base_duty_meets_idc_load);
const longDistanceHybridSatisfied = toBool(longDistance.hybrid_operation_feasible || longDistance.hybrid_load_satisfied);
const longDistanceRequiresSupplementalWarmup = toBool(longDistance.requires_supplemental_warmup);
const maxFeasibleDistanceKm = toNumber(longDistance.max_feasible_distance_m) / 1000.0;
const maxBaseDutyDistanceKm = toNumber(longDistance.max_base_duty_distance_m) / 1000.0;
const feasibleSupplyRows = supplyRows
  .filter((row) => row.status === "feasible")
  .sort((left, right) => toNumber(left.pump_power_kw) - toNumber(right.pump_power_kw));
const bestSupplyRow = feasibleSupplyRows[0] || null;
const supplyFallbackRow = supplyRows[0] || { supply_temp_k: "220", selected_fluid: "No feasible point", pump_power_kw: "NaN" };
const displayBestSupplyRow = bestSupplyRow || supplyFallbackRow;
const recover35Row = supplyRows
  .filter((row) => row.status === "feasible" && toBool(row.long_distance_base_duty_meets_load))
  .sort((left, right) => toNumber(left.pump_power_kw) - toNumber(right.pump_power_kw))[0] || bestSupplyRow || supplyFallbackRow;
const annualMap = Object.fromEntries(annualRows.map((row) => [row.metric, row]));
const rankedAlternatives = alternativeRows
  .slice()
  .sort((left, right) => {
    const leftFeasible = toBool(left.design_feasible);
    const rightFeasible = toBool(right.design_feasible);
    if (leftFeasible !== rightFeasible) {
      return leftFeasible ? -1 : 1;
    }
    const pumpDiff = toNumber(left.pump_power_kw) - toNumber(right.pump_power_kw);
    if (Math.abs(pumpDiff) > 1e-9) {
      return pumpDiff;
    }
    return toNumber(right.screening_score) - toNumber(left.screening_score);
  });
const feasibleAlternatives = rankedAlternatives.filter((row) => toBool(row.design_feasible));
const selectedAlternative = feasibleAlternatives[0] || rankedAlternatives[0];
const topAlternatives = [
  feasibleAlternatives[0] || selectedAlternative,
  feasibleAlternatives[1] || selectedAlternative,
  feasibleAlternatives[2] || selectedAlternative,
];
const bestAuxiliary = auxiliaryHeatRows
  .slice()
  .sort((left, right) => toNumber(right.net_power_saving_kw) - toNumber(left.net_power_saving_kw))[0];
const bestFinancialAuxiliary = auxiliaryHeatRows
  .slice()
  .sort((left, right) => toNumber(right.npv_krw) - toNumber(left.npv_krw))[0];
const feasibleTransportRows = transportRows.filter((row) => row.status === "feasible");
const transportReference = feasibleTransportRows.find((row) => toBool(row.is_reference)) || feasibleTransportRows[0];
const transportAreaMinDeltaPct = feasibleTransportRows.length
  ? Math.min(...feasibleTransportRows.map((row) => toNumber(row.required_area_m2_delta_pct)))
  : NaN;
const transportAreaMaxDeltaPct = feasibleTransportRows.length
  ? Math.max(...feasibleTransportRows.map((row) => toNumber(row.required_area_m2_delta_pct)))
  : NaN;
const conservativeNetwork = idcGranularityRows
  .slice()
  .sort((left, right) => toNumber(right.pump_power_kw) - toNumber(left.pump_power_kw))[0];
const practicalPassiveRows = passiveHeatRows.filter((row) => toBool(row.practical_zero_warmup_design_found));

function addBackground(slide) {
  slide.background = { color: colors.white };
}

function addPageNumber(slide, page) {
  slide.addText(String(page), {
    x: 0.18,
    y: 7.02,
    w: 0.6,
    h: 0.18,
    fontFace: "Malgun Gothic",
    fontSize: 10,
    color: colors.gray,
    align: "left",
  });
}

function addSectionHeader(slide, part, title, page) {
  addBackground(slide);
  const partLabel = part === "" ? "" : `Part ${part}`;
  slide.addShape(pptx.ShapeType.rect, {
    x: 0.18,
    y: 0.17,
    w: 1.55,
    h: 0.08,
    fill: { color: colors.teal },
    line: { color: colors.teal, transparency: 100 },
  });
  slide.addShape(pptx.ShapeType.line, {
    x: 0,
    y: 0.21,
    w: 13.333,
    h: 0,
    line: { color: colors.teal, pt: 1 },
  });
  slide.addText(partLabel, {
    x: 0.75,
    y: 0.47,
    w: 1.0,
    h: 0.3,
    fontFace: "Malgun Gothic",
    fontSize: 15,
    color: colors.ink,
  });
  slide.addText(title, {
    x: 1.95,
    y: 0.43,
    w: 9.4,
    h: 0.34,
    fontFace: "Malgun Gothic",
    fontSize: 22,
    color: colors.ink,
  });
  addPageNumber(slide, page);
}

function addCoverBracket(slide, x, y, side = "left") {
  const lineColor = { color: colors.teal, pt: 8 };
  const arm = 0.38;
  const height = 3.08;
  if (side === "left") {
    slide.addShape(pptx.ShapeType.line, { x, y, w: 0, h: height, line: lineColor });
    slide.addShape(pptx.ShapeType.line, { x, y, w: arm, h: 0, line: lineColor });
    slide.addShape(pptx.ShapeType.line, { x, y: y + height, w: arm, h: 0, line: lineColor });
  } else {
    slide.addShape(pptx.ShapeType.line, { x, y, w: 0, h: height, line: lineColor });
    slide.addShape(pptx.ShapeType.line, { x: x - arm, y, w: arm, h: 0, line: lineColor });
    slide.addShape(pptx.ShapeType.line, { x: x - arm, y: y + height, w: arm, h: 0, line: lineColor });
  }
}

function addBullets(slide, x, y, w, bullets, fontSize = 18, color = colors.ink) {
  slide.addText(
    bullets.map((bullet) => ({ text: bullet, options: { bullet: { indent: 14 } } })),
    {
      x,
      y,
      w,
      h: 0.42 * bullets.length + 0.3,
      fontFace: "Malgun Gothic",
      fontSize,
      color,
      breakLine: false,
      paraSpaceAfterPt: 7,
      margin: 0,
      valign: "top",
    }
  );
}

function addFigure(slide, imagePath, x, y, w, h, caption) {
  slide.addImage({
    path: imagePath,
    ...imageSizingContain(imagePath, x, y, w, h),
  });
  if (caption) {
    slide.addText(caption, {
      x,
      y: y + h + 0.05,
      w,
      h: 0.18,
      fontFace: "Malgun Gothic",
      fontSize: 10,
      color: colors.teal,
      bold: true,
      align: "left",
    });
  }
}

function addSoftBox(slide, x, y, w, h, title, lines) {
  slide.addShape(pptx.ShapeType.rect, {
    x,
    y,
    w,
    h,
    fill: { color: colors.light },
    line: { color: colors.mid, pt: 0.8 },
  });
  if (title) {
    slide.addText(title, {
      x: x + 0.16,
      y: y + 0.12,
      w: w - 0.32,
      h: 0.22,
      fontFace: "Malgun Gothic",
      fontSize: 13,
      bold: true,
      color: colors.teal,
    });
  }
  slide.addText(lines.join("\n"), {
    x: x + 0.16,
    y: y + (title ? 0.45 : 0.18),
    w: w - 0.32,
    h: h - (title ? 0.54 : 0.26),
    fontFace: "Malgun Gothic",
    fontSize: 14,
    color: colors.ink,
    valign: "top",
    margin: 0,
    breakLine: false,
  });
}

function addMetricBox(slide, x, y, w, h, label, value, caption, accent = colors.teal) {
  slide.addShape(pptx.ShapeType.rect, {
    x,
    y,
    w,
    h,
    fill: { color: colors.white },
    line: { color: accent, pt: 1.2 },
  });
  slide.addText(label, {
    x: x + 0.14,
    y: y + 0.1,
    w: w - 0.28,
    h: 0.18,
    fontFace: "Malgun Gothic",
    fontSize: 10.5,
    color: colors.gray,
    bold: true,
  });
  slide.addText(value, {
    x: x + 0.14,
    y: y + 0.34,
    w: w - 0.28,
    h: 0.28,
    fontFace: "Malgun Gothic",
    fontSize: 20,
    color: colors.ink,
    bold: true,
  });
  if (caption) {
    slide.addText(caption, {
      x: x + 0.14,
      y: y + h - 0.22,
      w: w - 0.28,
      h: 0.16,
      fontFace: "Malgun Gothic",
      fontSize: 9.5,
      color: colors.gray,
    });
  }
}

function addFooterNote(slide, text) {
  slide.addText(text, {
    x: 9.0,
    y: 7.0,
    w: 4.05,
    h: 0.16,
    fontFace: "Malgun Gothic",
    fontSize: 8.5,
    color: colors.gray,
    align: "right",
  });
}

function finalizeSlide(slide) {
  warnIfSlideHasOverlaps(slide, pptx);
  warnIfSlideElementsOutOfBounds(slide, pptx);
}

function buildDeck() {
  let page = 1;

  // 1. Cover
  {
    const slide = pptx.addSlide();
    addBackground(slide);
    addCoverBracket(slide, 2.12, 1.44, "left");
    addCoverBracket(slide, 11.62, 1.44, "right");
    slide.addText("열시스템 디자인 프로젝트 재구성", {
      x: 4.15,
      y: 1.25,
      w: 5.2,
      h: 0.3,
      fontFace: "Malgun Gothic",
      fontSize: 18,
      color: colors.teal,
      bold: true,
      align: "center",
    });
    slide.addText("LNG 냉열을 활용한\n데이터센터 냉각시스템 및\n주요 부품의 설계", {
      x: 2.8,
      y: 2.0,
      w: 7.8,
      h: 2.1,
      fontFace: "Malgun Gothic",
      fontSize: 31,
      color: colors.ink,
      bold: true,
      align: "center",
      breakLine: false,
    });
    slide.addText("코드 기반 재구성본", {
      x: 10.6,
      y: 5.68,
      w: 1.6,
      h: 0.3,
      fontFace: "Malgun Gothic",
      fontSize: 16,
      color: colors.ink,
      bold: true,
      align: "left",
    });
    slide.addShape(pptx.ShapeType.line, {
      x: 10.52,
      y: 6.12,
      w: 1.95,
      h: 0,
      line: { color: colors.gray, pt: 1 },
    });
    slide.addText("lng-idc-design-study\n재현 가능한 계산, 보고서, 발표자료", {
      x: 10.62,
      y: 6.25,
      w: 2.2,
      h: 0.62,
      fontFace: "Malgun Gothic",
      fontSize: 10.5,
      color: colors.gray,
      breakLine: false,
    });
    addPageNumber(slide, page++);
    finalizeSlide(slide);
  }

  // 2. Agenda
  {
    const slide = pptx.addSlide();
    addSectionHeader(slide, "", "목차", page++);
    addSoftBox(slide, 0.75, 1.35, 5.75, 4.9, "발표 구성", [
      "Part 1. 예비설계",
      "  - 설계 대상과 냉방부하",
      "  - 이론 최소동력",
      "  - 기준 R-134a 사이클",
      "",
      "Part 2. 냉각유체 선정",
      "  - 선정 기준",
      "  - 후보 비교와 기본안 결정",
      "",
      "Part 3. LNG 기화기 설계",
      "  - 구간 분할 해석과 핀치",
      "  - 형상 스캔과 최종 제원",
    ]);
    addSoftBox(slide, 6.95, 1.35, 5.55, 4.9, "이후 구성", [
      "Part 4. 순환 배관 설계",
      "  - 설계 조건",
      "  - 거리 민감도",
      "  - 공급온도 민감도",
      "",
      "Part 5. 열역학/경제성 평가",
      "  - 소비동력 비교",
      "  - 연간 효과와 회수기간",
      "",
      "Part 6. 추가 고려 사항",
      "  - 확장 과제와 출처 체계",
      "",
      "최종 결론",
    ]);
    addFooterNote(slide, "A11의 파트 중심 공학 발표 흐름을 따라 재편성");
    finalizeSlide(slide);
  }

  // 3. Load basis
  {
    const slide = pptx.addSlide();
    addSectionHeader(slide, 1, "예비설계 - 설계 대상과 냉방부하", page++);
    addFigure(slide, requireFigure("load_breakdown.png"), 0.65, 1.45, 6.1, 4.45, "냉방부하 구성 결과");
    addBullets(slide, 7.6, 1.55, 4.85, [
      "대상 건물은 100 m × 40 m × 36 m 규모 IDC로 가정하였다.",
      "랙 발열 11 MW를 기본으로 외피, 조명, 전력손실, 보조설비를 포함했다.",
      "총 냉방부하는 13.48 MW로 계산되었다.",
      "이 값이 이후 기화기와 배관 설계의 기준 duty가 된다.",
    ], 16.5);
    addMetricBox(slide, 7.7, 4.8, 2.05, 0.95, "총 냉방부하", "13.48 MW", "모델 결과", colors.teal);
    addMetricBox(slide, 9.95, 4.8, 2.05, 0.95, "랙 발열", "11.00 MW", "설계 기준", colors.gold);
    addMetricBox(slide, 12.2, 4.8, 0.9, 0.95, "층수", "11", "IDC", colors.blue);
    addFooterNote(slide, "과제 조건과 코드 기반 부하모델을 통합해 재현");
    finalizeSlide(slide);
  }

  // 4. Theoretical minimum
  {
    const slide = pptx.addSlide();
    addSectionHeader(slide, 1, "예비설계 - 이론 최소동력", page++);
    addSoftBox(slide, 0.72, 1.55, 4.45, 2.05, "가정 조건", [
      "외기 조건: 35 °C",
      "냉방부하: 13.48 MW",
      "실내/냉수 경계조건은 과제 기준을 유지",
      "카르노 한계를 이용해 이론 최소동력을 계산",
    ]);
    addSoftBox(slide, 0.72, 4.02, 4.45, 1.6, "핵심 식", [
      "W_min = Q_L · (T_H / T_L - 1)",
      "절대값 자체보다 기준 사이클과의 간격이 중요",
    ]);
    addMetricBox(slide, 5.65, 1.9, 2.7, 1.2, "이론 최소동력", "1.22 MW", "카르노 하한", colors.gold);
    addBullets(slide, 5.65, 3.45, 6.0, [
      "이 값은 실제 설계가 절대적으로 넘을 수 없는 하한선이다.",
      "이후의 R-134a 기준 시스템과 LNG 냉열 시스템은 모두 이 값보다 큰 동력을 사용한다.",
      "따라서 비교의 초점은 절대 효율보다 얼마나 이 하한에 가까운가에 있다.",
    ], 16.5);
    addFooterNote(slide, "기준 시스템과 LNG 시스템 비교의 출발점");
    finalizeSlide(slide);
  }

  // 5. Baseline cycle
  {
    const slide = pptx.addSlide();
    addSectionHeader(slide, 1, "예비설계 - 기준 R-134a 증기압축 사이클", page++);
    addFigure(slide, requireFigure("baseline_cycle_ph.png"), 0.72, 1.45, 6.0, 4.75, "R-134a 기준 사이클 P-h 선도");
    addBullets(slide, 7.55, 1.55, 4.95, [
      "기준 시스템은 단순 R-134a 증기압축 냉동 사이클로 모델링하였다.",
      "코드 기준 압축기 소비동력은 4.19 MW다.",
      "기존 엑셀 결과 3.99 MW와 크기 수준이 일관되어 기준선으로 활용 가능하다.",
      "이 기준선이 LNG 냉열 개념의 전력 절감 효과를 판단하는 앵커가 된다.",
    ], 16);
    addMetricBox(slide, 7.7, 4.95, 2.45, 1.02, "기준 압축기", "4.19 MW", "현재 코드", colors.red);
    addMetricBox(slide, 10.35, 4.95, 2.1, 1.02, "기존 엑셀", "3.99 MW", "과거 결과", colors.teal);
    addFooterNote(slide, "기준 시스템은 단순하되 비교 기준으로 충분히 강함");
    finalizeSlide(slide);
  }

  // 6. Screening criteria
  {
    const slide = pptx.addSlide();
    addSectionHeader(slide, 2, "냉각유체 선정 - 선정 기준", page++);
    addSoftBox(slide, 0.75, 1.45, 5.9, 4.9, "후보군과 필터", [
      "후보 유체: R-170, R-717, R-744, R-1270, R-290, R-600a, R-1150",
      "",
      "1) 환경성: ODP/GWP와 규제 적합성",
      "2) 온도창: 120~270 K 영역에서 사용 가능성",
      "3) 압력 제약: 루프 압력 1 MPa 이하 유지 가능성",
      "4) 설계성: 기화기 성립 여부와 장거리 운반 적합성",
      "5) 후속성: 연간 절감 효과와 구현 리스크",
    ]);
    addSoftBox(slide, 7.05, 1.45, 5.45, 4.9, "이번 재구축에서 달라진 점", [
      "A11은 표와 근거로 후보를 줄여나갔고, 이번 코드는 그 과정을 재현 가능하게 만들었다.",
      "탈락 유체도 사유와 함께 남기기 때문에 선정 논리가 더 명확하다.",
      "최종 선택은 단순 감이 아니라 전체 설계 문제의 결과로 이해할 수 있다.",
    ]);
    addFooterNote(slide, "친환경성, 물성, 압력, 설계성, 경제성을 동시에 고려");
    finalizeSlide(slide);
  }

  // 7. Ranking result
  {
    const slide = pptx.addSlide();
    addSectionHeader(slide, 2, "냉각유체 선정 - 후보 비교 결과", page++);
    addFigure(slide, requireFigure("fluid_ranking.png"), 0.72, 1.45, 6.2, 4.75, "스크리닝 점수와 요구 질량유량");
    addBullets(slide, 7.55, 1.6, 4.9, [
      "최종 순위는 R-717, R-290, R-600a 순으로 정리된다.",
      "암모니아는 실현 가능한 후보 중 펌프동력이 가장 낮다.",
      "프로판과 이소부탄도 후보로 남지만, 펌프동력과 전체 설계성에서 밀린다.",
      "또한 현재 기준점에서는 상위 3개 유체 모두 LNG hot-end 조건 때문에 추가 warm-up 요구량이 남는다.",
    ], 16.5);
    addMetricBox(slide, 7.75, 4.9, 1.45, 0.98, "1위", topAlternatives[0].fluid, `${formatNumber(toNumber(topAlternatives[0].pump_power_kw), 1)} kW`, colors.teal);
    addMetricBox(slide, 9.45, 4.9, 1.45, 0.98, "2위", topAlternatives[1].fluid, `${formatNumber(toNumber(topAlternatives[1].pump_power_kw), 1)} kW`, colors.gold);
    addMetricBox(slide, 11.15, 4.9, 1.45, 0.98, "3위", topAlternatives[2].fluid, `${formatNumber(toNumber(topAlternatives[2].pump_power_kw), 1)} kW`, colors.red);
    addFooterNote(slide, "후보 비교는 펌프동력, 열교환기 규모, 연간 절감까지 포함");
    finalizeSlide(slide);
  }

  // 8. Selected fluid
  {
    const slide = pptx.addSlide();
    addSectionHeader(slide, 2, "냉각유체 선정 - 기본안 결정", page++);
    addMetricBox(slide, 0.95, 1.55, 2.35, 1.15, "선정 유체", summary["Selected coolant"].value, "기본안", colors.teal);
    addMetricBox(slide, 3.55, 1.55, 2.35, 1.15, "기본 공급온도", `${formatNumber(bestSupplyRow ? toNumber(bestSupplyRow.supply_temp_k) : 220.0, 0)} K`, bestSupplyRow ? "스윕 최적점" : "feasible point 없음", colors.gold);
    addMetricBox(slide, 6.15, 1.55, 2.35, 1.15, "Core system power", `${formatNumber(toNumber(summary["Core LNG system power"].value), 1)} kW`, "현재 결과", colors.green);
    addSoftBox(slide, 0.95, 3.05, 5.55, 2.65, "암모니아가 기본안인 이유", [
      "실현 가능한 후보 중 루프 동력이 가장 작다.",
      "기화기 쉘 직경이 비교적 작아 장치 규모가 과도하게 커지지 않는다.",
      "장거리 운반 문제까지 포함한 전체 설계 관점에서 가장 안정적인 해를 준다.",
    ]);
    addSoftBox(slide, 6.8, 3.05, 5.55, 2.65, "동시에 남겨둘 리스크", [
      "안전성과 취급성은 탄화수소와 다른 별도 검토가 필요하다.",
      `현재 기준점에서는 LNG hot-end를 맞추기 위해 ${formatNumber(toNumber(summary["Supplemental warm-up duty"].value), 1)} kW의 추가 warm-up 모델이 필요하다.`,
      "따라서 최종 설계에서는 성능 우위와 안전/운전 서술을 함께 가져가야 한다.",
      "즉 성능은 암모니아가, 시스템 단순성은 추가 검토가 더 필요하다.",
    ]);
    addFooterNote(slide, "기본안은 성능 기준, 대안 유체는 확장 시나리오 기준");
    finalizeSlide(slide);
  }

  // 9. HX thermodynamic analysis
  {
    const slide = pptx.addSlide();
    addSectionHeader(slide, 3, "LNG 기화기 설계 - 열역학 해석과 핀치", page++);
    addFigure(slide, requireFigure("hx_temperature_profile.png"), 0.72, 1.45, 6.0, 4.65, "구간 분할 온도 프로파일");
    addBullets(slide, 7.55, 1.55, 4.9, [
      "7 MPa 혼합 LNG surrogate의 유효 엔탈피 변화는 온도에 따라 크게 달라진다.",
      "따라서 단일 평균 비열이 아니라 구간 분할 엔탈피 기반 해석이 필요하다.",
      "이번 모델은 112~190 K, 190~205 K, 205~220 K, 220~283 K의 4구간으로 나누어 계산한다.",
      "전 구간에서 최소 핀치 10 K를 만족하도록 설계한다.",
    ], 15.5);
    addMetricBox(slide, 7.75, 5.0, 1.65, 0.96, "기화 duty", `${formatNumber(toNumber(summary["LNG vaporizer duty"].value), 1)} kW`, "LNG/NG 기준", colors.teal);
    addMetricBox(slide, 9.65, 5.0, 1.45, 0.96, "구간 수", "4", "엔탈피 해석", colors.gold);
    addMetricBox(slide, 11.35, 5.0, 1.15, 0.96, "핀치", "10 K", "최소조건", colors.red);
    addFooterNote(slide, "A11의 핀치 문제 제기를 코드 기반 구간 해석으로 재현");
    finalizeSlide(slide);
  }

  // 10. HX geometry scan
  {
    const slide = pptx.addSlide();
    addSectionHeader(slide, 3, "LNG 기화기 설계 - 형상 스캔과 최종 제원", page++);
    addFigure(slide, requireFigure("hx_geometry_scan.png"), 0.72, 1.45, 6.0, 4.65, "관 개수/형상 변화에 따른 설계 스캔");
    addSoftBox(slide, 7.5, 1.55, 5.0, 2.1, "형상 스캔에서 얻은 판단", [
      "관 수를 늘리면 길이가 줄어들지만, 일정 지점 이후 효과가 둔화된다.",
      "따라서 최소 길이만이 아니라 전체 장치 현실성으로 선택해야 한다.",
    ]);
    addMetricBox(slide, 7.6, 4.1, 1.55, 1.02, "튜브 수", `${Math.round(toNumber(selectedAlternative.hx_tube_count))}`, "현재 결과", colors.teal);
    addMetricBox(slide, 9.4, 4.1, 1.75, 1.02, "튜브 길이", `${formatNumber(toNumber(selectedAlternative.hx_tube_length_m), 1)} m`, "현재 결과", colors.gold);
    addMetricBox(slide, 11.4, 4.1, 1.1, 1.02, "쉘", `${formatNumber(toNumber(selectedAlternative.hx_shell_diameter_m), 3)} m`, "직경", colors.red);
    addSoftBox(slide, 7.5, 5.3, 5.0, 0.85, "최종 설계 요약", [
      "향류 1-pass 쉘-튜브 구조, LNG는 tube side, 2차 루프는 shell side로 두었다.",
    ]);
    addFooterNote(slide, "기화기 설계는 성능과 현실성의 절충 문제");
    finalizeSlide(slide);
  }

  // 11. HX design summary
  {
    const slide = pptx.addSlide();
    addSectionHeader(slide, 3, "LNG 기화기 설계 - 최종 설계 판단", page++);
    addSoftBox(slide, 0.85, 1.55, 3.75, 2.1, "열역학적으로", [
      "기화기 최소 핀치 10 K를 만족한다.",
      "구간 분할 모델이라 극저온 영역의 물성 변화를 더 잘 반영한다.",
    ]);
    addSoftBox(slide, 4.8, 1.55, 3.75, 2.1, "기계적으로", [
      "관 수와 길이의 조합이 과도한 장치 길이 증가를 피한다.",
      "쉘 직경도 실무적으로 과도하게 커지지 않는다.",
    ]);
    addSoftBox(slide, 8.75, 1.55, 3.75, 2.1, "발표 포인트", [
      "이번 기화기 설계는 단순 계산이 아니라 현실성 필터를 거친 결과다.",
      "A11의 공정한 단계 설명을 현재 코드로 다시 세운 슬라이드다.",
    ]);
    addFigure(slide, requireFigure("hx_temperature_profile.png"), 1.05, 4.1, 4.6, 2.0, "");
    addFigure(slide, requireFigure("hx_geometry_scan.png"), 7.0, 4.1, 4.6, 2.0, "");
    addFooterNote(slide, "열역학 해석과 형상 스캔을 함께 보여주는 요약 페이지");
    finalizeSlide(slide);
  }

  // 12. Pipeline conditions
  {
    const slide = pptx.addSlide();
    addSectionHeader(slide, 4, "순환 배관 설계 - 설계 조건", page++);
    addFigure(slide, requireFigure("pipeline_tradeoff.png"), 0.72, 1.55, 5.9, 4.55, "배관 직경에 따른 압력강하와 열유입");
    addBullets(slide, 7.45, 1.55, 5.0, [
      `기본 설계 거리는 10 km, 도전 조건은 ${formatNumber(longDistanceKm, 0)} km로 둔다.`,
      "배관은 압력강하와 열유입을 동시에 만족해야 한다.",
      "직경이 커지면 압력강하는 줄지만 재료량과 시공 부담이 증가한다.",
      "따라서 배관 설계는 기화기 설계와 별개의 최적화 문제가 된다.",
    ], 16);
    addMetricBox(slide, 7.7, 5.0, 1.7, 0.95, "기본 거리", "10 km", "설계점", colors.teal);
    addMetricBox(slide, 9.7, 5.0, 1.7, 0.95, "도전 거리", `${formatNumber(longDistanceKm, 0)} km`, "확장 조건", colors.gold);
    addMetricBox(slide, 11.7, 5.0, 0.9, 0.95, "루프", "왕복", "배관", colors.red);
    addFooterNote(slide, "배관 문제는 압력강하와 열유입을 동시에 관리해야 함");
    finalizeSlide(slide);
  }

  // 13. Distance sensitivity
  {
    const slide = pptx.addSlide();
    addSectionHeader(slide, 4, "순환 배관 설계 - 거리 민감도", page++);
    addFigure(slide, requireFigure("pipeline_distance_sensitivity.png"), 0.72, 1.45, 6.1, 4.75, "거리 증가에 따른 펌프동력과 열여유 변화");
    addBullets(slide, 7.55, 1.55, 4.9, [
      `기본 ${formatNumber(toNumber(baseDistance.distance_km), 0)} km 조건은 ${baseDistanceBaseDutyMeetsLoad ? "기본 LNG duty까지 성립한다." : baseDistanceHybridSatisfied ? "하이브리드 운전으로는 성립하지만 supplemental warm-up이 필요하다." : "하이브리드까지 포함해도 불성립이다."}`,
      `거리 증가와 함께 열유입이 누적되며, ${formatNumber(longDistanceKm, 0)} km에서는 ${longDistanceHybridSatisfied ? "유압/상태 해는 유지된다." : "유압 또는 상태 제약에서 막힌다."}`,
      `다만 현재 모델은 부족한 hot-end 환수온도를 supplemental warm-up으로 메우는 부분까지 같이 계산한다.`,
      `현재 코드 기준 최대 하이브리드 편도 성립거리는 약 ${formatNumber(maxFeasibleDistanceKm, 1)} km이고, 기본 LNG duty 기준 최대 성립거리는 약 ${formatNumber(maxBaseDutyDistanceKm, 1)} km다.`,
      `즉 ${formatNumber(longDistanceKm, 0)} km 조건은 ${longDistanceBaseDutyMeetsLoad ? "기본 LNG duty까지 성립한다." : longDistanceHybridSatisfied ? "하이브리드 운전은 가능하지만 기본 LNG duty는 불성립이다." : "하이브리드 운전까지 포함해 불성립이다."}`,
    ], 15.8);
    addMetricBox(slide, 7.7, 5.0, 1.55, 0.95, "10 km", baseDistanceBaseDutyMeetsLoad ? "기본 성립" : baseDistanceHybridSatisfied ? "하이브리드" : "불가", baseDistanceRequiresSupplementalWarmup ? "보조 warm-up 필요" : "기본안", baseDistanceBaseDutyMeetsLoad ? colors.green : baseDistanceHybridSatisfied ? colors.gold : colors.red);
    addMetricBox(slide, 9.5, 5.0, 1.7, 0.95, "하이브리드 한계", `${formatNumber(maxFeasibleDistanceKm, 1)} km`, "편도 추정", colors.gold);
    addMetricBox(slide, 11.2, 5.0, 1.4, 0.95, `${formatNumber(longDistanceKm, 0)} km`, longDistanceBaseDutyMeetsLoad ? "기본 성립" : longDistanceHybridSatisfied ? "하이브리드만" : "불가", longDistanceRequiresSupplementalWarmup ? "보조 warm-up 필요" : "기본점", longDistanceBaseDutyMeetsLoad ? colors.green : longDistanceHybridSatisfied ? colors.gold : colors.red);
    addFooterNote(slide, "이송거리가 시스템의 진짜 경계조건임을 보여주는 슬라이드");
    finalizeSlide(slide);
  }

  // 14. Temperature sensitivity
  {
    const slide = pptx.addSlide();
    addSectionHeader(slide, 4, "순환 배관 설계 - 공급온도 민감도", page++);
    addFigure(slide, requireFigure("supply_temperature_sensitivity.png"), 0.72, 1.45, 6.1, 4.75, "공급온도 변화에 따른 유체 선택과 성립거리");
    const temperatureBullets = longDistanceBaseDutyMeetsLoad
      ? [
          bestSupplyRow
            ? `가장 효율적인 지점은 ${formatNumber(bestSupplyRow.supply_temp_k, 0)} K, ${bestSupplyRow.selected_fluid} 기본안이다.`
            : "현재 설정 범위에서는 별도의 feasible 공급온도 최적점이 정의되지 않았다.",
          `현재 기본안만으로도 ${formatNumber(longDistanceKm, 0)} km 조건이 기본 LNG duty 경계 안에서 성립한다.`,
          "따라서 공급온도 스윕은 거리 복구보다 여유와 펌프동력 변화의 trade-off를 읽는 도구가 된다.",
          practicalPassiveRows.length === 0 ? "다만 현실성 필터를 거치면 현재는 채택 가능한 무보조 해가 남지 않는다." : "현실성 필터를 거친 무보조 해도 일부 남아 있어 후속 설계 후보가 된다.",
          "온도 수준이 바뀌면 유체 선택과 최적 거리 여유도 함께 바뀐다.",
        ]
      : [
          bestSupplyRow
            ? `가장 효율적인 지점은 ${formatNumber(bestSupplyRow.supply_temp_k, 0)} K, ${bestSupplyRow.selected_fluid} 기본안이다.`
            : "현재 설정 범위에서는 별도의 feasible 공급온도 최적점이 정의되지 않았다.",
          `공급온도를 ${formatNumber(recover35Row.supply_temp_k, 0)} K까지 높이면 ${formatNumber(longDistanceKm, 0)} km 기본 LNG duty 조건을 회복할 수 있다.`,
          `하지만 그 과정에서 우선 유체가 ${recover35Row.selected_fluid}로 바뀌고 펌프동력은 크게 증가한다.`,
          practicalPassiveRows.length === 0 ? "또한 무보조 점이 나와도 현실성 필터를 통과하는 해는 아직 없다." : "현실성 필터를 통과하는 무보조 해는 제한적으로만 남는다.",
          "즉 거리 회복은 가능하지만 공짜는 아니다.",
        ];
    addBullets(slide, 7.55, 1.55, 4.9, temperatureBullets, 15.8);
    addMetricBox(slide, 7.7, 5.0, 1.7, 0.95, "최적점", `${formatNumber(displayBestSupplyRow.supply_temp_k, 0)} K`, String(displayBestSupplyRow.selected_fluid || "N/A").replace(" (Ammonia)", ""), colors.teal);
    addMetricBox(
      slide,
      9.55,
      5.0,
      1.85,
      0.95,
      `${formatNumber(longDistanceKm, 0)} km`,
      longDistanceBaseDutyMeetsLoad ? "기본 성립" : longDistanceHybridSatisfied ? "하이브리드만" : "복구 필요",
      longDistanceBaseDutyMeetsLoad ? String(displayBestSupplyRow.selected_fluid || "N/A").replace(" (Ammonia)", "") : String(recover35Row.selected_fluid || "N/A").replace(" (Ammonia)", ""),
      longDistanceBaseDutyMeetsLoad ? colors.green : longDistanceHybridSatisfied ? colors.gold : colors.red
    );
    addMetricBox(slide, 11.65, 5.0, 0.95, 0.95, "펌프", `${formatNumber(toNumber(displayBestSupplyRow.pump_power_kw), 0)} kW`, bestSupplyRow ? "최적점" : "fallback", colors.red);
    addFooterNote(slide, "온도 수준이 곧 거리와 유체 선택을 바꾸는 손잡이");
    finalizeSlide(slide);
  }

  // 15. Power comparison
  {
    const slide = pptx.addSlide();
    addSectionHeader(slide, 5, "열역학/경제성 평가 - 소비동력 비교", page++);
    addFigure(slide, requireFigure("system_power_comparison.png"), 0.72, 1.45, 6.0, 4.65, "이론 최소동력, 기준 시스템, LNG 시스템 비교");
    addBullets(slide, 7.5, 1.55, 5.0, [
      `이론 최소동력은 ${formatNumber(toNumber(summary["Theoretical minimum power"].value) / 1000.0, 2)} MW, 기준 압축기 동력은 ${formatNumber(toNumber(summary["Baseline R-134a compressor power"].value) / 1000.0, 2)} MW다.`,
      `LNG 시스템의 핵심 전동부하는 외부 루프 ${formatNumber(toNumber(summary["LNG system pump power"].value), 1)} kW와 IDC 2차 루프 ${formatNumber(toNumber(summary["IDC secondary-loop pump power"].value), 1)} kW를 합한 ${formatNumber(toNumber(summary["Core LNG system power"].value), 1)} kW 수준이다.`,
      `보조 열원이 남는다면 현재 시나리오 중 최선은 ${bestAuxiliary.scenario_label}이며 총 시스템 동력은 ${formatNumber(toNumber(bestAuxiliary.total_system_power_kw), 1)} kW다.`,
      "이 결과는 LNG 냉열 활용이 압축기 동력을 거의 제거하는 구조임을 보여준다.",
    ], 16);
    addMetricBox(slide, 7.75, 4.95, 1.55, 0.95, "이론 최소", `${formatNumber(toNumber(summary["Theoretical minimum power"].value) / 1000.0, 2)} MW`, "하한", colors.gold);
    addMetricBox(slide, 9.55, 4.95, 1.8, 0.95, "기준 시스템", `${formatNumber(toNumber(summary["Baseline R-134a compressor power"].value) / 1000.0, 2)} MW`, "R-134a", colors.red);
    addMetricBox(slide, 11.35, 4.95, 1.2, 0.95, "LNG", `${formatNumber(toNumber(summary["Core LNG system power"].value), 1)} kW`, "core", colors.green);
    addFooterNote(slide, "비교 경계는 기준 압축기 대비 core LNG system power");
    finalizeSlide(slide);
  }

  // 16. Annual impact
  {
    const slide = pptx.addSlide();
    addSectionHeader(slide, 5, "열역학/경제성 평가 - 연간 효과와 회수기간", page++);
    addFigure(slide, requireFigure("annual_impact_comparison.png"), 0.72, 1.45, 5.7, 4.7, "연간 전력, 비용, 탄소 효과");
    addMetricBox(slide, 6.75, 1.7, 2.55, 1.0, "전력 절감", formatNumber(toNumber(annualMap["Electricity saving"].value), 1), "MWh/년", colors.teal);
    addMetricBox(slide, 9.65, 1.7, 2.65, 1.0, "비용 절감", formatNumber(toNumber(annualMap["Electricity cost saving"].value) / 1_000_000.0, 1), "백만원/년", colors.green);
    addMetricBox(slide, 6.75, 3.05, 2.55, 1.0, "회피 배출", formatNumber(toNumber(annualMap["Avoided indirect emissions"].value), 1), "tCO2/년", colors.gold);
    addMetricBox(slide, 9.65, 3.05, 2.65, 1.0, "Core CAPEX", formatNumber(toNumber(summary["Core installed CAPEX"].value) / 1_000_000_000.0, 2), "십억원", colors.red);
    addSoftBox(slide, 6.75, 4.5, 5.55, 1.15, "해석 범위", [
      `현재 core-system NPV는 ${formatNumber(toNumber(summary["Core-system NPV"].value) / 1_000_000_000.0, 2)} 십억원으로, 장거리 외부 배관 CAPEX가 매우 크게 작용한다.`,
      `보조 열원까지 포함한 재무 최선 시나리오는 ${bestFinancialAuxiliary.scenario_label}이며 NPV는 ${formatNumber(toNumber(bestFinancialAuxiliary.npv_krw) / 1_000_000_000.0, 2)} 십억원이다.`,
    ]);
    addFooterNote(slide, "현재 버전은 core-system CAPEX와 단순 O&M/금융비용까지 포함");
    finalizeSlide(slide);
  }

  // 17. Additional considerations
  {
    const slide = pptx.addSlide();
    addSectionHeader(slide, 6, "추가 고려 사항 - 확장 과제", page++);
    addSoftBox(slide, 0.82, 1.45, 3.8, 4.95, "추가로 다뤄야 할 물리 문제", [
      "1) 실제 LNG 조성 변화",
      "2) IDC 냉수 배관 네트워크 상세 설계",
      "3) 장거리 조건에서의 제어 전략",
      "",
      "이번 코드 v2는 혼합 LNG surrogate와 IDC 2차 루프 등가 유압모델까지 포함한다.",
      transportReference
        ? `Transport proxy를 바꾸면 기화기 면적이 ${formatNumber(transportAreaMinDeltaPct, 2)}%~${formatNumber(transportAreaMaxDeltaPct, 2)}% 흔들린다.`
        : "혼합 LNG transport proxy 민감도는 비교 가능한 범위 안에서만 해석했다.",
    ]);
    addSoftBox(slide, 4.82, 1.45, 3.8, 4.95, `${formatNumber(longDistanceKm, 0)} km를 정말 목표로 할 경우`, [
      longDistanceBaseDutyMeetsLoad ? `현재 기본안으로도 ${formatNumber(longDistanceKm, 0)} km가 기본 LNG duty 경계 안에서 성립한다.` : longDistanceHybridSatisfied ? `현재 ${formatNumber(longDistanceKm, 0)} km는 하이브리드 운전은 가능하지만 기본 LNG duty는 부족하다.` : "공급온도 수준 조정",
      longDistanceBaseDutyMeetsLoad ? "다만 추가 거리 여유 확보는 별도 최적화 문제다." : "유체 변경(R-600a 방향)",
      longDistanceBaseDutyMeetsLoad ? "열유입 여유와 펌프동력 증가는 계속 trade-off다." : "펌프동력 증가 수용",
      "배관/단열 재최적화",
      "",
      longDistanceBaseDutyMeetsLoad ? `즉 ${formatNumber(longDistanceKm, 0)} km는 이제 기준안의 성립 영역 안에 들어오지만, 그 이상 확장은 여전히 설계 과제다.` : longDistanceHybridSatisfied ? `즉 ${formatNumber(longDistanceKm, 0)} km는 완전 불가가 아니라 하이브리드 해석과 기본 LNG duty 해석을 분리해 읽어야 한다.` : `즉 ${formatNumber(longDistanceKm, 0)} km는 기본안이 아니라 별도 설계 과제로 보는 편이 타당하다.`,
    ]);
    addSoftBox(slide, 8.82, 1.45, 3.68, 4.95, "발표에서 말하면 좋은 점", [
      "안 되는 조건도 설계 결론이다.",
      "이번 재구축은 계산 자동화와 민감도 분석까지 연결한다.",
      `IDC 2차 루프는 보수적 네트워크에서 펌프동력이 ${formatNumber(toNumber(conservativeNetwork.pump_power_kw), 1)} kW까지 증가할 수 있다.`,
      "따라서 이후 보고서 수정이나 조건 변경에 바로 대응할 수 있다.",
    ]);
    addFooterNote(slide, "A11의 ‘추가 고려 사항’ 파트를 현재 코드 기반으로 이어받음");
    finalizeSlide(slide);
  }

  // 18. Reproducibility and sources
  {
    const slide = pptx.addSlide();
    addSectionHeader(slide, 6, "추가 고려 사항 - 출처 체계와 재현성", page++);
    addSoftBox(slide, 0.85, 1.45, 3.7, 4.9, "재현 가능한 구조", [
      "config/base.toml",
      "docs/sources.md",
      "docs/assumptions.md",
      "output/*.csv",
      "output/figures/*.png",
      "deliverables/*.md",
      "deliverables/presentation_draft.pptx",
    ]);
    addSoftBox(slide, 4.9, 1.45, 3.7, 4.9, "이번 발표의 장점", [
      "외부 수치의 출처 추적이 가능하다.",
      "같은 조건에서 결과를 다시 만들 수 있다.",
      "민감도 분석과 보고서 초안이 자동으로 이어진다.",
    ]);
    addSoftBox(slide, 8.95, 1.45, 3.5, 4.9, "교수님께 전달할 메시지", [
      "이 발표는 단순 복기가 아니라 설계 프로젝트의 구조적 업그레이드다.",
      "따라서 이후 질의응답에서도 수치와 가정을 바로 추적할 수 있다.",
    ]);
    addFooterNote(slide, "코드, 문서, 출처 로그가 하나의 저장소 안에서 연결됨");
    finalizeSlide(slide);
  }

  // 19. Conclusion
  {
    const slide = pptx.addSlide();
    addBackground(slide);
    addCoverBracket(slide, 0.9, 1.05, "left");
    addCoverBracket(slide, 12.45, 1.05, "right");
    slide.addText("최종 결론", {
      x: 5.25,
      y: 0.85,
      w: 2.8,
      h: 0.35,
      fontFace: "Malgun Gothic",
      fontSize: 23,
      bold: true,
      color: colors.teal,
      align: "center",
    });
    addSoftBox(slide, 1.15, 1.8, 3.55, 3.25, "결론 1", [
      baseDistanceBaseDutyMeetsLoad ? "10 km 설계점에서는 기본 LNG duty 기준으로도 LNG 냉열 기반 IDC 냉각 개념이 성립한다." : baseDistanceHybridSatisfied ? "10 km 설계점에서는 supplemental warm-up을 포함한 하이브리드 운전 기준으로 LNG 냉열 기반 IDC 냉각 개념이 성립한다." : "10 km 설계점조차 현재 기본안으로는 별도 보조조건 없이는 성립하지 않는다.",
      "기준 압축기 시스템 대비 core-system 전력 요구는 매우 크게 감소한다.",
    ]);
    addSoftBox(slide, 4.9, 1.8, 3.55, 3.25, "결론 2", [
      "냉각유체 기본안은 R-717이며, 기화기 최소 핀치 10 K와 장치 현실성을 함께 만족한다.",
      "즉 성능과 설계성 모두에서 현재 가장 균형이 좋다.",
    ]);
    addSoftBox(slide, 8.65, 1.8, 3.55, 3.25, "결론 3", [
      longDistanceBaseDutyMeetsLoad ? `IDC 측 HX와 LNG hot-end 제약을 함께 풀어도 ${formatNumber(longDistanceKm, 0)} km가 현재 기본안의 기본 LNG duty 경계 안에서 성립한다.` : longDistanceHybridSatisfied ? `${formatNumber(longDistanceKm, 0)} km는 하이브리드 운전에서는 성립하지만 기본 LNG duty 경계에서는 불성립한다.` : `${formatNumber(longDistanceKm, 0)} km는 기본안의 단순 연장이 아니라 별도 최적화가 필요한 확장 조건이다.`,
      longDistanceBaseDutyMeetsLoad ? "따라서 이번 재구축의 메시지는 기존보다 완화된 실제 성립영역을 재계산했다는 데 있다." : "따라서 이번 프로젝트의 진짜 메시지는 ‘가능/불가능의 경계’를 물리적으로 분해해냈다는 데 있다.",
    ]);
    addMetricBox(slide, 1.25, 5.55, 2.8, 1.02, "기본안", baseDistanceBaseDutyMeetsLoad ? "10 km 기본 성립" : baseDistanceHybridSatisfied ? "10 km 하이브리드 운전 가능" : "10 km 재설계 필요", baseDistanceRequiresSupplementalWarmup ? "보조 warm-up 필요" : "LNG 냉열 활용", baseDistanceBaseDutyMeetsLoad ? colors.green : baseDistanceHybridSatisfied ? colors.gold : colors.red);
    addMetricBox(slide, 4.45, 5.55, 2.8, 1.02, "경계조건", `${formatNumber(maxFeasibleDistanceKm, 1)} km`, "추정 하이브리드 편도 한계", colors.gold);
    addMetricBox(slide, 7.65, 5.55, 4.3, 1.02, "확장 판단", `${formatNumber(longDistanceKm, 0)} km ${longDistanceBaseDutyMeetsLoad ? "기본안 성립" : longDistanceHybridSatisfied ? "하이브리드 운전 가능" : "확장 실패"}`, longDistanceBaseDutyMeetsLoad ? "현재 설계 가능" : longDistanceHybridSatisfied ? "보조 warm-up 필요" : "기본안 불성립", longDistanceBaseDutyMeetsLoad ? colors.green : longDistanceHybridSatisfied ? colors.gold : colors.red);
    addPageNumber(slide, page++);
    addFooterNote(slide, "A11 스타일의 장문형 발표 흐름으로 재구성한 최종 장표");
    finalizeSlide(slide);
  }
}

async function main() {
  buildDeck();
  await pptx.writeFile({ fileName: outputFile });
  console.log(outputFile);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
