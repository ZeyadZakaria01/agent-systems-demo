# 25: C4′ provenance probe

**What to build:** A one-line probe in the "probes of the proposed C1′ and C4′, outside [P1]'s claims" section: does an entry's provenance resolve to a stored source message? C4′ extends C4 with a state component, the retained source (report §7.5). Expected [INFERENCE]: pass on the reference GEM, absent on upstream, the patch and the versioned row. Spec: user stories 9, 67, 72; Implementation Decisions "Stricter check pass criteria" (C4′ probe), "System adapter" (`resolve_source`); ticket "Answer the challenge list" (C3′ and C4′).

**Blocked by:** 21 (probe scoring and section)

**Status:** resolved

- [x] The adapter offers `resolve_source(entry)`: the stored source message that the entry's provenance points to, or an explicit nothing-value. `ingest` carries the source message where the system stores one.
- [x] The probe writes one value with a source message, reads the entry back and resolves its provenance. Resolves to that message → `pass`; the system has no source store, confirmed by a probe (no field or endpoint) → `absent`; it accepts a source but provenance does not resolve to it → `fail`.
- [x] The row is flagged as not claimed by [P1] and sits in the probes section.
- [x] Suite tests with stand-ins: one that stores and resolves passes; one that accepts a source but stores none fails; one with no source store is absent; the versioned row is absent.
- [x] Smoke run on upstream: the probe reads `absent` with its evidence.

## Comments

2026-10-21: Built. `System.resolve_source(entry)` (logged read; default `None`), `describe()` gains `accepts_source` (False default; MemState: `source_message` among request-model properties of its OpenAPI, `None` if unreadable) and `source_surface` (source-named request properties and paths). Field writes carry `source_message` only where `accepts_source`. Check `demo/checks/c4_prime.py`, row `C4′` (claim text starts "Not claimed by [P1]", probes section); `slug` maps `′` to `prime` so its snapshot does not collide with C4's. Absent when no source store (refuses when the schema is unreadable); fail when a source is accepted but provenance does not resolve to it or the write is rejected. Tests `tests/checks/test_c4_prime.py` (store+resolve pass, accepts-but-stores-none fail, dangling fail, versioned-row baseline absent). Smoke: `flock /tmp/gem-suite-live.lock python -m demo.run --systems upstream,baseline --checks 'C4′' --results-root /tmp/c4prime-smoke-146826` → upstream absent (`accepts_source: false`, `source_surface: {request_properties: [], paths: []}`), baseline absent. Departures: `MemStateSystem` does not implement `_resolve_source`; a patched server that stores sources would need it. The scorecard's section/column rendering is ticket 31; the flag is the claim text for now. Findings entry not added (smoke proves schema absence from the committed check, not a new MemState behaviour claim beyond reading its OpenAPI).
