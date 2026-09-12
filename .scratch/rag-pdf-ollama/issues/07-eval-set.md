# 07: Eval Set for end-to-end quality checks

**What to build:** A small, hand-curated Eval Set of Thai questions with their expected answers/facts, drawn from the PTT 2024 One Report, plus a short written procedure for running them manually against the query entry point to sanity-check retrieval and answer quality whenever chunking, the embedding model, or the similarity threshold changes.

**Blocked by:** 05

**Status:** ready-for-agent

- [ ] The Eval Set contains 5-10 question/expected-answer pairs, each traceable to a specific fact and page in the PTT report
- [ ] Questions are phrased in Thai (matching the primary use case) and cover a mix of simple factual lookups and at least one question expected to fall outside the document's content (to exercise the no-match path)
- [ ] A short written procedure explains how to run each Eval Set question against the query entry point and what to compare the response against
- [ ] Running the full Eval Set against the current implementation is documented as producing correct, cited answers for the in-scope questions and a "no relevant information found" response for the out-of-scope one
