import React from "react";
import { Slide, Appear, Pill, Footnote, Narration, beat, C } from "./ui";
import { DATA } from "./data";

// Segment 6: each row appears as the voice reaches that idea.
const S = "seg6";
const ANCHORS = ["HyDE, where", "Fine-tuning the embedding model", "Switching to a better embedder", "And a score cutoff"];
export const FailedIdeas: React.FC = () => (
  <Slide title="What didn't work">
    <Narration seg={S} />
    <div style={{ marginTop: 16 }}>
      {DATA.failed.map((r, i) => (
        <Appear key={r.idea} at={beat(S, ANCHORS[i])} style={{ display: "flex", alignItems: "center", gap: 40, background: C.panel, borderRadius: 20, padding: "26px 36px", marginBottom: 22, border: `2px solid ${C.panelLine}` }}>
          <div style={{ width: 560, fontSize: 38, fontWeight: 700 }}>{r.idea}</div>
          <div style={{ flex: 1, fontSize: 30, color: C.muted, lineHeight: 1.3 }}>{r.result}</div>
          <Pill color={r.verdict === "HURT" ? C.red : C.amber}>{r.verdict}</Pill>
        </Appear>
      ))}
    </div>
    <Appear at={beat(S, "Components interact")} style={{ position: "absolute", left: 90, right: 90, bottom: 110, fontSize: 46, fontWeight: 700, color: C.teal }}>
      A win in isolation doesn{"’"}t predict a win in the system.
    </Appear>
    <Footnote>Same 19 in-scope questions for every test</Footnote>
  </Slide>
);
