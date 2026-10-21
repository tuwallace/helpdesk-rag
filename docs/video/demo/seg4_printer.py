"""Segment 4 on-screen demo: the 'printer' problem. Run from anywhere:  python docs/video/demo/seg4_printer.py"""
import collections, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[3]; sys.path.insert(0, str(ROOT / "src"))
from rag.ingest import build_docs
from rag.retrieve import dense, sparse, hybrid

q = "printer"; seen = []
print(f'\n  query: "{q}"   (top 5 tickets from each method)\n')
for name, f in [("dense (embeddings)", dense), ("bm25 (keywords)", sparse), ("hybrid (both)", hybrid)]:
    print(f"  {name}")
    for d in f(q, 5): print(f"    {d['id']:>4}  {d['summary']}"); seen.append(d["summary"])
print(f"\n  distinct problems in these {len(seen)} results: {len(set(seen))}")
per = collections.Counter(d["summary"] for d in build_docs() if "printer" in d["summary"].lower())
print("\n  printer problems that actually exist in the data:")
for s, n in per.most_common(): print(f"    {n:>3} tickets  {s}")
print()
