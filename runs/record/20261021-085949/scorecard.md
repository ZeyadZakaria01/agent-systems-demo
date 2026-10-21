| Row | Claimed by [P1]? | MemState: upstream (Kuzu) | MemState: step 1 | MemState: step 2 | MemState: step 3 | Reference: phase 1 | Reference: phase 2 | Baseline: versioned row |
|---|---|---|---|---|---|---|---|---|
| C1 (control) | yes: by construction (§4.3) | pass [snapshot](snapshots/upstream/c1.json) | pass [snapshot](snapshots/step1/c1.json) | pass [snapshot](snapshots/step2/c1.json) | pass [snapshot](snapshots/step3/c1.json) | pass [snapshot](snapshots/reference-gem-p1/c1.json) | pass [snapshot](snapshots/reference-gem-p2/c1.json) | pass [snapshot](snapshots/baseline/c1.json) |
| C2(a) | yes: by construction (§4.3) | fail [snapshot](snapshots/upstream/c2-a.json) | fail [snapshot](snapshots/step1/c2-a.json) | fail [snapshot](snapshots/step2/c2-a.json) | pass [snapshot](snapshots/step3/c2-a.json) | pass [snapshot](snapshots/reference-gem-p1/c2-a.json) | pass [snapshot](snapshots/reference-gem-p2/c2-a.json) | not-scored [snapshot](snapshots/baseline/c2-a.json) |
| C2(b) | yes: by construction (§4.3) | fail [snapshot](snapshots/upstream/c2-b.json) | fail [snapshot](snapshots/step1/c2-b.json) | fail [snapshot](snapshots/step2/c2-b.json) | fail [snapshot](snapshots/step3/c2-b.json) | pass [snapshot](snapshots/reference-gem-p1/c2-b.json) | pass [snapshot](snapshots/reference-gem-p2/c2-b.json) | pass [snapshot](snapshots/baseline/c2-b.json) |
| C2(c) | yes: by construction (§4.3) | absent [snapshot](snapshots/upstream/c2-c.json) | absent [snapshot](snapshots/step1/c2-c.json) | absent [snapshot](snapshots/step2/c2-c.json) | absent [snapshot](snapshots/step3/c2-c.json) | pass [snapshot](snapshots/reference-gem-p1/c2-c.json) | pass [snapshot](snapshots/reference-gem-p2/c2-c.json) | absent [snapshot](snapshots/baseline/c2-c.json) |
| C2(d) lapsed override | yes: by construction (§4.3) | pass [snapshot 1](snapshots/upstream/c2-d--story-1.json) [snapshot 2](snapshots/upstream/c2-d--story-2.json) | pass [snapshot 1](snapshots/step1/c2-d--story-1.json) [snapshot 2](snapshots/step1/c2-d--story-2.json) | pass [snapshot 1](snapshots/step2/c2-d--story-1.json) [snapshot 2](snapshots/step2/c2-d--story-2.json) | pass [snapshot 1](snapshots/step3/c2-d--story-1.json) [snapshot 2](snapshots/step3/c2-d--story-2.json) | pass [snapshot 1](snapshots/reference-gem-p1/c2-d--story-1.json) [snapshot 2](snapshots/reference-gem-p1/c2-d--story-2.json) | pass [snapshot 1](snapshots/reference-gem-p2/c2-d--story-1.json) [snapshot 2](snapshots/reference-gem-p2/c2-d--story-2.json) | pass [snapshot 1](snapshots/baseline/c2-d--story-1.json) [snapshot 2](snapshots/baseline/c2-d--story-2.json) |
| C3 | yes: §4's opening, "by construction"; not in §4.3 | absent [snapshot](snapshots/upstream/c3.json) | absent [snapshot](snapshots/step1/c3.json) | absent [snapshot](snapshots/step2/c3.json) | absent [snapshot](snapshots/step3/c3.json) | pass [snapshot](snapshots/reference-gem-p1/c3.json) | pass [snapshot](snapshots/reference-gem-p2/c3.json) | absent [snapshot](snapshots/baseline/c3.json) |
| C4 | yes: by construction (§4.3) | partial (2 cases n/a) [snapshot](snapshots/upstream/c4.json) | partial (2 cases n/a) [snapshot](snapshots/step1/c4.json) | partial (1 case n/a) [snapshot](snapshots/step2/c4.json) | partial (1 case n/a) [snapshot](snapshots/step3/c4.json) | pass [snapshot](snapshots/reference-gem-p1/c4.json) | pass [snapshot](snapshots/reference-gem-p2/c4.json) | pass (3 cases n/a) [snapshot](snapshots/baseline/c4.json) |
| C5-1 mechanism | yes: under transitions (§4.3) | pass (500 active topics, declared bound 500 topics (topic_count_soft_limit)) [snapshot](snapshots/upstream/c5-1--c5-mech.json) | pass (500 active topics, declared bound 500 topics (topic_count_soft_limit)) [snapshot](snapshots/step1/c5-1--c5-mech.json) | pass (500 active topics, declared bound 500 topics (topic_count_soft_limit)) [snapshot](snapshots/step2/c5-1--c5-mech.json) | pass (500 active topics, declared bound 500 topics (topic_count_soft_limit)) [snapshot](snapshots/step3/c5-1--c5-mech.json) | pass (401 active topics, declared bound 500 topics (β)) [snapshot](snapshots/reference-gem-p1/c5-1--c5-mech.json) | pass (401 active topics, declared bound 500 topics (β)) [snapshot](snapshots/reference-gem-p2/c5-1--c5-mech.json) | absent [snapshot](snapshots/baseline/c5-1--c5-mech.json) |
| C5-2 natural trajectory | yes: under transitions (§4.3) | fail (2000 active topics at n=2000, declared bound 500 topics (topic_count_soft_limit)) [snapshot 1](snapshots/upstream/c5-2--ramp-100-r1.json) [snapshot 2](snapshots/upstream/c5-2--ramp-100-r2.json) [snapshot 3](snapshots/upstream/c5-2--ramp-100-r3.json) [snapshot 4](snapshots/upstream/c5-2--ramp-250-r1.json) [snapshot 5](snapshots/upstream/c5-2--ramp-250-r2.json) [snapshot 6](snapshots/upstream/c5-2--ramp-250-r3.json) [snapshot 7](snapshots/upstream/c5-2--ramp-500-r1.json) [snapshot 8](snapshots/upstream/c5-2--ramp-500-r2.json) [snapshot 9](snapshots/upstream/c5-2--ramp-500-r3.json) [snapshot 10](snapshots/upstream/c5-2--ramp-1000-r1.json) [snapshot 11](snapshots/upstream/c5-2--ramp-1000-r2.json) [snapshot 12](snapshots/upstream/c5-2--ramp-1000-r3.json) [snapshot 13](snapshots/upstream/c5-2--ramp-2000-r1.json) [snapshot 14](snapshots/upstream/c5-2--ramp-2000-r2.json) [snapshot 15](snapshots/upstream/c5-2--ramp-2000-r3.json) | fail (2000 active topics at n=2000, declared bound 500 topics (topic_count_soft_limit)) [snapshot 1](snapshots/step1/c5-2--ramp-100-r1.json) [snapshot 2](snapshots/step1/c5-2--ramp-100-r2.json) [snapshot 3](snapshots/step1/c5-2--ramp-100-r3.json) [snapshot 4](snapshots/step1/c5-2--ramp-250-r1.json) [snapshot 5](snapshots/step1/c5-2--ramp-250-r2.json) [snapshot 6](snapshots/step1/c5-2--ramp-250-r3.json) [snapshot 7](snapshots/step1/c5-2--ramp-500-r1.json) [snapshot 8](snapshots/step1/c5-2--ramp-500-r2.json) [snapshot 9](snapshots/step1/c5-2--ramp-500-r3.json) [snapshot 10](snapshots/step1/c5-2--ramp-1000-r1.json) [snapshot 11](snapshots/step1/c5-2--ramp-1000-r2.json) [snapshot 12](snapshots/step1/c5-2--ramp-1000-r3.json) [snapshot 13](snapshots/step1/c5-2--ramp-2000-r1.json) [snapshot 14](snapshots/step1/c5-2--ramp-2000-r2.json) [snapshot 15](snapshots/step1/c5-2--ramp-2000-r3.json) | fail (2000 active topics at n=2000, declared bound 500 topics (topic_count_soft_limit)) [snapshot 1](snapshots/step2/c5-2--ramp-100-r1.json) [snapshot 2](snapshots/step2/c5-2--ramp-100-r2.json) [snapshot 3](snapshots/step2/c5-2--ramp-100-r3.json) [snapshot 4](snapshots/step2/c5-2--ramp-250-r1.json) [snapshot 5](snapshots/step2/c5-2--ramp-250-r2.json) [snapshot 6](snapshots/step2/c5-2--ramp-250-r3.json) [snapshot 7](snapshots/step2/c5-2--ramp-500-r1.json) [snapshot 8](snapshots/step2/c5-2--ramp-500-r2.json) [snapshot 9](snapshots/step2/c5-2--ramp-500-r3.json) [snapshot 10](snapshots/step2/c5-2--ramp-1000-r1.json) [snapshot 11](snapshots/step2/c5-2--ramp-1000-r2.json) [snapshot 12](snapshots/step2/c5-2--ramp-1000-r3.json) [snapshot 13](snapshots/step2/c5-2--ramp-2000-r1.json) [snapshot 14](snapshots/step2/c5-2--ramp-2000-r2.json) [snapshot 15](snapshots/step2/c5-2--ramp-2000-r3.json) | fail (2000 active topics at n=2000, declared bound 500 topics (topic_count_soft_limit)) [snapshot 1](snapshots/step3/c5-2--ramp-100-r1.json) [snapshot 2](snapshots/step3/c5-2--ramp-100-r2.json) [snapshot 3](snapshots/step3/c5-2--ramp-100-r3.json) [snapshot 4](snapshots/step3/c5-2--ramp-250-r1.json) [snapshot 5](snapshots/step3/c5-2--ramp-250-r2.json) [snapshot 6](snapshots/step3/c5-2--ramp-250-r3.json) [snapshot 7](snapshots/step3/c5-2--ramp-500-r1.json) [snapshot 8](snapshots/step3/c5-2--ramp-500-r2.json) [snapshot 9](snapshots/step3/c5-2--ramp-500-r3.json) [snapshot 10](snapshots/step3/c5-2--ramp-1000-r1.json) [snapshot 11](snapshots/step3/c5-2--ramp-1000-r2.json) [snapshot 12](snapshots/step3/c5-2--ramp-1000-r3.json) [snapshot 13](snapshots/step3/c5-2--ramp-2000-r1.json) [snapshot 14](snapshots/step3/c5-2--ramp-2000-r2.json) [snapshot 15](snapshots/step3/c5-2--ramp-2000-r3.json) | pass (396 active topics at n=2000, declared bound 500 topics (β)) [snapshot 1](snapshots/reference-gem-p1/c5-2--ramp-100-r1.json) [snapshot 2](snapshots/reference-gem-p1/c5-2--ramp-250-r1.json) [snapshot 3](snapshots/reference-gem-p1/c5-2--ramp-500-r1.json) [snapshot 4](snapshots/reference-gem-p1/c5-2--ramp-1000-r1.json) [snapshot 5](snapshots/reference-gem-p1/c5-2--ramp-2000-r1.json) | pass (396 active topics at n=2000, declared bound 500 topics (β)) [snapshot 1](snapshots/reference-gem-p2/c5-2--ramp-100-r1.json) [snapshot 2](snapshots/reference-gem-p2/c5-2--ramp-250-r1.json) [snapshot 3](snapshots/reference-gem-p2/c5-2--ramp-500-r1.json) [snapshot 4](snapshots/reference-gem-p2/c5-2--ramp-1000-r1.json) [snapshot 5](snapshots/reference-gem-p2/c5-2--ramp-2000-r1.json) | absent [snapshot 1](snapshots/baseline/c5-2--ramp-100-r1.json) [snapshot 2](snapshots/baseline/c5-2--ramp-100-r2.json) [snapshot 3](snapshots/baseline/c5-2--ramp-100-r3.json) [snapshot 4](snapshots/baseline/c5-2--ramp-250-r1.json) [snapshot 5](snapshots/baseline/c5-2--ramp-250-r2.json) [snapshot 6](snapshots/baseline/c5-2--ramp-250-r3.json) [snapshot 7](snapshots/baseline/c5-2--ramp-500-r1.json) [snapshot 8](snapshots/baseline/c5-2--ramp-500-r2.json) [snapshot 9](snapshots/baseline/c5-2--ramp-500-r3.json) [snapshot 10](snapshots/baseline/c5-2--ramp-1000-r1.json) [snapshot 11](snapshots/baseline/c5-2--ramp-1000-r2.json) [snapshot 12](snapshots/baseline/c5-2--ramp-1000-r3.json) [snapshot 13](snapshots/baseline/c5-2--ramp-2000-r1.json) [snapshot 14](snapshots/baseline/c5-2--ramp-2000-r2.json) [snapshot 15](snapshots/baseline/c5-2--ramp-2000-r3.json) |
| C6-1 clause 1 | yes: under transitions (§4.3) | pass (1 case n/a) [snapshot](snapshots/upstream/c6-1.json) | pass (1 case n/a) [snapshot](snapshots/step1/c6-1.json) | pass [snapshot](snapshots/step2/c6-1.json) | pass [snapshot](snapshots/step3/c6-1.json) | pass [snapshot](snapshots/reference-gem-p1/c6-1.json) | pass [snapshot](snapshots/reference-gem-p2/c6-1.json) | absent [snapshot](snapshots/baseline/c6-1.json) |
| C6-2 clause 2 | yes: under transitions (§4.3) | pass [snapshot](snapshots/upstream/c6-2.json) | pass [snapshot](snapshots/step1/c6-2.json) | pass [snapshot](snapshots/step2/c6-2.json) | pass [snapshot](snapshots/step3/c6-2.json) | pass [snapshot](snapshots/reference-gem-p1/c6-2.json) | pass [snapshot](snapshots/reference-gem-p2/c6-2.json) | absent [snapshot](snapshots/baseline/c6-2.json) |
| **Counts** | | pass 5 · partial 1 · fail 3 · absent 2 · not-scored 0 · error 0 | pass 5 · partial 1 · fail 3 · absent 2 · not-scored 0 · error 0 | pass 5 · partial 1 · fail 3 · absent 2 · not-scored 0 · error 0 | pass 6 · partial 1 · fail 2 · absent 2 · not-scored 0 · error 0 | pass 11 · partial 0 · fail 0 · absent 0 · not-scored 0 · error 0 | pass 11 · partial 0 · fail 0 · absent 0 · not-scored 0 · error 0 | pass 4 · partial 0 · fail 0 · absent 6 · not-scored 1 · error 0 |

