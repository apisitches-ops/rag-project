# 05: No-match threshold fallback

**What to build:** Before asking the Generation Model to answer, the query flow checks whether any retrieved Chunk is actually relevant enough (via the chunk-selection/threshold function from ticket 01); if none clear the threshold, it reports that no relevant information was found instead of generating a guess from weak context.

**Blocked by:** 04

**Status:** ready-for-agent

- [ ] Retrieved Chunks and their similarity scores are passed through the chunk-selection function from ticket 01 before any Generation Model call is made
- [ ] If no Chunk clears the similarity threshold, the Generation Model is not called at all, and the user sees an explicit "no relevant information found" response
- [ ] If at least one Chunk clears the threshold, behavior is unchanged from ticket 04 (answer + citations)
- [ ] Asking a question clearly unrelated to the ingested Document(s) (e.g. about an unrelated topic) reliably produces the "no relevant information found" response rather than a fabricated answer
- [ ] Asking a question that ticket 04 already answered correctly still works the same way

## Comments

Done in `48a9055`. Code review found `select_chunks`'s filtered result was
discarded (only used as a gate, chunks rebuilt from the unfiltered list) - fixed
in `e3b00c4` alongside ticket 04's citation-parsing fixes.
