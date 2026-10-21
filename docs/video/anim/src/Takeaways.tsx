import React from "react";
import { Slide, Appear, Narration, beat, C } from "./ui";
const S = "seg11";
const ANCHORS = ["One: read", "Two: measure", "Three: test", "Four: report", "And five: decide"];

// Segment 11 (45 s): five takeaways, one every ~7 s.
const POINTS = [
  "Read your data before you pick techniques.",
  "Measure every stage: the pool limits everything after it.",
  "Test components in the full system, not alone.",
  "Report your sample size. Be honest about tuning.",
  "Decide up front: what costs more, a wrong answer or a refusal?",
];
export const Takeaways: React.FC = () => (
  <Slide title="Five takeaways">
    <Narration seg={S} />
    <div style={{ marginTop: 26 }}>
      {POINTS.map((p, i) => (
        <Appear key={p} at={beat(S, ANCHORS[i])} style={{ display: "flex", alignItems: "center", gap: 30, fontSize: 48, margin: "26px 0" }}>
          <span style={{ width: 70, height: 70, borderRadius: 35, background: C.teal, color: C.bg, fontWeight: 800, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 40 }}>{i + 1}</span>
          {p}
        </Appear>
      ))}
    </div>
  </Slide>
);
