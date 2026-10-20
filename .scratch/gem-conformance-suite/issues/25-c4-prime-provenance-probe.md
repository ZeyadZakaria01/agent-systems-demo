# 25: C4′ provenance probe

**What to build:** A one-line probe in the "probes of the proposed C1′ and C4′, outside [P1]'s claims" section: does an entry's provenance resolve to a stored source message? C4′ extends C4 with a state component, the retained source (report §7.5). Expected [INFERENCE]: pass on the reference GEM, absent on upstream, the patch and the versioned row. Spec: user stories 9, 67, 72; Implementation Decisions "Stricter check pass criteria" (C4′ probe), "System adapter" (`resolve_source`); ticket "Answer the challenge list" (C3′ and C4′).

**Blocked by:** 21 (probe scoring and section)

**Status:** ready-for-agent

- [ ] The adapter offers `resolve_source(entry)`: the stored source message that the entry's provenance points to, or an explicit nothing-value. `ingest` carries the source message where the system stores one.
- [ ] The probe writes one value with a source message, reads the entry back and resolves its provenance. Resolves to that message → `pass`; the system has no source store, confirmed by a probe (no field or endpoint) → `absent`; it accepts a source but provenance does not resolve to it → `fail`.
- [ ] The row is flagged as not claimed by [P1] and sits in the probes section.
- [ ] Suite tests with stand-ins: one that stores and resolves passes; one that accepts a source but stores none fails; one with no source store is absent; the versioned row is absent.
- [ ] Smoke run on upstream: the probe reads `absent` with its evidence.
