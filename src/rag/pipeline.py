import ollama
from . import config as C
from .pre_retrieval import rewrite, hyde
from .retrieve import hybrid_grouped
from .rerank import rerank
from .post_retrieval import filter_low, dedupe, long_context_reorder, build_context
from .tracing import tracer

import re
SYSTEM = ("You are an IT help-desk assistant. Answer ONLY from the tickets provided; they contain symptoms, status and timing but NO fix steps, so never invent a fix. "
          "Cite ticket ids like [ticket 12]. If the context is insufficient, say so.")
# A single-word NO_MATCH sentinel in the prompt made qwen3:8b refuse 8/19 valid questions (vs 2/19 here); phrase matching is used instead.
NO_MATCH_MSG = "I couldn't find a matching ticket in the help-desk history. Please open a new ticket."
_REFUSAL = re.compile(r"do(es)? not (contain|include|mention|address)|none of the tickets|insufficient context|cannot (answer|provide)", re.I)

def retrieve_docs(question, *, use_rewrite=True, use_hyde=False, use_rerank=True, k=20, top_n=5,
                  filters=None, min_top_score=None):
    """min_top_score: answerability floor on the best rerank score (None = off; eval ranking metrics leave it off)."""
    q = rewrite(question) if use_rewrite else question
    if use_hyde: q = hyde(q)
    cands = hybrid_grouped(q, k, filters)
    docs = rerank(q, cands, k) if use_rerank else cands
    if min_top_score is not None and use_rerank and (not docs or docs[0]["rerank_score"] < min_top_score):
        return []
    docs = dedupe(filter_low(docs) if use_rerank else docs)
    return docs[:top_n]

def answer(question, *, floor=C.ANSWER_FLOOR, **kw):
    with tracer.start_as_current_span("rag.answer") as root:
        root.set_attribute("openinference.span.kind", "CHAIN")
        root.set_attribute("input.value", question)
        docs = retrieve_docs(question, min_top_score=floor, **kw)
        if not docs:                                   # below the floor: skip the generator entirely
            root.set_attribute("refused", "below_floor"); root.set_attribute("output.value", NO_MATCH_MSG)
            return {"answer": NO_MATCH_MSG, "sources": [], "refused": "below_floor"}
        with tracer.start_as_current_span("generate") as s:
            s.set_attribute("openinference.span.kind", "LLM")
            ctx = build_context(long_context_reorder(docs))
            r = ollama.chat(model=C.GEN_MODEL, think=False, messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"Tickets:\n{ctx}\n\nQuestion: {question}"}])
            out = r["message"]["content"]
            s.set_attribute("output.value", out)
        if _REFUSAL.search(out):                       # model said nothing matches: don't show citations
            root.set_attribute("refused", "model"); root.set_attribute("output.value", out)
            return {"answer": out, "sources": [], "refused": "model"}
        root.set_attribute("output.value", out)
        return {"answer": out, "sources": [d["id"] for d in docs], "refused": None}

if __name__ == "__main__":
    import sys
    print(answer(" ".join(sys.argv[1:]) or "How do we usually fix VPN disconnects?"))
