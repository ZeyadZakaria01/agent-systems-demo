# Reinforcement precision and the engine latency ramps

Type: grilling
Status: resolved
Blocked by: 24

## Question

Report §9.2 adds two measurements. How is each defined and budgeted?

- **Reinforcement precision for C6**, "the share of salience increments that went to topics the answer used": on the `/v1` path there is no answer, so what counts as used (ground-truth topic per question, top-1, or the chat run's cited topics)?
- **Latency on both engines, with and without the extension**: up to four ramps to 2,000 topics on the laptop. Which ramps are needed to attribute each effect to one commit, and does the one-week build budget from [Review of the demo plan](21-review-of-the-demo-plan.md) still hold?

## Comments

- 2026-10-20, from [Patch packaging for the three-commit patch on LadybugDB](28-patch-packaging-for-three-commits.md): the conformance suite runs on each of the three commits; latency is left to this ticket. Commit 1 → commit 2 holds the engine constant, so it is the clean measure of what Zep's model costs MemState in speed; upstream → commit 1 is the engine comparison (F11).

## Answer

Resolved 2026-10-20 (Q1–Q5 accepted; Q1 and Q2 revised once). Facts: every `/v1/query` adds +0.1 salience to each returned topic, up to `top_k` = 8, unrelated ones included (F8); the patch does not touch salience; one 2,000-topic ramp took about 3 min on Kuzu and 2.5 min on LadybugDB (result-file times in `.runtime/probes-20261020/`).

- **Q1, "used" = the labelled topic.** Each storyline question is labelled with the topic that holds its answer (in `demo/workload.py`). A wrong answer is sorted with StateMemBench's first triage question ("is the gold fact in context? (no → retrieval failure)", `2608.19652v1.md:455`; aim "separately from retrieval and reasoning", `:126`): labelled topic not returned → *search failure*; returned but stored value wrong → *memory failure*. Reinforcement precision = increments to the labelled topic ÷ all increments; since every returned topic is bumped it equals Precision@k (`2602.05665.md:1329`), at most 1/8. Also reported: on how many questions the labelled topic was bumped at all. Rejected: top-1 (constant 1/8), chat-cited topics (n=1, different salience path).
- **Q2, number without a verdict.** C6 clause 1 is scored against its wording, "every retrieval that accesses $u_i$" (`2605.26252v1.md:218`): pass, with over-reinforcement. The paper's motivation is narrower, "User interaction patterns cannot reinforce useful information" (`:73`) and "Retrieval reinforces important facts" (`:178`); reinforcement precision measures the gap between the wording and that motivation. Correction: the "right units" aim is the paper's motivation, not our idea; the measurement is ours (report §7.7).
- **Q3, four ramps.** Upstream (Kuzu), commit 1, commit 2, commit 3, same undated writes and plain reads. Upstream → commit 1 = engine; commit 1 → 2 = Zep's model; commit 2 → 3 = whether merge by valid time slows ordinary writes (the ramp's distinct titles trigger no merge, but every ingest from 500 topics runs the duplicate check). Commit 3 also times 20 as-of reads at 2,000 topics. Merge duration itself is the merge revision window, timed in the ×20 merge test. Each ramp keeps the latency row of [Review of the demo plan](21-review-of-the-demo-plan.md): client latency of `/v1/query` and `/v1/ingest`, Reasoner time, archived count per step.
- **Q4, repeats.** One run per ramp while building, as a working check; three runs per ramp on the final commits at the end (~36 min); report median and range; a difference inside the range is "no measurable difference".
- **Q5, budget.** Replaces the one-week budget of Review of the demo plan: built in two days with subagents, nothing cut. Commit 2 is the critical path (commit 3 builds on it, per-commit runs need all three); the suite is built in parallel against the API in Bitemporal history model and API; runs are serial on the laptop.

Applied: report §9.2 (Repeats, Search vs. memory, Measurements) and §9.4 C6 row; `GLOSSARY.md` (Search failure, Memory failure, Reinforcement precision); map.
