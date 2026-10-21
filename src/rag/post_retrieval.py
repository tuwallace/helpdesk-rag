"""Post-retrieval: threshold, de-duplicate, reorder (lost-in-the-middle), build context."""
def filter_low(docs, rel=None):
    """Relative cutoff: keep docs scoring >= rel x the best rerank score. Cross-encoder scores
    (0-1 for bge-reranker) depend on the query, so a fixed threshold either keeps junk or drops
    good hits on short queries. Starting value; tune on the golden set."""
    from . import config as C
    rel = C.CUTOFF_REL if rel is None else rel
    if not docs:
        return docs
    top = max(d["rerank_score"] for d in docs)
    return [d for d in docs if d["rerank_score"] >= rel * top]

def dedupe(docs):
    """Synthetic (and real!) ticket data is full of near-duplicates. Keep the best-ranked ticket
    per summary and record how many siblings were collapsed, so the answer can say 'seen 5x'."""
    kept = {}
    for d in docs:
        k = d.get("summary", d["text"][:120]).lower()
        if k in kept: kept[k]["similar_count"] += 1
        else: kept[k] = {**d, "similar_count": d.get("similar_count", 1)}
    return list(kept.values())

def long_context_reorder(docs):
    """Best docs at the start AND end; weakest in the middle."""
    return docs[0::2] + docs[1::2][::-1]

def build_context(docs, max_chars=6000):
    ctx, used = [], 0
    for d in docs:
        block = f"[ticket {d['id']}] (seen {d.get('similar_count',1)}x in results)\n{d['text']}"
        if used + len(block) > max_chars: break
        ctx.append(block); used += len(block)
    return "\n\n".join(ctx)
