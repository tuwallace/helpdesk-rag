import React from "react";
import { Slide, Appear, Footnote, Narration, beat, C } from "./ui";

// Segment 1: every step is anchored to the phrase being spoken (see ui.tsx `beat`).
const S = "seg1";
const ITEMS: [string, string, string][] = [
  ["HyDE", beat(S, "HyDE") + "", "— no gain"], ["Fine-tuning", beat(S, "fine-tuning") + "", "— no gain"],
  ["A better embedder", beat(S, "a better embedding model") + "", "— no gain"], ["A tool-definition bug", beat(S, "one tiny bug") + "", "— cost ~60%"],
];
export const Hook: React.FC = () => (
  <Slide>
    <Narration seg={S} />
    <div style={{ marginTop: 60 }}>
      <Appear at={beat(S, "I built")} dur={1}><div style={{ fontSize: 96, fontWeight: 800, letterSpacing: -2 }}>I built a local RAG.</div></Appear>
      <Appear at={beat(S, "But the interesting part")} dur={1}><div style={{ fontSize: 96, fontWeight: 800, letterSpacing: -2, marginTop: 6 }}>Most of my best ideas <span style={{ color: C.red }}>failed</span>.</div></Appear>
    </div>
    <div style={{ display: "flex", gap: 70, marginTop: 70 }}>
      <Appear at={beat(S, "ninety-five percent")} style={{ flex: 1, background: C.panel, borderRadius: 24, padding: 44, border: `2px solid ${C.teal}` }}>
        <div style={{ fontSize: 120, fontWeight: 800, color: C.teal, lineHeight: 1 }}>0.95</div>
        <div style={{ fontSize: 34, color: C.muted, marginTop: 14 }}>hit@5: the right problem is in the top 5</div>
      </Appear>
      <div style={{ flex: 1.3, background: C.panel, borderRadius: 24, padding: "36px 44px", border: `2px solid ${C.red}`, minHeight: 330 }}>
        {ITEMS.map(([t, at, note]) => (
          <Appear key={t} at={Number(at)} style={{ fontSize: 44, margin: "12px 0" }}>
            <span style={{ color: C.red, fontWeight: 800 }}>{"✗"}</span> {t} <span style={{ color: C.muted }}>{note}</span>
          </Appear>
        ))}
      </div>
    </div>
    <Footnote>19 in-scope questions {"·"} tuned on the same set {"·"} synthetic data</Footnote>
  </Slide>
);
