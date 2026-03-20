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
pptx.subject = "LNG 냉열 기반 IDC 냉각시스템 설계 연구";
pptx.title = "LNG 냉열 기반 IDC 설계 연구";
pptx.lang = "ko-KR";
pptx.theme = {
  headFontFace: "Malgun Gothic",
  bodyFontFace: "Malgun Gothic",
  lang: "ko-KR",
};

const colors = {
  ink: "10243D",
  teal: "1C6E73",
  cyan: "5AA7A4",
  gold: "D7A64A",
  red: "B55349",
  green: "2E7D5A",
  cream: "F6F2E8",
  white: "FFFFFF",
  slate: "5A6675",
  mist: "E9EDF0",
  charcoal: "28323F",
};

const figuresDir = path.resolve(__dirname, "..", "..", "output", "figures");
const outputFile = path.resolve(__dirname, "..", "presentation_draft.pptx");

function addBackground(slide, fill) {
  slide.background = { color: fill };
}

function addHeader(slide, title, kicker, fill = colors.cream) {
  slide.addText(kicker, {
    x: 0.55,
    y: 0.28,
    w: 5.0,
    h: 0.18,
    fontFace: "Malgun Gothic",
    fontSize: 10,
    color: colors.cyan,
    bold: true,
    charSpace: 1.2,
  });
  slide.addText(title, {
    x: 0.55,
    y: 0.7,
    w: 9.5,
    h: 0.42,
    fontFace: "Malgun Gothic",
    fontSize: 22,
    bold: true,
    color: fill,
  });
}

function addFooter(slide, text) {
  slide.addText(text, {
    x: 0.55,
    y: 7.03,
    w: 12.15,
    h: 0.18,
    fontFace: "Malgun Gothic",
    fontSize: 8,
    color: colors.slate,
    align: "right",
  });
}

function addMetricCard(slide, x, y, w, h, label, value, accent, caption) {
  const compact = h <= 1.15;
  const labelY = compact ? y + 0.14 : y + 0.18;
  const labelFontSize = compact ? 9 : 10;
  const valueY = compact ? y + 0.34 : y + 0.42;
  const valueHeight = compact ? 0.34 : 0.52;
  const valueFontSize = compact ? 18 : 23;
  const captionY = compact ? y + h - 0.16 : y + h - 0.3;
  const captionHeight = compact ? 0.12 : 0.2;
  const captionFontSize = compact ? 7.8 : 8.5;
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    fill: { color: colors.white },
    line: { color: colors.mist, pt: 1.1 },
    shadow: {
      type: "outer",
      color: "9AA5B4",
      blur: 1,
      angle: 45,
      distance: 1,
      opacity: 0.12,
    },
  });
  slide.addShape(pptx.ShapeType.rect, {
    x,
    y,
    w: 0.12,
    h,
    fill: { color: accent },
    line: { color: accent, transparency: 100 },
  });
  slide.addText(label, {
    x: x + 0.25,
    y: labelY,
    w: w - 0.35,
    h: 0.18,
    fontFace: "Malgun Gothic",
    fontSize: labelFontSize,
    bold: true,
    color: colors.slate,
    charSpace: 0.4,
  });
  slide.addText(value, {
    x: x + 0.25,
    y: valueY,
    w: w - 0.35,
    h: valueHeight,
    fontFace: "Malgun Gothic",
    fontSize: valueFontSize,
    bold: true,
    color: colors.ink,
  });
  if (caption) {
    slide.addText(caption, {
      x: x + 0.25,
      y: captionY,
      w: w - 0.35,
      h: captionHeight,
      fontFace: "Malgun Gothic",
      fontSize: captionFontSize,
      color: colors.slate,
    });
  }
}