**No regressions on the rows the suite checks:** none of the 18 rows measured at step 1 and step 3 is worse at step 3 (verdict and case level).

### Probes of the proposed C1′ and C4′, outside [P1]'s claims

Not claimed by [P1]: each time probe reads C1 as C1′ (the value valid on a date) and has two cells, whether the system accepts the dates the probe needs and whether it answers correctly given them; C4′ is C4 plus the retained source message.

| Probe | MemState: upstream (Kuzu) | MemState: step 1 | MemState: step 2 | MemState: step 3 | Reference: phase 1 | Reference: phase 2 | Baseline: versioned row |
|---|---|---|---|---|---|---|---|
| T1 accepts dates | no | no | yes | yes | yes | yes | no |
| T1 answers correctly given dates | absent [snapshot 1](snapshots/upstream/t1--retroactive.json) [snapshot 2](snapshots/upstream/t1--out-of-order.json) [snapshot 3](snapshots/upstream/t1--future-dated.json) [snapshot 4](snapshots/upstream/t1--lapsed-override-1.json) [snapshot 5](snapshots/upstream/t1--lapsed-override-2.json) [snapshot 6](snapshots/upstream/t1--as-of.json) [snapshot 7](snapshots/upstream/t1--future-value.json) | absent [snapshot 1](snapshots/step1/t1--retroactive.json) [snapshot 2](snapshots/step1/t1--out-of-order.json) [snapshot 3](snapshots/step1/t1--future-dated.json) [snapshot 4](snapshots/step1/t1--lapsed-override-1.json) [snapshot 5](snapshots/step1/t1--lapsed-override-2.json) [snapshot 6](snapshots/step1/t1--as-of.json) [snapshot 7](snapshots/step1/t1--future-value.json) | pass [snapshot 1](snapshots/step2/t1--retroactive.json) [snapshot 2](snapshots/step2/t1--out-of-order.json) [snapshot 3](snapshots/step2/t1--future-dated.json) [snapshot 4](snapshots/step2/t1--lapsed-override-1.json) [snapshot 5](snapshots/step2/t1--lapsed-override-2.json) [snapshot 6](snapshots/step2/t1--as-of.json) [snapshot 7](snapshots/step2/t1--future-value.json) | pass [snapshot 1](snapshots/step3/t1--retroactive.json) [snapshot 2](snapshots/step3/t1--out-of-order.json) [snapshot 3](snapshots/step3/t1--future-dated.json) [snapshot 4](snapshots/step3/t1--lapsed-override-1.json) [snapshot 5](snapshots/step3/t1--lapsed-override-2.json) [snapshot 6](snapshots/step3/t1--as-of.json) [snapshot 7](snapshots/step3/t1--future-value.json) | pass [snapshot 1](snapshots/reference-gem-p1/t1--retroactive.json) [snapshot 2](snapshots/reference-gem-p1/t1--out-of-order.json) [snapshot 3](snapshots/reference-gem-p1/t1--future-dated.json) [snapshot 4](snapshots/reference-gem-p1/t1--lapsed-override-1.json) [snapshot 5](snapshots/reference-gem-p1/t1--lapsed-override-2.json) [snapshot 6](snapshots/reference-gem-p1/t1--as-of.json) [snapshot 7](snapshots/reference-gem-p1/t1--future-value.json) | pass [snapshot 1](snapshots/reference-gem-p2/t1--retroactive.json) [snapshot 2](snapshots/reference-gem-p2/t1--out-of-order.json) [snapshot 3](snapshots/reference-gem-p2/t1--future-dated.json) [snapshot 4](snapshots/reference-gem-p2/t1--lapsed-override-1.json) [snapshot 5](snapshots/reference-gem-p2/t1--lapsed-override-2.json) [snapshot 6](snapshots/reference-gem-p2/t1--as-of.json) [snapshot 7](snapshots/reference-gem-p2/t1--future-value.json) | absent [snapshot 1](snapshots/baseline/t1--retroactive.json) [snapshot 2](snapshots/baseline/t1--out-of-order.json) [snapshot 3](snapshots/baseline/t1--future-dated.json) [snapshot 4](snapshots/baseline/t1--lapsed-override-1.json) [snapshot 5](snapshots/baseline/t1--lapsed-override-2.json) [snapshot 6](snapshots/baseline/t1--as-of.json) [snapshot 7](snapshots/baseline/t1--future-value.json) |
| T2 accepts dates | no | no | yes | yes | yes | yes | no |
| T2 answers correctly given dates | absent [snapshot 1](snapshots/upstream/t1--retroactive.json) [snapshot 2](snapshots/upstream/t1--out-of-order.json) [snapshot 3](snapshots/upstream/t1--future-dated.json) [snapshot 4](snapshots/upstream/t1--lapsed-override-1.json) [snapshot 5](snapshots/upstream/t1--lapsed-override-2.json) [snapshot 6](snapshots/upstream/t1--as-of.json) [snapshot 7](snapshots/upstream/t1--future-value.json) | absent [snapshot 1](snapshots/step1/t1--retroactive.json) [snapshot 2](snapshots/step1/t1--out-of-order.json) [snapshot 3](snapshots/step1/t1--future-dated.json) [snapshot 4](snapshots/step1/t1--lapsed-override-1.json) [snapshot 5](snapshots/step1/t1--lapsed-override-2.json) [snapshot 6](snapshots/step1/t1--as-of.json) [snapshot 7](snapshots/step1/t1--future-value.json) | pass [snapshot 1](snapshots/step2/t1--retroactive.json) [snapshot 2](snapshots/step2/t1--out-of-order.json) [snapshot 3](snapshots/step2/t1--future-dated.json) [snapshot 4](snapshots/step2/t1--lapsed-override-1.json) [snapshot 5](snapshots/step2/t1--lapsed-override-2.json) [snapshot 6](snapshots/step2/t1--as-of.json) [snapshot 7](snapshots/step2/t1--future-value.json) | pass [snapshot 1](snapshots/step3/t1--retroactive.json) [snapshot 2](snapshots/step3/t1--out-of-order.json) [snapshot 3](snapshots/step3/t1--future-dated.json) [snapshot 4](snapshots/step3/t1--lapsed-override-1.json) [snapshot 5](snapshots/step3/t1--lapsed-override-2.json) [snapshot 6](snapshots/step3/t1--as-of.json) [snapshot 7](snapshots/step3/t1--future-value.json) | pass [snapshot 1](snapshots/reference-gem-p1/t1--retroactive.json) [snapshot 2](snapshots/reference-gem-p1/t1--out-of-order.json) [snapshot 3](snapshots/reference-gem-p1/t1--future-dated.json) [snapshot 4](snapshots/reference-gem-p1/t1--lapsed-override-1.json) [snapshot 5](snapshots/reference-gem-p1/t1--lapsed-override-2.json) [snapshot 6](snapshots/reference-gem-p1/t1--as-of.json) [snapshot 7](snapshots/reference-gem-p1/t1--future-value.json) | pass [snapshot 1](snapshots/reference-gem-p2/t1--retroactive.json) [snapshot 2](snapshots/reference-gem-p2/t1--out-of-order.json) [snapshot 3](snapshots/reference-gem-p2/t1--future-dated.json) [snapshot 4](snapshots/reference-gem-p2/t1--lapsed-override-1.json) [snapshot 5](snapshots/reference-gem-p2/t1--lapsed-override-2.json) [snapshot 6](snapshots/reference-gem-p2/t1--as-of.json) [snapshot 7](snapshots/reference-gem-p2/t1--future-value.json) | absent [snapshot 1](snapshots/baseline/t1--retroactive.json) [snapshot 2](snapshots/baseline/t1--out-of-order.json) [snapshot 3](snapshots/baseline/t1--future-dated.json) [snapshot 4](snapshots/baseline/t1--lapsed-override-1.json) [snapshot 5](snapshots/baseline/t1--lapsed-override-2.json) [snapshot 6](snapshots/baseline/t1--as-of.json) [snapshot 7](snapshots/baseline/t1--future-value.json) |
| T3 accepts dates | no | no | yes | yes | yes | yes | no |
| T3 answers correctly given dates | absent [snapshot 1](snapshots/upstream/t1--retroactive.json) [snapshot 2](snapshots/upstream/t1--out-of-order.json) [snapshot 3](snapshots/upstream/t1--future-dated.json) [snapshot 4](snapshots/upstream/t1--lapsed-override-1.json) [snapshot 5](snapshots/upstream/t1--lapsed-override-2.json) [snapshot 6](snapshots/upstream/t1--as-of.json) [snapshot 7](snapshots/upstream/t1--future-value.json) | absent [snapshot 1](snapshots/step1/t1--retroactive.json) [snapshot 2](snapshots/step1/t1--out-of-order.json) [snapshot 3](snapshots/step1/t1--future-dated.json) [snapshot 4](snapshots/step1/t1--lapsed-override-1.json) [snapshot 5](snapshots/step1/t1--lapsed-override-2.json) [snapshot 6](snapshots/step1/t1--as-of.json) [snapshot 7](snapshots/step1/t1--future-value.json) | pass [snapshot 1](snapshots/step2/t1--retroactive.json) [snapshot 2](snapshots/step2/t1--out-of-order.json) [snapshot 3](snapshots/step2/t1--future-dated.json) [snapshot 4](snapshots/step2/t1--lapsed-override-1.json) [snapshot 5](snapshots/step2/t1--lapsed-override-2.json) [snapshot 6](snapshots/step2/t1--as-of.json) [snapshot 7](snapshots/step2/t1--future-value.json) | pass [snapshot 1](snapshots/step3/t1--retroactive.json) [snapshot 2](snapshots/step3/t1--out-of-order.json) [snapshot 3](snapshots/step3/t1--future-dated.json) [snapshot 4](snapshots/step3/t1--lapsed-override-1.json) [snapshot 5](snapshots/step3/t1--lapsed-override-2.json) [snapshot 6](snapshots/step3/t1--as-of.json) [snapshot 7](snapshots/step3/t1--future-value.json) | pass [snapshot 1](snapshots/reference-gem-p1/t1--retroactive.json) [snapshot 2](snapshots/reference-gem-p1/t1--out-of-order.json) [snapshot 3](snapshots/reference-gem-p1/t1--future-dated.json) [snapshot 4](snapshots/reference-gem-p1/t1--lapsed-override-1.json) [snapshot 5](snapshots/reference-gem-p1/t1--lapsed-override-2.json) [snapshot 6](snapshots/reference-gem-p1/t1--as-of.json) [snapshot 7](snapshots/reference-gem-p1/t1--future-value.json) | pass [snapshot 1](snapshots/reference-gem-p2/t1--retroactive.json) [snapshot 2](snapshots/reference-gem-p2/t1--out-of-order.json) [snapshot 3](snapshots/reference-gem-p2/t1--future-dated.json) [snapshot 4](snapshots/reference-gem-p2/t1--lapsed-override-1.json) [snapshot 5](snapshots/reference-gem-p2/t1--lapsed-override-2.json) [snapshot 6](snapshots/reference-gem-p2/t1--as-of.json) [snapshot 7](snapshots/reference-gem-p2/t1--future-value.json) | absent [snapshot 1](snapshots/baseline/t1--retroactive.json) [snapshot 2](snapshots/baseline/t1--out-of-order.json) [snapshot 3](snapshots/baseline/t1--future-dated.json) [snapshot 4](snapshots/baseline/t1--lapsed-override-1.json) [snapshot 5](snapshots/baseline/t1--lapsed-override-2.json) [snapshot 6](snapshots/baseline/t1--as-of.json) [snapshot 7](snapshots/baseline/t1--future-value.json) |
| T4 accepts dates | no | no | yes | yes | partly | yes | no |
| T4 answers correctly given dates | absent [snapshot 1](snapshots/upstream/t1--retroactive.json) [snapshot 2](snapshots/upstream/t1--out-of-order.json) [snapshot 3](snapshots/upstream/t1--future-dated.json) [snapshot 4](snapshots/upstream/t1--lapsed-override-1.json) [snapshot 5](snapshots/upstream/t1--lapsed-override-2.json) [snapshot 6](snapshots/upstream/t1--as-of.json) [snapshot 7](snapshots/upstream/t1--future-value.json) | absent [snapshot 1](snapshots/step1/t1--retroactive.json) [snapshot 2](snapshots/step1/t1--out-of-order.json) [snapshot 3](snapshots/step1/t1--future-dated.json) [snapshot 4](snapshots/step1/t1--lapsed-override-1.json) [snapshot 5](snapshots/step1/t1--lapsed-override-2.json) [snapshot 6](snapshots/step1/t1--as-of.json) [snapshot 7](snapshots/step1/t1--future-value.json) | pass [snapshot 1](snapshots/step2/t1--retroactive.json) [snapshot 2](snapshots/step2/t1--out-of-order.json) [snapshot 3](snapshots/step2/t1--future-dated.json) [snapshot 4](snapshots/step2/t1--lapsed-override-1.json) [snapshot 5](snapshots/step2/t1--lapsed-override-2.json) [snapshot 6](snapshots/step2/t1--as-of.json) [snapshot 7](snapshots/step2/t1--future-value.json) | pass [snapshot 1](snapshots/step3/t1--retroactive.json) [snapshot 2](snapshots/step3/t1--out-of-order.json) [snapshot 3](snapshots/step3/t1--future-dated.json) [snapshot 4](snapshots/step3/t1--lapsed-override-1.json) [snapshot 5](snapshots/step3/t1--lapsed-override-2.json) [snapshot 6](snapshots/step3/t1--as-of.json) [snapshot 7](snapshots/step3/t1--future-value.json) | absent [snapshot 1](snapshots/reference-gem-p1/t1--retroactive.json) [snapshot 2](snapshots/reference-gem-p1/t1--out-of-order.json) [snapshot 3](snapshots/reference-gem-p1/t1--future-dated.json) [snapshot 4](snapshots/reference-gem-p1/t1--lapsed-override-1.json) [snapshot 5](snapshots/reference-gem-p1/t1--lapsed-override-2.json) [snapshot 6](snapshots/reference-gem-p1/t1--as-of.json) [snapshot 7](snapshots/reference-gem-p1/t1--future-value.json) | pass [snapshot 1](snapshots/reference-gem-p2/t1--retroactive.json) [snapshot 2](snapshots/reference-gem-p2/t1--out-of-order.json) [snapshot 3](snapshots/reference-gem-p2/t1--future-dated.json) [snapshot 4](snapshots/reference-gem-p2/t1--lapsed-override-1.json) [snapshot 5](snapshots/reference-gem-p2/t1--lapsed-override-2.json) [snapshot 6](snapshots/reference-gem-p2/t1--as-of.json) [snapshot 7](snapshots/reference-gem-p2/t1--future-value.json) | absent [snapshot 1](snapshots/baseline/t1--retroactive.json) [snapshot 2](snapshots/baseline/t1--out-of-order.json) [snapshot 3](snapshots/baseline/t1--future-dated.json) [snapshot 4](snapshots/baseline/t1--lapsed-override-1.json) [snapshot 5](snapshots/baseline/t1--lapsed-override-2.json) [snapshot 6](snapshots/baseline/t1--as-of.json) [snapshot 7](snapshots/baseline/t1--future-value.json) |
| T5 accepts dates | no | no | yes | yes | partly | yes | partly |
| T5 answers correctly given dates | absent [snapshot 1](snapshots/upstream/t1--retroactive.json) [snapshot 2](snapshots/upstream/t1--out-of-order.json) [snapshot 3](snapshots/upstream/t1--future-dated.json) [snapshot 4](snapshots/upstream/t1--lapsed-override-1.json) [snapshot 5](snapshots/upstream/t1--lapsed-override-2.json) [snapshot 6](snapshots/upstream/t1--as-of.json) [snapshot 7](snapshots/upstream/t1--future-value.json) | absent [snapshot 1](snapshots/step1/t1--retroactive.json) [snapshot 2](snapshots/step1/t1--out-of-order.json) [snapshot 3](snapshots/step1/t1--future-dated.json) [snapshot 4](snapshots/step1/t1--lapsed-override-1.json) [snapshot 5](snapshots/step1/t1--lapsed-override-2.json) [snapshot 6](snapshots/step1/t1--as-of.json) [snapshot 7](snapshots/step1/t1--future-value.json) | pass [snapshot 1](snapshots/step2/t1--retroactive.json) [snapshot 2](snapshots/step2/t1--out-of-order.json) [snapshot 3](snapshots/step2/t1--future-dated.json) [snapshot 4](snapshots/step2/t1--lapsed-override-1.json) [snapshot 5](snapshots/step2/t1--lapsed-override-2.json) [snapshot 6](snapshots/step2/t1--as-of.json) [snapshot 7](snapshots/step2/t1--future-value.json) | pass [snapshot 1](snapshots/step3/t1--retroactive.json) [snapshot 2](snapshots/step3/t1--out-of-order.json) [snapshot 3](snapshots/step3/t1--future-dated.json) [snapshot 4](snapshots/step3/t1--lapsed-override-1.json) [snapshot 5](snapshots/step3/t1--lapsed-override-2.json) [snapshot 6](snapshots/step3/t1--as-of.json) [snapshot 7](snapshots/step3/t1--future-value.json) | absent [snapshot 1](snapshots/reference-gem-p1/t1--retroactive.json) [snapshot 2](snapshots/reference-gem-p1/t1--out-of-order.json) [snapshot 3](snapshots/reference-gem-p1/t1--future-dated.json) [snapshot 4](snapshots/reference-gem-p1/t1--lapsed-override-1.json) [snapshot 5](snapshots/reference-gem-p1/t1--lapsed-override-2.json) [snapshot 6](snapshots/reference-gem-p1/t1--as-of.json) [snapshot 7](snapshots/reference-gem-p1/t1--future-value.json) | pass [snapshot 1](snapshots/reference-gem-p2/t1--retroactive.json) [snapshot 2](snapshots/reference-gem-p2/t1--out-of-order.json) [snapshot 3](snapshots/reference-gem-p2/t1--future-dated.json) [snapshot 4](snapshots/reference-gem-p2/t1--lapsed-override-1.json) [snapshot 5](snapshots/reference-gem-p2/t1--lapsed-override-2.json) [snapshot 6](snapshots/reference-gem-p2/t1--as-of.json) [snapshot 7](snapshots/reference-gem-p2/t1--future-value.json) | absent [snapshot 1](snapshots/baseline/t1--retroactive.json) [snapshot 2](snapshots/baseline/t1--out-of-order.json) [snapshot 3](snapshots/baseline/t1--future-dated.json) [snapshot 4](snapshots/baseline/t1--lapsed-override-1.json) [snapshot 5](snapshots/baseline/t1--lapsed-override-2.json) [snapshot 6](snapshots/baseline/t1--as-of.json) [snapshot 7](snapshots/baseline/t1--future-value.json) |
| T6 accepts dates | no | no | yes | yes | yes | yes | no |
| T6 answers correctly given dates | absent [snapshot 1](snapshots/upstream/t1--retroactive.json) [snapshot 2](snapshots/upstream/t1--out-of-order.json) [snapshot 3](snapshots/upstream/t1--future-dated.json) [snapshot 4](snapshots/upstream/t1--lapsed-override-1.json) [snapshot 5](snapshots/upstream/t1--lapsed-override-2.json) [snapshot 6](snapshots/upstream/t1--as-of.json) [snapshot 7](snapshots/upstream/t1--future-value.json) | absent [snapshot 1](snapshots/step1/t1--retroactive.json) [snapshot 2](snapshots/step1/t1--out-of-order.json) [snapshot 3](snapshots/step1/t1--future-dated.json) [snapshot 4](snapshots/step1/t1--lapsed-override-1.json) [snapshot 5](snapshots/step1/t1--lapsed-override-2.json) [snapshot 6](snapshots/step1/t1--as-of.json) [snapshot 7](snapshots/step1/t1--future-value.json) | pass [snapshot 1](snapshots/step2/t1--retroactive.json) [snapshot 2](snapshots/step2/t1--out-of-order.json) [snapshot 3](snapshots/step2/t1--future-dated.json) [snapshot 4](snapshots/step2/t1--lapsed-override-1.json) [snapshot 5](snapshots/step2/t1--lapsed-override-2.json) [snapshot 6](snapshots/step2/t1--as-of.json) [snapshot 7](snapshots/step2/t1--future-value.json) | pass [snapshot 1](snapshots/step3/t1--retroactive.json) [snapshot 2](snapshots/step3/t1--out-of-order.json) [snapshot 3](snapshots/step3/t1--future-dated.json) [snapshot 4](snapshots/step3/t1--lapsed-override-1.json) [snapshot 5](snapshots/step3/t1--lapsed-override-2.json) [snapshot 6](snapshots/step3/t1--as-of.json) [snapshot 7](snapshots/step3/t1--future-value.json) | pass [snapshot 1](snapshots/reference-gem-p1/t1--retroactive.json) [snapshot 2](snapshots/reference-gem-p1/t1--out-of-order.json) [snapshot 3](snapshots/reference-gem-p1/t1--future-dated.json) [snapshot 4](snapshots/reference-gem-p1/t1--lapsed-override-1.json) [snapshot 5](snapshots/reference-gem-p1/t1--lapsed-override-2.json) [snapshot 6](snapshots/reference-gem-p1/t1--as-of.json) [snapshot 7](snapshots/reference-gem-p1/t1--future-value.json) | pass [snapshot 1](snapshots/reference-gem-p2/t1--retroactive.json) [snapshot 2](snapshots/reference-gem-p2/t1--out-of-order.json) [snapshot 3](snapshots/reference-gem-p2/t1--future-dated.json) [snapshot 4](snapshots/reference-gem-p2/t1--lapsed-override-1.json) [snapshot 5](snapshots/reference-gem-p2/t1--lapsed-override-2.json) [snapshot 6](snapshots/reference-gem-p2/t1--as-of.json) [snapshot 7](snapshots/reference-gem-p2/t1--future-value.json) | absent [snapshot 1](snapshots/baseline/t1--retroactive.json) [snapshot 2](snapshots/baseline/t1--out-of-order.json) [snapshot 3](snapshots/baseline/t1--future-dated.json) [snapshot 4](snapshots/baseline/t1--lapsed-override-1.json) [snapshot 5](snapshots/baseline/t1--lapsed-override-2.json) [snapshot 6](snapshots/baseline/t1--as-of.json) [snapshot 7](snapshots/baseline/t1--future-value.json) |
| C4′ provenance resolves to the stored source | absent [snapshot](snapshots/upstream/c4prime.json) | absent [snapshot](snapshots/step1/c4prime.json) | absent [snapshot](snapshots/step2/c4prime.json) | absent [snapshot](snapshots/step3/c4prime.json) | pass [snapshot](snapshots/reference-gem-p1/c4prime.json) | pass [snapshot](snapshots/reference-gem-p2/c4prime.json) | absent [snapshot](snapshots/baseline/c4prime.json) |

