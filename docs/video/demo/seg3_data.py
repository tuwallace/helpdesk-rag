"""Segment 3 on-screen demo: the data twist. Run from anywhere:  python docs/video/demo/seg3_data.py"""
import collections, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[3]; sys.path.insert(0, str(ROOT / "src"))
import pandas as pd
from rag import config as C
from rag.ingest import build_docs

docs = build_docs(); per = collections.Counter(d["summary"] for d in docs)
com = pd.read_csv(C.RAW / C.COMMENTS_CSV)
rows = [("tickets", f"{len(docs):,}"), ("distinct problems (summaries)", f"{len(per)}"),
        ("tickets per problem", f"{min(per.values())} to {max(per.values())}"),
        ("comments", f"{len(com):,}"), ("distinct comment sentences", f"{com['body'].nunique()}")]
print()
for k, v in rows: print(f"  {k:<32}{v:>8}")
print("\n  most repeated comments (attached to tickets at random):")
for body, n in com["body"].value_counts().head(3).items(): print(f"    {n:>3}x  {body}")
print()
