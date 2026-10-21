# Reference GEM design: scope per condition, stricter checks, scorecard place

Type: grilling
Status: resolved
Blocked by: 37

## Question

How is the reference GEM ("Reference GEM: show the time gap is in the conditions, not the prototype") built and scored? The agent's recommendations come from the 2026-10-20 session, and the cost figures are design reasoning [INFERENCE]:

1. **C3 propagation depth.** Recommended: one hop. An update to A flags the topics linked to it by extension edges, with a visible flag, and no LLM repair: O(d) per update. The alternative is a transitive walk with a visited set, O(V + E) over the reachable subgraph (report §5.5, "how many hops").
2. **C2(c) policy expressiveness.** Recommended: ⟨event, condition, action⟩ rules stored in the state, with conditions restricted to predicates on the touched topic, checked against the proposed next state before commit; a violation rejects the commit. That costs O(|P|) per commit. Conditions that may query the whole state are the paper's open "policy language" (`2605.26252v1.md:353`).
3. **C5 decay.** Recommended: lazy decay. Store the last access and compute s·λ^Δt on read (O(1)). A forgetting pass archives topics below θ_archive at a topic-count gate like MemState's 500. The values of λ, θ_archive, the gate and β(n) need choosing, and the report declares them.
4. **C6 bump.** Fixed step per returned topic, as MemState does (0.1, F2)?
5. **Stricter checks**, to be in place before the reference GEM is scored:
   - **C3:** the dependent is flagged because of the extension edge, and a topic linked only by an association edge is *not* flagged (control). Today the check passes on any change to B.
   - **C2(c):** a declared policy rejects a violating transition, and an ordinary transition commits (control). Today the check raises an error when it finds a policy surface.
6. **Scorecard place.** Two new systems (reference GEM; reference GEM + Zep). Are they columns beside upstream, the patch and the baseline? Or do they form a separate table and chain, so the per-step change table shows reference → reference + Zep?
7. **Which workloads run on it.** The checks and time probes only, or also the storyline, triage and latency ramps? Do the chat runs stay MemState-only?
8. **Retrieval.** MiniLM brute-force top-k with `top_k` 8, as MemState does, so that C6 and the triage numbers are comparable?
9. **Report changes.** §9.1 goal, §9.2 systems, §9.5 the two-phase structure beside the three real-MemState commits, §9.8 columns, and the declared simplifications.
10. **Grading our own work** ([challenge list](../assets/challenge-conditions-baseline-suite-probes.md) S1, S6). The same authors write the checks, build the reference GEM and choose β, θ and λ. Proposed:
    - write the stricter checks (item 5) and the parameter values down *before* building the reference GEM;
    - test each check against one deliberately broken reference GEM per condition, which the check must fail;
    - word the result as "passes the suite's checks, with declared simplifications".

    Also from the challenge list: phase 1's reading of Definition 4's `t` ([Answer the challenge list](40-answer-the-challenge-list.md) item 1) fixes what phase 1 is built to.

## Comments