### Case-level controls

A control case is the ordinary path beside the case under test (C4's update, a probe's control date): a system that breaks it is blocking what it should allow.

| Row: control case | MemState: upstream (Kuzu) | MemState: step 1 | MemState: step 2 | MemState: step 3 | Reference: phase 1 | Reference: phase 2 | Baseline: versioned row |
|---|---|---|---|---|---|---|---|
| C2(c): control: an ordinary write (Deadline after Start) commits | — | — | — | — | held | held | — |
| C3: control: a topic linked to A only by an association edge is not flagged (B->A) | n/a | n/a | n/a | n/a | held | held | n/a |
| C3: control: a topic linked to A only by an association edge is not flagged (A->B) | n/a | n/a | n/a | n/a | held | held | n/a |
| C4: history survives a value update | held | held | held | held | held | held | held |
| T1: Dec 20: 2026-08-25 -> 'March 1' | — | — | held | held | held | held | — |
| T2: Sep 1: 2026-09-02 -> 'basic' | — | — | held | held | held | held | — |
| T3: Dec 5: 2026-11-05 -> 'premium' | — | — | held | held | held | held | — |
| T4: story 1: Oct 15: 2026-09-30 -> '$80' | — | — | held | held | — | held | — |
| T4: story 2: today: 2026-10-21 -> '$100' | — | — | held | held | — | held | — |
| T5: true on Feb 10: 2026-10-16 -> 'May 1' | — | — | held | held | — | held | — |
| T6: Dec 5: 2026-11-05 -> 'premium' | — | — | held | held | held | held | — |

