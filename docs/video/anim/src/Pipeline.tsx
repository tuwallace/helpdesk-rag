import React from "react";
import { Slide, Appear, Narration, beat, C } from "./ui";

// Segment 2: the stack chips appear as each tool is named; the pipeline boxes appear as the final sentence walks the path.
const S = "seg2";
const CHIPS: [string, string][] = [
  ["All local · M2 MacBook Pro", "Everything is local"], ["Ollama: qwen3:8b + nomic-embed-text", "Ollama runs the models"],
  ["Qdrant (vector DB)", "Qdrant is the vector database"], ["bge-reranker-base", "A cross-encoder reranks results"],
  ["Arize Phoenix (tracing)", "Phoenix traces every step"], ["ollmcp + FastMCP", "ollmcp lets a local model"],
  ["1,000 synthetic tickets", "a thousand tickets"],
];
const STEPS: [string, string, string][] = [
  ["Question", "plain words from an employee", "Here is the path a question takes"],
  ["Rewrite", "LLM turns it into a search query", "It gets rewritten"],
  ["Hybrid search", "dense embeddings + BM25, fused", "searched two ways at once"],
  ["Grouped pool", "20 distinct problems, not 20 tickets", "grouped into distinct problems"],
  ["Rerank", "cross-encoder reads question + summary", "reranked"],
  ["Cutoff & floor", "drop weak hits; say “no match”", "filtered"],
  ["Generate", "answer only from the tickets, with citations", "handed to the model"],
];
export const Pipeline: React.FC = () => (
  <Slide title="A help-desk assistant that searches past tickets">
    <Narration seg={S} />
    <div style={{ display: "flex", gap: 16, flexWrap: "wrap", minHeight: 150 }}>
      {CHIPS.map(([label, phrase]) => (
        <Appear key={label} at={beat(S, phrase)}><span style={{ display: "inline-block", background: C.panel, border: `2px solid ${C.panelLine}`, borderRadius: 40, padding: "12px 26px", fontSize: 30 }}>{label}</span></Appear>
      ))}
    </div>
    <div style={{ display: "flex", alignItems: "flex-start", gap: 22, marginTop: 90 }}>
      {STEPS.map(([t, d, phrase], i) => (
        <React.Fragment key={t}>
          <Appear at={beat(S, phrase)} style={{ width: 215 }}>
            <div style={{ background: C.panel, border: `2px solid ${i === 3 ? C.teal : C.panelLine}`, borderRadius: 18, padding: "26px 16px", textAlign: "center", fontSize: 34, fontWeight: 700, minHeight: 100, display: "flex", alignItems: "center", justifyContent: "center" }}>{t}</div>
            <div style={{ fontSize: 24, color: C.muted, textAlign: "center", marginTop: 16, lineHeight: 1.3 }}>{d}</div>
          </Appear>
          {i < STEPS.length - 1 && <Appear at={beat(S, STEPS[i + 1][2]) - 0.1} style={{ fontSize: 44, color: C.muted, marginTop: 28 }}>{"→"}</Appear>}
        </React.Fragment>
      ))}
    </div>
  </Slide>
);