- 2026-10-20, settled by [Answer the challenge list](40-answer-the-challenge-list.md). These are inputs, not open questions:
  - **Phase 1** is built once, on the kindest reading: one timestamp per value, meaning when it became true, and "current" judged at the question date. Phase 2 = phase 1 + C1′ (report §9.5 rules). Each probe's expected result is written in the spec before building.
  - **C3:** a read of a dependent before it is re-checked carries a flag naming the update (C3′'s testable core). The flag clears when the dependent is next written.
  - **C4′:** the reference GEM stores the source message with each write, and the provenance points to it, so the C4′ probe can pass here.
  - **C5:** the reference GEM declares its β, and the C5 verdict text states it beside the active count.
  - **Archived valid value:** a read returns no current value plus a note that an archived value exists.
  - **Wording:** "passes the suite's checks, with declared simplifications".

## Answer

Resolved 2026-10-21 with the user. The answers were checked against the paper (`docs/papers/2605.26252v1.md`) and the report.

1. **C3, one hop.** This is the paper's own Listing 1 (`:281-287`, `flag_for_revision(dependent_topic) WITH evidence = {updated_field, timestamp}`) and C3's pairwise wording (`:212`).
   - An update flags each direct extension-edge neighbour with the update named. Association edges never flag.
   - The flag clears when the dependent is next written, and that write flags its own neighbours.
   - Repair is out: in the paper it belongs to the revision operator.
   - **Measurement beside the verdict:** a transitive walk runs on one chain scenario that holds one anti-trap (a dependent that does not actually change). It reports flags raised against flags needed, for report §5.5 "how many hops" and StateMem's over-propagation cost (report :198-200, :608).
2. **Policies (C2(c)).**
   - Policies are ⟨event, condition, action⟩ rules stored in the state as data and addable at runtime (Definition 3, `:188`; `:277`). Conditions come from a small fixed vocabulary: field comparisons on the topic being written, and "a neighbour exists via an extension or association edge". Actions are *reject* (a postcondition checked before commit) and *flag for revision*.
   - C3 runs as the Listing 1 policy.
   - Arbitrary conditions over the whole state, the paper's open "policy language" (`:353`), are a declared simplification.
   - **Stricter C2(c) check:** a policy added through the API at runtime ("Deadline not before Start") rejects a violating write with nothing saved, while an ordinary write still commits.
3. **Decay (C5), counted per interaction.** Each ingest and each query counts as one interaction.
   - Settings: θ_archive = 0.05 (MemState's threshold); an untouched topic at 1.0 falls below θ after 400 interactions (λ ≈ 0.9925); declared β = 500 active topics (MemState's soft limit).
   - The forgetting check runs after every interaction and is computed lazily.
   - The compress and hide rungs of the ladder (`:323`) are out of scope.
   - **C6-2 check change:** it stops at the first forgetting pass. There the never-read control must be archived and the read topic must not be. Upstream's recorded `pass` is unaffected, because its first pass is at 501 topics (F15).
4. **C6 bump:** +0.1 per returned topic, as MemState's `query_salience_bump`. Reinforcement precision stays comparable.
5. **Merge (revision), asynchronous on a declared, deterministic schedule.** This follows the paper: "Revision and forgetting run asynchronously" (`:291`).
   - The survivor keeps both histories with their provenance. In phase 1, current is the later write; in phase 2, the later valid date.
   - Until revision runs, reads can see both copies. The **merge revision window** and the **dependent-topic staleness window** are reported **in interactions**: report §6.8 defines the staleness window as "the time, or number of transitions" (:429).
   - The schedule itself is a build detail and is declared.
6. **History cap and empty writes (C4).**
   - **Cap 500, as MemState, but overflow is archived, not deleted.** Overflow leaves the active history and stays readable by id ("archived content remains recoverable", `:216`). Same test as upstream: upstream deletes the oldest and fails C4 (F21); the reference GEM keeps them and is expected to pass [INFERENCE].
   - A default policy rejects empty or null values.
7. **Scorecard:** one table in three groups:
   1. MemState: upstream, then steps 1–3;
   2. Reference: phase 1, then phase 2;
   3. Baseline: the versioned row.

   The change table gets a second chain, phase 1 → phase 2, which isolates C1′ on a system that meets the conditions.
8. **Workloads.**
   - **Run on the reference GEM:** the C1–C6 checks, the time probes, the storyline with its triage and reinforcement precision, and the two windows counted in interactions.
   - **Not run:** the latency ramps (in-process milliseconds are not comparable with an HTTP server; the ramps measure the engine swap and the patch, report §9.2 :670, :673) and the chat runs (the reference GEM has no LLM chat).
9. **Retrieval:** MiniLM, top 8, for every in-process system, including the versioned-row baseline (closes challenge B5).
10. **Grading our own work:**
    - Checks, parameters and expected verdicts are written in the spec before the build.
    - Each check is run against one deliberately broken reference GEM per condition, and must catch it.
    - The wording is "passes the suite's checks, with declared simplifications".

Also settled earlier (Comments above):
- phase 1 uses the kindest reading, and phase 2 = phase 1 + C1′ (report §9.5 rules, ADR 0005 as narrowed);
- stored source messages for the C4′ probe;
- the archived-valid-value read;
- the declared β in C5's verdict text.

**Report changes** (applied in "Revise the spec and build tickets for the reference GEM and the suite audit"):
- §9.1 goal;
- §9.2 systems and measurements;
- §9.5, the two phases beside the three MemState commits;
- §9.8 columns and change-table chains;
- a declared-simplifications list: one-hop flagging with no repair, the restricted policy vocabulary, a single archive threshold, no compression, async revision on a declared schedule.

## Comments (after resolution)

- 2026-10-21, *settled in part* during "Revise the spec and build tickets for the reference GEM and the suite audit":
  - **Revision schedule:** runs after every ingest, as MemState's Reasoner does (`reasoner/engine.py:36-37`).
  - **C3 flagging:** undirected. Both ends of an extension edge are flagged, per C3's "pair" wording (`:212`, `:275`).
  - **Salience:** halved when a topic is archived, reused from MemState's code (`executor.py:360`). A read or write resets the decay clock.
  - **C6-2:** seeded at 0.06 on the reference GEM, a declared test setting.

- 2026-10-21, built in ticket 26 (phase 1): all ten items hold in `demo/reference_gem.py`; read the departures in the ticket's Comments (phase 1 accepts `valid_at` as well as `valid_from`; decay clock; merge deletes the dropped topic).
