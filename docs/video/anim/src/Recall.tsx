import React from "react";
import { Slide, Appear, Bar, Footnote, Narration, beat, C } from "./ui";
import { DATA } from "./data";

// Segment 5: each bar grows as its number is spoken.
const S = "seg5";
export const Recall: React.FC = () => (
  <Slide title="The fix: retrieve problems, not tickets">
    <Narration seg={S} />
    <div style={{ display: "flex", gap: 90, marginTop: 10 }}>
      <div>
        <Appear at={beat(S, "The chance that the right problem")}><div style={{ fontSize: 34, marginBottom: 20 }}>Right problem is in the candidate pool</div></Appear>
        <div style={{ display: "flex", gap: 30 }}>
          <Bar label={"Top 20 tickets"} value={DATA.poolRecall.ticketTop20} color={C.red} at={beat(S, "seventy-four")} />
          <Bar label={"Top 20 distinct summaries"} value={DATA.poolRecall.grouped} color={C.teal} at={beat(S, "ninety-five percent")} />
        </div>
      </div>
      <div>
        <Appear at={beat(S, "Then a cross-encoder reranker")}><div style={{ fontSize: 34, marginBottom: 20 }}>Right problem is in the final top 5</div></Appear>
        <div style={{ display: "flex", gap: 30 }}>
          <Bar label={"Hybrid search only"} value={DATA.hitAt5.firstStage} color={C.blue} at={beat(S, "Then a cross-encoder reranker") + 1.2} />
          <Bar label={"+ rerank on full ticket text"} value={DATA.hitAt5.rerankFull} color={C.amber} at={beat(S, "reranking on the full ticket text")} />
          <Bar label={"+ rerank on the summary"} value={DATA.hitAt5.rerankSummary} color={C.teal} at={beat(S, "reranking on the short summary")} />
        </div>
      </div>
    </div>
    <Appear at={beat(S, "The real lesson")} style={{ position: "absolute", left: 90, right: 90, bottom: 110, fontSize: 46, fontWeight: 700, color: C.teal }}>
      Retrieval can{"’"}t recover what it never fetched. Measure every stage.
    </Appear>
    <Footnote>n = 19 in-scope questions {"·"} tuned on the same set</Footnote>
  </Slide>
);
