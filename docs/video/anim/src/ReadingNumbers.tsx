import React from "react";
import { Slide, Appear, Footnote, Narration, beat, C } from "./ui";
const S = "seg7";

// Segment 7 (90 s): four panels, then the rule.
const Panel: React.FC<{ at: number; title: string; children: React.ReactNode }> = ({ at, title, children }) => (
  <Appear at={at} style={{ background: C.panel, border: `2px solid ${C.panelLine}`, borderRadius: 22, padding: "28px 36px", width: 810, height: 340 }}>
    <div style={{ fontSize: 36, fontWeight: 700, marginBottom: 20 }}>{title}</div>
    {children}
  </Appear>
);
const SIGN = [["1 – 0", "nothing", C.muted], ["5 – 0", "borderline", C.amber], ["6 – 0", "likely real", C.teal], ["8 – 1", "likely real", C.teal], ["10 – 2", "likely real", C.teal]];

export const ReadingNumbers: React.FC = () => (
  <Slide title="How to tell if a number is any good">
    <Narration seg={S} />
    <div style={{ display: "flex", flexWrap: "wrap", gap: 30 }}>
      <Panel at={beat(S, "My first set of test questions")} title={"A too-easy test set: every score 1.00"}>
        <div style={{ fontSize: 110, fontWeight: 800, color: C.red }}>1.00</div>
        <div style={{ fontSize: 28, color: C.muted }}>Questions copied the ticket titles, so no system could look worse than another.</div>
      </Panel>
      <Panel at={beat(S, "One question is worth five points")} title={"One question = 5.3 points"}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, width: 660 }}>
          {Array.from({ length: 19 }).map((_, i) => <div key={i} style={{ width: 52, height: 52, borderRadius: 10, background: i === 0 ? C.red : C.teal, opacity: i === 0 ? 1 : 0.55 }} />)}
        </div>
        <div style={{ fontSize: 28, color: C.muted, marginTop: 18 }}>With 19 questions, 1 or 2 flips is noise.</div>
      </Panel>
      <Panel at={beat(S, "To be confident one system")} title={"Sign test: better – worse"}>
        {SIGN.map(([k, v, col]) => <div key={k as string} style={{ fontSize: 32, display: "flex", gap: 24 }}><span style={{ width: 130, fontWeight: 700 }}>{k}</span><span style={{ color: col as string }}>{v}</span></div>)}
      </Panel>
      <Panel at={beat(S, "And if you see nineteen out of nineteen")} title={"19 of 19 is not 100%"}>
        <div style={{ fontSize: 100, fontWeight: 800, color: C.amber }}>up to ~16%</div>
        <div style={{ fontSize: 28, color: C.muted }}>Rule of three: with 0 failures in n trials, the true failure rate can still be about 3 / n.</div>
      </Panel>
    </div>
    <Appear at={beat(S, "One more thing I have to be upfront")} style={{ position: "absolute", left: 90, right: 90, bottom: 100, fontSize: 40, fontWeight: 700, color: C.teal }}>
      Report n. Repeat LLM runs. Admit when you tuned on the test set.
    </Appear>
    <Footnote>Full guide: docs/reading-the-numbers.md</Footnote>
  </Slide>
);
