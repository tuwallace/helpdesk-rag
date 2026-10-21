import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT, Narration, beat } from "./ui";
import { Ev, Replay, ReplayLabel, TerminalScene, Window } from "./Terminal";
import cap from "./captures.json";

// Live segments as terminal replays of REAL captured output (docs/video/demo/*), timed to the narration with beat().
const typeEnd = (at: number, text: string, cps: number) => at + text.length / cps;

export const Seg3: React.FC = () => {
  const S = "seg3", go = beat(S, "A thousand tickets");
  const ev: Ev[] = [
    { kind: "type", at: 0.2, text: "python docs/video/demo/seg3_data.py", cps: 40 },
    { kind: "print", at: go, text: cap.seg3, reveal: 0.8 },
    { kind: "hl", at: go, until: beat(S, "Each one is repeated"), match: ["tickets  ", "distinct problems"] },
    { kind: "hl", at: beat(S, "Each one is repeated"), until: beat(S, "The comments are even worse"), match: ["tickets per problem"] },
    { kind: "hl", at: beat(S, "The comments are even worse"), until: beat(S, "And there is no real resolution"), match: ["comments  ", "distinct comment sentences", "most repeated"] },
    { kind: "hl", at: beat(S, "And there is no real resolution"), until: beat(S, "It's a ticket search"), match: ["Found stale token", "Issue now limited", "Closing after three"] },
  ];
  return <TerminalScene seg={S} events={ev} />;
};

export const Seg4: React.FC = () => {
  const S = "seg4", go = beat(S, "I searched for");
  const ev: Ev[] = [
    { kind: "type", at: 0.1, text: "python docs/video/demo/seg4_printer.py", cps: 45 },
    { kind: "print", at: go + 0.3, text: cap.seg4, reveal: 1.6 },
    { kind: "hl", at: beat(S, "Every single result"), until: beat(S, "But the data has three"), match: ["Label printer feeds blank stock", "distinct problems in these"] },
    { kind: "hl", at: beat(S, "But the data has three"), until: beat(S, "The biggest cluster"), match: ["tickets  Label printer", "tickets  Printer on dock", "tickets  New Zebra", "printer problems that actually exist"] },
    { kind: "hl", at: beat(S, "The biggest cluster"), until: beat(S, "Averages would have hidden"), match: ["23 tickets"] },
  ];
  return <TerminalScene seg={S} events={ev} />;
};

export const Seg8: React.FC = () => {
  const S = "seg8", [q1, q2, q3] = cap.seg8;
  const block = (r: { answer: string; sources: number[]; refused: string | null; seconds: number }) =>
    `\n  ${r.answer}\n  sources=[${r.sources.join(", ")}]  refused=${r.refused ?? "None"}  [${r.seconds.toFixed(2)}s]\n`;
  const t1 = beat(S, "Below it, the system"), t2 = beat(S, "The cost: it also wrongly"), t3 = beat(S, "That's a trade-off");
  const e1 = beat(S, "It says there's no match"), e2 = typeEnd(t2, q2.question, 55) + 0.5, e3 = typeEnd(t3, q3.question, 45) + 0.5;
  const repl = "warming up (loading models)...\nready. Type a question.\n";
  const ev: Ev[] = [
    { kind: "print", at: 0.1, text: repl }, { kind: "type", at: 1.2, text: "", prompt: "question> " },
    { kind: "clear", at: beat(S, "So I added a floor") },
    { kind: "type", at: beat(S, "So I added a floor") + 0.2, text: "grep -n ANSWER_FLOOR src/rag/config.py", cps: 40 },
    { kind: "print", at: beat(S, "So I added a floor") + 1.4, text: cap.grep_floor },
    { kind: "clear", at: t1 - 0.2 }, { kind: "print", at: t1 - 0.2, text: repl },
    { kind: "type", at: t1, text: q1.question, cps: 45, prompt: "question> " },
    { kind: "print", at: e1, text: block({ ...q1, answer: q1.answer }) },
    { kind: "hl", at: e1, until: t2, match: ["refused=below_floor"] },
    { kind: "type", at: t2, text: q2.question, cps: 55, prompt: "question> " },
    { kind: "print", at: e2, text: block(q2) },
    { kind: "hl", at: e2, until: t3, match: ["refused=below_floor"] },
    { kind: "type", at: t3, text: q3.question, cps: 45, prompt: "question> " },
    { kind: "print", at: e3 + q3.seconds, text: block(q3) },
  ];
  return <TerminalScene seg={S} events={ev} title="helpdesk-rag: demo REPL" />;
};

