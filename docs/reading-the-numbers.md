# Reading the numbers: is this result acceptable or bad?

A metric on its own tells you almost nothing. This guide shows how to judge the numbers this project produces,
using real examples from it. Figures are from the 19 in-scope and 7 out-of-scope golden questions and were
current at the time of writing; re-run the scripts in `docs/commands.md` for fresh values.

## 1. Compare against yardsticks

Ask "compared to what?" before "is it high?".

| Yardstick | top1 | hit@5 | Where it comes from |
|---|---|---|---|
| Random guess (56 summaries) | 0.02 | 0.09 | 1/56 and 5/56 |
| BM25 only (no embeddings) | 0.21 | 0.37 | `scripts/22_embedder_pipeline.py` |
| Current pipeline (nomic + rerank) | 0.79 | 0.95 | same script |

hit@5 of 0.95 sounds excellent, but it is meaningful only because the trivial baselines are 0.09 and 0.37.
When a number is "high", find the trivial method that would also score high. If the gap is small, you have
not built much. Always compare against the **current system**, not just a floor: "bge scores 1.00" means little
when nomic scores 0.95.

## 2. Know your resolution

With n = 19 questions, **one question is worth 5.3 points**. Bootstrap 95% confidence intervals make this
concrete: top1 = 0.79 has an interval of about [0.58, 0.95], an 18-point band.

- A difference of one or two questions is noise. Do not act on it.
- Repeat LLM-dependent steps (query rewrite, generation). In this project, the "with rewrite" column flipped
  between embedders (nomic 1.00, bge 0.95) because of one question in one run.
- To detect a 5-point improvement reliably you need hundreds of questions, not dozens.

## 3. Use paired counts, not averages

Average scores hide how the systems differ. For two variants on the same questions, count the questions where
A is better, worse, or the same. bge versus nomic on hit@5: **better 1, worse 0, same 18**.

That is not evidence. A rough two-sided sign test (ties ignored):

| Better – worse | Approx. p-value | Reading |
|---|---|---|
| 1 – 0 | 1.0 | nothing |
| 5 – 0 | 0.06 | borderline |
| 6 – 0 | 0.03 | likely real |
| 8 – 1 | 0.04 | likely real |
| 8 – 2 | 0.11 | not convincing |
| 10 – 2 | 0.04 | likely real |

Rule of thumb: you need roughly **6–0, 8–1 or 10–2** before a difference is unlikely to be chance.
Even then it only shows the difference is probably not random on *these* questions, not that it generalizes.

## 4. Beware 100%

A result of 19/19 does not mean the true rate is 100%. The **rule of three**: with zero failures in n trials,
the true failure rate could still be up to about 3/n, here about **16%**. The printed bootstrap interval
`[1.00, 1.00]` for bge's hit@5 is misleading for the same reason: bootstrapping a sample with no failures
cannot invent any. Treat perfect scores on small sets as "no failures seen", not "no failures".

## 5. Set targets from the cost of errors, before measuring

There is no universal good number. Decide what a failure costs, write the targets down, then measure.
The targets below are **examples to replace with your own**:

| Metric | What it means to a user | Example target | Recent value | Verdict |
|---|---|---|---|---|
| hit@5 | the right problem is somewhere in the shown list | ≥ 0.90 | 0.95–1.00 | acceptable |
| top1 | the right problem is the first one shown | ≥ 0.90 to auto-answer; ~0.70 is fine for a suggestions list | 0.79 | OK for suggestions only |
| valid questions wrongly refused | "no match, open a ticket" when a match exists | ≤ 10% | 16% (3 of 19) | not acceptable yet |
| unanswerable questions reaching the generator | a confident answer to something we have no data on | ≤ 5% | 14% (1 of 7) | not acceptable if wrong answers are costly |

Two metrics can pull against each other: the answerability floor trades false refusals against leakage.
Lowering the floor from 0.10 to 0.05 answered 84% of valid questions instead of 79%, but let one out-of-scope
question through. Choose which error is cheaper, then set the threshold.

## 6. Test the stages separately

For any question the target must pass: be **in the candidate pool**, rank in the top 5, survive the reranker,
and survive the cutoff.

- **Pool recall is a ceiling.** Nothing downstream can recover a ticket that was never retrieved.
- If the final result is far below the pool, the reranker or cutoff is losing hits (the 0.25 cutoff cost about
  3 of 19 hits with rewrite).
- If the pool is low, fix retrieval (pool design, embeddings, query).
- `scripts/12_failures.py` and `scripts/14_recall_experiments.py` show which stage lost each question.

Evaluating a component in isolation can mislead. Base bge-small beat nomic by a wide margin when tested alone
(top1 0.84 vs 0.53), but in the full pipeline the reranker erased the gap (both 0.79).

## 7. Distrust your own tuning

- **In-sample optimism.** The cutoff, floor and design were chosen after looking at these same questions.
  Real performance on new questions will be lower; by how much is unknown until you test.
- **Too-easy evals.** If everything scores 1.00, the eval cannot discriminate. The first golden set did this.
  The fine-tuning sanity check also scored 1.00 for every model.
- **Leakage.** Never put golden-question wording into prompts or training data. One prompt draft nearly did
  this. Split by what must not be seen (here, by *summary*, not by ticket).
- **Synthetic data.** Templated tickets mean near-duplicates and noisy metadata, so scores are optimistic
  compared to real tickets.

## 8. Read the failures, not only the average

An average hides the cause. Print every miss, along with what was returned instead and what the scores were.
In this project the last remaining miss ("login approval prompts… new handset") was a vocabulary gap, not a
tuning problem, and the HyDE and fine-tuning experiments could not fix it. Only reading the case showed that.

## Checklist before believing a result

1. What are the trivial baselines, and how far above them is it?
2. How many questions, and how many questions is the difference?
3. Was it repeated, if an LLM was involved?
4. Paired better/worse counts, not just averages?
5. Which stage is the bottleneck (pool, ranking, cutoff, generation)?
6. Which error type matters more here, and does the number reflect it?
7. Were the questions used for tuning also used for the score?
8. Did you read the failures?
