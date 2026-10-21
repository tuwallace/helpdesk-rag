// Every number here is from this project's own runs (see ../../script.md, Appendix A).
// 19 in-scope and 7 out-of-scope golden questions; tuned on the same questions.
export const DATA = {
  poolRecall: { ticketTop20: 0.74, grouped: 0.95 },
  hitAt5: { firstStage: 0.79, rerankFull: 0.89, rerankSummary: 0.95 },
  failed: [
    { idea: "HyDE (search with a made-up answer)", result: "Replacing the query: hit@5 fell to 0.77. As an extra query: no change.", verdict: "NO GAIN" },
    { idea: "Fine-tune the embedder", result: "252 pairs, 13 s of training. Held-out top1 0.79 vs 0.84 for the untouched model.", verdict: "NO GAIN" },
    { idea: "A better embedder (bge vs nomic)", result: "Alone: top1 0.53 → 0.84. In the full pipeline: 0.79 for both.", verdict: "NO GAIN" },
    { idea: "Strict score cutoff (0.25)", result: "Silently dropped about 3 of 19 correct results with query rewriting.", verdict: "HURT" },
  ],
};
