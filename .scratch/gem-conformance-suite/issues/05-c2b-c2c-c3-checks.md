# 05: C2(b) atomicity, C2(c) declarative policies, C3 propagation

**What to build:** Three scorecard rows: C2(b) atomicity, scored with the bad-edge ingest; C2(c) declarative policies, probed; and C3 propagation along extension edges, probed as in F7. The dependent-topic staleness window is reported too. Each `absent` carries the probe that confirmed it. Spec: user stories 17, 21, 22, 23, 30 (dependent window); report §9.4; ADR 0002.

**Blocked by:** 01 (C1 tracer bullet)

**Status:** ready-for-agent

- [ ] C2(b) sends one `/v1/ingest new_topic` with valid fields and an edge to a non-existent topic, then classifies the outcome. An error with the topic or fields persisted is a partial commit (fail). Success with the edge reported applied is a soundness issue, reported as an observation. Neither outcome means not-scored.
- [ ] C2(c) probes for declarative policies and scores absent, with the probe evidence attached, when the system exposes only numeric knobs.
- [ ] C3 links B → A with an extension edge, and a second pair A → B. It updates A and reads B before and after revision. The verdict follows the scale, and absent only with that run as evidence.
- [ ] The dependent-topic staleness window is reported. When C3 is absent it reads "unbounded (C3 absent)" and cites the C3 run.
- [ ] The suite's tests assert, on the baseline: C2(b) not-scored, C2(c) absent, C3 absent.
- [ ] Smoke run: a recorded upstream run prints all three rows and the window, with snapshots.
