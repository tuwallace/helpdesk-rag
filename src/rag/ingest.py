"""Chunking + indexing. One doc per ticket (subject+description) + one per comment thread."""
import pandas as pd, ollama
from qdrant_client import QdrantClient, models
from . import config as C
from .tracing import tracer

def build_docs():
    """One doc per ticket. Joins category name, PUBLIC comments only (internal notes must
    never reach an end-user answer), and computed time-to-resolve."""
    t = pd.read_csv(C.RAW / C.TICKETS_CSV)
    c = pd.read_csv(C.RAW / C.COMMENTS_CSV)
    cat = pd.read_csv(C.RAW / C.CATEGORIES_CSV).rename(columns={"id": "category_id", "name": "category"})
    t = t.merge(cat[["category_id", "category"]], on="category_id", how="left")
    c = c[c["visibility"] == "public"].sort_values("created_at")
    thread = c.groupby("ticket_id")["body"].apply(lambda s: "; ".join(dict.fromkeys(s.astype(str))))
    t["hours_to_resolve"] = (pd.to_datetime(t["resolved_at"]) - pd.to_datetime(t["created_at"])
                             ).dt.total_seconds() / 3600
    docs = []
    for _, r in t.iterrows():
        tid = int(r["ticket_id"])
        text = (f"{r['summary']} {r['description']}\n"
                f"Category: {r['category']}. Service: {r['affected_service']}. "
                f"Priority: {r['priority']}. Status: {r['status']}. Channel: {r['channel']}.")
        if pd.notna(r["hours_to_resolve"]):
            text += f" Resolved in {r['hours_to_resolve']:.1f}h."
        if thread.get(tid):
            text += f"\nPublic updates: {thread[tid]}"
        meta = {k: (r[k].item() if hasattr(r[k], "item") else r[k]) for k in C.FILTER_FIELDS}
        docs.append({"id": tid, "summary": r["summary"], "text": text, **meta})
    return docs

def embed(texts, prefix="search_document: "):
    with tracer.start_as_current_span("embed") as s:
        s.set_attribute("openinference.span.kind", "EMBEDDING"); s.set_attribute("n_texts", len(texts))
        out = ollama.embed(model=C.EMBED_MODEL, input=[prefix + x for x in texts])
        return out["embeddings"]

def main():
    docs = build_docs()
    q = QdrantClient(url=C.QDRANT_URL)
    dim = len(embed(["x"])[0])
    if q.collection_exists(C.COLLECTION):
        q.delete_collection(C.COLLECTION)      # full rebuild each run
    q.create_collection(C.COLLECTION,
        vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE))
    q.create_payload_index(C.COLLECTION, "summary", models.PayloadSchemaType.KEYWORD)   # needed for group_by
    for i in range(0, len(docs), 64):
        b = docs[i:i+64]
        q.upsert(C.COLLECTION, points=[models.PointStruct(
            id=d["id"], vector=v, payload=d) for d, v in zip(b, embed([d["text"] for d in b]))])
    print(f"indexed {len(docs)} tickets, dim={dim}")

if __name__ == "__main__":
    main()
