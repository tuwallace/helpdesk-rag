"""Fine-tune a small embedding model on (question, ticket) pairs with in-batch negatives.
Train only on TRAIN summaries (eval/split.json); golden questions come from TEST summaries."""
import json, random, sys, ollama
sys.path.insert(0, "src")
from datasets import Dataset
from sentence_transformers import (SentenceTransformer, SentenceTransformerTrainer,
                                   losses, SentenceTransformerTrainingArguments)
from rag import config as C
from rag.ingest import build_docs

split = json.load(open("eval/split.json"))      # split by summary: test summaries never seen in training
train_sums = set(split["train"])
by_sum = {}
for d in build_docs():
    if d["summary"] in train_sums: by_sum.setdefault(d["summary"], []).append(d)
random.seed(1)
train = [x for v in by_sum.values() for x in random.sample(v, min(6, len(v)))]   # a few tickets per summary
import os
PAIRS = "data/ft-embedder/pairs.jsonl"                      # cache: generating pairs is ~250 LLM calls
os.makedirs("data/ft-embedder", exist_ok=True)
pairs = [json.loads(l) for l in open(PAIRS)] if os.path.exists(PAIRS) else []
for d in ([] if pairs else train):
    q = ollama.chat(model=C.GEN_MODEL, think=False, messages=[{"role": "user", "content":
        "Write one realistic employee question answered by this ticket. Output only the question.\n\n"
        + d["text"][:1200]}])["message"]["content"].strip()
    pairs.append({"anchor": q, "positive": d["text"]})   # same-summary dupes in a batch are false negatives; keep per-summary count small

if not os.path.exists(PAIRS):
    open(PAIRS, "w").write("".join(json.dumps(x) + "\n" for x in pairs))
print(f"{len(pairs)} training pairs")
model = SentenceTransformer("BAAI/bge-small-en-v1.5")
SentenceTransformerTrainer(
    model=model, train_dataset=Dataset.from_list(pairs),
    loss=losses.MultipleNegativesRankingLoss(model),
    args=SentenceTransformerTrainingArguments("data/ft-embedder", num_train_epochs=2,
        per_device_train_batch_size=16, learning_rate=2e-5, report_to="none"),
).train()
model.save("data/ft-embedder/final")
print("saved. Next: index with this model and re-run 11_eval.py to compare hit@5/MRR.")
