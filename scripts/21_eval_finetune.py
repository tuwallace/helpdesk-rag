"""Embedding-only comparison (no BM25, no reranker) at summary level, on the in-scope golden questions:
  nomic-embed-text (current index, vectors read from Qdrant) | bge-small base | bge-small fine-tuned.
Queries get NO instruction prefix for the bge models (same as in training) so base vs fine-tuned is like-for-like.
Sanity check: the fine-tuned model should improve on questions like the TRAINING pairs (held-in); the real
test is the golden questions, whose summaries were never seen in training."""
import json, sys, numpy as np
sys.path.insert(0, "src")
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from rag import config as C
from rag.ingest import build_docs, embed

docs = build_docs(); ids = [d["id"] for d in docs]; sums = np.array([d["summary"] for d in docs])
uniq = sorted(set(sums))
gold = [g for g in map(json.loads, open("eval/golden.jsonl")) if g["tier"] != "out_of_scope"]
pairs = [json.loads(l) for l in open("data/ft-embedder/pairs.jsonl")][::3]       # ~1/3 of training pairs
pair_sum = {d["text"]: d["summary"] for d in docs}

def summary_ranks(doc_vecs, q_vecs, targets):
    """rank of the target summary, scoring each summary by its best ticket"""
    out = []
    for qv, t in zip(q_vecs, targets):
        sims = doc_vecs @ qv
        best = {u: sims[sums == u].max() for u in uniq}
        order = sorted(uniq, key=lambda u: -best[u]); out.append(order.index(t) + 1)
    return np.array(out)

def report(name, ranks):
    print(f"  {name:28s} top1={np.mean(ranks == 1):.2f}  hit@5={np.mean(ranks <= 5):.2f}  MRR={np.mean(1 / ranks):.2f}")

def norm(x): x = np.asarray(x, dtype="float32"); return x / np.linalg.norm(x, axis=-1, keepdims=True)

qc = QdrantClient(url=C.QDRANT_URL)
pts, _ = qc.scroll(C.COLLECTION, limit=2000, with_vectors=True)
vec = {p.id: p.vector for p in pts}
nomic_docs = norm([vec[i] for i in ids])

results = {}
gq, gt = [g["question"] for g in gold], [g["summary"] for g in gold]
pq, pt = [p["anchor"] for p in pairs], [pair_sum[p["positive"]] for p in pairs]
results["nomic-embed-text (current)"] = (summary_ranks(nomic_docs, norm(embed(gq, "search_query: ")), gt),
                                         summary_ranks(nomic_docs, norm(embed(pq, "search_query: ")), pt))
for name, path in (("bge-small base", "BAAI/bge-small-en-v1.5"), ("bge-small fine-tuned", "data/ft-embedder/final")):
    m = SentenceTransformer(path)
    dv = m.encode([d["text"] for d in docs], normalize_embeddings=True, batch_size=64)
    results[name] = (summary_ranks(dv, m.encode(gq, normalize_embeddings=True), gt),
                     summary_ranks(dv, m.encode(pq, normalize_embeddings=True), pt))

print(f"\nHELD-OUT golden questions (n={len(gold)}; summaries never seen in training)")
for k, (g, _) in results.items(): report(k, g)
print(f"\nSANITY: training-style questions on TRAINING summaries (n={len(pairs)})")
for k, (_, p) in results.items(): report(k, p)
