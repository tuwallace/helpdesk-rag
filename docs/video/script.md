# Video script: "I built a local RAG, and most of my good ideas didn't work"

Target length: about 12 minutes (about 1,700 spoken words at a relaxed pace).
Format: hybrid. **LIVE** = you record your screen and talk over it. **ANIM** = animated clip I build in Remotion
from the numbers in the appendix. Narration is written to be read aloud; change anything that doesn't sound like you.

All numbers come from this repo's own runs (19 in-scope and 7 out-of-scope golden questions on a synthetic
dataset). They were also used for tuning, which the video says out loud.

## Segment plan

| # | Time | Segment | Type |
|---|---|---|---|
| 1 | 0:00 | Hook | ANIM + you on camera or voice |
| 2 | 0:30 | What I built, and the stack | ANIM |
| 3 | 1:30 | The data twist | LIVE |
| 4 | 2:30 | The "printer" problem | LIVE |
| 5 | 4:00 | The fix: grouped pool plus reranking | ANIM |
| 6 | 5:30 | What didn't work | ANIM |
| 7 | 7:00 | Evaluating honestly | ANIM |
| 8 | 8:30 | Knowing when to say "I don't know" | LIVE |
| 9 | 9:30 | Tracing: where the time goes | LIVE |
| 10 | 10:30 | Letting a local model use it (ollmcp) | LIVE |
| 11 | 11:45 | Takeaways | ANIM |

---

## 1. Hook (0:00)

**Visual (ANIM):** title card, then a split screen: left a green "hit@5 0.95", right a red "HyDE, fine-tuning, a better embedder: no gain".

**Narration:**
> I built a RAG system that runs entirely on my laptop. It ended up with a retrieval score of
> ninety-five percent. But the interesting part isn't what worked. Three of the techniques everyone recommends,
> HyDE, fine-tuning, and a better embedding model, did nothing. And one tiny bug in a tool definition cut my
> results by sixty percent. Here's the whole story, with the numbers.

## 2. What I built (0:30)

**Visual (ANIM):** pipeline diagram appearing step by step: question → rewrite → hybrid search (dense + BM25) →
grouped pool → rerank → cutoff and floor → generate. Stack icons underneath.

**Narration:**
> The project is a help-desk assistant. You describe an IT problem, and it searches past tickets and tells you what
> they say. Everything is local on an M2 MacBook Pro. Ollama runs the models: qwen3 eight-billion for generation and
> nomic for embeddings. Qdrant is the vector database. A cross-encoder reranks results. Phoenix traces every step.
> And at the end, ollmcp lets a local model decide when to search. The data is a synthetic ticket dataset from
> Hugging Face, a thousand tickets in the free sample. Here is the path a question takes. It gets rewritten, then
> searched two ways at once, then grouped into distinct problems, reranked, filtered, and only then handed to the model.

**On-screen caption:** "Ollama · Qdrant · bge-reranker · Arize Phoenix · ollmcp · all local"

## 3. The data twist (1:30)

**Visual (LIVE):** terminal. Run:

```bash
PYTHONPATH=src .venv/bin/python -W ignore -c "
from rag.ingest import build_docs; import collections
c = collections.Counter(d['summary'] for d in build_docs())
print(len(c), 'distinct summaries in', sum(c.values()), 'tickets'); print(c.most_common(3))"
```

**Narration:**
> First surprise. A thousand tickets, but only fifty-six distinct problems. Each one is repeated ten to thirty times
> with different names attached. The comments are even worse: twenty-four distinct sentences, attached to tickets more
> or less at random. And there is no real resolution field, so I can't trust any of it as a fix. It's a ticket search
> and triage tool. That one fact shaped almost every decision after this.

## 4. The "printer" problem (2:30)

**Visual (LIVE):** terminal. Run the retrieval comparison with the query `printer`:

```bash
PYTHONPATH=src .venv/bin/python -W ignore -c "
from rag.retrieve import dense, sparse, hybrid
q='printer'
for name,f in [('dense',dense),('bm25',sparse),('hybrid',hybrid)]:
    print('==',name)
    for d in f(q,5): print(d['id'], d['summary'])
"
```

**Narration:**
> I searched for "printer" with three methods: embeddings, keyword search, and the two combined. Every single result,
> in all three, was the same problem: label printer feeds blank stock. But the data has three different printer
> problems. The biggest cluster of near-duplicates filled the whole top of the list, and I'd never have known the
> other two existed. Averages would have hidden this. I only saw it by reading the actual results.

**On-screen caption:** "15 slots, 1 problem. 3 printer problems exist."

## 5. The fix (4:00)

**Visual (ANIM):** bar chart, "target in candidate pool": 0.74 → 0.95. Then a second chart for hit@5: first stage 0.79, reranked 0.95.

