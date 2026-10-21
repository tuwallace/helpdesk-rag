"""Two experiments sharing one scoring pass (grouped pool -> cross-encoder on summary, as in the pipeline).
 EXP 1  relative cutoff sweep: keep results scoring >= REL x best score. hit@5 and mean #results kept.
 EXP 2  absolute answerability floor: can the BEST rerank score separate out-of-scope from in-scope questions?
Modes: raw question, and rewrite (3 runs; LLM output varies)."""
import json, sys, statistics
sys.path.insert(0, "src")
from rag.pre_retrieval import rewrite
from rag.retrieve import hybrid_grouped
from rag.rerank import _model

K, REPS = 5, 3
allg = [json.loads(l) for l in open("eval/golden.jsonl")]
gold = [g for g in allg if g["tier"] != "out_of_scope"]
oos = [g for g in allg if g["tier"] == "out_of_scope"]

def scored(mode, q):
    """-> list of (rerank_score, summary) sorted desc; the reranker sees the query the pipeline would use."""
    rq = rewrite(q) if mode == "rewrite" else q
    cands = hybrid_grouped(rq, 20)
    sc = _model().predict([(rq, d["summary"]) for d in cands])
    return sorted(((float(s), d["summary"]) for s, d in zip(sc, cands)), reverse=True)

def hit(lst, rel, target):
    top = lst[0][0]
    kept = [(s, t) for s, t in lst if s >= rel * top][:K]
    return any(t == target for _, t in kept), len(kept)

RELS = [0.0, 0.05, 0.10, 0.25]
runs = {"raw": 1, "rewrite": REPS}
cache = {m: [[(g, scored(m, g["question"])) for g in gold] for _ in range(n)] for m, n in runs.items()}
ocache = {m: [[(g, scored(m, g["question"])) for g in oos] for _ in range(n)] for m, n in runs.items()}

print("EXP 1 - relative cutoff sweep (hit@5 | mean results kept)   n=%d" % len(gold))
print(f"{'rel':>6s} " + "  ".join(f"{m:>16s}" for m in runs))
for rel in RELS:
    row = []
    for m in runs:
        hs, ks = [], []
        for rep in cache[m]:
            r = [hit(lst, rel, g["summary"]) for g, lst in rep]
            hs.append(sum(h for h, _ in r) / len(r)); ks.append(statistics.mean(k for _, k in r))
        row.append(f"{statistics.mean(hs):.2f} | {statistics.mean(ks):.1f}")
    print(f"{rel:6.2f} " + "  ".join(f"{x:>16s}" for x in row))

print("\nEXP 2 - best rerank score as an answerability signal")
for m in runs:
    ins = [lst[0][0] for rep in cache[m] for _, lst in rep]
    outs = [(lst[0][0], g["question"][:52]) for rep in ocache[m] for g, lst in rep]
    pairs = [(i > o) + 0.5 * (i == o) for i in ins for o, _ in outs]
    print(f"\n[{m}] in-scope top score: min={min(ins):.3f} p10={sorted(ins)[len(ins)//10]:.3f} "
          f"median={statistics.median(ins):.3f}   AUC(in > out)={statistics.mean(pairs):.2f}")
    seen = {}
    for s, q in outs: seen.setdefault(q, []).append(s)
    for q, ss in sorted(seen.items(), key=lambda x: -max(x[1])):
        print(f"    out-of-scope  best={max(ss):.3f}  mean={statistics.mean(ss):.3f}   {q}")
    print("    floor   in-scope answered   out-of-scope rejected")
    for fl in (0.01, 0.02, 0.05, 0.1, 0.2, 0.3):
        a = statistics.mean(s >= fl for s in ins); r = statistics.mean(o < fl for o, _ in outs)
        print(f"    {fl:5.2f}   {a:15.0%}   {r:20.0%}")
