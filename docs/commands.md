# Command reference

Every command used while building the helpdesk RAG project, in the order you'd normally run them.
Run everything from the project root unless noted:

```bash
cd path/to/helpdesk-rag
```

Conventions used below:

- `PYTHONPATH=src` lets scripts import the `rag` package. `.venv/bin/python` is the Python 3.12 environment created by `uv sync`. `-W ignore` hides Python warnings.
- Several commands pipe through `grep -v -i -e warn -e "Loading weights"` to hide noise. **That filter also hides any output line that contains the word "warn"**, which once swallowed a golden question ("...without any warning"). Drop the `grep` if a line looks missing.
- "Timed" means I measured it on this machine (M2 Pro, 32 GB). "Not timed" means I didn't.
- LLM-backed steps (`qwen3:8b`) are **non-deterministic**: the query rewrite, golden-question generation and answers can differ between runs.

## Typical order

1. [Setup](#1-setup) (once)
2. [Data and indexing](#2-data-and-indexing)
3. [Exploring retrieval](#3-exploring-retrieval)
4. [Golden set and evaluation](#4-golden-set-and-evaluation)
5. [Experiments](#5-experiments-used-to-make-design-decisions)
6. [End-to-end answers and tracing](#6-end-to-end-answers-and-tracing)
7. [Fine-tuning and MCP](#7-fine-tuning-and-mcp)
8. [Gotchas](#8-gotchas)

---

## 1. Setup

### 1.1 Pull the embedding model
- **Does:** downloads `nomic-embed-text` (274 MB) into Ollama.
- **Supports:** embeddings for dense retrieval (`src/rag/ingest.py`, `retrieve.py`).
- **Run details:** one-time; needs Ollama running. `qwen3:8b` (the generator and rewriter) must also already be pulled.
```bash
ollama pull nomic-embed-text
```

### 1.2 Start Qdrant and Phoenix
- **Does:** starts two containers from `docker-compose.yml`: Qdrant (vector DB, port 6333) and Arize Phoenix (tracing UI on 6006, OTLP on 4317).
- **Supports:** the vector store and tracing.
- **Run details:** Qdrant data persists in `data/qdrant`, Phoenix data in `data/phoenix`. **If Docker restarts the containers exit**, and every script then fails with "Connection refused" on :6333 or :6006; re-run this command (the 1,000 indexed points survive). Ollama runs on the host, not in Docker, so it can use the Apple GPU.
```bash
docker compose up -d
```

### 1.3 Check that services are up
- **Does:** prints the Qdrant point count and the HTTP status of Phoenix and Ollama.
- **Supports:** a first thing to run when a script fails to connect.
- **Run details:** instant. Expect `points: 1000`, `phoenix http 200`, `ollama http 200`.
```bash
curl -s localhost:6333/collections/tickets | python3 -c "import sys,json; r=json.load(sys.stdin)['result']; print('points:', r['points_count'], '| status:', r['status'])"; curl -s -o /dev/null -w "phoenix http %{http_code}\n" localhost:6006; curl -s localhost:11434/api/tags -o /dev/null -w "ollama http %{http_code}\n"
```

### 1.4 Install Python dependencies
- **Does:** creates `.venv` with Python 3.12 and installs everything in `pyproject.toml` (PyTorch, sentence-transformers, qdrant-client, fastmcp, etc.).
- **Supports:** all scripts.
- **Run details:** first run downloads a few GB (PyTorch). Python 3.12 is required because the system Python 3.14 lacks wheels for some ML libraries.
```bash
uv sync --python 3.12
```

### 1.5 Download the reranker model (optional, otherwise automatic)
- **Does:** pre-downloads `BAAI/bge-reranker-base` (1.1 GB) into `~/.cache/huggingface`.
- **Supports:** the cross-encoder reranker (`src/rag/rerank.py`).
- **Run details:** about 30 seconds on this connection. If you skip it, the first reranked query downloads it. `du` on the cache folder shows ~20 KB because files are symlinks; check `du -shL` on the snapshot instead.
```bash
.venv/bin/python -W ignore -c "
from huggingface_hub import snapshot_download
print(snapshot_download('BAAI/bge-reranker-base', allow_patterns=['*.json','*.safetensors','*.txt','*.model','tokenizer*','sentencepiece*']))"
```

---

## 2. Data and indexing

### 2.1 Download the dataset and print schemas
- **Does:** downloads the `mindweave/help-desk-tickets` repo into `data/raw/` and prints each CSV's columns and two rows.
- **Supports:** data understanding. It showed that the CSVs live under `data/`, and that the repo ships macOS `._*.csv` junk files (the script skips them).
- **Run details:** about 546 KB of CSV plus metadata; seconds. Tables: tickets (1,000), comments (2,000), agents (10), categories (8), sla_breaches (1,249). License CC-BY-NC-4.0 (non-commercial). Before `uv sync` you can run it without the full environment: `uv run --no-project --python 3.12 --with huggingface_hub --with pandas python scripts/00_download.py`.
```bash
.venv/bin/python scripts/00_download.py
```

### 2.2 Build the index
- **Does:** builds one document per ticket (summary, description, category, public comments only, time-to-resolve), embeds them with `nomic-embed-text`, and rebuilds the Qdrant `tickets` collection (with a `summary` index needed for group-by).
- **Supports:** ingestion, chunking and indexing.
- **Run details:** deletes and recreates the collection every run. Embeds in batches of 64; roughly a minute or two (not timed). Internal comments are excluded on purpose.
```bash
PYTHONPATH=src .venv/bin/python -W ignore -m rag.ingest
```

---

## 3. Exploring retrieval

### 3.1 Compare dense, BM25 and hybrid (ticket level)
- **Does:** for a query, prints the top 5 from dense search, BM25, and RRF-fused hybrid, with scores.
- **Supports:** understanding retrieval. It showed score scales differ (cosine ~0.7 versus BM25 ~10), and that near-duplicate tickets fill the top-k.
- **Run details:** seconds. Uses the original ticket-level functions (`dense`, `sparse`, `hybrid`), not the grouped pool the pipeline now uses. Replace the query text freely.
```bash
PYTHONPATH=src .venv/bin/python -W ignore -c "
from rag.retrieve import dense, sparse, hybrid
q='outlook keeps asking for my password on my mac'
for name,f in [('dense',dense),('bm25',sparse),('hybrid',hybrid)]:
    print('==',name)
    for d in f(q,5): print(d['id'], d['summary'])
"
```

### 3.2 Run the full retrieval path with and without rewrite/rerank
- **Does:** runs `retrieve_docs` (grouped pool, dedupe by summary, optional rewrite and rerank) and prints each result with its rerank score and corpus-wide ticket count.
- **Supports:** pre-retrieval (rewrite), ranking and re-ranking, post-retrieval (cutoff, dedupe).
- **Run details:** about 1 second per query without rewrite; the rewrite adds one LLM call. The answerability floor is not applied here (only in `answer()`).
```bash
PYTHONPATH=src .venv/bin/python -W ignore -c "
from rag.pipeline import retrieve_docs
for q in ['printer','cant print to the warehouse label thing']:
    for label,kw in [('no rewrite',dict(use_rewrite=False)),('with rewrite',dict(use_rewrite=True))]:
        print(f'\n##### {q!r}  [{label} + rerank]')
        for d in retrieve_docs(q,use_rerank=True,top_n=5,**kw):
            print(f\"  {d['id']:4d} x{d['similar_count']:<2d} rerank={d['rerank_score']:+.2f}  {d['summary']}\")
"
```

### 3.3 Show the rewritten queries
- **Does:** prints three LLM rewrites of each input so you can see variance.
- **Supports:** pre-retrieval inspection.
- **Run details:** seconds; non-deterministic.
```bash
PYTHONPATH=src .venv/bin/python -W ignore -c "
from rag.pre_retrieval import rewrite
for q in ['printer','cant print to the warehouse label thing']:
    for i in range(3): print(repr(q),'->',repr(rewrite(q)))
"
```

---

## 4. Golden set and evaluation

### 4.1 Generate the golden set
- **Does:** splits the 56 distinct summaries 75/25 into train and test (`eval/split.json`), has the LLM paraphrase each test summary into a question (retrying up to 4 times if it shares too many words with the summary), and appends the 10 hand-written hard questions from `eval/hard_questions.json`. Writes `eval/golden.jsonl`. Every ticket sharing a summary is marked relevant.
- **Supports:** golden questions and eval questions.
- **Run details:** about 14 to 50 LLM calls. **Refuses to run if `eval/golden.jsonl` exists** unless you pass `--force`, because it would erase hand-added questions. The paraphrases need hand review (five ambiguous ones were deleted by hand in this project). `eval/golden_v1_easy.jsonl` is the first, too-easy version, kept for comparison.
```bash
PYTHONPATH=src .venv/bin/python -W ignore scripts/10_make_golden.py            # add --force to overwrite
```

### 4.2 Add your own golden question
- **Does:** appends one hand-written question to `eval/golden.jsonl`. `relevant_ids` come from a substring of an existing **held-out** summary.
- **Supports:** golden questions written by you.
- **Run details:** instant. Only the 14 test summaries are accepted; a miss prints the closest summaries. Use `--list` to see them and `--oos` for a question no ticket answers.
```bash
PYTHONPATH=src .venv/bin/python -W ignore scripts/13_add_golden.py --list
PYTHONPATH=src .venv/bin/python -W ignore scripts/13_add_golden.py "we came back from lunch and the support@ mailbox has 300 unread messages, all junk" "spam burst"
PYTHONPATH=src .venv/bin/python -W ignore scripts/13_add_golden.py --oos "what time does the cafeteria open on fridays"
```

### 4.3 Run the retrieval evaluation
- **Does:** for four configurations (baseline hybrid, +rewrite, +rerank, +rewrite+rerank) prints top1, hit@5, MRR and nDCG@5 for the `paraphrase`, `hard` and `ALL` tiers, then compares the best-match cosine of out-of-scope questions against in-scope ones. `--judge` adds an LLM faithfulness score.
- **Supports:** evaluation, ranking and re-ranking ablations, scoring.
- **Run details:** about 35 to 45 seconds (timed). With 19 in-scope questions, one question is about 5 points, so small differences are noise. The rewrite configurations vary between runs. `--judge` was never run.
```bash
PYTHONPATH=src .venv/bin/python -W ignore scripts/11_eval.py
PYTHONPATH=src .venv/bin/python -W ignore scripts/11_eval.py --judge     # not yet run
```

### 4.4 Failure analysis
- **Does:** for each in-scope question, with and without rewrite, shows where the target is lost: not in the candidate pool, ranked down by the reranker, or removed by the cutoff.
- **Supports:** diagnosing retrieval failures.
- **Run details:** about 1 to 2 minutes (not timed). It is how we found that 26% of questions never reached the pool. Note it still uses the older ticket-level `hybrid` and the 0.25 cutoff constant defined inside the script, so it reflects the earlier pipeline.
```bash
PYTHONPATH=src .venv/bin/python -W ignore scripts/12_failures.py
```

---

## 5. Experiments used to make design decisions

These compare variants on the same 19 in-scope questions. They are **in-sample**: the design was chosen after seeing these questions, so treat the numbers as optimistic.

### 5.1 Recall experiments
- **Does:** compares V0 (top 20 tickets), V1 (top 20 distinct summaries via Qdrant group-by), and V2 (V1 with summary-only embeddings), each reranked on full text and on summary only.
- **Supports:** retrieval recall. Result: grouped pool raised target-in-pool from 0.74 to 0.95; reranking on the summary beat reranking on full text (0.95 versus 0.89); summary-only embeddings did not help.
- **Run details:** creates a second collection `tickets_core` (1,000 points, embeds only the 56 unique summaries) and a keyword index on `summary`. About 1 to 2 minutes (not timed). Uses raw questions, so it is deterministic.
```bash
PYTHONPATH=src .venv/bin/python -W ignore scripts/14_recall_experiments.py
```

### 5.2 HyDE versus rewrite
- **Does:** compares raw, rewrite, HyDE replacing the query everywhere, and HyDE as an extra dense query only. LLM modes are run 3 times.
- **Supports:** pre-retrieval. Result: HyDE did not help (replacing the query hurt: hit@5 0.77); the remaining miss was a vocabulary gap the model could not bridge.
- **Run details:** 1 minute 46 seconds (timed), about 170 LLM calls. Uses the HyDE prompt that asks for a ticket title (the corpus has no reliable resolution text, only symptom summaries).
```bash
PYTHONPATH=src .venv/bin/python -W ignore scripts/15_hyde.py
```

### 5.3 Cutoff sweep and answerability floor
- **Does:** (1) sweeps the relative cutoff (none, 0.05, 0.10, 0.25) for raw and rewritten queries; (2) tests whether the best rerank score separates out-of-scope from in-scope questions at floors from 0.01 to 0.3.
- **Supports:** post-retrieval tuning. Result: cutoff 0.25 cost about 3 of 19 hits with rewrite; 0.05 kept all hits. A floor of 0.05 answers 84% of valid questions and rejects 6 of 7 out-of-scope; 0.10 rejects 7 of 7 but refuses about 21% of valid ones.
- **Run details:** 53 seconds (timed), about 78 LLM rewrite calls. Defaults chosen from this are `CUTOFF_REL = 0.05` and `ANSWER_FLOOR = 0.05` in `src/rag/config.py`.
```bash
PYTHONPATH=src .venv/bin/python -W ignore scripts/16_cutoff_and_floor.py
```

---

## 6. End-to-end answers and tracing

### 6.1 Ask one question
- **Does:** runs the whole pipeline (rewrite, grouped hybrid retrieval, rerank on summary, cutoff, floor, generate) and prints the answer, sources and `refused` field (`None`, `below_floor` or `model`).
- **Supports:** the generation step and the final user-facing behavior.
- **Run details:** about 3 to 10 seconds; the first call after a cold start is slower (models load). Questions below the floor return in under half a second without calling the generator. With no argument it asks a default VPN question.
```bash
PYTHONPATH=src .venv/bin/python -W ignore -m rag.pipeline "outlook keeps asking me to sign in on my macbook"
```

### 6.2 Answer check on the whole golden set
- **Does:** runs `answer()` on every golden question and reports how many out-of-scope questions were refused, how many in-scope questions were wrongly refused, and how many answers cite the right ticket. Prints the answer for any out-of-scope question that was not refused.
- **Supports:** answerability and refusal behavior.
- **Run details:** 26 full pipeline runs (not timed, a few minutes). Latest result: out-of-scope refused 7/7, in-scope refused 3/19 (all by the floor), 16 of 16 answered questions cite the right ticket. Generation varies between runs.
```bash
PYTHONPATH=src .venv/bin/python -W ignore scripts/17_answer_check.py
```

### 6.3 Tracing demo and latency by stage
- **Does:** runs three questions (two in-scope, one out-of-scope), flushes spans to Phoenix, reads them back over Phoenix's REST API, and prints the per-stage latency. Pass your own questions as arguments.
- **Supports:** tracing. Spans are named `rag.answer`, `pre.rewrite`, `embed`, `retrieve.hybrid_grouped`, `rerank.cross_encoder`, `generate`, in the `helpdesk-rag` Phoenix project.
- **Run details:** the three-question run (timed) took about 4.5 seconds per trace on average, but the first trace included model cold-start and took 9.9 seconds. Warm: generation about 78% of the time, rewrite 16%, rerank 3%. Open http://localhost:6006 to browse the traces. Spans from earlier scripts run before this change are in the Phoenix `default` project (about 1,500 traces).
```bash
PYTHONPATH=src .venv/bin/python -W ignore scripts/18_trace_demo.py
PYTHONPATH=src .venv/bin/python -W ignore scripts/18_trace_demo.py "my vpn drops every hour" "how do I order lunch"
```

---

## 7. Fine-tuning and MCP

All of section 7 has been run. The interactive ollmcp session (7.3) was smoke-tested only; I did not drive the chat UI.

### 7.1 Fine-tune the embedding model (run once; no gain measured)
- **Does:** generates (question, ticket) training pairs for the training summaries only (`eval/split.json`), caches them in `data/ft-embedder/pairs.jsonl`, then fine-tunes `BAAI/bge-small-en-v1.5` with in-batch negatives (2 epochs, batch 16, lr 2e-5) and saves it to `data/ft-embedder/final`.
- **Supports:** fine-tuning. The target was vocabulary-gap misses such as the "login approval prompts" question.
- **Run details:** pair generation is about 252 LLM calls (the first run; cached afterwards). Training itself took 12.8 seconds (32 steps, final train loss 0.18); a re-run with cached pairs took 25 seconds in total. Downloads `bge-small-en-v1.5` (about 130 MB) on first use. Needs the `accelerate` package (now in `pyproject.toml`). **Check Python's own exit code**: piping to `tail` hides a failure behind tail's exit code, which is how the first attempt looked successful when it had failed.
- **Known flaw:** tickets sharing a summary are near-identical, so in-batch negatives sometimes mark a correct match as wrong (false negatives). Not fixed.
```bash
mkdir -p data/ft-embedder
PYTHONPATH=src .venv/bin/python -W ignore scripts/20_finetune_embedder.py > data/ft-embedder/train.log 2>&1; echo "python exit code: $?"
```

### 7.1b Compare embedders before and after fine-tuning
- **Does:** embedding-only comparison at summary level (no BM25, no reranker) of `nomic-embed-text` (current index, vectors read from Qdrant), base `bge-small` and fine-tuned `bge-small`, on the 19 in-scope golden questions. Also runs a sanity check on training-style questions.
- **Supports:** evaluating fine-tuning, and comparing embedding models.
- **Run details:** under a minute (not timed precisely). Result: held-out top1 nomic 0.53, **bge-small base 0.84**, bge-small fine-tuned 0.79; hit@5 0.89, 1.00, 1.00. The sanity check scored 1.00 for all three, so it was saturated and uninformative. Fine-tuning showed **no measurable gain**; the base `bge-small` beat the current `nomic-embed-text` at the embedding stage. These are embedding-only numbers on 19 questions (query prefixes differ by model), not a full-pipeline result.
```bash
PYTHONPATH=src .venv/bin/python -W ignore scripts/21_eval_finetune.py
```

### 7.1c Test embedders in the real pipeline
- **Does:** runs the full pipeline (grouped hybrid pool, rerank on summary, cutoff, floor) with `nomic` (current), `bge-small`, and `bge-small` with its retrieval instruction prefix. Prints yardsticks (chance, BM25-only), 95% bootstrap CIs, paired better/worse/same counts against nomic, and answerability at the floor.
- **Supports:** evaluating an embedder swap, and learning how to read the numbers (see `docs/reading-the-numbers.md`).
- **Run details:** 1 minute 8 seconds (timed). Creates a second Qdrant collection `tickets_bge` (1,000 points). The embedder is selected by `EMBEDDER` in `src/rag/config.py` (`nomic` | `bge` | `bge-instr`); the collection by `COLLECTION`. Rewrites are generated once and shared across variants. Result: hit@5 1.00 vs 0.95, top1 identical (0.79) for 19/19 questions; the instruction prefix made no difference; bge rejected fewer out-of-scope questions at the same floor (71% vs 86%). The "[1.00,1.00]" CI is misleading: see the rule of three in the guide.
```bash
PYTHONPATH=src .venv/bin/python -W ignore scripts/22_embedder_pipeline.py
```

### 7.2 MCP server, tested with a tool-calling loop
- **Does:** `src/rag/mcp_server.py` exposes one tool, `search_tickets(query, top_n)`, over stdio. It runs the full pipeline with the answerability floor and returns one match per distinct problem (with how many tickets share it) or an explicit "no matching tickets, do not guess" note. `mcp.json` (project root) tells a client how to launch it.
- **Supports:** the ollmcp / agentic-retrieval part of the project.
- **Run details:** `scripts/23_mcp_test.py` starts the server, lists the tool, calls it directly (Part A), then plays the role of ollmcp (Part B): `qwen3:8b` sees the tool, decides whether to call it, gets the result and answers, for all golden questions plus 6 non-search prompts. About 5 minutes per mode (not precisely timed). Environment switches: `THINK=1` turns on model thinking (ollmcp enables it by default for qwen3), `MODES=nosys` runs only the no-system-prompt mode (ollmcp's default). Results (19 in-scope, 7 out-of-scope, 6 non-search): the tool was called for 19/19 IT questions and **0/6** chit-chat prompts; the target ticket was in the tool result for **16/19** (the same as the direct pipeline; the 3 misses are the floor refusing); out-of-scope answers said "no match" in 6/7 (no system prompt), 7/7 (with a system prompt), and effectively the same with thinking on (my phrase-matching regex undercounts, so read the printed answers). The first version failed (6/19 hits) because the model filled an optional `priority` argument with P1/P2/P3 on every call; the parameter was removed.
```bash
PYTHONPATH=src .venv/bin/python -W ignore scripts/23_mcp_test.py                          # both modes
THINK=1 MODES=nosys PYTHONPATH=src .venv/bin/python -W ignore scripts/23_mcp_test.py      # mimic ollmcp's defaults
```

### 7.3 Use it interactively with ollmcp
- **Does:** starts the real ollmcp client with the server from `mcp.json`. It connected and enabled `helpdesk-rag.search_tickets` in a headless smoke test (the interactive session itself I did not drive).
- **Supports:** trying the agentic flow by hand. Ask an IT problem ("outlook keeps asking me to sign in on my mac"), then something unrelated ("what is 17 times 23?") and check that it does **not** call the tool, then an unanswerable one ("how many vacation days do I have left?") and check that it says there is no match.
- **Run details:** needs Ollama, Docker (Qdrant) running. The server loads the reranker on its first call, so the first search is slower. ollmcp has no system prompt by default: without one, the model answered the lost-badge question from general knowledge, so set one (the one used in the test is `SYSTEM` in `scripts/23_mcp_test.py`) with ollmcp's system-prompt command. Quit with `/quit`. Type `/help` for commands.
```bash
ollmcp -j mcp.json -m qwen3:8b
```

## 8. Gotchas

- **"Connection refused" on :6333 or :6006** means the containers stopped (usually after a Docker restart). Run `docker compose up -d`. The data survives.
- **`10_make_golden.py` will not overwrite** an existing `eval/golden.jsonl` without `--force`.
- **Relevance is by summary.** There are only 56 distinct summaries, so every golden question has exactly one relevant summary (10 to 28 tickets). Results are deduplicated by summary, so P@k is not meaningful; use top1, hit@k, MRR and nDCG.
- **Metadata is noisy.** In this synthetic data, category, service and comments are assigned independently of the summary, so a label-printer ticket can sit under "Access Management". Do not trust category filters.
- **There is no reliable resolution text.** The dataset has no resolution field. The public comments are 24 canned lines, some of which sound like fixes ("Applied GPO update and forced policy refresh"), attached to tickets essentially at random. The system prompt says the tickets have no fix steps, but the model can still repeat one of those comments as if it were the fix (seen in a live answer), so treat any "how it was resolved" wording in answers as unreliable. This is a ticket-search and triage assistant, not a "how did we fix it" assistant.
- **A single-word NO_MATCH instruction in the prompt made `qwen3:8b` refuse 8 of 19 valid questions.** The pipeline uses the original prompt plus phrase matching instead. Re-run `scripts/17_answer_check.py` after any prompt change.
- **Defaults are tuned on 26 questions** (`CUTOFF_REL`, `ANSWER_FLOOR` in `src/rag/config.py`). Re-tune with `scripts/16_cutoff_and_floor.py` when the data or the questions change.
- **MCP tools: avoid optional arguments you do not need.** qwen3:8b filled an optional `priority` filter on every call, which hid the correct tickets. Keep tool schemas minimal.
- **Check Python's exit code, not a pipeline's.** A command ending in `| tail` or `| grep` reports the last command's status, so a crashed script can look like it succeeded.
- **Rewrites and answers are non-deterministic.** Repeat an LLM-dependent measurement a few times before drawing conclusions.

---

## 9. Video production (script, narration, animated clips)

The video plan is in `docs/video/script.md`. Animated clips are a Remotion project in `docs/video/anim/`; narration audio is generated from the script by `docs/video/narration/build_narration.py`. Every animation step is tied to a phrase in the narration (`beat()` in `anim/src/ui.tsx`), so changing the voice or the wording retimes the clips automatically.

### 9.1 Generate the narration (Kokoro neural voice)
- **Does:** speaks every segment of `script.md` one sentence at a time with Kokoro-82M (voice `af_heart` by default), joins them with pauses, normalizes to -16 LUFS, and writes `anim/public/narration/seg<N>.wav` plus the sentence timings `anim/src/narration.json`.
- **Setup (done once):** `brew install espeak-ng`; `uv venv --python 3.12 .venv` and `uv pip install --python .venv/bin/python kokoro soundfile` inside `docs/video/narration/` (an isolated environment). First use downloads about 330 MB of model weights plus a small spaCy model.
- **Run details:** about a minute for all 11 segments (not precisely timed). Total narration is about 7.2 minutes. Pronunciation fixes for jargon words live in `PRONOUNCE` in the script (for example "Qwen" is spoken "Kwen", "nomic" "Noh-mick"). `--lufs -14` makes it louder; `--loudness-only` re-levels existing files without re-speaking. The older macOS voice is `--engine say --voice Daniel` (run with plain `python3`).
```bash
cd docs/video/narration && .venv/bin/python build_narration.py --engine kokoro --voice af_heart
```

### 9.2 Audition voices
- **Does:** speaks the same jargon-heavy passage in several voices into `docs/video/narration/samples/` (gitignored); play with `afplay`.
- **Voices tried:** `af_heart`, `af_bella` (US female), `am_michael` (US male), `bm_george` (UK male), `bf_emma` (UK female), plus macOS Daniel.
```bash
cd docs/video/narration && .venv/bin/python make_samples.py
afplay samples/kokoro_af_heart.wav
```

### 9.3 Preview and render the animated clips
- **Does:** `npm run studio` opens Remotion Studio at http://localhost:3000 (also reachable from your LAN; stop it with Ctrl+C when done). `npm run render:all` renders the six clips to `docs/video/anim/out/*.mp4` (1920x1080, 30 fps, narration embedded).
- **Run details:** rendering all six clips takes a few minutes. The scripts use port 3100, so rendering works while Studio is open on 3000. Clip lengths follow the narration audio plus 2 seconds. First render downloads a headless Chrome. Remotion bundles its own ffmpeg; the system ffmpeg (`brew install ffmpeg`) is for checks and editing. Verify files with `ffprobe` (duration, streams) and `ffmpeg -af ebur128` (loudness).
```bash
cd docs/video/anim && npm run studio
cd docs/video/anim && npm run render:all
cd docs/video/anim && npx remotion render src/index.ts Recall out/Recall.mp4 --overwrite --port=3100   # one clip
```

### 9.4 Live-segment demos and the recording guide
- **Does:** the guide `docs/video/live-recording-guide.md` explains how to record the five live segments (3, 4, 8, 9, 10), with cue sheets timed to the narration audio, expected output and iMovie assembly steps. It is generated from `anim/src/narration.json`, so re-generate it after changing the narration.
- **Demo commands used on screen:** `docs/video/demo/seg3_data.py` (the data twist, about 1 s), `seg4_printer.py` (the printer problem, about 2 s), `scripts/19_demo_repl.py` (warm REPL with a per-question timer, used for segment 8; start-up and warm-up take about 10 s), `scripts/18_trace_demo.py` (segment 9; about 15 s, lists only its own traces in the order they ran). Helper files: `docs/video/demo/seg8_questions.txt`, `seg10_prompts.txt`, `ollmcp_system_prompt.txt`.
- **Run details:** `scripts/19_demo_repl.py` with `DEMO_WATCHDOG=1` prints a stack trace if a step stalls for more than 45 s (two unexplained multi-minute stalls happened during testing and could not be reproduced). `build_narration.py --only N` regenerates just segment N and keeps every other segment's audio and timings, so the rendered animated clips stay in sync.
```bash
python3 docs/video/make_live_guide.py
python docs/video/demo/seg3_data.py
python docs/video/demo/seg4_printer.py
python scripts/19_demo_repl.py
cd docs/video/narration && .venv/bin/python build_narration.py --engine kokoro --voice af_heart --only 9
```

### 9.5 Build the final video (replays, assembly, upload folder)
- **Does:** the five live segments are rendered as **terminal replays** of real captured output (`docs/video/anim/src/Terminal.tsx`, `LiveSegs.tsx`), each carrying an on-screen label saying so. Captures come from: `docs/video/demo/seg3_data.py`, `seg4_printer.py`, the demo REPL (`seg8.json`), `scripts/18_trace_demo.py` plus a full-resolution Phoenix screenshot, and a real ollmcp session driven through a pseudo-terminal (`docs/video/demo/capture_ollmcp.py`, using `pexpect` and the terminal emulator `pyte`). `docs/video/finalize.py` then joins all 11 clips, trims idle tails, fades in and out, and writes `docs/video/upload/` (video, `captions.srt`, `thumbnail.png`, `description.txt` with chapters, `tags.txt`, `README.txt`).
- **Run details:** assembly takes about 20 s (timed). Result: 7.2 minutes, 1080p30 H.264 with AAC at -16.4 LUFS, no black frames, 112 caption cues. Re-capturing ollmcp takes 1 to 3 minutes and needs Ollama and Docker running. ollmcp asks for confirmation on every tool call by default, so the capture turns that off with `/hil`; it also sets the system prompt through `/mc` > `sp`. Phoenix screenshots use a Remotion composition (`PhoenixShot`) because `chrome-headless-shell` hung on that page. `build_captures.py` bundles everything under `anim/public/captures` into `anim/src/captures.json`.
```bash
uv run --no-project --python 3.12 --with pexpect --with pyte python docs/video/demo/capture_ollmcp.py
python3 docs/video/demo/build_captures.py
cd docs/video/anim && for c in Seg3 Seg4 Seg8 Seg9 Seg10; do npx remotion render src/index.ts $c out/$c.mp4 --overwrite --port=3100; done
python3 docs/video/finalize.py
```
- **Gotchas:** the removal check in this environment blocks `rm` with an unquoted variable; write literal paths. Changing the narration voice or wording means regenerating narration, re-rendering every clip and re-running `finalize.py`.

