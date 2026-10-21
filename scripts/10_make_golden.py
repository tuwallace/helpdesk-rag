"""Golden set = two tiers over the HELD-OUT summaries (eval/split.json).
 tier "paraphrase": LLM paraphrase, with a programmatic word-overlap check + retries (an instruction
                    like "don't reuse words" is not enforceable by prompting alone).
 tier "hard":       hand-written in eval/hard_questions.json (typos, slang, symptom-only, vague).
Every ticket sharing the summary is relevant. REVIEW the output by hand."""
import json, os, random, re, sys, ollama
sys.path.insert(0, "src")
from rag import config as C
from rag.ingest import build_docs

STOP = set("a an the and or of to in on for with is are was were be it its my our we i me you your this that "
           "not no from at by as after before when why what how do does did can cant will wont keeps keep "
           "again any every get got has have there their them they up out into".split())
def content(s): return {w.rstrip("s") for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP}
def overlap(q, summary):
    s = content(summary); return len(s & content(q)) / len(s)

if os.path.exists("eval/golden.jsonl") and "--force" not in sys.argv:
    sys.exit("eval/golden.jsonl exists and may contain hand-added questions. Re-run with --force to overwrite.")
MAX_OVERLAP, TRIES = 0.34, 4
docs = build_docs()
by_sum = {}
for d in docs: by_sum.setdefault(d["summary"], []).append(d["id"])

if os.path.exists("eval/split.json"):                # keep the existing split stable
    test = json.load(open("eval/split.json"))["test"]
else:
    random.seed(7); sums = sorted(by_sum); random.shuffle(sums); cut = int(len(sums) * .75)
    json.dump({"train": sums[:cut], "test": sums[cut:]}, open("eval/split.json", "w"), indent=1); test = sums[cut:]

rows = []
for s in test:
    banned, best = "", None
    for _ in range(TRIES):
        q = ollama.chat(model=C.GEN_MODEL, think=False, messages=[{"role": "user", "content":
            "An employee has this IT problem. Write how THEY would casually ask the help desk about it, as one "
            "question, describing the symptom in completely different words. Output only the question.\n"
            f"Problem: {s}\n{banned}"}])["message"]["content"].strip()
        o = overlap(q, s)
        if best is None or o < best[1]: best = (q, o)
        if o <= MAX_OVERLAP: break
        banned = "You MUST NOT use these words: " + ", ".join(sorted(content(s) & content(q)))
    rows.append({"question": best[0], "relevant_ids": by_sum[s], "summary": s, "tier": "paraphrase",
                 "overlap": round(best[1], 2), "needs_review": best[1] > MAX_OVERLAP})
for h in json.load(open("eval/hard_questions.json")):
    assert h["summary"] in by_sum, f"unknown summary: {h['summary']}"
    rows.append({"question": h["question"], "relevant_ids": by_sum[h["summary"]], "summary": h["summary"],
                 "tier": "hard", "kind": h["kind"], "overlap": round(overlap(h["question"], h["summary"]), 2)})
with open("eval/golden.jsonl", "w") as f:
    for r in rows: f.write(json.dumps(r) + "\n")
print(f"{len(rows)} questions -> eval/golden.jsonl")
