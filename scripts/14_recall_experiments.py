"""Recall experiments on the in-scope golden questions (raw question, no rewrite => deterministic).
 V0 baseline : top-20 TICKETS, then dedupe by summary          (what the pipeline does today)
 V1 grouped  : top-20 DISTINCT SUMMARIES via Qdrant group_by    (pool can't be monopolised by a cluster)
 V2 grouped+clean : V1, but dense+BM25 index only the summary (random category/comment text stays in payload)
Each variant is reranked on full text and on summary-only. Metric: summary-level rank of the target."""
import copy, json, sys
sys.path.insert(0, "src")
from qdrant_client import QdrantClient, models
from rag import config as C
from rag.ingest import build_docs, embed
from rag.retrieve import tok, rrf, hybrid
from rag.rerank import _model
from rag.post_retrieval import dedupe
from rank_bm25 import BM25Okapi

K, POOL = 5, 20
q = QdrantClient(url=C.QDRANT_URL)
docs = build_docs()
gold = [g for g in map(json.loads, open("eval/golden.jsonl")) if g["tier"] != "out_of_scope"]

# ---- build the "clean" collection: one embedding per unique summary, reused for every ticket ----
CORE = "tickets_core"
if not q.collection_exists(CORE):
    sums = sorted({d["summary"] for d in docs})
    vec = dict(zip(sums, embed(sums)))
    q.create_collection(CORE, vectors_config=models.VectorParams(size=len(vec[sums[0]]), distance=models.Distance.COSINE))
    q.upsert(CORE, points=[models.PointStruct(id=d["id"], vector=vec[d["summary"]], payload=d) for d in docs])
for coll in (C.COLLECTION, CORE):
    q.create_payload_index(coll, "summary", models.PayloadSchemaType.KEYWORD)

full_bm = BM25Okapi([tok(d["text"]) for d in docs])
sums = sorted({d["summary"] for d in docs})
by_sum = {}
for d in docs: by_sum.setdefault(d["summary"], d)
core_bm = BM25Okapi([tok(s) for s in sums])

def grouped_dense(query, coll):
    r = q.query_points_groups(coll, query=embed([query], "search_query: ")[0], group_by="summary",
                              limit=POOL, group_size=1, with_payload=True)
    return [dict(g.hits[0].payload) for g in r.groups]

def distinct_bm25_full(query):
    sc = full_bm.get_scores(tok(query)); seen, out = set(), []
    for i in sorted(range(len(docs)), key=lambda i: -sc[i]):
        if docs[i]["summary"] not in seen:
            seen.add(docs[i]["summary"]); out.append(dict(docs[i]))
        if len(out) == POOL: break
    return out

def bm25_core(query):
    sc = core_bm.get_scores(tok(query))
    return [dict(by_sum[sums[i]]) for i in sorted(range(len(sums)), key=lambda i: -sc[i])[:POOL]]

def pool_v0(query): return dedupe(hybrid(query, POOL))
def pool_v1(query): return rrf([grouped_dense(query, C.COLLECTION), distinct_bm25_full(query)])[:POOL]
def pool_v2(query): return rrf([grouped_dense(query, CORE), bm25_core(query)])[:POOL]

def rerank_scores(query, cands, field):
    ce = _model()
    texts = [d["summary"] if field == "summary" else d["text"] for d in cands]
    return ce.predict([(query, t) for t in texts])

def rank_of(cands, target):
    return next((i + 1 for i, d in enumerate(cands) if d["summary"] == target), None)

VARIANTS = {"V0 baseline (20 tickets)": pool_v0, "V1 grouped pool": pool_v1, "V2 grouped + clean text": pool_v2}
print(f"{'variant':26s} {'in-pool':>8s} {'1st top1':>9s} {'1st hit@5':>10s} {'rr(full) hit@5':>15s} {'rr(summary) hit@5':>18s}")
misses = {}
for name, fn in VARIANTS.items():
    c = dict(pool=0, f1=0, f5=0, rf=0, rs=0); miss = []
    for g in gold:
        cands = fn(g["question"]); t = g["summary"]
        r = rank_of(cands, t)
        c["pool"] += r is not None; c["f1"] += r == 1; c["f5"] += bool(r and r <= K)
        for field, key in (("text", "rf"), ("summary", "rs")):
            sc = rerank_scores(g["question"], cands, field)
            order = [d for _, d in sorted(zip(sc, cands), key=lambda x: -x[0])]
            rr = rank_of(order, t); c[key] += bool(rr and rr <= K)
        if r is None: miss.append(g["question"][:60])
    n = len(gold); misses[name] = miss
    print(f"{name:26s} {c['pool']/n:8.2f} {c['f1']/n:9.2f} {c['f5']/n:10.2f} {c['rf']/n:15.2f} {c['rs']/n:18.2f}")
print(f"\nn={n} in-scope questions; in-pool = target summary among the {POOL} candidates")
for name, m in misses.items():
    print(f"\nnot in pool, {name}: {len(m)}"); [print("   -", x) for x in m]