### The merge (C2(a)) as existence

Existence, not a rate: in the arranged case the dropped topic holds the newer value, so one repetition that makes the superseded value current decides it. Beside it, the natural count on random IDs (shown, not compared between systems, never part of the verdict).

| System | Arranged case (existence) | Natural random-ID count |
|---|---|---|
| MemState: upstream (Kuzu) | fail [snapshot](snapshots/upstream/c2-a.json) — the merge does not make the superseded value current in the arranged case (existence): 20 of 20 arranged repetitions made March 15 current; 0 had no value or another value; 0 were not cases (no merge seen or arrangement not met) | 11/20 |
| MemState: step 1 | fail [snapshot](snapshots/step1/c2-a.json) — the merge does not make the superseded value current in the arranged case (existence): 20 of 20 arranged repetitions made March 15 current; 0 had no value or another value; 0 were not cases (no merge seen or arrangement not met) | 10/20 |
| MemState: step 2 | fail [snapshot](snapshots/step2/c2-a.json) — the merge does not make the superseded value current in the arranged case (existence): 20 of 20 arranged repetitions made March 15 current; 0 had no value or another value; 0 were not cases (no merge seen or arrangement not met) | 9/20 |
| MemState: step 3 | pass [snapshot](snapshots/step3/c2-a.json) — the merge does not make the superseded value current in the arranged case (existence): 0 of 20 arranged repetitions made March 15 current; 0 had no value or another value; 0 were not cases (no merge seen or arrangement not met) | 0/20 |
| Reference: phase 1 | pass [snapshot](snapshots/reference-gem-p1/c2-a.json) — the merge does not make the superseded value current in the arranged case (existence): 0 of 20 arranged repetitions made March 15 current; 0 had no value or another value; 0 were not cases (no merge seen or arrangement not met) | 0/20 |
| Reference: phase 2 | pass [snapshot](snapshots/reference-gem-p2/c2-a.json) — the merge does not make the superseded value current in the arranged case (existence): 0 of 20 arranged repetitions made March 15 current; 0 had no value or another value; 0 were not cases (no merge seen or arrangement not met) | 0/20 |
| Baseline: versioned row | not-scored [snapshot](snapshots/baseline/c2-a.json) — the merge does not make the superseded value current in the arranged case (existence): no arranged repetition was a case: 20 merges seen, 20 with the arrangement not met, 0 timeouts | n/a (no merge seen) |

