"""Add one hand-written golden question to eval/golden.jsonl.
  --list                              show the 14 held-out (test) summaries you may write questions about
  "question" "summary substring"      in-scope question (tier=hard); relevant_ids come from that summary
  --oos "question"                    OUT-OF-SCOPE question: no ticket in the data answers it
"""
import difflib, json, sys
sys.path.insert(0, "src")
from rag.ingest import build_docs

by = {}
for d in build_docs(): by.setdefault(d["summary"], []).append(d["id"])
test = json.load(open("eval/split.json"))["test"]
def add(row):
    open("eval/golden.jsonl", "a").write(json.dumps(row) + "\n")

if sys.argv[1:2] == ["--list"]:
    for s in test: print(f"{len(by[s]):3d} tickets  {s}")
elif sys.argv[1:2] == ["--oos"]:
    add({"question": sys.argv[2], "relevant_ids": [], "summary": None, "tier": "out_of_scope"})
    print("added out-of-scope question (expected: the system finds nothing relevant)")
else:
    question, key = sys.argv[1], sys.argv[2].lower()
    m = [s for s in test if key in s.lower()]
    if len(m) != 1:
        close = difflib.get_close_matches(sys.argv[2], test, n=3, cutoff=0.2)
        sys.exit(f"'{sys.argv[2]}' matched {len(m)} of the 14 test summaries. The 2nd argument must be a "
                 f"substring of an EXISTING summary (run --list). Closest: {close or 'none'}.\n"
                 f"If no ticket in the data covers your question, use:  --oos \"your question\"")
    add({"question": question, "relevant_ids": by[m[0]], "summary": m[0], "tier": "hard", "kind": "mine"})
    print(f"added -> {m[0]}  ({len(by[m[0]])} relevant tickets)")