**Narration:**
> The fix was to stop retrieving tickets and start retrieving distinct problems. Qdrant can group by a field, so I
> asked for the top twenty different summaries. The chance that the right problem was even in the candidate pool
> jumped from seventy-four to ninety-five percent. Then a cross-encoder reranker, reading the question and each
> summary together, took the right answer in the top five from about seventy to ninety-five percent. One lesson
> inside that: reranking on the short summary beat reranking on the full ticket text, because the full text had
> random noise attached to it. The real lesson: retrieval can't recover what it never fetched, so measure each
> stage separately.

## 6. What didn't work (5:30)

**Visual (ANIM):** a table that fills row by row, each row stamped "no gain" or "hurt".

| Idea | Result |
|---|---|
| HyDE (embed a made-up answer) | replacing the query everywhere: hit@5 fell to 0.77; as an extra query: no change |
| Fine-tuning the embedder | 252 pairs, 13 seconds of training, held-out top1 0.79 vs 0.84 for the untouched model |
| A better embedder (bge vs nomic) | looked great alone (top1 0.53 → 0.84), identical in the full pipeline (0.79) |
| A strict score cutoff (0.25) | cost about 3 of 19 hits with query rewriting |

**Narration:**
> Now the things that didn't work. HyDE, where the model writes a fake answer to search with: no gain, and it got worse
> when I let it replace the question. Fine-tuning the embedding model: it trained fine, and changed nothing, because
> the untouched model was already finding the right answer. Switching to a better embedder: dramatically better
> on its own, and exactly the same once the reranker was in the pipeline. The reranker erased the difference. And a
> score cutoff I'd tuned by eye was silently throwing away correct results. Components interact. A win in isolation
> doesn't predict a win in the system.

## 7. Evaluating honestly (7:00)

**Visual (ANIM):** left, a "too easy" golden set where every score is 1.00. Right, the rules from the reading guide:
one question = 5.3 points; the sign-test table; the rule of three.

**Narration:**
> How do you know any of this is real? My first set of test questions was too easy: the model had paraphrased the
> ticket titles, and everything scored near perfect. Useless. Then I had a result that said ninety-five percent,
> and it was computed on only nineteen questions. One question is worth five points. To be confident one system really
> beats another, and isn't just lucky, you'd want something like six wins and no losses, not one win. And if you see nineteen out of
> nineteen, the real failure rate could still be sixteen percent. I wrote a guide on reading these numbers, and I'll
> link it. One more thing I have to be upfront about: I tuned on the same questions I scored on, so these numbers
> are optimistic.

## 8. Knowing when to say "I don't know" (8:30)

**Visual (LIVE):** terminal. Run two questions, an answerable one and an unanswerable one:

```bash
PYTHONPATH=src .venv/bin/python -W ignore -m rag.pipeline "outlok keeps askin me to sign in again on my macbook"
PYTHONPATH=src .venv/bin/python -W ignore -m rag.pipeline "what time does the cafeteria open on fridays"
```

**Narration:**
> The scariest failure in RAG is the confident wrong answer. So I added a floor on the reranker score. Below it, the
> system doesn't even call the model. It says there's no match and suggests opening a ticket, and that path takes under
> half a second. In my tests it refused all seven questions it couldn't answer. The cost: it also wrongly refused
> three of nineteen valid questions, about sixteen percent. That's a trade-off you choose, not a bug you fix. And I
> broke it once: I told the model to reply "no match" when unsure, and it refused eight of nineteen good questions.
> Small models take instructions very literally.

## 9. Tracing (9:30)

**Visual (LIVE):** run the trace demo, then show Phoenix in the browser (project `helpdesk-rag`, open one trace tree).

```bash
PYTHONPATH=src .venv/bin/python -W ignore scripts/18_trace_demo.py
```

**Narration:**
> Tracing shows where the time goes. In a warm run it takes a few seconds, and the generator is roughly three quarters
> of that. The query rewrite is about a fifth, and retrieval plus reranking barely register. The first run after a
> cold start is slower, because the models have to load. So if you want this faster, shrink the context or the model.
> Don't optimize the retrieval. Caveat: that's three traces, so treat the percentages as illustrative.

## 10. Letting a local model use it (10:30)

**Visual (LIVE):** run `ollmcp`, then three prompts:
1. "outlook keeps asking me to sign in on my mac" → it calls the tool.
2. "what is 17 times 23?" → it answers without the tool.
3. "how many vacation days do I have left?" → it searches, finds nothing, and says so.

```bash
ollmcp -j mcp.json -m qwen3:8b
```

**Narration:**
> Last piece: ollmcp lets a local model decide when to search. I exposed my pipeline as one tool. In my tests it used
> the tool for all nineteen IT questions and none of the six chit-chat prompts. But the first test found only six
> of nineteen correct tickets, versus sixteen in the pipeline. The reason: the model was filling in an optional
> priority filter on every call, with a value nobody asked for, and that hid the right tickets. I deleted the
> parameter and the results matched. If you build tools for small models, keep the schema minimal.

