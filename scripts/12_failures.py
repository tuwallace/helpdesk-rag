"""Failure analysis. For each golden question, trace WHERE the relevant summary is lost:
  pool   = is it among the 20 hybrid candidates at all?          (retrieval failure)
  1st    = its rank after first-stage ranking, de-duped by summary
  rerank = its rank after cross-encoder re-ranking, de-duped
  cut    = would the relative cutoff (score < REL x top score) remove it?   (post-retrieval failure)"""
import json, sys, copy
sys.path.insert(0, "src")
from rag.pre_retrieval import rewrite
from rag.retrieve import hybrid
from rag.rerank import rerank
from rag.post_retrieval import dedupe

REL, K = 0.25, 5
gold = [g for g in map(json.loads, open("eval/golden.jsonl")) if g["tier"] != "out_of_scope"]

def rank_of(docs, rel):
    return next((i + 1 for i, d in enumerate(docs) if d["id"] in rel), None)

tot = {rw: {"first": 0, "rerank": 0, "rerank_cut": 0, "pool": 0} for rw in (False, True)}
for g in gold:
    rel = set(g["relevant_ids"])
    print(f"\n[{g['tier']}] {g['question']}\n   target: {g['summary']}")
    for rw in (False, True):
        q = rewrite(g["question"]) if rw else g["question"]
        cands = hybrid(q, 20)
        first = dedupe(copy.deepcopy(cands))
        r_first = rank_of(first, rel)
        rr = rerank(q, copy.deepcopy(cands), 20)          # sorted by rerank_score, all 20
        top = rr[0]["rerank_score"]
        rr_d = dedupe(rr)
        r_rr = rank_of(rr_d, rel)
        tgt = next((d for d in rr_d if d["id"] in rel), None)
        cut = tgt is not None and tgt["rerank_score"] < REL * top
        kept = [d for d in rr_d if d["rerank_score"] >= REL * top]
        t = tot[rw]
        t["pool"] += r_first is not None
        t["first"] += r_first is not None and r_first <= K
        t["rerank"] += r_rr is not None and r_rr <= K
        t["rerank_cut"] += (r_rr is not None and r_rr <= K) and not cut
        tag = "rewrite" if rw else "raw    "
        why = ("NOT IN POOL (retrieval miss)" if r_first is None else
               "CUT by relative cutoff" if cut and r_rr <= K else
               "" if r_rr == 1 else f"reranked to #{r_rr}")
        sc = f"{tgt['rerank_score']:.2f}/{top:.2f}" if tgt else "--"
        print(f"   {tag} 1st=#{r_first}  rerank=#{r_rr}  target/top score={sc}  {why}")
        if rw: print(f"           rewritten query: {q!r}")
        if r_rr != 1 and rr_d:
            print(f"           rerank top-2: {[d['summary'][:38] for d in rr_d[:2]]}")

n = len(gold)
print(f"\n=== hit@{K} over {n} questions ===")
for rw, t in tot.items():
    print(f"{'rewrite' if rw else 'raw    '}  in-pool={t['pool']/n:.2f}  first-stage={t['first']/n:.2f}  "
          f"rerank(no cutoff)={t['rerank']/n:.2f}  rerank+cutoff={t['rerank_cut']/n:.2f}")