### Staleness windows

| System | Window | Value | Run cited |
|---|---|---|---|
| upstream | Merge revision window | median 0.005 s, range 0.005-0.006 s over 20 repetitions | C2(a): [snapshots/upstream/c2-a.json] |
| upstream | Dependent-topic staleness window | unbounded (C3 absent) | C3: [snapshots/upstream/c3.json] |
| step1 | Merge revision window | median 0.004 s, range 0.004-0.005 s over 20 repetitions | C2(a): [snapshots/step1/c2-a.json] |
| step1 | Dependent-topic staleness window | unbounded (C3 absent) | C3: [snapshots/step1/c3.json] |
| step2 | Merge revision window | median 0.004 s, range 0.004-0.006 s over 20 repetitions | C2(a): [snapshots/step2/c2-a.json] |
| step2 | Dependent-topic staleness window | unbounded (C3 absent) | C3: [snapshots/step2/c3.json] |
| step3 | Merge revision window | median 0.007 s, range 0.005-0.01 s over 20 repetitions | C2(a): [snapshots/step3/c2-a.json] |
| step3 | Dependent-topic staleness window | unbounded (C3 absent) | C3: [snapshots/step3/c3.json] |
| reference-gem-p1 | Merge revision window | median 0 interactions, range 0-0 over 20 repetitions | C2(a): [snapshots/reference-gem-p1/c2-a.json] |
| reference-gem-p1 | Dependent-topic staleness window | median 0 interactions (B->A 0, A->B 0) | C3: [snapshots/reference-gem-p1/c3.json] |
| reference-gem-p2 | Merge revision window | median 0 interactions, range 0-0 over 20 repetitions | C2(a): [snapshots/reference-gem-p2/c2-a.json] |
| reference-gem-p2 | Dependent-topic staleness window | median 0 interactions (B->A 0, A->B 0) | C3: [snapshots/reference-gem-p2/c3.json] |
| baseline | Merge revision window | not applicable: no duplicate is ever created (same-topic write) | C2(a): [snapshots/baseline/c2-a.json] |
| baseline | Dependent-topic staleness window | unbounded (C3 absent) | C3: [snapshots/baseline/c3.json] |

### Per-step change table: upstream → step 1 → step 2 → step 3

| Row | upstream | step 1 | step 2 | step 3 |
|---|---|---|---|---|
| C1 (control) | pass | pass | pass | pass |
| C2(a) | fail | fail | fail | **fail → pass** (vs step 2) |
| C2(b) | fail | fail | fail | fail |
| C2(c) | absent | absent | absent | absent |
| C2(d) | pass | pass | pass | pass |
| C3 | absent | absent | absent | absent |
| C4 | partial | partial | partial | partial |
| C4′ | absent | absent | absent | absent |
| C5-1 | pass | pass | pass | pass |
| C5-2 | fail | fail | fail | fail |
| C6-1 | pass | pass | pass | pass |
| C6-2 | pass | pass | pass | pass |
| T1 | absent | absent | **absent → pass** (vs step 1) | pass |
| T2 | absent | absent | **absent → pass** (vs step 1) | pass |
| T3 | absent | absent | **absent → pass** (vs step 1) | pass |
| T4 | absent | absent | **absent → pass** (vs step 1) | pass |
| T5 | absent | absent | **absent → pass** (vs step 1) | pass |
| T6 | absent | absent | **absent → pass** (vs step 1) | pass |

- step 1 vs upstream: no change.
- step 2 vs step 1: changed: T1 (absent → pass), T2 (absent → pass), T3 (absent → pass), T4 (absent → pass), T5 (absent → pass), T6 (absent → pass).
- step 3 vs step 2: changed: C2(a) (fail → pass).
- step 1 cases: C2(a): fail → fail · random-ID count 11/20 → 10/20 (shown, not compared) (vs upstream)
- step 2 cases: C2(a): fail → fail · random-ID count 10/20 → 9/20 (shown, not compared) (vs step 1)
- step 2 cases: C4: partial → partial · a dated merge keeps both values, today reads April 20: n/a → broken (vs step 1)
- step 2 cases: C6-1: pass → pass · an as-of read raises the salience of the topic it returns: n/a → held (vs step 1)
- step 2 cases: T1: absent → pass · today: 2026-10-21 -> 'April 20': n/a → held · Dec 20: 2026-08-25 -> 'March 1': n/a → held · history intact: no value lost, expired entries copied and linked: n/a → held (vs step 1)
- step 2 cases: T2: absent → pass · today: 2026-10-21 -> 'pro': n/a → held · Sep 1: 2026-09-02 -> 'basic': n/a → held · history intact: no value lost, expired entries copied and linked: n/a → held (vs step 1)
- step 2 cases: T3: absent → pass · today: 2026-10-21 -> 'basic': n/a → held · Dec 5: 2026-11-05 -> 'premium': n/a → held · history intact: no value lost, expired entries copied and linked: n/a → held (vs step 1)
- step 2 cases: T4: absent → pass · story 1: Oct 15: 2026-09-30 -> '$80': n/a → held · story 1: today: 2026-10-21 -> '$50': n/a → held · story 1: history intact: no value lost, expired entries copied and linked: n/a → held · story 2: today: 2026-10-21 -> '$100': n/a → held · story 2: Oct 15: 2026-09-30 -> '$100': n/a → held · story 2: Oct 5: 2026-09-20 -> '$80': n/a → held · story 2: history intact: no value lost, expired entries copied and linked: n/a → held (vs step 1)
- step 2 cases: T5: absent → pass · true on Feb 10: 2026-10-16 -> 'May 1': n/a → held · believed on Feb 10: -> 'April 20': n/a → held · history intact: no value lost, expired entries copied and linked: n/a → held (vs step 1)
- step 2 cases: T6: absent → pass · today: 2026-10-21 -> NO_VALUE: n/a → held · Dec 5: 2026-11-05 -> 'premium': n/a → held · history intact: no value lost, expired entries copied and linked: n/a → held (vs step 1)
- step 3 cases: C2(a): fail → pass · the merge does not make the superseded value current in the arranged case (existence): broken → fixed · random-ID count 9/20 → 0/20 (shown, not compared) (vs step 2)
- step 3 cases: C4: partial → partial · history survives a merge: broken → fixed · a dated merge keeps both values, today reads April 20: broken → fixed (vs step 2)
- Changed cells are bold (`before → after`, naming the system compared with: the nearest earlier real verdict of the row, never an `error`).

