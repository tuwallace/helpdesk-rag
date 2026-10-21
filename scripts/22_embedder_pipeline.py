"""Test embedders in the REAL pipeline (grouped hybrid pool -> rerank on summary -> cutoff -> floor).
Variants: nomic (current) | bge (no prefix) | bge-instr (bge with its retrieval instruction prefix).
Everything except the dense query/doc embedder is identical. Also prints the yardsticks you need to JUDGE the numbers:
chance, BM25-only, 95% bootstrap CIs over questions, and paired wins/losses against the nomic baseline."""
import json, random, statistics, sys
import numpy as np
sys.path.insert(0, "src")
from qdrant_client import models
from rag import config as C
from rag.ingest import build_docs
from rag.embedders import bge
from rag.pre_retrieval import rewrite
from rag.retrieve import _q, hybrid_grouped, sparse_grouped
from rag.pipeline import retrieve_docs

REPS, K, FLOOR = 3, 5, C.ANSWER_FLOOR
allg = [json.loads(l) for l in open("eval/golden.jsonl")]
gold = [g for g in allg if g["tier"] != "out_of_scope"]
oos = [g for g in allg if g["tier"] == "out_of_scope"]

# ---- build the bge collection once (full ticket text, same payload as the nomic collection) ----
BGE_COLL = "tickets_bge"
if not _q.collection_exists(BGE_COLL):
    docs = build_docs()
    vecs = bge().encode([d["text"] for d in docs], normalize_embeddings=True, batch_size=64)
    _q.create_collection(BGE_COLL, vectors_config=models.VectorParams(size=vecs.shape[1], distance=models.Distance.COSINE))
    _q.create_payload_index(BGE_COLL, "summary", models.PayloadSchemaType.KEYWORD)
    _q.upsert(BGE_COLL, points=[models.PointStruct(id=d["id"], vector=v.tolist(), payload=d) for d, v in zip(docs, vecs)])
    print(f"built {BGE_COLL}: {len(docs)} points")

VARIANTS = {"nomic (current)": (C.COLLECTION, "nomic"), "bge": (BGE_COLL, "bge"), "bge-instr": (BGE_COLL, "bge-instr")}
rank_of = lambda docs, target: next((i + 1 for i, d in enumerate(docs) if d["summary"] == target), None)

# rewrites are generated ONCE per question and shared by all variants, so variants differ only in the embedder
rw = {g["question"]: [rewrite(g["question"]) for _ in range(REPS)] for g in gold + oos}

res = {}
for name, (coll, emb) in VARIANTS.items():
    C.COLLECTION, C.EMBEDDER = coll, emb
    r = dict(pool=[], first=[], raw=[], rw=[], top_raw=[], top_rw=[], oos_raw=[], oos_rw=[])
    for g in gold:
        t, q = g["summary"], g["question"]
        fr = rank_of(hybrid_grouped(q, 20), t); r["pool"].append(fr is not None); r["first"].append(fr)
        d = retrieve_docs(q, use_rewrite=False, top_n=K); r["raw"].append(rank_of(d, t))
        runs = [retrieve_docs(x, use_rewrite=False, top_n=K) for x in rw[q]]
        r["rw"].append([rank_of(d, t) for d in runs]); r["top_rw"].append([d[0]["rerank_score"] if d else 0.0 for d in runs])
    for g in oos:
        d = retrieve_docs(g["question"], use_rewrite=False, top_n=1); r["oos_raw"].append(d[0]["rerank_score"] if d else 0.0)
        r["oos_rw"].append([(lambda d: d[0]["rerank_score"] if d else 0.0)(retrieve_docs(x, use_rewrite=False, top_n=1)) for x in rw[g["question"]]])
    res[name] = r
C.COLLECTION, C.EMBEDDER = "tickets", "nomic"

# ---- yardsticks: chance and BM25-only (lexical) at summary level ----
n_sum = len({d["summary"] for d in build_docs()})
bm = [rank_of(sparse_grouped(g["question"], 56), g["summary"]) for g in gold]
hit = lambda ranks, k: np.array([(x is not None and x <= k) for x in ranks], dtype=float)
mrr = lambda ranks: np.array([1 / x if x else 0.0 for x in ranks])
random.seed(0)
def ci(v):
    b = [np.mean(random.choices(list(v), k=len(v))) for _ in range(2000)]
    return np.percentile(b, 2.5), np.percentile(b, 97.5)

print(f"\nn={len(gold)} in-scope questions, {len(oos)} out-of-scope; {n_sum} distinct summaries to choose from\n")
print("YARDSTICKS")
print(f"  chance (random guess)   top1={1/n_sum:.2f}  hit@{K}={K/n_sum:.2f}")
print(f"  BM25 only (no embedder) top1={hit(bm,1).mean():.2f}  hit@{K}={hit(bm,K).mean():.2f}\n")
print(f"{'variant':16s} {'in-pool':>7s} {'1st-stage':>10s} | final (raw question): {'top1':>5s} {'[95% CI]':>12s} {'hit@5':>6s} {'[95% CI]':>12s} {'MRR':>5s} | with rewrite (mean of {REPS}): {'top1':>5s} {'hit@5':>6s}")
for name, r in res.items():
    t1, h5 = hit(r["raw"], 1), hit(r["raw"], K)
    w1 = np.mean([hit([x[i] for x in r["rw"]], 1).mean() for i in range(REPS)]); w5 = np.mean([hit([x[i] for x in r["rw"]], K).mean() for i in range(REPS)])
    print(f"{name:16s} {np.mean(r['pool']):7.2f} {hit(r['first'],K).mean():10.2f} | "
          f"{'':23s}{t1.mean():5.2f} [{ci(t1)[0]:.2f},{ci(t1)[1]:.2f}] {h5.mean():6.2f} [{ci(h5)[0]:.2f},{ci(h5)[1]:.2f}] {mrr(r['raw']).mean():5.2f} | {'':27s}{w1:5.2f} {w5:6.2f}")

print(f"\nPAIRED vs nomic (same questions): questions where the variant is better / worse / same")
base = res["nomic (current)"]
for name, r in res.items():
    if name == "nomic (current)": continue
    for label, k in (("top1", 1), ("hit@5", K)):
        a, b = hit(r["raw"], k), hit(base["raw"], k)
        print(f"  {name:10s} {label:6s} better={int((a>b).sum())}  worse={int((a<b).sum())}  same={int((a==b).sum())}")

print(f"\nANSWERABILITY at floor {FLOOR} (best rerank score; rewrite mode, mean of {REPS} runs)")
for name, r in res.items():
    ans = np.mean([np.mean([x[i] >= FLOOR for x in r["top_rw"]]) for i in range(REPS)])
    rej = np.mean([np.mean([x[i] < FLOOR for x in r["oos_rw"]]) for i in range(REPS)])
    print(f"  {name:16s} in-scope answered={ans:.0%}   out-of-scope rejected={rej:.0%}")

print("\nPER-QUESTION final rank (raw question; '-' = target not in top 5 after cutoff)  nomic | bge | bge-instr")
for i, g in enumerate(gold):
    row = [res[v]["raw"][i] for v in VARIANTS]
    if len({str(x) for x in row}) > 1 or any(x is None for x in row):
        print("  " + " | ".join(f"{(x if x else '-')!s:>2s}" for x in row) + f"   {g['question'][:62]}")