function addBulletBlock(slide, x, y, w, heading, bullets, fill = colors.white) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h: 1.7 + bullets.length * 0.34,
    rectRadius: 0.05,
    fill: { color: fill },
    line: { color: colors.mist, pt: 0.8 },
  });
  slide.addText(heading, {
    x: x + 0.22,
    y: y + 0.16,
    w: w - 0.44,
    h: 0.24,
    fontFace: "Malgun Gothic",
    fontSize: 15,
    bold: true,
    color: colors.ink,
  });
  slide.addText(
    bullets.map((bullet) => ({ text: bullet, options: { bullet: { indent: 10 } } })),
    {
      x: x + 0.2,
      y: y + 0.46,
      w: w - 0.4,
      h: 0.26 + bullets.length * 0.34,
      fontFace: "Malgun Gothic",
      fontSize: 12.5,
      color: colors.charcoal,
      breakLine: false,
      paraSpaceAfterPt: 6,
      valign: "top",
      margin: 0,
    }
  );
}

function addImagePanel(slide, x, y, w, h, imagePath, caption) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.05,
    fill: { color: colors.white },
    line: { color: colors.mist, pt: 0.8 },
  });
  slide.addImage({
    path: imagePath,
    ...imageSizingContain(imagePath, x + 0.08, y + 0.08, w - 0.16, h - 0.36),
  });
  slide.addText(caption, {
    x: x + 0.12,
    y: y + h - 0.22,
    w: w - 0.24,
    h: 0.14,
    fontFace: "Malgun Gothic",
    fontSize: 8.5,
    color: colors.slate,
    align: "center",
  });
}

function finalizeSlide(slide) {
  warnIfSlideHasOverlaps(slide, pptx);
  warnIfSlideElementsOutOfBounds(slide, pptx);
}

function requireFigure(fileName) {
  const filePath = path.join(figuresDir, fileName);
  if (!fs.existsSync(filePath)) {
    throw new Error(`Missing figure: ${filePath}`);
  }
  return filePath;
}

