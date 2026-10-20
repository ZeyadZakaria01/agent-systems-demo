# 24: Stricter C3 and C2(c) checks

**What to build:** Pass criteria that certify an implementation, not only detect an absence, written and tested before the reference GEM is built (ticket "Reference GEM design" items 5 and 10; ADR 0007). C3 passes only if the dependent is flagged because of the extension edge; C2(c) passes only if a policy added at runtime rejects a violating write. Upstream stays `absent` with the F17 probe evidence. Spec: user stories 22, 23, 64, 65; Implementation Decisions "Stricter check pass criteria" (C3, C2(c)), "System adapter" (`add_policy`, flags in `read_topic`).

**Blocked by:** 05 (C2(b), C2(c), C3), 21 (verdict rules)

**Status:** ready-for-agent

- [ ] The adapter reads a topic's revision flag and its evidence through `read_topic` and offers `add_policy(rule)`; where a system has no such surface both return an explicit nothing-value. Both are documented in the adapter module.
- [ ] **C3 cases**, run on both pairs, B → A and A → B, each scored: (1) after A's field is updated, a read of the topic linked to A (B) before it is written carries a flag that names that update, with the updated field and timestamp as evidence; the extension edge is the cause, whatever its direction; (2) control: a topic linked to A only by an association edge is not flagged; (3) the flag clears when the flagged topic is next written. No flag and no propagation, confirmed by the F17 probe (B unchanged after a polled wait), is `absent`.
- [ ] **C2(c) cases:** (1) a policy "Deadline not before Start" added at runtime through `add_policy` rejects a write that sets Deadline before Start, and a read-back shows nothing saved; (2) control: an ordinary write (Deadline after Start) commits. No way to add a policy at runtime, confirmed by the schema probe, is `absent`.
- [ ] The pass criteria are written in the check modules' docstrings and match the spec; the reference GEM tickets (26, 27) are built against them.
- [ ] Suite tests with in-process stand-ins: a stand-in that flags every change to B fails case (2) and does not pass; one that never flags is absent; one that flags correctly passes; a stand-in whose runtime policy is ignored fails C2(c); one that rejects the ordinary write breaks the control. The versioned row reads absent on both rows.
- [ ] Smoke run on upstream: C3 and C2(c) still read `absent` with their probe evidence (F17).
