"""Retrieval: dense (Qdrant) + sparse (BM25) fused with Reciprocal Rank Fusion."""
import re
from functools import lru_cache
from rank_bm25 import BM25Okapi
from qdrant_client import QdrantClient, models
from . import config as C
from .ingest import build_docs, embed
from .embedders import embed_query
from .tracing import tracer

_q = QdrantClient(url=C.QDRANT_URL)
tok = lambda s: re.findall(r"\w+", s.lower())   # strips punctuation: "printer." -> "printer"

@lru_cache
def _bm25():
    docs = build_docs()
    return docs, BM25Okapi([tok(d["text"]) for d in docs])

def dense(query, k=20, filters: dict | None = None):
    flt = models.Filter(must=[models.FieldCondition(key=a, match=models.MatchValue(value=b))
                              for a, b in (filters or {}).items()]) if filters else None
    hits = _q.query_points(C.COLLECTION, query=embed_query(query),
                           limit=k, query_filter=flt, with_payload=True).points
    return [{**h.payload, "dense_score": h.score} for h in hits]

def sparse(query, k=20):
    docs, bm = _bm25()
    scores = bm.get_scores(tok(query))
    top = sorted(range(len(docs)), key=lambda i: -scores[i])[:k]
    return [{**docs[i], "bm25_score": float(scores[i])} for i in top]

@lru_cache
def _counts():
    c = {}
    for d in _bm25()[0]: c[d["summary"]] = c.get(d["summary"], 0) + 1
    return c

def _flt(filters):
    return models.Filter(must=[models.FieldCondition(key=a, match=models.MatchValue(value=b))
                               for a, b in filters.items()]) if filters else None

def dense_grouped(query, k=20, filters=None):
    """Top-k DISTINCT summaries (one ticket each). A big cluster of near-duplicates can no longer
    fill the candidate pool."""
    r = _q.query_points_groups(C.COLLECTION, query=embed_query(query), group_by="summary",
                               limit=k, group_size=1, query_filter=_flt(filters), with_payload=True)
    return [{**g.hits[0].payload, "dense_score": g.hits[0].score} for g in r.groups]

def sparse_grouped(query, k=20, filters=None):
    docs, bm = _bm25()
    scores = bm.get_scores(tok(query)); seen, out = set(), []
    for i in sorted(range(len(docs)), key=lambda i: -scores[i]):
        d = docs[i]
        if d["summary"] in seen or any(d.get(a) != b for a, b in (filters or {}).items()): continue
        seen.add(d["summary"]); out.append({**d, "bm25_score": float(scores[i])})
        if len(out) == k: break
    return out

def rrf(lists, k=60):
    fused, seen = {}, {}
    for lst in lists:
        for rank, d in enumerate(lst):
            fused[d["id"]] = fused.get(d["id"], 0) + 1 / (k + rank + 1)
            seen.setdefault(d["id"], {}).update(d)
    return [{**seen[i], "rrf_score": s} for i, s in sorted(fused.items(), key=lambda x: -x[1])]

def hybrid(query, k=20, filters=None):
    with tracer.start_as_current_span("retrieve.hybrid") as s:
        out = rrf([dense(query, k, filters), sparse(query, k)])[:k]
        s.set_attribute("n_candidates", len(out))
        return out

def hybrid_grouped(query, k=20, filters=None):
    with tracer.start_as_current_span("retrieve.hybrid_grouped") as s:
        s.set_attribute("openinference.span.kind", "RETRIEVER")
        out = rrf([dense_grouped(query, k, filters), sparse_grouped(query, k, filters)])[:k]
        for d in out: d["similar_count"] = _counts()[d["summary"]]     # corpus-wide, not pool-wide
        s.set_attribute("n_candidates", len(out))
        return out
