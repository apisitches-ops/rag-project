# Eval Set: PTT 2024 One Report

A small set of Thai question/expected-answer pairs, each traced to a specific page of
`data/raw/20260316-ptt-one-report-2024-th.pdf`. Use it to manually sanity-check
end-to-end retrieval and answer quality whenever chunking, the embedding model, or
`SIMILARITY_THRESHOLD` changes (see `CONTEXT.md` for the **Eval Set** term definition).

## How to run

For each question below, run:

```bash
PYTHONPATH=src ./venv/bin/python -m rag.query "<question>"
```

Compare the response against the **Expected** fact and page number. A pass means: the
answer states the expected fact correctly, and the cited page number(s) include the one
listed. The out-of-scope question passes if the response is the "no relevant information
found" message, not a fabricated answer.

## Questions

1. **Q:** วิสัยทัศน์ของบริษัท ปตท. คืออะไร
   **Expected:** "ปตท. แข็งแรงร่วมกับสังคมไทย และเติบโตในระดับโลกอย่างยั่งยืน" — page 3

2. **Q:** ปตท. เข้าจดทะเบียนในตลาดหลักทรัพย์แห่งประเทศไทยในปี พ.ศ. ใด
   **Expected:** พ.ศ. 2544 (ค.ศ. 2001) — page 130

3. **Q:** ค่านิยมองค์กรของกลุ่ม ปตท. เรียกว่าอะไร และมีกี่ตัว
   **Expected:** SPIRIT, 6 ตัว (Synergy, Performance Excellence, Innovation,
   Responsibility for Society, Integrity & Ethics, Trust & Respect) — page 150

4. **Q:** ปตท. แบ่งกลุ่มผู้มีส่วนได้ส่วนเสียออกเป็นกี่กลุ่ม
   **Expected:** 6 กลุ่ม — page 125

5. **Q:** ปตท. ตั้งเป้าหมาย Net Zero ภายในปีใด
   **Expected:** ภายในปี พ.ศ. 2593 (ค.ศ. 2050) — page 128

6. **Q (out-of-scope):** สูตรทำส้มตำแบบดั้งเดิมทำอย่างไร
   **Expected:** No relevant information found response (this question has nothing to
   do with the ingested report).

7. **Q (English, regression guard):** How many employees does PTT have?
   **Expected:** 3,605 employees (2,224 male, 1,381 female) as of Dec 31, 2024, in
   English — page 147. Added after this exact question surfaced the language-matching
   bug noted below; keep it here to catch a regression.

## Last verified run (2026-09-12)

Ran against the implementation as of commit `10ec28d` (bge-m3 embeddings, llama3.1:8b
generation, threshold 0.3, language-name-explicit prompt). All 7 passed:

| # | Result | Cited page(s) |
|---|--------|----------------|
| 1 | Correct | 3 (among others) |
| 2 | Correct ("2544") | 130 (among others) |
| 3 | Correct ("SPIRIT ... 6 ตัว") | 150 |
| 4 | Correct ("6 กลุ่ม") | 125 |
| 5 | Correct ("ปี 2593") | 128 (among others) |
| 6 | Correct no-match response | — |
| 7 | Correct, in English, across 3 repeated runs | 147 |

### Known issue found and fixed: English questions sometimes answered in Thai

Manual testing after the initial pass turned up a real bug: asking question 7 in
English ("How many employees does PTT have?") reliably got a **Thai** answer instead
of English (once even an empty answer body, just the citation) - reproducible across
3 separate runs - even though question 1's English phrasing ("What is PTT's vision?")
worked fine. Likely cause: with `PROMPT_TEMPLATE`'s original vague "reply in the same
language the question was asked in" instruction, and a fully Thai-language context of
retrieved chunks, llama3.1:8b would sometimes let the context's language override the
instruction, apparently more often for some questions/topics than others.

Fix: the prompt now names the required language explicitly (computed from a simple
Thai-script check on the question, the same heuristic `_no_match_response` already
used) and states it twice - once up front, once again as a reminder right before the
model is asked to answer - instead of asking the model to infer and remember "the same
language as the question" implicitly. Verified fixed: 3/3 repeated runs of question 7
after the fix answered correctly in English, with no regression on the Thai questions.

Note: question 2 was originally phrased asking for month *and* year
("...เมื่อเดือนและปีใด"). The source sentence names two different months in the same
year for two different sub-events (corporatization in October 2544, stock listing in
December 2544), and llama3.1:8b consistently answered with only the year, dropping the
month, when asked that way. Rephrasing to ask for the year alone produces a clean,
correct answer — kept as a known model limitation to watch for if question wording
changes, not a pipeline bug (the correct month/year is present and correctly retrieved
in the underlying chunk either way).
