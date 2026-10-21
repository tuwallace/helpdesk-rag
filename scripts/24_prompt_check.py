"""A/B a system-prompt change on the golden questions, same retrieval for both.
Measures (a) answers that claim a resolution/fix (the canned-comment problem), (b) refusals, (c) target cited.
Run:  python scripts/24_prompt_check.py   (about 3-4 minutes)
Caveat: the claim regex also matches the word "resolved" when it merely reports a ticket status, so it overcounts.
Result when run: the reworded prompt did NOT reduce fix claims (10/16 vs 13/17 answers), so the pipeline prompt was left unchanged."""
import json, re, sys
sys.path.insert(0, "src")
import rag.pipeline as P

OLD = P.SYSTEM
NEW = ("You are an IT help-desk assistant. Answer ONLY from the tickets provided; they contain symptoms, status and timing. "
       "The 'Public updates' lines are generic notes that are often unrelated to the problem: never present them as the fix or "
       "resolution, and never invent a fix. Cite ticket ids like [ticket 12]. If the context is insufficient, say so.")
CLAIM = re.compile(r"\b(resolved|was fixed|fixed by|applied|reinstalled|reset the|restored|workaround|resolution|the fix)\b", re.I)
gold = [json.loads(l) for l in open("eval/golden.jsonl")]
for name, prompt in (("old prompt", OLD), ("new prompt", NEW)):
    P.SYSTEM = prompt; c = dict(n=0, claim=0, ref_in=0, cited=0, oos=0, oos_ref=0)
    for g in gold:
        r = P.answer(g["question"]); ref = bool(r["refused"])
        if g["tier"] == "out_of_scope": c["oos"] += 1; c["oos_ref"] += ref
        else:
            c["n"] += 1; c["ref_in"] += ref; c["cited"] += bool(set(r["sources"]) & set(g["relevant_ids"]))
            c["claim"] += (not ref) and bool(CLAIM.search(r["answer"]))
    print(f"{name}: in-scope answers claiming a fix/resolution {c['claim']}/{c['n'] - c['ref_in']} answered | refused {c['ref_in']}/{c['n']} | "
          f"target cited {c['cited']}/{c['n']} | out-of-scope refused {c['oos_ref']}/{c['oos']}")
