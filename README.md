# Helpdesk RAG: a production-RAG learning project

**Goal:** an IT help-desk **ticket search and triage assistant**: "have we seen this before, how often, how urgent, how long did it take to resolve?"
([mindweave/help-desk-tickets](https://huggingface.co/datasets/mindweave/help-desk-tickets), synthetic, CC-BY-NC-4.0, non-commercial).
The free sample has `tickets` (1,000), `comments` (2,000), `agents` (10), `categories` (8). The full set has 10,000 tickets plus `sla_breaches`.

## Local stack (M2 Pro, 32 GB)

| Piece | Choice | Why |
|---|---|---|
| LLM runtime | **Ollama on the host (not Docker)** | Docker on macOS cannot use the Apple GPU. Containerised Ollama would run on CPU. |
| Generator | `qwen3:8b` (already pulled) | Reliable tool-calling, so it also works with ollmcp. |
| Embeddings | `nomic-embed-text` | Small, fast, and uses query/document prefixes. |
| Vector DB | **Qdrant (Docker)** | Payload filters for metadata, and it handles the hybrid and scale topics later. |
| Sparse | `rank-bm25` in-process | Teaches lexical vs semantic retrieval with no extra service. |
| Reranker | `BAAI/bge-reranker-base` cross-encoder | Runs locally on MPS or CPU. |
| Tracing | **Arize Phoenix (Docker)** | One container, OpenTelemetry, a UI at :6006. Langfuse v3 needs about 5 containers. |
| Agent / tools | **ollmcp** + FastMCP server | Your retrieval becomes an MCP tool that a local LLM chooses to call. |
| Python | `uv`, Python 3.12 | Your system Python 3.14 lacks wheels for some ML libraries. |

## Setup

```bash
cd helpdesk-rag
ollama pull nomic-embed-text            # ~270 MB; qwen3:8b is already installed
docker compose up -d                    # Qdrant :6333, Phoenix :6006
uv sync --python 3.12
uv run python scripts/00_download.py    # downloads ~546 kB CSV sample to data/raw/, prints schemas
```

Check that the printed file names match `TICKETS_CSV`, `COMMENTS_CSV` and `CATEGORIES_CSV` in `src/rag/config.py`. The column names are already mapped. For the full 10k set, fetch the Parquet or SQLite files from the same repo.

## Curriculum (do these in order)

Each step has one file to read, one command to run, and one thing to look at in Phoenix.

| # | Topic | File | Run |
|---|---|---|---|
| 1 | **Ingestion & chunking**: ticket plus comment thread as one document per ticket plus category join, **public comments only**, time-to-resolve; metadata payload | `src/rag/ingest.py` | `uv run python -m rag.ingest` |
| 2 | **Retrieval**: dense, BM25, hybrid with RRF, metadata filters | `retrieve.py` | |
| 3 | **Pre-retrieval**: query rewrite, HyDE | `pre_retrieval.py` | |
| 4 | **Ranking → re-ranking**: bi-encoder scores vs cross-encoder; compare `dense_score`, `rrf_score` and `rerank_score` on the same query | `rerank.py` | |
| 5 | **Post-retrieval**: score threshold, dedupe by summary ("seen 5x"), lost-in-the-middle reordering, context budget | `post_retrieval.py` | |
| 6 | **Generation + tracing**: grounded answer with citations; watch every stage appear as a span | `pipeline.py` | `PYTHONPATH=src uv run python -m rag.pipeline "VPN keeps disconnecting"` |
| 7 | **Golden questions**: paraphrase each held-out summary; **every ticket with that summary is relevant**; train/test split by summary. You review by hand | `scripts/10_make_golden.py` | `uv run python scripts/10_make_golden.py` |
| 8 | **Eval questions & metrics**: hit@k, MRR, P@k, nDCG@k per ablation, plus an LLM-judge for faithfulness | `scripts/11_eval.py` | `uv run python scripts/11_eval.py --judge` |
| 9 | **Fine-tuning**: train an embedder on synthetic (question, ticket) pairs. Hold out the golden tickets, then re-eval | `scripts/20_finetune_embedder.py` | |
| 10 | **Ollmcp / agentic RAG**: serve retrieval as an MCP tool | `mcp_server.py` | see below |

Run commands from the project root with `PYTHONPATH=src` (or `export PYTHONPATH=src`).
Run the `rag` modules as `-m rag.<name>`.

### Step 10: ollmcp

```bash
ollmcp --servers-json mcp.json --model qwen3:8b
```

The project ships an `mcp.json` that uses paths relative to the project root, so **start ollmcp from the project root**:

```json
{"mcpServers": {"helpdesk-rag": {"command": ".venv/bin/python",
  "args": ["-W", "ignore", "-m", "rag.mcp_server"], "env": {"PYTHONPATH": "src"}}}}
```

Ask "Our VPN drops every hour, any past fixes?" and watch the model call `search_tickets`.
Then ask a non-search question, such as "what's 2+2", and confirm it does **not** call the tool. That is tool-selection behaviour, and it is worth adding to your eval set.

## Things to try after the basics

1. **Ablation table**: the four configs in `11_eval.py` show what rewrite and rerank each buy you. Add HyDE and a metadata filter as new rows.
2. **Tracing**: in Phoenix, find the slowest span. It is usually the cross-encoder or the rewrite call. Decide whether each is worth its latency.
3. **Fine-tune honestly**: index with `data/ft-embedder/final` in place of `nomic-embed-text`, then compare against the baseline on the *same* golden set.
4. **Failure analysis**: list the golden questions with `hit@5 = 0`. Are they bad questions, bad chunking, or a vocabulary mismatch?
5. **Production hardening**: prompt-injection text in a ticket body, PII redaction, caching, an eval run in CI, and an index-refresh strategy.

## Caveats

- Only 56 summaries means about 42 train and 14 golden questions at the default split. Treat metrics as directional, and add your own hard questions. The full 10k set has the same templating.
- Fine-tuning will show small or noisy gains here. The lesson is the method: split by summary, avoid false negatives, compare against baseline.
- Try adding filters (`priority="P1"`, `category_id=3`), and test a question like "any P1 outages last month?". Pure semantic search handles that badly, which motivates metadata filtering and, in a later step, text-to-SQL for aggregate questions.
- Code was only syntax-checked; nothing has been downloaded or run. Expect small fixes on the first run, such as CSV file names.

## The companion video

The project is also the subject of a YouTube video about what worked and what did not. Its script, animation project, narration tooling and upload
files are in [`docs/video`](docs/video/README.md) (optional; the project does not depend on it). Command-by-command details for everything in this
repository are in [`docs/commands.md`](docs/commands.md), and [`docs/reading-the-numbers.md`](docs/reading-the-numbers.md) explains how to judge the results.

## Data and licenses

- **Dataset:** [mindweave/help-desk-tickets](https://huggingface.co/datasets/mindweave/help-desk-tickets) on Hugging Face (synthetic IT tickets), licensed **CC-BY-NC-4.0**: attribution required, **non-commercial use only**. The data is not stored in this repository; `scripts/00_download.py` fetches it into `data/raw/`. The small files in `eval/` (golden questions and the train/test split) are derived from it and carry the same terms.
- **Models and tools** (Ollama models, `BAAI/bge-reranker-base`, Qdrant, Arize Phoenix, Kokoro, Remotion, ollmcp) have their own licenses; check them before commercial use, in particular Remotion's company-size terms.
- Run every command from the project root. `data/`, `.venv/` and rendered media are git-ignored and can be regenerated; see `docs/commands.md`.
- **License for this code:** MIT, see [LICENSE](LICENSE). The MIT license covers the code and docs here only; the dataset and the third-party models and tools above keep their own terms (the dataset is non-commercial).

