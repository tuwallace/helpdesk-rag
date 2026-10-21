"""Ranking vs re-ranking: first-stage scores (cosine/BM25/RRF) are cheap and coarse;
a cross-encoder reads (query, doc) TOGETHER and scores relevance far more accurately."""
from functools import lru_cache
from sentence_transformers import CrossEncoder
from .tracing import tracer

@lru_cache
def _model():
    name = "BAAI/bge-reranker-base"                      # ~1 GB, runs on MPS/CPU
    try:                                                  # cache first: no network call that could hang on a flaky connection
        return CrossEncoder(name, local_files_only=True)
    except Exception:
        return CrossEncoder(name)                         # first run: download

def rerank(query, docs, top_n=5, field="summary"):
    """field='summary' beat field='text' in scripts/14 (the text carries noisy category/comment lines)."""
    with tracer.start_as_current_span("rerank.cross_encoder") as s:
        s.set_attribute("openinference.span.kind", "RERANKER")
        scores = _model().predict([(query, d[field]) for d in docs])
        for d, sc in zip(docs, scores):
            d["rerank_score"] = float(sc)
        out = sorted(docs, key=lambda d: -d["rerank_score"])[:top_n]
        s.set_attribute("top_ids", str([d["id"] for d in out]))
        return out