### Per-step change table: phase 1 → phase 2

| Row | phase 1 | phase 2 |
|---|---|---|
| C1 (control) | pass | pass |
| C2(a) | pass | pass |
| C2(b) | pass | pass |
| C2(c) | pass | pass |
| C2(d) | pass | pass |
| C3 | pass | pass |
| C4 | pass | pass |
| C4′ | pass | pass |
| C5-1 | pass | pass |
| C5-2 | pass | pass |
| C6-1 | pass | pass |
| C6-2 | pass | pass |
| T1 | pass | pass |
| T2 | pass | pass |
| T3 | pass | pass |
| T4 | absent | **absent → pass** (vs phase 1) |
| T5 | absent | **absent → pass** (vs phase 1) |
| T6 | pass | pass |

- phase 2 vs phase 1: changed: T4 (absent → pass), T5 (absent → pass).
- phase 2 cases: T4: absent → pass · story 1: Oct 15: 2026-09-30 -> '$80': n/a → held · story 1: today: 2026-10-21 -> '$50': n/a → held · story 1: history intact: no value lost, expired entries copied and linked: n/a → held · story 2: today: 2026-10-21 -> '$100': n/a → held · story 2: Oct 15: 2026-09-30 -> '$100': n/a → held · story 2: Oct 5: 2026-09-20 -> '$80': n/a → held · story 2: history intact: no value lost, expired entries copied and linked: n/a → held (vs phase 1)
- phase 2 cases: T5: absent → pass · true on Feb 10: 2026-10-16 -> 'May 1': n/a → held · believed on Feb 10: -> 'April 20': n/a → held · history intact: no value lost, expired entries copied and linked: n/a → held (vs phase 1)
- Changed cells are bold (`before → after`, naming the system compared with: the nearest earlier real verdict of the row, never an `error`).

### Storyline: search failures vs memory failures

| System | top_k | Questions | Correct | Search failures | Memory failures | Events with unexpected stored state (titles, field values, edges) |
|---|---|---|---|---|---|---|
| upstream | 8 | 15 | 15 | 0 | 0 | 0 of 29 (edges compared on 5 of 5) |
| step1 | 8 | 15 | 15 | 0 | 0 | 0 of 29 (edges compared on 5 of 5) |
| step2 | 8 | 15 | 15 | 0 | 0 | 0 of 29 (edges compared on 5 of 5) |
| step3 | 8 | 15 | 15 | 0 | 0 | 0 of 29 (edges compared on 5 of 5) |
| reference-gem-p1 | 8 | 15 | 15 | 0 | 0 | 0 of 29 (edges compared on 5 of 5) |
| reference-gem-p2 | 8 | 15 | 15 | 0 | 0 | 0 of 29 (edges compared on 5 of 5) |
| baseline | 8 | 15 | 15 | 0 | 0 | 0 of 29 (edges n/a) |

### Storyline questions, per system

| Q | Ability | Question | Ground truth | upstream | step1 | step2 | step3 | reference-gem-p1 | reference-gem-p2 | baseline |
|---|---|---|---|---|---|---|---|---|---|---|
| Q01 | information extraction | Who is our contact at the design vendor? | Priya | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) |
| Q02 | knowledge update | What is the deadline of the Website Redesign? | April 20 | correct (rank 2) | correct (rank 2) | correct (rank 2) | correct (rank 2) | correct (rank 2) | correct (rank 2) | correct (rank 2) |
| Q03 | knowledge update | What is the total budget for the website redesign? | $46,500 | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) |
| Q04 | knowledge update | What time is the weekly sync meeting? | 11:30 | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) |
| Q05 | information extraction | On which day is the weekly sync meeting held? | Tuesday | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) |
| Q06 | knowledge update | Who is on the website redesign team? | Alice (Frontend lead), Bob (Backend), Erin (QA) | correct (rank 2) | correct (rank 2) | correct (rank 2) | correct (rank 2) | correct (rank 2) | correct (rank 2) | correct (rank 2) |
| Q07 | knowledge update | What is Alice's role on the website project? | Frontend lead | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) |
| Q08 | knowledge update | When does user testing start for the website redesign? | April 13 | correct (rank 3) | correct (rank 3) | correct (rank 3) | correct (rank 3) | correct (rank 3) | correct (rank 3) | correct (rank 3) |
| Q09 | knowledge update | When is the website launch milestone? | April 20 | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) |
| Q10 | information extraction | Who approves the redesign budget? | Dana | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) |
| Q11 | knowledge update | What is the current status of the website redesign project? | Complete | correct (rank 2) | correct (rank 2) | correct (rank 2) | correct (rank 2) | correct (rank 2) | correct (rank 2) | correct (rank 2) |
| Q12 | knowledge update | How much money is set aside for the site revamp? | $46,500 | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) |
| Q13 | information extraction | Which room do the weekly team gatherings use? | Room 4B | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) |
| Q14 | knowledge update | What cuisine does the team want for lunch? | Mexican | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) |
| Q15 | knowledge update | When is the design vendor's mockup delivery due? | March 22 | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) | correct (rank 1) |

### Reinforcement precision (beside C6 clause 1; no verdict)

| System | Increments to labelled topic | All increments | Reinforcement precision | Questions with labelled topic bumped | Precision@k from returned lists |
|---|---|---|---|---|---|
| upstream | 1.5 | 12 | 0.125 | 15 of 15 | 0.125 (equal) |
| step1 | 1.5 | 12 | 0.125 | 15 of 15 | 0.125 (equal) |
| step2 | 1.5 | 12 | 0.125 | 15 of 15 | 0.125 (equal) |
| step3 | 1.5 | 12 | 0.125 | 15 of 15 | 0.125 (equal) |
| reference-gem-p1 | 1.5 | 12 | 0.125 | 15 of 15 | 0.125 (equal) |
| reference-gem-p2 | 1.5 | 12 | 0.125 | 15 of 15 | 0.125 (equal) |
| baseline | n/a | n/a | n/a | n/a | n/a |

Reinforcement precision = salience increments to the labelled topic / all increments over the storyline questions. It carries no verdict. Because every returned topic is bumped, it equals Precision@k (micro-averaged over the questions: labelled topics returned / topics returned), at most 1/k per question with one labelled topic (1/8 at the default top_k of 8). n/a: the system keeps no salience. Limit: only the storyline's own topics are read for salience, so on a live server that already holds other topics a bumped foreign topic is not in 'all increments' and precision can read above Precision@k ([INFERENCE]: not run against a live database; the 'DIFFERENT' flag would show it).

### Over-flagging (one chain, beside C3)

Measurement, not a verdict, beside the C3 row (report §5.5, "how many hops"). One chain A ← B ← C ← D over extension edges; A's field is updated; B and C need revision, D does not depend on the updated field (the anti-trap). *Missed* = needed and not flagged; *not needed* = flagged and not needed. No MemState system is measured: none propagates (F17).

| System | Propagation | Flags raised | Flags needed | Flags missed | Flags not needed |
|---|---|---|---|---|---|
| reference-gem-p1 | one hop | 1 (B) | 2 (B, C) | 1 (C) | 0 (none) |
| reference-gem-p1 | transitive walk | 3 (B, C, D) | 2 (B, C) | 0 (none) | 1 (D) |

### Chat cases (recorded, n = 1 each, hand-graded; no verdict)

Each case is one recorded Ollama chat run on MemState, replayed from `demo/recordings/` without a server (`python -m demo.chat_run replay`). The grade slots are empty until a person fills them in. A recording is one sample of a 2B model: the other takes of a case are in `demo/recordings/attempts/`, and `docs/journal.md` says how many were made.

#### Bad merge on upstream: the re-explained Website Redesign is merged over the original (`bad-merge-20261021-085949.json`)

Recorded 2026-10-21T06:49:07+00:00 (run `20261021-085949`, n = 1, graded by hand). System: upstream, commit 945d7c4, MemState engine module: kuzu, DB `/home/zeyad/work/agent-systems-demo/.runtime/gem-suite/20261021-085949/upstream-chat-bad-merge/memstate.kuzu`. LLM: ollama `qwen3.5:2b` at http://127.0.0.1:11435 (think-off proxy, ADR 0003) -> Ollama :11434; no `intent_override`; no `model` in the request (the server's `MEMSTATE_OLLAMA_MODEL`); no Groq; no judge.

29 storyline events and the re-explained Website Redesign (`1a2c4e22-90c9-4ab6-b825-62e620d275ae`, Deadline = April 20) were written through `/v1`; the merge 0.01 s after the trigger kept `1a2c4e22-90c9-4ab6-b825-62e620d275ae` and deleted `9ebe3e10-f813-4f74-b3d4-8e634bd016b6` (the original; as arranged).
The merge lost: Deadline: April 20 (pm-email, reason: vendor delay), March 15 (kickoff-notes). Fields only the original held and still on the survivor: Status, Team.

##### Turns