## 11. Takeaways (11:45)

**Visual (ANIM):** five bullets, one at a time.

**Narration:**
> Five things. One: read your data before you pick techniques. Two: measure every stage, because the pool limits
> everything after it. Three: test components in the full system, not alone. Four: report your sample size and be honest
> about tuning on your test set. And five: decide up front which error costs more, wrong answers or refusals. The
> code, commands, and the number-reading guide are linked below. If you want a follow-up where I test this on questions
> I wrote blind, say so in the comments.

---

## Appendix A: data for the animated clips (all verified in this repo)

```json
{
  "dataset": {"tickets": 1000, "distinct_summaries": 56, "distinct_comment_bodies": 24},
  "printer_problem": {"results_shown": 15, "distinct_problems_returned": 1, "printer_problems_in_data": 3},
  "pool_recall": {"ticket_level_top20": 0.74, "grouped_by_summary": 0.95},
  "hit_at_5": {"hybrid_first_stage_grouped": 0.79, "rerank_on_summary": 0.95, "rerank_on_full_text": 0.89},
  "failed_ideas": {
    "hyde_replace_query_hit5": 0.77, "hyde_dense_only_hit5": 0.95,
    "finetune_top1": 0.79, "base_bge_top1": 0.84, "finetune_pairs": 252, "finetune_train_seconds": 13,
    "embedder_alone_top1": {"nomic": 0.53, "bge": 0.84}, "embedder_in_pipeline_top1": {"nomic": 0.79, "bge": 0.79},
    "cutoff_0.25_rewrite_hit5": 0.79, "cutoff_0.05_rewrite_hit5": 0.95
  },
  "answerability": {"out_of_scope_refused": "7/7", "in_scope_wrongly_refused": "3/19", "sentinel_prompt_false_refusals": "8/19"},
  "latency_warm_trace_seconds": {"total": 3.26, "generate": 2.55, "rewrite": 0.52, "rerank": 0.10, "cold_first_trace": 9.93, "floor_refusal": 0.41},
  "mcp": {"tool_called_in_scope": "19/19", "tool_called_chitchat": "0/6", "target_found_before_fix": "6/19", "target_found_after_fix": "16/19"},
  "yardsticks": {"chance_top1": 0.02, "chance_hit5": 0.09, "bm25_only_top1": 0.21, "bm25_only_hit5": 0.37},
  "eval_size": {"in_scope": 19, "out_of_scope": 7, "one_question_points": 5.3}
}
```

## Appendix B: before you record

1. `docker compose up -d`, then check `docker compose ps` shows both services `Up`.
2. **Warm the models** with one throwaway query. The first call after startup takes about 10 seconds.
3. Close notifications, set a large terminal font, and use a clean terminal profile (hide the user name and paths if you don't want them shown).
4. Open Phoenix at http://localhost:6006 and have the `helpdesk-rag` project selected. The `default` project holds about 1,500 old traces.
5. Rehearse each LIVE command once. Answers vary between runs (LLM), so your output can differ from the narration. Read what's on screen.
6. Record each segment separately so you can re-take one without redoing the video.

## Appendix C: upload text

**Title options**
- "I built a local RAG. Most of my best ideas failed."
- "Local RAG with Ollama: what worked, what didn't (with real numbers)"
- "HyDE, fine-tuning, better embeddings: I tested them. Here's what happened."

**Thumbnail text:** "95% → but 3 ideas did NOTHING" (big), with a red X over "HyDE · Fine-tuning · Better embeddings".

**Description (draft)**
```
I built a help-desk RAG that runs entirely on a MacBook: Ollama (qwen3:8b + nomic-embed-text), Qdrant, a
cross-encoder reranker, Arize Phoenix tracing, and ollmcp. This is what worked, what didn't, and how I checked.

Chapters
0:00 Hook
0:30 What I built
1:30 The data twist
2:30 The "printer" problem
4:00 The fix: grouped pool + reranking
5:30 What didn't work
7:00 Evaluating honestly
8:30 Knowing when to say "I don't know"
9:30 Tracing
10:30 ollmcp
11:45 Takeaways

Caveats: results are on 19 in-scope and 7 out-of-scope questions, tuned on the same questions, on a synthetic dataset.
Treat them as illustrations, not benchmarks.

Dataset: mindweave/help-desk-tickets on Hugging Face, license CC-BY-NC-4.0 (non-commercial). Credit: mindweave.
Code and commands: <link to your repo>
Guide to reading the numbers: <link>
```

**Tags:** RAG, local LLM, Ollama, Qdrant, reranking, HyDE, fine-tuning, embeddings, MCP, ollmcp, AI engineering

**Disclosure:** if you use synthetic narration or AI-generated visuals that could be mistaken for real footage,
use YouTube's altered/synthetic content disclosure when uploading. Real screen recordings and charts don't need it.