function buildDeck() {
  // Slide 1
  {
    const slide = pptx.addSlide();
    addBackground(slide, colors.ink);
    slide.addShape(pptx.ShapeType.ellipse, {
      x: 11.0,
      y: 4.35,
      w: 1.9,
      h: 1.9,
      fill: { color: colors.gold, transparency: 70 },
      line: { color: colors.gold, transparency: 100 },
    });
    slide.addText("LNG 냉열 활용\nIDC 냉각시스템", {
      x: 0.65,
      y: 0.85,
      w: 6.9,
      h: 1.7,
      fontFace: "Malgun Gothic",
      fontSize: 26,
      bold: true,
      color: colors.cream,
      breakLine: false,
    });
    slide.addText("시나리오 분석, 경제성 평가, 출처 추적을 포함한 재현 가능한 코드 기반 설계 연구", {
      x: 0.7,
      y: 2.6,
      w: 6.0,
      h: 0.55,
      fontFace: "Malgun Gothic",
      fontSize: 13,
      color: "D8E1E8",
    });
    addMetricCard(slide, 0.7, 4.4, 2.35, 1.45, "냉방부하", "13.48 MW", colors.cyan, "모델링된 IDC 부하");
    addMetricCard(slide, 3.25, 4.4, 2.35, 1.45, "기본 조건", "10 km", colors.gold, "편도 이송거리");
    addMetricCard(slide, 5.8, 4.4, 2.55, 1.45, "전력 절감", "4.17 MW", colors.green, "기준 압축기 대비");
    addBulletBlock(slide, 8.9, 1.15, 3.8, "이번 재구축에서 달라진 점", [
      "스프레드시트가 아닌 코드 중심 재구축",
      "출처와 가정을 명시적으로 기록",
      "거리, 유체, 온도 민감도까지 분석",
    ], "132B45");
    addFooter(slide, "열시스템디자인 프로젝트 | slides_src/presentation_draft.js에서 생성");
    finalizeSlide(slide);
  }

  // Slide 2
  {
    const slide = pptx.addSlide();
    addBackground(slide, colors.cream);
    addHeader(slide, "설계 질문과 기준", "프로젝트 개요");
    addBulletBlock(slide, 0.65, 1.25, 4.1, "핵심 질문", [
      "LNG 냉열로 대형 IDC의 기준 R-134a 냉방부하를 대체할 수 있는가?",
      "LNG 기지와 부지 사이 장거리 이송 페널티를 견딜 수 있는가?",
      "이 전력 절감이 지속될 때 경제적 가치는 어느 정도인가?",
    ], colors.white);
    addMetricCard(slide, 5.1, 1.28, 2.1, 1.28, "모델 부하", "13.48 MW", colors.red, "IDC 냉방부하");
    addMetricCard(slide, 7.45, 1.28, 2.1, 1.28, "도전 조건", "35 km", colors.gold, "장거리 검토");
    addMetricCard(slide, 9.8, 1.28, 2.1, 1.28, "기준 전력", "4.19 MW", colors.teal, "R-134a 압축기");
    slide.addShape(pptx.ShapeType.line, {
      x: 5.65,
      y: 4.05,
      w: 6.0,
      h: 0,
      line: { color: colors.mist, pt: 1.6 },
    });
    const nodes = [
      { x: 5.45, title: "LNG 기지", note: "112 K 메탄 유입" },
      { x: 7.45, title: "기화기", note: "쉘-튜브 열교환기" },
      { x: 9.45, title: "2차 루프", note: "냉열 이송" },
      { x: 11.45, title: "IDC", note: "11층 냉방부하" },
    ];
    nodes.forEach((node, idx) => {
      slide.addShape(pptx.ShapeType.ellipse, {
        x: node.x + 0.28,
        y: 3.68,
        w: 0.78,
        h: 0.78,
        fill: { color: idx % 2 === 0 ? "EDF4F6" : "F7F0DE" },
        line: { color: idx % 2 === 0 ? colors.cyan : colors.gold, pt: 1.2 },
      });
      slide.addText(node.title, {
        x: node.x - 0.08,
        y: 4.58,
        w: 1.52,
        h: 0.2,
        fontFace: "Malgun Gothic",
        fontSize: 11.5,
        bold: true,
        color: colors.ink,
        align: "center",
      });
      slide.addText(node.note, {
        x: node.x - 0.12,
        y: 4.86,
        w: 1.58,
        h: 0.18,
        fontFace: "Malgun Gothic",
        fontSize: 8.2,
        color: colors.slate,
        align: "center",
      });
      if (idx < nodes.length - 1) {
        slide.addText("→", {
          x: node.x + 1.43,
          y: 3.82,
          w: 0.4,
          h: 0.2,
          fontFace: "Malgun Gothic",
          fontSize: 18,
          color: colors.teal,
          bold: true,
          align: "center",
        });
      }
    });
    addFooter(slide, "출처: SRC-001, SRC-009, ASM-001 to ASM-011");
    finalizeSlide(slide);
  }

  // Slide 3
  {
    const slide = pptx.addSlide();
    addBackground(slide, colors.cream);
    addHeader(slide, "LNG 냉각 개념과 해석 구조", "시스템 개념");
    addImagePanel(slide, 0.65, 1.3, 5.75, 4.95, requireFigure("hx_temperature_profile.png"), "구간 분할 LNG 기화기 온도 프로파일");
    addBulletBlock(slide, 6.7, 1.35, 5.9, "설계를 좌우한 선택", [
      "단일 등비열 가정 대신 구간 분할 엔탈피 모델을 사용했다.",
      "기본 2차 루프 유체는 220 K 공급 조건의 암모니아다.",
      "선정 기화기 형상은 500본 x 14 m이며 최소 핀치는 10 K다.",
    ], colors.white);
    addMetricCard(slide, 6.95, 4.55, 1.7, 1.25, "유체", "R-717", colors.teal, "암모니아");
    addMetricCard(slide, 8.85, 4.55, 1.7, 1.25, "핀치", "10 K", colors.gold, "설계 제약");
    addMetricCard(slide, 10.75, 4.55, 1.7, 1.25, "쉘 직경", "0.723 m", colors.red, "선정 크기");
    addFooter(slide, "출처: SRC-001, SRC-006, SRC-007");
    finalizeSlide(slide);
  }

  // Slide 4
  {
    const slide = pptx.addSlide();
    addBackground(slide, colors.cream);
    addHeader(slide, "기준 사이클 대비 성능", "성능 비교");
    addMetricCard(slide, 0.7, 1.4, 2.55, 1.4, "이론 최소", "1.22 MW", colors.gold, "카르노 하한");
    addMetricCard(slide, 0.7, 3.0, 2.55, 1.4, "기준 사이클", "4.19 MW", colors.red, "R-134a 압축기");
    addMetricCard(slide, 0.7, 4.6, 2.55, 1.4, "LNG 루프", "13.1 kW", colors.green, "기본안 펌프동력");
    addImagePanel(slide, 3.6, 1.35, 4.0, 4.85, requireFigure("system_power_comparison.png"), "모델링된 전력 요구 비교");
    addBulletBlock(slide, 7.95, 1.45, 4.3, "해석 포인트", [
      "기본 개념은 냉방 시스템의 전력 요구를 크게 낮춘다.",
      "이 결과는 기준 사이클이 이미 이론 최소동력보다 높은 정상적인 수준이라는 점에서 의미가 있다.",
      "이후의 핵심 질문은 순수 효율보다 이송 가능 거리와 구현 상충관계로 이동한다.",
    ], colors.white);
    addFooter(slide, "출처: SRC-001, SRC-004, SRC-005");
    finalizeSlide(slide);
  }

  // Slide 5
  {
    const slide = pptx.addSlide();
    addBackground(slide, colors.cream);
    addHeader(slide, "냉각유체 선정은 감이 아니라 설계 결과다", "유체 스크리닝");
    addImagePanel(slide, 0.7, 1.35, 6.0, 4.8, requireFigure("fluid_ranking.png"), "스크리닝 점수와 요구 질량유량");
    addMetricCard(slide, 7.1, 1.45, 2.0, 1.28, "1위", "R-717", colors.teal, "13.1 kW 펌프");
    addMetricCard(slide, 9.3, 1.45, 2.0, 1.28, "2위", "R-290", colors.gold, "124.9 kW 펌프");
    addMetricCard(slide, 11.5, 1.45, 1.2, 1.28, "3위", "R-600a", colors.red, "134.5 kW");
    addBulletBlock(slide, 7.05, 3.0, 5.55, "기본안에서 암모니아가 앞선 이유", [
      "실현 가능한 후보 중 루프 펌프동력이 가장 낮다.",
      "탄화수소 대안보다 기화기 규모가 더 작다.",
      "안전성과 호환성 페널티를 코드 안에서 명시적으로 반영했다.",
    ], colors.white);
    addFooter(slide, "출처: SRC-003, SRC-008, ASM-017 to ASM-019");
    finalizeSlide(slide);
  }

  // Slide 6
  {
    const slide = pptx.addSlide();
    addBackground(slide, colors.cream);
    addHeader(slide, "실제 제약은 이송거리다", "배관 제약");
    addImagePanel(slide, 0.7, 1.35, 6.0, 4.9, requireFigure("pipeline_distance_sensitivity.png"), "거리 증가에 따른 펌프동력과 열유입");
    addBulletBlock(slide, 7.0, 1.45, 5.4, "기본안 판단", [
      "10 km는 충분한 열 여유와 함께 성립한다.",
      "추정된 편도 한계거리는 약 29.6 km다.",
      "35 km에서는 열유입이 사용 가능한 duty 여유를 넘어 기본안이 성립하지 않는다.",
    ], colors.white);
    addMetricCard(slide, 7.2, 4.95, 1.7, 1.1, "기본안", "10 km", colors.green, "성립");
    addMetricCard(slide, 9.1, 4.95, 1.7, 1.1, "한계", "29.6 km", colors.gold, "추정값");
    addMetricCard(slide, 11.0, 4.95, 1.7, 1.1, "도전조건", "35 km", colors.red, "불성립");
    addFooter(slide, "출처: SRC-001, ASM-014 to ASM-016");
    finalizeSlide(slide);
  }

  // Slide 7
  {
    const slide = pptx.addSlide();
    addBackground(slide, colors.cream);
    addHeader(slide, "공급온도를 올리면 거리는 늘어나지만 공짜는 아니다", "민감도");
    addImagePanel(slide, 0.7, 1.35, 6.0, 4.9, requireFigure("supply_temperature_sensitivity.png"), "공급온도 스윕 결과");
    addBulletBlock(slide, 7.0, 1.45, 5.4, "상충관계", [
      "가장 효율적인 지점은 여전히 220 K 암모니아 기본안이다.",
      "230 K 수준으로 올리면 35 km 설계를 성립시킬 수 있다.",
      "대신 이소부탄으로 바뀌고 펌프동력이 거의 10배 수준으로 커진다.",
    ], colors.white);
    addMetricCard(slide, 7.25, 4.95, 1.8, 1.08, "최적점", "220 K", colors.teal, "R-717");
    addMetricCard(slide, 9.3, 4.95, 1.8, 1.08, "35 km 복구", "230 K", colors.gold, "R-600a");
    addMetricCard(slide, 11.35, 4.95, 1.2, 1.08, "대가", "130 kW", colors.red, "루프 펌프");
    addFooter(slide, "출처: ASM-028, ASM-029");
    finalizeSlide(slide);
  }

  // Slide 8
  {
    const slide = pptx.addSlide();
    addBackground(slide, colors.cream);
    addHeader(slide, "연간 효과를 보면 의사결정이 선명해진다", "경제성");
    addImagePanel(slide, 0.7, 1.35, 5.5, 4.9, requireFigure("annual_impact_comparison.png"), "연간 전력, 비용, 탄소 비교");
    addMetricCard(slide, 6.55, 1.55, 2.8, 1.28, "전력 절감", "36,549", colors.teal, "MWh/년");
    addMetricCard(slide, 9.6, 1.55, 2.8, 1.28, "비용 절감", "3,839.5", colors.green, "백만원/년");
    addMetricCard(slide, 6.55, 3.15, 2.8, 1.28, "회피 배출", "16,757.7", colors.gold, "tCO2/년");
    addMetricCard(slide, 9.6, 3.15, 2.8, 1.28, "5년 허용 CAPEX", "19,197.4", colors.red, "백만원");
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 6.55,
      y: 4.85,
      w: 5.85,
      h: 0.95,
      rectRadius: 0.04,
      fill: { color: "EDF4F6" },
      line: { color: colors.cyan, pt: 0.8 },
    });
    slide.addText("경계조건 메모: 연간 지표는 기준 압축기 전력과 LNG 루프 펌프동력만 비교한 결과다.", {
      x: 6.8,
      y: 5.09,
      w: 5.35,
      h: 0.34,
      fontFace: "Malgun Gothic",
      fontSize: 10.5,
      color: colors.charcoal,
    });
    addFooter(slide, "출처: SRC-013, SRC-014, ASM-030 to ASM-032");
    finalizeSlide(slide);
  }

  // Slide 9
  {
    const slide = pptx.addSlide();
    addBackground(slide, colors.ink);
    addHeader(slide, "최종 제안", "결론", colors.cream);
    addBulletBlock(slide, 0.85, 1.35, 4.0, "확실히 말할 수 있는 점", [
      "LNG 냉열 개념은 10 km 설계점에서 기술적으로 성립한다.",
      "기본안은 기준 압축기 대비 전력 요구가 매우 낮다.",
      "핵심은 단일 최적값보다 성립 거리와 불성립 거리의 경계다.",
    ], "122A45");
    addBulletBlock(slide, 5.0, 1.35, 3.5, "발표에서 강조할 메시지", [
      "10 km는 된다.",
      "35 km는 기본점에서 안 된다.",
      "35 km는 다른 운전조건을 받아들일 때만 복구된다.",
    ], "122A45");
    addBulletBlock(slide, 8.75, 1.35, 3.75, "다음 정교화 단계", [
      "암모니아와 탄화수소 유체의 안전성 서술 보강",
      "구현 리스크와 제어 전략 추가",
      "마크다운 보고서를 최종 제출 형식으로 변환",
    ], "122A45");
    addMetricCard(slide, 0.95, 5.55, 3.0, 1.02, "기본안 결론", "10 km 가능", colors.green, "LNG 냉열 적용");
    addMetricCard(slide, 4.2, 5.55, 3.0, 1.02, "경계 통찰", "29.6 km 한계", colors.gold, "편도 기준 추정");
    addMetricCard(slide, 7.45, 5.55, 4.0, 1.02, "의사결정", "가능하지만 거리 민감", colors.red, "보편 해법은 아님");
    addFooter(slide, "수정 가능한 후속 작업을 위해 PptxGenJS 원본에서 생성");
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
