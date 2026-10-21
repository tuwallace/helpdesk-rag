import React from "react";
import { AbsoluteFill } from "remotion";
import { C, FONT } from "./ui";

// 1280x720 YouTube thumbnail: big claim, big number, three crossed-out ideas.
export const Thumbnail: React.FC = () => (
  <AbsoluteFill style={{ background: `linear-gradient(135deg, ${C.bg} 0%, #1a2340 100%)`, fontFamily: FONT, color: C.text, padding: "56px 64px" }}>
    <div style={{ fontSize: 92, fontWeight: 800, letterSpacing: -2, lineHeight: 1.02 }}>I built a local RAG.</div>
    <div style={{ fontSize: 92, fontWeight: 800, letterSpacing: -2, lineHeight: 1.02, color: C.red }}>Most ideas failed.</div>
    <div style={{ display: "flex", alignItems: "center", gap: 48, marginTop: 52 }}>
      <div style={{ background: C.panel, border: `4px solid ${C.teal}`, borderRadius: 28, padding: "10px 40px", textAlign: "center" }}>
        <div style={{ fontSize: 150, fontWeight: 800, color: C.teal, lineHeight: 1 }}>95%</div>
        <div style={{ fontSize: 28, color: C.muted, marginTop: -2 }}>right problem in the top 5</div>
      </div>
      <div style={{ fontSize: 50, fontWeight: 700, lineHeight: 1.3 }}>
        {["HyDE", "Fine-tuning", "Better embeddings"].map((t) => (
          <div key={t}><span style={{ color: C.red, fontWeight: 800 }}>{"✗"}</span> <span style={{ textDecoration: `line-through ${C.red} 4px` }}>{t}</span></div>
        ))}
      </div>
    </div>
    <div style={{ position: "absolute", left: 64, bottom: 34, fontSize: 28, color: C.muted }}>Ollama {"·"} Qdrant {"·"} reranking {"·"} MCP {"·"} all local</div>
  </AbsoluteFill>
);