- **Q02** [knowledge update] What is the deadline of the Website Redesign?
  - ground truth: April 20
  - answer: I found it. According to the topic "Website Redesign" in my memory, the deadline is April 20th. This information has been stored as a string field with history that shows it has only one change record.
  - answer contains every word of the ground truth: no (a match, not a grade)
  - route: query (classifier); tool calls: memory_graph_snapshot
  - latency: 2,535 ms; model qwen3.5:2b (ollama)
  - state violation: C4 violated on Deadline: history entries lost April 20 (pm-email, reason: vendor delay); March 15 (kickoff-notes); values gone from the history: March 15; current value now April 20
  - state changed by the turn itself: no
  - hand grade: [ ] (empty); note: (empty)
- **Q06** [knowledge update] Who is on the website redesign team?
  - ground truth: Alice (Frontend lead), Bob (Backend), Erin (QA)
  - answer: The Website Redesign team is composed of three members: - **Alice** - frontend lead - **Bob** - backend - **Erin** - QA
  - answer contains every word of the ground truth: yes (a match, not a grade)
  - route: query (classifier); tool calls: memory_list_topics, memory_get_topic_schema
  - latency: 2,504 ms; model qwen3.5:2b (ollama)
  - state violation: none on Team (current value Alice (Frontend lead), Bob (Backend), Erin (QA), no entry lost); the merge did lose history elsewhere (Deadline)
  - state changed by the turn itself: no
  - hand grade: [ ] (empty); note: (empty)
- **Q11** [knowledge update] What is the current status of the website redesign project?
  - ground truth: Complete
  - answer: Based on the data I've retrieved from the graph: The **Website Redesign project** has an overall status of **Complete**. However, the current breakdown shows: - **Deadline**: April 20 - **Status**: Complete (with three previous entries showing it was "In progress" during planning and now reflects as complete) - **Team**: Alice (Frontend lead), Bob (Backend), Erin (QA) The project appears to have moved from the "Planning" phase through "In progress" and is now in its final completion state.
  - answer contains every word of the ground truth: yes (a match, not a grade)
  - route: query (classifier); tool calls: memory_list_topics, memory_get_topic
  - latency: 5,029 ms; model qwen3.5:2b (ollama)
  - state violation: none on Status (current value Complete, no entry lost); the merge did lose history elsewhere (Deadline)
  - state changed by the turn itself: no
  - hand grade: [ ] (empty); note: (empty)

#### Two weeks ago on step 3: "I started my new job two weeks ago", then "how long have I been there?" (`two-weeks-20261021-085949.json`)

Recorded 2026-10-21T06:49:21+00:00 (run `20261021-085949`, n = 1, graded by hand). System: bitemporal patch step 3 (cb5d48c, LadybugDB), commit cb5d48c, MemState engine module: ladybug, DB `/home/zeyad/work/agent-systems-demo/.runtime/gem-suite/20261021-085949/step3-chat-two-weeks/memstate.lbug`. LLM: ollama `qwen3.5:2b` at http://127.0.0.1:11435 (think-off proxy, ADR 0003) -> Ollama :11434; no `intent_override`; no `model` in the request (the server's `MEMSTATE_OLLAMA_MODEL`); no Groq; no judge.

A fresh database: nothing written through `/v1` and no topic seeded. Two separate chat requests follow: reference time 2026-10-07 ("two weeks ago" means 2026-09-23), then reference time 2026-10-21 (the run day, 2026-10-21; the story (Oct 6, Oct 20) is shifted by +1 day(s) so that its last day is the run day). Both routes are the router's.

##### Turns

- **W1** [temporal reasoning] I started my new job two weeks ago
  - reference time sent: 2026-10-07T00:00:00+00:00
  - ground truth: 2026-09-23 (two weeks before the reference time 2026-10-07), +- 1 day
  - answer: The system currently has no topics at all. I'll help you create a new topic to store information about your new job starting from today (2026-10-07). What specific details would you like me to store about your new job? For example: - What position or role you have - Your location/office where you work - Date when the job started (confirming two weeks ago as 2026-09-24) - Any other relevant information Please let me know what details are important, and I'll create a topic with those fields.
  - route: query (classifier); tool calls: memory_list_topics, memory_graph_snapshot
  - latency: 3,616 ms; model qwen3.5:2b (ollama)
  - entries the turn wrote: none
  - stored start date: dates read from the stored entries: none; one within 1 day of 2026-09-23: no (a date match, not a grade)
  - hand grade (graded on: the stored start date): [ ] (empty); note: (empty)
- **W2** [temporal reasoning] how long have I been there?
  - reference time sent: 2026-10-21T00:00:00+00:00
  - ground truth: four weeks
  - answer: I don't see any topics in the graph currently. Could you help me clarify what you mean by "how long have I been there?" This would be a reference to something specific in my topic graph, like: - A place or location - An experience or event - A person or project Let me know more details so I can look up the relevant information.
  - the answer says four weeks ("four weeks", "4 weeks" or "28 days"): no (a match, not a grade)
  - route: query (classifier); tool calls: memory_list_topics
  - latency: 2,047 ms; model qwen3.5:2b (ollama)
  - entries the turn wrote: none
  - hand grade (graded on: the answer): [ ] (empty); note: (empty)

### Latency ramps

Median (min–max) over the repeats of each (system, n).

| System | n | repeats | ingest (ms) | query (ms) | settle time (poll floor 0.1 s) (s) | archived |
|---|---:|---:|---:|---:|---:|---:|
| upstream | 100 | 3 | 30.295 (29.879–30.845) | 146.925 (136.376–170.016) | 0.112 (0.112–0.119) | 0 |
| upstream | 250 | 3 | 30.544 (30.177–31.252) | 162.7 (154.778–199.521) | 0.115 (0.114–0.115) | 0 |
| upstream | 500 | 3 | 31.403 (30.793–31.647) | 200.262 (194.503–220.988) | 0.138 (0.136–0.152) | 0 |
| upstream | 1000 | 3 | 41.309 (40.258–81.913) | 253.775 (240.861–303.527) | 0.152 (0.144–0.164) | 0 |
| upstream | 2000 | 3 | 54.897 (52.794–56.591) | 377.458 (332.426–410.12) | 0.179 (0.162–0.198) | 0 |
| step1 | 100 | 3 | 17.915 (17.904–17.944) | 79.291 (75.123–178.934) | 0.127 (0.113–0.127) | 0 |
| step1 | 250 | 3 | 18.316 (18.279–18.425) | 98.008 (96.749–144.709) | 0.115 (0.114–0.119) | 0 |
| step1 | 500 | 3 | 18.852 (18.538–18.874) | 156.647 (125.765–187.05) | 0.154 (0.137–0.157) | 0 |
| step1 | 1000 | 3 | 30.896 (27.91–32.348) | 204.02 (180.807–226.975) | 0.153 (0.152–0.155) | 0 |
| step1 | 2000 | 3 | 45.135 (44.361–45.927) | 343.082 (274.733–403.812) | 0.197 (0.179–0.2) | 0 |
| step2 | 100 | 3 | 18.001 (17.844–18.076) | 79.71 (76.493–160.358) | 0.126 (0.125–0.127) | 0 |
| step2 | 250 | 3 | 18.007 (17.987–18.023) | 100.58 (96.447–163.626) | 0.13 (0.128–0.13) | 0 |
| step2 | 500 | 3 | 18.384 (18.343–18.459) | 138.415 (126.896–186.184) | 0.154 (0.153–0.154) | 0 |
| step2 | 1000 | 3 | 30.114 (27.065–30.292) | 202.21 (183.689–258.008) | 0.169 (0.164–0.173) | 0 |
| step2 | 2000 | 3 | 46.049 (45.26–46.548) | 331.151 (292.569–378.062) | 0.187 (0.147–0.207) | 0 |
| step3 | 100 | 3 | 18.97 (18.887–19.237) | 79.259 (76.063–154.481) | 0.113 (0.113–0.113) | 0 |
| step3 | 250 | 3 | 19.432 (18.928–20.261) | 99.968 (93.072–126.442) | 0.115 (0.114–0.116) | 0 |
| step3 | 500 | 3 | 19.204 (19.157–19.288) | 165.013 (141.765–203.765) | 0.147 (0.142–0.159) | 0 |
| step3 | 1000 | 3 | 30.268 (28.728–30.338) | 216.001 (191.434–245.816) | 0.156 (0.154–0.178) | 0 |
| step3 | 2000 | 3 | 45.427 (44.765–46.771) | 311.928 (279.177–364.119) | 0.187 (0.184–0.193) | 0 |

A difference of medians no larger than the larger sample range is reported as no measurable difference (spec story 43). Ingest samples are the per-repeat medians, query samples are every plain read.

As-of reads (`valid_at`) beside the plain reads at the same n; median (min–max) over every as-of read:

| System | n | as-of reads | as-of read (ms) | plain read (ms) |
|---|---:|---:|---:|---:|
| step2 | 2000 | 60 | 337.675 (291.98–473.152) | 331.151 (292.569–378.062) |
| step3 | 2000 | 60 | 322.624 (287.813–389.965) | 311.928 (279.177–364.119) |

