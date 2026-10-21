"""Pluggable QUERY embedder, chosen by config.EMBEDDER (read at call time so experiments can switch it):
  "nomic"      nomic-embed-text via Ollama, 'search_query:' prefix (current index: collection 'tickets')
  "bge"        bge-small-en-v1.5, no prefix                   (collection 'tickets_bge')
  "bge-instr"  bge-small-en-v1.5 with its recommended retrieval instruction prefix (collection 'tickets_bge')"""
from functools import lru_cache
from . import config as C
from .ingest import embed
from .tracing import tracer

BGE_MODEL = "BAAI/bge-small-en-v1.5"
INSTR = "Represent this sentence for searching relevant passages: "

@lru_cache
def bge():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(BGE_MODEL)

def embed_query(text: str):
    if C.EMBEDDER == "nomic":
        return embed([text], "search_query: ")[0]
    with tracer.start_as_current_span("embed") as s:
        s.set_attribute("openinference.span.kind", "EMBEDDING"); s.set_attribute("embedder", C.EMBEDDER)
        return bge().encode((INSTR if C.EMBEDDER == "bge-instr" else "") + text, normalize_embeddings=True).tolist()
