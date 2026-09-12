# 30-Question Correctness Stress Test (2026-09-12)

An ad-hoc, larger correctness test beyond the 5-question Eval Set in `docs/eval-set.md`
(requested to probe deeper into retrieval/generation reliability). 30 Thai questions
across 3 difficulty tiers, each run once against the live system as of commit `503a206`
(bge-m3 embeddings, llama3.1:8b generation, threshold 0.3). This is a point-in-time
snapshot, not a repeatable automated test — re-running may give different results since
generation is non-deterministic.

**Result: 23/30 (77%) correct.** All failures cluster into 2 root causes, both discussed
below. The 30 questions live in `scripts/eval30.py`; re-run with:

```bash
PYTHONPATH=src ./venv/bin/python scripts/eval30.py > scripts/eval30_results.json
```

Grading is manual (compare each result against its `expected` field) - this isn't a
pass/fail assertion suite, and results may vary run to run since generation is
non-deterministic.

## Summary by tier

| Tier | Pass | Notes |
|------|------|-------|
| Easy | 9/10 | 1 failure (Q8) - see Root Cause 2 |
| Medium | 8/10 | 2 failures (Q17, Q18) - see Root Cause 1 for Q18 |
| Hard | 6/10 | 4 failures (Q22, Q23, Q25, Q27) - Q22/Q23/Q25 are Root Cause 1, Q27 is Root Cause 2 |

## Root Cause 1: financial-table term confusion (3 failures: Q18, Q22, Q23)

**Q18** ("What is PTT's total assets (สินทรัพย์รวม) in 2567?") got **1,081,739 ล้านบาท**
(cited page 112) instead of the correct **3,438,784 ล้านบาท** (page 5). Diagnosed directly
against `retrieve()`: the correct page-5 chunk (containing the real
`สินทรัพย์รวม 3,415,632 3,460,462 3,438,784` row for 2565/2566/2567) **wasn't even in the
top-5 retrieved chunks** for this query. Instead, the top-scored chunk (0.55) was page 112,
which contains `รวมสินทรัพย์หมุนเวียน` ("total **current** assets", a different line item)
- textually similar enough in Thai for `bge-m3` to rank it above the real answer.

Q22 (assets in 2566) and Q23 (which of the last 3 years had the highest assets) both
inherit this same wrong chunk and are wrong for the same reason - Q23's answer ("2566")
happens to match the correct year, but only by chance from wrong source numbers, not
genuine 3-year comparison.

This is a genuine **retrieval** failure, not a generation/citation failure, and it's the
exact risk flagged (and deliberately deferred) back in the original spec's Q6
(`.scratch/rag-pdf-ollama/spec.md`): recursive character chunking doesn't understand table
structure, so a dense financial-highlights table with several similarly-worded row labels
is a genuine weak spot for pure embedding similarity.

## Root Cause 2: wrong-but-plausible chunk chosen from otherwise-correct context (2 failures: Q8, Q27)

**Q8** ("Who is PTT's largest shareholder?") answered with unrelated info about a PTTGM
subsidiary director, instead of the correct **กระทรวงการคลัง (Ministry of Finance)**.
Diagnosed directly: the correct page-54 chunk **was** retrieved (rank 2, score 0.506,
clears the 0.3 threshold) - a page-184 PTTGM-subsidiary chunk narrowly outranked it
(0.512) and the model built its answer from that chunk instead, even though the real
answer was one chunk away in the same context window.

**Q27** ("Does the 6th-largest shareholder send a board representative?") answered "no
information available", when the source text literally states the answer
(page 54: "...ผู้ถือหุ้นลำดับที่ 6 ไม่ได้มีพฤติการณ์...ส่งผู้แทนมาเป็นกรรมการ..."). Whether
the relevant chunk was retrieved wasn't independently re-checked for this one, but given
Q8's pattern on the same page/topic, likely the same failure mode: correct chunk present
among several shareholder-adjacent ones, model didn't pick it out.

Unlike Root Cause 1, this isn't obviously a chunking/embedding problem - the right
information was plausibly available in context. This looks more like llama3.1:8b, when
several superficially-similar "shareholder/subsidiary company" chunks are all present,
not reliably identifying which one actually answers the specific question asked.

## Other single-question notes

- **Q17** (main business segments): answered with a different, smaller 3-item business
  categorization ("Hydrocarbon Business", "Natural Gas Business", "Gas Pipeline Business")
  than the 6-item list on page 4 that the question was aimed at, even though page 4 was
  among the cited sources. Possibly a legitimate alternate categorization used elsewhere
  in the report rather than a clear-cut error - not independently re-verified.
- **Q30** (fabricated Oscar-award premise): correctly concluded PTT never won one, but
  answered with **no citations at all**, meaning the model likely used general world
  knowledge rather than grounding the "no" in retrieved context, sidestepping the
  no-match path entirely. The conclusion happens to be true, but this is a way for an
  ungrounded claim to slip through as a normal-looking cited answer with an empty
  citation list.
- All fully out-of-scope/fabricated questions (Q28: fake SCG merger, Q29: BOT governor,
  Q30: Oscar) correctly avoided hallucinating a fabricated in-document fact - the
  no-match threshold mechanism itself is working as designed for clearly unrelated
  topics; the failures above are all about *related, plausible-sounding* content, not
  wholesale hallucination.
- The recurring cosmetic Thai-generation glitch noted earlier in `docs/eval-set.md`
  (a stray malformed character, e.g. "โลกอ ย่�ง" instead of "อย่าง") reappeared once
  (Q1) - still judged a `llama3.1:8b` sampling quirk, not a pipeline bug.

## Takeaway

Both root causes point at the same underlying, already-known trade-off: this pipeline
uses generic recursive-character chunking and top-k similarity search with no
table-awareness or re-ranking step (see spec Q6 and the "Out of Scope" section of
`.scratch/rag-pdf-ollama/spec.md`). It works well for prose-style facts (23/23 of the
non-financial-table, non-multi-entity questions passed) but is measurably weaker on
dense financial tables with similarly-worded rows, and on questions where several
similar entities (parent company vs. subsidiaries, one shareholder vs. another) compete
for the model's attention. Worth a follow-up ticket if financial-table accuracy or
multi-entity disambiguation matters for how this system gets used.
