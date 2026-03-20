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
pptx.subject = "LNG IDC cooling system design study";
pptx.title = "LNG IDC Design Study";
pptx.lang = "en-US";
pptx.theme = {
  headFontFace: "Aptos Display",
  bodyFontFace: "Aptos",
  lang: "en-US",
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
    fontFace: "Aptos",
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
    fontFace: "Aptos Display",
    fontSize: 24,
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
    fontFace: "Aptos",
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
    fontFace: "Aptos",
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
    fontFace: "Aptos Display",
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
      fontFace: "Aptos",
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
    fontFace: "Aptos Display",
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
      fontFace: "Aptos",
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
    fontFace: "Aptos",
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
    slide.addText("LNG Cold-Energy\nIDC Cooling System", {
      x: 0.65,
      y: 0.85,
      w: 6.9,
      h: 1.7,
      fontFace: "Aptos Display",
      fontSize: 28,
      bold: true,
      color: colors.cream,
      breakLine: false,
    });
    slide.addText("Reproducible thermal-system design study with scenario, economics, and source traceability.", {
      x: 0.7,
      y: 2.6,
      w: 6.0,
      h: 0.55,
      fontFace: "Aptos",
      fontSize: 14,
      color: "D8E1E8",
    });
    addMetricCard(slide, 0.7, 4.4, 2.35, 1.45, "Cooling load", "13.48 MW", colors.cyan, "Modeled IDC duty");
    addMetricCard(slide, 3.25, 4.4, 2.35, 1.45, "Base case", "10 km", colors.gold, "One-way transport distance");
    addMetricCard(slide, 5.8, 4.4, 2.55, 1.45, "Power saving", "4.17 MW", colors.green, "Baseline compressor minus LNG loop");
    addBulletBlock(slide, 8.9, 1.15, 3.8, "What changed from the old project", [
      "Full code reproduction instead of spreadsheet-only work",
      "Explicit source and assumption registry",
      "Distance, fluid, and temperature sensitivity studies",
    ], "132B45");
    addFooter(slide, "Course project | Generated from deliverables/slides_src/presentation_draft.js");
    finalizeSlide(slide);
  }

  // Slide 2
  {
    const slide = pptx.addSlide();
    addBackground(slide, colors.cream);
    addHeader(slide, "Design Question and Basis", "PROJECT FRAME");
    addBulletBlock(slide, 0.65, 1.25, 4.1, "Design question", [
      "Can LNG cold energy replace the reference R-134a cooling load for a large IDC?",
      "Can the concept survive the transport-distance penalty between the LNG terminal and the site?",
      "What is the economic value if the modeled cooling power reduction is sustained year-round?",
    ], colors.white);
    addMetricCard(slide, 5.1, 1.28, 2.1, 1.28, "Modeled load", "13.48 MW", colors.red, "IDC cooling duty");
    addMetricCard(slide, 7.45, 1.28, 2.1, 1.28, "Challenge case", "35 km", colors.gold, "Long-distance test");
    addMetricCard(slide, 9.8, 1.28, 2.1, 1.28, "Reference power", "4.19 MW", colors.teal, "R-134a compressor");
    slide.addShape(pptx.ShapeType.line, {
      x: 5.65,
      y: 4.05,
      w: 6.0,
      h: 0,
      line: { color: colors.mist, pt: 1.6 },
    });
    const nodes = [
      { x: 5.45, title: "LNG terminal", note: "112 K methane stream" },
      { x: 7.45, title: "Vaporizer", note: "Shell-and-tube exchanger" },
      { x: 9.45, title: "Secondary loop", note: "Coolant transport" },
      { x: 11.45, title: "IDC", note: "11-floor cooling load" },
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
        fontFace: "Aptos Display",
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
        fontFace: "Aptos",
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
          fontFace: "Aptos Display",
          fontSize: 18,
          color: colors.teal,
          bold: true,
          align: "center",
        });
      }
    });
    addFooter(slide, "Sources: SRC-001, SRC-009, ASM-001 to ASM-011");
    finalizeSlide(slide);
  }

  // Slide 3
  {
    const slide = pptx.addSlide();
    addBackground(slide, colors.cream);
    addHeader(slide, "How the LNG Cooling Concept Works", "SYSTEM CONCEPT");
    addImagePanel(slide, 0.65, 1.3, 5.75, 4.95, requireFigure("hx_temperature_profile.png"), "Segmented LNG vaporizer temperature profile");
    addBulletBlock(slide, 6.7, 1.35, 5.9, "Design choices that matter", [
      "Segmented enthalpy model replaces a single constant-cp approximation.",
      "Base-case secondary-loop fluid is ammonia at 220 K supply level.",
      "The selected vaporizer geometry is 500 tubes x 14 m with a 10 K minimum pinch.",
    ], colors.white);
    addMetricCard(slide, 6.95, 4.55, 1.7, 1.25, "Fluid", "R-717", colors.teal, "Ammonia");
    addMetricCard(slide, 8.85, 4.55, 1.7, 1.25, "Pinch", "10 K", colors.gold, "Constraint");
    addMetricCard(slide, 10.75, 4.55, 1.7, 1.25, "Shell OD", "0.723 m", colors.red, "Selected size");
    addFooter(slide, "Sources: SRC-001, SRC-006, SRC-007");
    finalizeSlide(slide);
  }

  // Slide 4
  {
    const slide = pptx.addSlide();
    addBackground(slide, colors.cream);
    addHeader(slide, "Benchmark Against the Reference Cycle", "PERFORMANCE");
    addMetricCard(slide, 0.7, 1.4, 2.55, 1.4, "Theoretical minimum", "1.22 MW", colors.gold, "Carnot lower bound");
    addMetricCard(slide, 0.7, 3.0, 2.55, 1.4, "Reference cycle", "4.19 MW", colors.red, "R-134a compressor");
    addMetricCard(slide, 0.7, 4.6, 2.55, 1.4, "LNG loop", "13.1 kW", colors.green, "Base-case pumping demand");
    addImagePanel(slide, 3.6, 1.35, 4.0, 4.85, requireFigure("system_power_comparison.png"), "Modeled electric-power comparison");
    addBulletBlock(slide, 7.95, 1.45, 4.3, "Interpretation", [
      "The base concept dramatically reduces modeled cooling-system power draw.",
      "This result is strong because the benchmark already respects the theoretical lower bound ordering.",
      "The key question shifts from raw efficiency to transport feasibility and implementation trade-offs.",
    ], colors.white);
    addFooter(slide, "Sources: SRC-001, SRC-004, SRC-005");
    finalizeSlide(slide);
  }

  // Slide 5
  {
    const slide = pptx.addSlide();
    addBackground(slide, colors.cream);
    addHeader(slide, "Coolant Selection Is a Design Choice, Not a Guess", "SCREENING");
    addImagePanel(slide, 0.7, 1.35, 6.0, 4.8, requireFigure("fluid_ranking.png"), "Screening score versus required mass flow");
    addMetricCard(slide, 7.1, 1.45, 2.0, 1.28, "1st", "R-717", colors.teal, "13.1 kW pump");
    addMetricCard(slide, 9.3, 1.45, 2.0, 1.28, "2nd", "R-290", colors.gold, "124.9 kW pump");
    addMetricCard(slide, 11.5, 1.45, 1.2, 1.28, "3rd", "R-600a", colors.red, "134.5 kW");
    addBulletBlock(slide, 7.05, 3.0, 5.55, "Why ammonia wins in the base case", [
      "Lowest loop pumping demand among feasible options",
      "Compact vaporizer relative to the hydrocarbon alternatives",
      "Transparent penalty handling for safety and compatibility trade-offs",
    ], colors.white);
    addFooter(slide, "Sources: SRC-003, SRC-008, ASM-017 to ASM-019");
    finalizeSlide(slide);
  }

  // Slide 6
  {
    const slide = pptx.addSlide();
    addBackground(slide, colors.cream);
    addHeader(slide, "The Real Constraint Is Transport Distance", "PIPELINE");
    addImagePanel(slide, 0.7, 1.35, 6.0, 4.9, requireFigure("pipeline_distance_sensitivity.png"), "Distance sensitivity for pump power and heat gain");
    addBulletBlock(slide, 7.0, 1.45, 5.4, "Base-case verdict", [
      "10 km is feasible with healthy thermal margin.",
      "The estimated one-way limit is about 29.6 km.",
      "The 35 km case fails at the base design point because heat gain outruns the available duty buffer.",
    ], colors.white);
    addMetricCard(slide, 7.2, 4.95, 1.7, 1.1, "Base case", "10 km", colors.green, "Feasible");
    addMetricCard(slide, 9.1, 4.95, 1.7, 1.1, "Limit", "29.6 km", colors.gold, "Estimated");
    addMetricCard(slide, 11.0, 4.95, 1.7, 1.1, "Challenge", "35 km", colors.red, "Infeasible");
    addFooter(slide, "Sources: SRC-001, ASM-014 to ASM-016");
    finalizeSlide(slide);
  }

  // Slide 7
  {
    const slide = pptx.addSlide();
    addBackground(slide, colors.cream);
    addHeader(slide, "Temperature Level Can Recover Distance, But Not for Free", "SENSITIVITY");
    addImagePanel(slide, 0.7, 1.35, 6.0, 4.9, requireFigure("supply_temperature_sensitivity.png"), "Supply-temperature sweep");
    addBulletBlock(slide, 7.0, 1.45, 5.4, "Trade-off", [
      "The most efficient point remains the 220 K ammonia design.",
      "A warmer supply level of 230 K can make the 35 km case feasible.",
      "That recovery requires switching to isobutane and accepting a roughly tenfold pump-power increase.",
    ], colors.white);
    addMetricCard(slide, 7.25, 4.95, 1.8, 1.08, "Best power", "220 K", colors.teal, "R-717");
    addMetricCard(slide, 9.3, 4.95, 1.8, 1.08, "35 km fix", "230 K", colors.gold, "R-600a");
    addMetricCard(slide, 11.35, 4.95, 1.2, 1.08, "Cost", "130 kW", colors.red, "Loop pump");
    addFooter(slide, "Sources: ASM-028, ASM-029");
    finalizeSlide(slide);
  }

  // Slide 8
  {
    const slide = pptx.addSlide();
    addBackground(slide, colors.cream);
    addHeader(slide, "Annual Impact Makes the Design Decision Tangible", "ECONOMICS");
    addImagePanel(slide, 0.7, 1.35, 5.5, 4.9, requireFigure("annual_impact_comparison.png"), "Annualized energy, cost, and carbon comparison");
    addMetricCard(slide, 6.55, 1.55, 2.8, 1.28, "Electricity saving", "36,549 MWh/yr", colors.teal, "Modeled boundary");
    addMetricCard(slide, 9.6, 1.55, 2.8, 1.28, "Cost saving", "3,839.5 M KRW/yr", colors.green, "At 105.05 KRW/kWh");
    addMetricCard(slide, 6.55, 3.15, 2.8, 1.28, "Avoided emissions", "16,757.7 tCO2/yr", colors.gold, "Indirect emissions");
    addMetricCard(slide, 9.6, 3.15, 2.8, 1.28, "5-yr CAPEX room", "19,197.4 M KRW", colors.red, "Simple payback");
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 6.55,
      y: 4.85,
      w: 5.85,
      h: 0.95,
      rectRadius: 0.04,
      fill: { color: "EDF4F6" },
      line: { color: colors.cyan, pt: 0.8 },
    });
    slide.addText("Boundary note: these annual metrics compare the reference compressor power against the LNG loop pumping power only.", {
      x: 6.8,
      y: 5.09,
      w: 5.35,
      h: 0.34,
      fontFace: "Aptos",
      fontSize: 11,
      color: colors.charcoal,
    });
    addFooter(slide, "Sources: SRC-013, SRC-014, ASM-030 to ASM-032");
    finalizeSlide(slide);
  }

  // Slide 9
  {
    const slide = pptx.addSlide();
    addBackground(slide, colors.ink);
    addHeader(slide, "Recommendation", "CLOSING", colors.cream);
    addBulletBlock(slide, 0.85, 1.35, 4.0, "What we can say confidently", [
      "The LNG cold-energy concept is technically feasible at the 10 km design point.",
      "The base-case design is far better than the reference compressor benchmark in modeled power demand.",
      "The real story is the boundary between feasible transport and infeasible transport, not just a single best number.",
    ], "122A45");
    addBulletBlock(slide, 5.0, 1.35, 3.5, "Recommended message in the presentation", [
      "10 km works.",
      "35 km does not work at the base point.",
      "35 km can be recovered only by accepting a different operating trade-off.",
    ], "122A45");
    addBulletBlock(slide, 8.75, 1.35, 3.75, "Next refinement after this deck", [
      "Tighten the fluid-safety narrative for ammonia versus hydrocarbons.",
      "Add implementation risks and controls strategy.",
      "Convert the markdown report into the final submission format.",
    ], "122A45");
    addMetricCard(slide, 0.95, 5.55, 3.0, 1.02, "Base-case answer", "Use LNG cold energy", colors.green, "at 10 km");
    addMetricCard(slide, 4.2, 5.55, 3.0, 1.02, "Boundary insight", "29.6 km limit", colors.gold, "estimated one-way");
    addMetricCard(slide, 7.45, 5.55, 4.0, 1.02, "Decision posture", "Feasible, but distance-sensitive", colors.red, "not a universal win");
    addFooter(slide, "Generated with PptxGenJS source for editable follow-up");
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
