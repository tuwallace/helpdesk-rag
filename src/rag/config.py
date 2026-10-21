import os, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
GEN_MODEL = os.getenv("GEN_MODEL", "qwen3:8b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION = "tickets"
EMBEDDER = os.getenv("EMBEDDER", "nomic")   # nomic | bge | bge-instr  (see rag/embedders.py)

# Table files, relative to data/raw (confirmed from the download)
TICKETS_CSV, COMMENTS_CSV, CATEGORIES_CSV = "data/tickets.csv", "data/comments.csv", "data/categories.csv"
# Filterable payload fields (Qdrant metadata) - all exist in the tickets table
FILTER_FIELDS = ["category_id", "priority", "status", "channel",
                 "requester_department", "affected_service", "escalated"]

# Post-retrieval tuning, from scripts/16_cutoff_and_floor.py (n=19 in-scope, 7 out-of-scope; re-tune on new data)
CUTOFF_REL = 0.05      # keep results scoring >= CUTOFF_REL x best rerank score (0.25 cost ~3/19 hits with rewrite)
ANSWER_FLOOR = 0.05    # best rerank score below this => "no matching tickets", no generator call.
                       # 0.05: answers 84% of valid questions, rejects 6/7 out-of-scope. 0.10: 79% / 7 of 7.
