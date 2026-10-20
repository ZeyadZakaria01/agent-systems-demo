# 23: Case-level change table

**What to build:** The per-step change table lists the cases whose outcome changed between steps, beside each row's verdict. Step 3 fixes only the merge case of C4, so C4 reads `partial` on both steps; the table must still show "merge keeps history: broken → fixed". The table works on any chain of systems, so ticket 31 can use it for both chains. Spec: user story 13; Implementation Decisions "Scorecard output"; ticket "Close the suite audit's design gaps" item 2 (suite audit F2).

**Blocked by:** 03 (per-step runs and change table), 21 (verdict rules)

**Status:** ready-for-agent

- [ ] The change table takes a chain of systems and, per row, shows each system's verdict (changed cells marked) and, for each step in the chain, the cases whose outcome changed, for example `C4: partial → partial · merge keeps history: broken → fixed`. Rows with no case change list nothing.
- [ ] Case identity is stable across systems: a case has an id in the check, so a case n/a on one system and held on the next is shown as `n/a → held`.
- [ ] Step 1 is still compared with upstream verdict for verdict. Counts from random-ID tests are shown but not compared.
- [ ] `demo/changes.py` is generic over the chain, so the second chain (phase 1 → phase 2) needs no change.
- [ ] Suite tests with stand-in systems assert a row whose verdict is unchanged but whose case outcomes changed, and a row with no change.
- [ ] Smoke run: upstream, step 1 and step 2 or 3 (whichever exists) print the table with case-level lines.
