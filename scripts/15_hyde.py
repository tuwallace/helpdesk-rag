"""Pre-retrieval comparison on the in-scope golden questions. All modes: grouped pool -> rerank on summary
-> NO cutoff (isolates retrieval from the cutoff). LLM modes are repeated REPS times (non-deterministic).
  raw        : question for dense, BM25 and rerank
  rewrite    : LLM keyword rewrite replaces the question everywhere (today's default)
  hyde-full  : HyDE title replaces the question everywhere (reranker then sees the fake title)
  hyde-dense : HyDE title -> extra DENSE query only; BM25 and the reranker still use the original question"""
import json, sys, statistics, collections
sys.path.insert(0, "src")
from rag.pre_retrieval import rewrite, hyde
from rag.retrieve import dense_grouped, sparse_grouped, rrf, hybrid_grouped
from rag.rerank import _model

K, POOL, REPS = 5, 20, 3
gold = [g for g in map(json.loads, open("eval/golden.jsonl")) if g["tier"] != "out_of_scope"]

def pool(mode, q):
    if mode == "raw": return hybrid_grouped(q, POOL), q
    if mode == "rewrite": r = rewrite(q); return hybrid_grouped(r, POOL), q
    if mode == "hyde-full": h = hyde(q); return hybrid_grouped(h, POOL), h
    if mode == "hyde-dense":
        h = hyde(q)
        return rrf([dense_grouped(h, POOL), dense_grouped(q, POOL), sparse_grouped(q, POOL)])[:POOL], q

def score(mode, g):
    cands, rq = pool(mode, g["question"])
    t = g["summary"]; pr = next((i + 1 for i, d in enumerate(cands) if d["summary"] == t), None)
    sc = _model().predict([(rq, d["summary"]) for d in cands])
    order = [d for _, d in sorted(zip(sc, cands), key=lambda x: -x[0])]
    rr = next((i + 1 for i, d in enumerate(order) if d["summary"] == t), None)
    return pr is not None, rr == 1, bool(rr and rr <= K)

res = {}
miss = collections.defaultdict(lambda: collections.Counter())
for mode in ("raw", "rewrite", "hyde-full", "hyde-dense"):
    runs = []
    for _ in range(1 if mode == "raw" else REPS):
        cnt = [0, 0, 0]
        for g in gold:
            p, t1, h5 = score(mode, g)
            cnt[0] += p; cnt[1] += t1; cnt[2] += h5
            if not h5: miss[mode][g["question"][:58]] += 1
        runs.append([c / len(gold) for c in cnt])
    res[mode] = runs
print(f"{'mode':12s} {'in-pool':>8s} {'top1':>6s} {'hit@5 mean':>11s} {'hit@5 min-max':>14s}   (n={len(gold)}, LLM modes x{REPS} runs)")
for mode, runs in res.items():
    cols = list(zip(*runs)); h = cols[2]
    print(f"{mode:12s} {statistics.mean(cols[0]):8.2f} {statistics.mean(cols[1]):6.2f} {statistics.mean(h):11.2f} {min(h):8.2f}-{max(h):.2f}")
for mode, c in miss.items():
    print(f"\nquestions missing hit@5 in {mode}  (count of runs):")
    for q, n in c.most_common(): print(f"   {n}x {q}")
print("\nsample hyde titles for the vocabulary-gap question:")
for _ in range(3): print("   ", hyde("the login approval prompts never show up since I got a new handset"))