- upstream vs step1 at n=100, query: no measurable difference (medians 146.925 / 79.291 ms)
- upstream vs step1 at n=500, query: no measurable difference (medians 200.262 / 156.647 ms)
- upstream vs step1 at n=1000, ingest: no measurable difference (medians 41.309 / 30.896 ms)
- upstream vs step1 at n=1000, query: no measurable difference (medians 253.775 / 204.02 ms)
- upstream vs step1 at n=2000, query: no measurable difference (medians 377.458 / 343.082 ms)
- step1 vs step2 at n=100, ingest: no measurable difference (medians 17.915 / 18.001 ms)
- step1 vs step2 at n=100, query: no measurable difference (medians 79.291 / 79.71 ms)
- step1 vs step2 at n=250, query: no measurable difference (medians 98.008 / 100.58 ms)
- step1 vs step2 at n=500, query: no measurable difference (medians 156.647 / 138.415 ms)
- step1 vs step2 at n=1000, ingest: no measurable difference (medians 30.896 / 30.114 ms)
- step1 vs step2 at n=1000, query: no measurable difference (medians 204.02 / 202.21 ms)
- step1 vs step2 at n=2000, ingest: no measurable difference (medians 45.135 / 46.049 ms)
- step1 vs step2 at n=2000, query: no measurable difference (medians 343.082 / 331.151 ms)
- step2 vs step3 at n=100, query: no measurable difference (medians 79.71 / 79.259 ms)
- step2 vs step3 at n=250, query: no measurable difference (medians 100.58 / 99.968 ms)
- step2 vs step3 at n=500, query: no measurable difference (medians 138.415 / 165.013 ms)
- step2 vs step3 at n=1000, ingest: no measurable difference (medians 30.114 / 30.268 ms)
- step2 vs step3 at n=1000, query: no measurable difference (medians 202.21 / 216.001 ms)
- step2 vs step3 at n=2000, ingest: no measurable difference (medians 46.049 / 45.427 ms)
- step2 vs step3 at n=2000, query: no measurable difference (medians 331.151 / 311.928 ms)

### MemState's 39 upstream tests

Upstream's own tests, run unedited at upstream and at each patch step (`demo/upstream_tests.py`). A step on which any of them fails is flagged.

| System | Passed | Failed | Total | |
|---|---|---|---|---|
| upstream (Kuzu) | 39 | 0 | 39 | all pass |
| bitemporal patch step 1 | 39 | 0 | 39 | all pass |
| bitemporal patch step 2 | 39 | 0 | 39 | all pass |
| bitemporal patch step 3 | 39 | 0 | 39 | all pass |

### MemState's limits, with their numbers

- **History cap.** MemState keeps the newest 500 entries per field and drops older ones (501 writes to one field leave 500 entries with the oldest gone, F21). A correction uses two entries, so a field holds at most 250 corrections before the oldest entries go [INFERENCE: arithmetic from the cap and the two-entry correction].
- **Forgetting gate.** MemState's forgetting pass runs only from the 500-topic soft limit (`topic_count_soft_limit`) on, and the C5 ramp reaches 2,000 active topics with none archived (F10): the active state is four times the limit, so C5's bound is declared, not enforced.

Verdicts measure the published proof of concept against the paper's conditions; fail and absent mark gaps its authors state (its README: "Proof-of-Concept, NOT Full Implementation"), not defects.

### Deviations

| Item | As shipped | Used here | Why |
|---|---|---|---|
| MemState's intent router | [INFERENCE, from reading the chat code] each chat request first makes an extra Ollama call that routes to query, ingest or both | as shipped: no `intent_override`; the route of every turn is recorded | the chat runs show MemState as published, not a tuned path |
| Ollama model default | `llama3.2:latest` (`MemState/src/memstate/config.py:21`), not installed on the demo machine | `qwen3.5:2b` through `MEMSTATE_OLLAMA_MODEL`, set by `scripts/run_memstate.sh` | the only local model pulled; chat runs are n=1 and hand-graded |
| Thinking-off proxy (ADR 0003) | MemState sends no `think` field, so `qwen3.5:2b` thinks on every round | `scripts/ollama_nothink_proxy.py` defaults `think` to false on `/api/chat` and `/api/generate` | a thinking turn took 19 s instead of 2-4 s on the laptop (ADR 0003); MemState stays unmodified (ADR 0001) |
| Kuzu pin (ADR 0004) | `kuzu>=0.11.0` (Kuzu is archived upstream) | `kuzu==0.11.3`, the final release, for upstream; the patch runs on LadybugDB 0.21.2 (ADR 0006) | a reproducible engine; the engine line of each server is in its snapshot |
| Baseline (versioned row) settings | the baseline has no settings of its own; MemState retrieves with `top_k` 8 and the same MiniLM model | an in-process versioned row: an append-only history per (title, field) with the recorded time, one transaction per write, empty and `null` values rejected, no valid-time dates; MiniLM embeddings (the model MemState uses), top 8 (the same as every in-process system) | it stands for the versioned fact store MAFBench calls for (`2602.03128v2.md:568`), so the baseline differs from MemState in structure, not in embedder or top-k |
| Duplicate pairs for C2(a) and C4's merge case | a duplicate arises from two same-title `/v1 new_topic` writes; which topic the merge drops is chance (random ids) | two topics written through `/v1` under distinct titles, the older value on the lower id and the newer on the higher, then both given one title by a labelled setup `PATCH title` (an editor edit; values are written through `/v1` only); a system with no retitle path gets the plain same-title writes. The merge extras of C2(a) also retitle three topics, and force a low id and archive one topic, by labelled setup writes | MemState keeps the lower id (F9), so this makes the dropped topic hold the newer value in every repetition; F9 recorded the stale value current in 10/20 on random ids |
| Bad-merge chat run (duplicate of the storyline's own topic) | the user's re-explanation reaches memory as a second `/v1 new_topic` with the same title; which topic the merge keeps is chance (the lower random id, F9) | two topics created through `/v1` under distinct placeholder titles, the lower id holding the re-explanation (`Deadline = April 20` only) and the higher the whole storyline (the original, with the deadline history March 15 -> April 20 and its `vendor delay` provenance); then both are given the title `Website Redesign` by a labelled setup `PATCH title`, and a field-less `/v1 extend_topic` triggers the merge scan. The chat model is loaded by one direct request to the proxy before the first turn, so turn 1's latency is not the model load | the merge then keeps the re-explanation and drops the original in every run, which is the 'looks right' outcome (C4) the report's answer-level contrast needs; the scored storyline stays duplicate-free |
| Two-weeks chat run (dates shifted to the run day) | the spec tells the case on Oct 6 and Oct 20 (ticket 18: "I started my new job two weeks ago" at reference time Oct 6, "how long have I been there?" at Oct 20) and says the dates are shifted so that Oct 20 is the run day | both `reference_time` values and the ground-truth start date move by the run day's offset from Oct 20 (a run on Oct 21 sends Oct 7 and Oct 21 and grades the start date against Sep 23, ± 1 day); the two messages are sent verbatim, one request each with no conversation history, on a fresh step-3 database with nothing seeded, no `intent_override` and no `model`; the recording states the dates it used. The model is loaded by one direct request to the proxy before the first turn. The variants that force W1's route or seed a profile topic are not the case of record (`demo/recordings/attempts/`) | relative time is resolved against the request's date, as the spec asks; the second request carries nothing from the first, so the answer can only come from what the first one stored |
| Reference GEM parameters (phase 1) | the paper names a policy-defined bound β(n), thresholds θ and decay on disuse (`2605.26252v1.md:323`) and sets no values; MemState has a 0.05 archive threshold and a 500-topic soft limit, but no decay in its code (F10, F24) | θ_archive 0.05 (MemState's); λ = 0.05^(1/400) ≈ 0.9925 per interaction, so an untouched topic at 1.0 falls below θ after 400 interactions (computed lazily; an ingest and a query are one interaction each); the forgetting check runs after every interaction; the decay clock restarts on any read or write; salience is halved when a topic is archived (MemState `executor.py:360`); declared β = 500 active topics (MemState's `topic_count_soft_limit`); +0.1 per returned topic (MemState's `query_salience_bump`), as-of reads included; history capped at 500 entries per field, overflow archived and readable by id; MiniLM, top 8; revision (merge) after every ingest, as MemState's Reasoner does | values fixed in the spec before the build; the paper leaves them open, so the reference GEM's C5 verdict is stated beside its declared β |
| Reference GEM C6 clause 2 seeds | upstream seeds the read topic at 0.03 and the never-read control at 0.01 (below the 0.05 threshold, which upstream's forgetting pass reaches only at the 500-topic gate) | target and control both at 0.06 on the reference GEM, a per-system test setting (`describe()["c6_clause_2_seeds"]`); the topic is read on every interaction until the first forgetting pass, where the control must be archived and the target not | the reference GEM's forgetting check runs after every interaction, so a topic seeded below θ is archived by its own interaction |
| Reference GEM declared simplifications | the paper's C3 revision repairs dependents, its policies may reference the whole state (`:353`, an open policy language), and forgetting is a graded ladder (compress, hide, archive, `:323`) | one-hop flagging over extension edges in either direction (Listing 1: flag with evidence `{updated_field, timestamp}`, no repair, association edges never flag, the flag clears when the topic is next written); policy conditions limited to field comparisons on the topic being written and "a neighbour exists via an extension or association edge", actions reject and flag; a single archive threshold, no compress or hide rungs; no LLM, so no chat. Phase 1 reads Definition 4 with one timestamp per value (when it became true): no end date and no recorded time | each one is a build decision of ADR 0007; the result is worded "passes the suite's checks, with declared simplifications" |
| Reference GEM ramps (C5-2 counts, once) | every other system's C5-2 runs each ramp size 1 or 3 times and its milliseconds fill the latency table | the reference GEM runs each ramp size once, times nothing and records only the counts (no repeats, no latency rows, no ramp milliseconds in `results.json`); `describe()["latency_comparable"]` is False | ticket 19 says the reference GEM "runs no ramps", but its C5-2 verdict rests on the active and archived counts at n=2000 (about 400 active against β = 500); in-process milliseconds are not comparable with an HTTP server |
