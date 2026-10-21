"""Retrieval metrics per tier + ablations, and an optional LLM-judge for faithfulness.
Results are de-duplicated by summary, so each golden question has exactly ONE relevant summary:
  top1 = relevant summary ranked first; hit@K = within top K; MRR; nDCG@K (single relevant item)."""
import json, math, sys, collections, ollama
sys.path.insert(0, "src")
from rag import config as C
from rag.pipeline import retrieve_docs, answer

all_gold = [json.loads(l) for l in open("eval/golden.jsonl")]
gold = [g for g in all_gold if g["tier"] != "out_of_scope"]      # ranking metrics need a relevant answer
oos = [g for g in all_gold if g["tier"] == "out_of_scope"]
CONFIGS = {
    "baseline (hybrid)":    dict(use_rewrite=False, use_rerank=False),
    "+ rewrite":            dict(use_rewrite=True,  use_rerank=False),
    "+ rerank":             dict(use_rewrite=False, use_rerank=True),
    "+ rewrite + rerank":   dict(use_rewrite=True,  use_rerank=True),
}
K = 5
for name, kw in CONFIGS.items():
    agg = collections.defaultdict(lambda: collections.Counter())
    for g in gold:
        ids = [d["id"] for d in retrieve_docs(g["question"], top_n=K, **kw)]
        rel = set(g["relevant_ids"])
        rank = next((i + 1 for i, x in enumerate(ids) if x in rel), None)
        for t in (g["tier"], "ALL"):
            a = agg[t]; a["n"] += 1
            a["top1"] += rank == 1; a["hit"] += rank is not None
            a["mrr"] += 1 / rank if rank else 0
            a["ndcg"] += 1 / math.log2(rank + 1) if rank else 0
    print(f"\n{name}")
    for t in ("paraphrase", "hard", "ALL"):
        a = agg[t]; n = a["n"]
        print(f"  {t:11s} n={n:2d}  top1={a['top1']/n:.2f}  hit@{K}={a['hit']/n:.2f}  MRR={a['mrr']/n:.2f}  nDCG@{K}={a['ndcg']/n:.2f}")

# ---- out-of-scope: can a score tell "no matching ticket" apart from a real match? ----
# Measured, not assumed: we compare the best cosine score of in-scope vs out-of-scope questions.
if oos:
    import statistics
    from rag.retrieve import dense
    top = lambda q: dense(q, 1)[0]["dense_score"]
    ins = sorted(top(g["question"]) for g in gold)
    outs = [(top(g["question"]), g["question"]) for g in oos]
    print(f"\nOUT-OF-SCOPE ({len(oos)} questions) - top dense cosine score of the best match")
    print(f"  in-scope  n={len(ins)}  min={ins[0]:.3f}  median={statistics.median(ins):.3f}  max={ins[-1]:.3f}")
    for sc, q in sorted(outs):
        print(f"  out-scope {sc:.3f}  {q[:70]}")
    best = max(((sum(i >= t for i in ins) / len(ins) + sum(o < t for o, _ in outs) / len(outs)) / 2, t)
               for t in [x / 1000 for x in range(300, 1000)])
    print(f"  best single threshold: {best[1]:.3f} -> balanced accuracy {best[0]:.2f} "
          f"(fit on these {len(ins) + len(outs)} questions: optimistic, and meaningless with few OOS questions)")

if "--judge" in sys.argv:   # generation quality: faithfulness via LLM judge
    ok = 0
    sample = gold[:20]
    for g in sample:
        r = answer(g["question"])
        v = ollama.chat(model=C.GEN_MODEL, think=False, format="json", messages=[{"role": "user", "content":
            f'Question: {g["question"]}\nAnswer: {r["answer"]}\nIs the answer grounded in cited tickets (tickets contain no fix steps, so any invented fix is unfaithful) '
            f'and non-hallucinated? Reply JSON {{"faithful": true|false, "reason": "..."}}'}])
        ok += json.loads(v["message"]["content"]).get("faithful", False)
    print(f"\nfaithfulness (judge) = {ok/len(sample):.2f}")
