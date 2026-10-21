"""End-to-end check of answer(): refusals on out-of-scope questions, false refusals on in-scope ones.
Prints the generated answer for any out-of-scope question that was NOT refused, so you can judge it."""
import json, sys
sys.path.insert(0, "src")
from rag.pipeline import answer

s = {"oos": [0, 0], "in": [0, 0, 0]}
reasons = {}
for l in open("eval/golden.jsonl"):
    g = json.loads(l); r = answer(g["question"]); ref = r["refused"]
    reasons[ref] = reasons.get(ref, 0) + 1
    if g["tier"] == "out_of_scope":
        s["oos"][0] += 1; s["oos"][1] += bool(ref)
        print(f"OOS  {'refused(' + ref + ')' if ref else 'ANSWERED':22s} {g['question'][:58]}")
        if not ref: print("       ->", r["answer"][:220].replace("\n", " "), "| sources:", r["sources"])
    else:
        hit = bool(set(r["sources"]) & set(g["relevant_ids"]))
        s["in"][0] += 1; s["in"][1] += bool(ref); s["in"][2] += hit
        print(f"IN   {'refused(' + ref + ')' if ref else 'answered':22s} target_in_sources={hit!s:5s} {g['question'][:50]}")
print(f"\nout-of-scope refused {s['oos'][1]}/{s['oos'][0]} | in-scope refused {s['in'][1]}/{s['in'][0]} | "
      f"in-scope target cited {s['in'][2]}/{s['in'][0]} | by reason {reasons}")
