# 05: C2(b) atomicity, C2(c) declarative policies, C3 propagation

**What to build:** Three scorecard rows: C2(b) atomicity, scored with the bad-edge ingest; C2(c) declarative policies, probed; and C3 propagation along extension edges, probed as in F7. The dependent-topic staleness window is reported too. Each `absent` carries the probe that confirmed it. Spec: user stories 17, 21, 22, 23, 30 (dependent window); report §9.4; ADR 0002.

**Blocked by:** 01 (C1 tracer bullet)

**Status:** resolved

- [x] C2(b) sends one `/v1/ingest new_topic` with valid fields and an edge to a non-existent topic, then classifies the outcome. An error with the topic or fields persisted is a partial commit (fail). Success with the edge reported applied is a soundness issue, reported as an observation. Neither outcome means not-scored.
- [x] C2(c) probes for declarative policies and scores absent, with the probe evidence attached, when the system exposes only numeric knobs.
- [x] C3 links B → A with an extension edge, and a second pair A → B. It updates A and reads B before and after revision. The verdict follows the scale, and absent only with that run as evidence.
- [x] The dependent-topic staleness window is reported. When C3 is absent it reads "unbounded (C3 absent)" and cites the C3 run.
- [x] The suite's tests assert, on the baseline: C2(b) not-scored, C2(c) absent, C3 absent.
- [x] Smoke run: a recorded upstream run prints all three rows and the window, with snapshots.

## Comments

Merged as `e8e86e4`; reviewed and fixed in `16f2bd5` (C2(b) matches under live title scopes, C2(c) whole-word match, C3 waits 15 s from the update). Smoke F17; C3 not re-recorded with the new wait.

- 2026-10-21, spec revision (this ticket stays resolved): C2(b)'s input becomes a second field with a missing `ref_topic_id` (F23, ticket 22); the edge input stays as a separate observation (F17). C3 and C2(c) get stricter pass criteria (ticket 24): a flag because of the extension edge with an association-edge control, and a runtime-added policy that rejects a violating write. Upstream stays `absent` on both.