export const Seg9: React.FC = () => {
  const S = "seg9", f = useCurrentFrame(), { fps } = useVideoConfig(), t = f / fps;
  const toPhoenix = beat(S, "So if you want this faster");
  const p = interpolate(t, [toPhoenix, toPhoenix + 0.8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const zoom = interpolate(t, [toPhoenix, toPhoenix + 14], [1, 1.06], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const ev: Ev[] = [
    { kind: "type", at: 0.2, text: "python scripts/18_trace_demo.py", cps: 40 },
    { kind: "print", at: 1.4, text: "(the real run took about 16 s; the wait is trimmed here)", color: "#8b95a8" },
    { kind: "print", at: 3.0, text: cap.seg9, reveal: 2.2 },
    { kind: "hl", at: beat(S, "In a warm run"), until: beat(S, "The query rewrite"), match: ["generate"] },
    { kind: "hl", at: beat(S, "The query rewrite"), until: beat(S, "The first run after"), match: ["pre.rewrite"] },
    { kind: "hl", at: beat(S, "The first run after"), until: toPhoenix, match: ["trace: 'outlok"] },
  ];
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Narration seg={S} />
      <div style={{ opacity: 1 - p }}><Window><Replay events={ev} /></Window><ReplayLabel /></div>
      <AbsoluteFill style={{ opacity: p }}>
        <Img src={staticFile("captures/phoenix_trace.png")} style={{ width: 1920, height: 1080, transform: `scale(${zoom})`, transformOrigin: "35% 30%" }} />
        <div style={{ position: "absolute", left: 90, bottom: 26, fontFamily: FONT, fontSize: 22, color: "#c9d1e0", background: "rgba(14,19,32,.85)", padding: "6px 14px", borderRadius: 8 }}>
          Arize Phoenix: real screenshot of the cold-start trace for the first question
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// Segment 10: a replay of the REAL ollmcp session (captured through a pseudo-terminal; spinners and in-place redraws resolved by a terminal emulator).
export const Seg10: React.FC = () => {
  const S = "seg10", o = cap.ollmcp as { lines: string[]; marks: Record<string, number>; seconds: Record<string, number>; prompts: string[] };
  const L = o.lines, m = o.marks;
  const box = (title: string) => { const i = L.findIndex((l) => l.includes(title)); return i < 0 ? "" : L.slice(i, i + 3).join("\n"); };
  const panels = [box("Available Tools"), L.slice(L.findIndex((l) => l.includes("Current model")) - 1, L.findIndex((l) => l.includes("Current model")) + 3).join("\n")].join("\n");
  const answerOf = (a: number, b: number) => L.slice(a + 1, b).filter((l, i, arr) => !(i === arr.length - 1 && /\u276f/.test(l)) && !l.startsWith("Loading weights")).join("\n").replace(/\n{3,}/g, "\n\n").trim();
  const out1 = answerOf(m.p1_start, m.p2_start), out2 = answerOf(m.p2_start, m.end);
  const t1 = beat(S, "In my tests it used the tool"), t2 = beat(S, "But the first test found"), tg = beat(S, "The reason: the model was filling"), ts = beat(S, "If you build tools");
  const P = "qwen3/1-tool\u276f ";
  const ev: Ev[] = [
    { kind: "print", at: 0.3, text: panels, reveal: 0.8 },
    { kind: "clear", at: t1 - 0.3 }, { kind: "print", at: t1 - 0.3, text: panels },
    { kind: "type", at: t1, text: o.prompts[0], cps: 38, prompt: P },
    { kind: "print", at: t1 + 2.0, text: `(real run: about ${Math.round(o.seconds.p1)} s of thinking and tool calls; the wait is trimmed)`, color: "#8b95a8" },
    { kind: "print", at: t1 + 3.0, text: out1, reveal: 5.0 },
    { kind: "hl", at: t1 + 3.0, until: t2, match: ['"query"', '"top_n"', "Executing Tool"] },
    { kind: "type", at: t2 - 1.0, text: o.prompts[1], cps: 30, prompt: P },
    { kind: "print", at: t2 + 0.2, text: out2, reveal: 0.6 },
    { kind: "hl", at: t2 + 0.2, until: tg - 0.5, match: ["391"] },
    { kind: "clear", at: tg - 0.4 },
    { kind: "type", at: tg, text: 'grep -n -B1 -A1 "No optional filters" src/rag/mcp_server.py', cps: 40 },
    { kind: "print", at: tg + 1.6, text: cap.grep_priority },
    { kind: "hl", at: tg + 1.6, until: ts - 0.5, match: ["No optional filters"] },
    { kind: "clear", at: ts - 0.4 },
    { kind: "type", at: ts, text: "sed -n 9,17p src/rag/mcp_server.py", cps: 30 },
    { kind: "print", at: ts + 1.4, text: cap.sed_tool },
    { kind: "hl", at: ts + 1.4, until: ts + 30, match: ["def search_tickets"] },
  ];
  return <TerminalScene seg={S} events={ev} title="ollmcp -j mcp.json -m qwen3:8b" label="Terminal replay of a real ollmcp session (spinners and one progress-bar line trimmed; not a live screen recording)" />;
};
