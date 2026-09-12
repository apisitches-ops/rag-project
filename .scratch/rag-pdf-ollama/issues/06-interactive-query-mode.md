# 06: Interactive query mode

**What to build:** Running the query entry point with no argument starts an interactive loop: the user can ask several questions in a row in one session, each handled with the same embed/retrieve/threshold/generate/citation behavior as the one-shot mode, until they choose to exit.

**Blocked by:** 05

**Status:** ready-for-agent

- [ ] Invoking the query entry point with no question argument starts an interactive loop instead of exiting immediately
- [ ] Each question typed into the loop is answered using the same behavior as one-shot mode: embedding, retrieval, threshold check, generation, and citations (or the no-match response)
- [ ] The user can ask multiple different questions in a single session without restarting the process
- [ ] There's a clear way to exit the loop and return to the shell
- [ ] Invoking the query entry point with a question argument still behaves exactly as in ticket 04/05 (one-shot, no loop)

## Comments

Done in `5098cbd`. Code review found the interactive loop wasn't resilient to a
failing query, and (across follow-up review passes) the citation-marker regex
needed several rounds of hardening for real llama3.1:8b output shapes (indented
markers, trailing remarks, markdown/punctuation decoration, prose false
positives) - fixed across `81075f9`, `9761f90`, and `10ec28d`.
