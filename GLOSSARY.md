# Agent memory evaluation

The language for reviewing the GEM paper and evaluating its MemState prototype: GEM's memory model, and the terms of the conformance suite that tests it.

## Language

### GEM memory model

**Semantic unit**:
The smallest self-contained piece of memory that GEM reasons about; GEM states its correctness conditions over units.
_Avoid_: record, entry, memory item

**Topic**:
MemState's semantic unit: one concept with a title, a summary and its fields.
_Avoid_: entity, node, document

**Field history**:
The ordered values one field of a topic has held, each with when it was true, when memory recorded it, and its provenance; appending a value never removes an earlier one.
_Avoid_: versions, log, changelog

**Valid time**:
When a value was true in the world: from when, and until when if it ended.
_Avoid_: event time, effective date

**Recorded time**:
When memory held a value: from when it was recorded until it expired.
_Avoid_: transaction time, ingestion time

**Expired entry**:
A field-history entry memory no longer holds, because a later write corrected it; it is kept so that what memory believed earlier stays answerable.
_Avoid_: deleted, invalidated, retired

**Scoped override**:
A value given its own end date that sits on top of the base value; the base value applies again once the override ends.
_Avoid_: temporary value, exception

**Current value**:
The value valid at the asked time that memory has not expired; by default the asked time is now.
_Avoid_: latest value, head

**As-of query**:
A query about another date, on either time: what was true then, or what memory believed then.
_Avoid_: time-travel query, historical query

**Provenance**:
The recorded source of a value: who or what supplied it, and why it changed.
_Avoid_: origin, lineage

**Extension edge**:
A typed link from one topic to another whose content may change when the first changes; updates must propagate along it.
_Avoid_: dependency link, related edge

**Association edge**:
A typed link between related but independent topics; it aids retrieval and never propagates updates.
_Avoid_: related edge, reference

**Salience**:
A unit's relevance score: retrieval raises it, and low salience makes the unit eligible for attenuation.
_Avoid_: importance, weight, priority

**Attenuation**:
Reducing a unit's influence without destroying it, as a ladder from compression to archiving.
_Avoid_: deletion, eviction, pruning

**Archived**:
The last rung of attenuation: excluded from default retrieval, still recoverable by explicit lookup.
_Avoid_: deleted, forgotten

**GEM operator**:
One of the four state-level transitions GEM defines: ingestion, revision, forgetting, retrieval.
_Avoid_: CRUD operation, API call

**Trajectory**:
The sequence of memory states over successive interactions; GEM defines correctness as a property of the trajectory, not of single records.
_Avoid_: history (that word belongs to fields), timeline

**Correctness condition**:
One of GEM's six conditions C1–C6 that a memory system's trajectory must satisfy.
_Avoid_: requirement, invariant, property

### Conformance suite

**Conformance suite**:
The demo's set of checks that test a memory system against C1–C6 and E4 by inspecting its stored state.
_Avoid_: harness, benchmark, test suite

**State-level check**:
A check that reads what a memory system stores (current values, histories, salience, archived flags, edges).
_Avoid_: white-box test

**Answer-level check**:
A check that judges only the answer a memory-backed agent gives to a question.
_Avoid_: end-to-end test, QA score

**Verdict**:
The outcome of checking one condition on one system: pass, partial, fail or absent.
_Avoid_: score, result, grade

**Pass**:
The condition holds in every case tested.

**Partial**:
The condition holds in some tested cases and not others.

**Fail**:
The system implements the capability the condition needs, but it behaves incorrectly.
_Avoid_: absent (a different verdict)

**Absent**:
The system does not implement the capability the condition needs, confirmed by a probe.
_Avoid_: fail, not applicable, skipped

**Control**:
A check expected to pass, which shows the conformance suite can detect a pass.

**Probe**:
A run that exercises a capability the system may lack, to confirm whether it exists.
_Avoid_: smoke test

**Time probe**:
A probe told as a short dated story and asked on more than one date, one of which is its control.
_Avoid_: temporal test, date test

**Over-blocking**:
Failing a control: the system rejects an update it should have accepted.
_Avoid_: false positive, regression

**Search failure**:
A wrong answer where the read did not return the topic that holds the answer (StateMemBench's retrieval failure).
_Avoid_: bad RAG, retrieval miss

**Memory failure**:
A wrong answer where the read returned the right topic but its stored value is wrong.
_Avoid_: state error, storage bug

**Reinforcement precision**:
The share of salience increments that went to the topic holding the answer; a measurement beside C6, not a verdict.
_Avoid_: salience accuracy

**Baseline**:
The comparison system put through the same checks: a last-write-wins row keyed by topic title and field.
_Avoid_: reference implementation, straw man

**Scored transition**:
A state change made through a GEM operator, whose effect the conformance suite judges.

**Setup write**:
A direct edit that arranges a starting state for a check and is never itself judged.
_Avoid_: fixture, seed (when the write bypasses GEM operators)

**System adapter**:
The one interface through which every check drives and reads a memory system: scored transitions (`ingest`, `query`), reads of stored state, labelled setup writes, `wait_until` and `describe`. A capability the system lacks reads as a nothing-value, never as an error. MemState (upstream or patched, over HTTP) and the baseline each have one; adding a system means writing one adapter.
_Avoid_: driver, client (MemState's HTTP client is only one adapter's transport)

**Staleness window**:
The time between a transition and the moment the state that depends on it reflects it.
_Avoid_: lag, delay, consistency gap

**Merge revision window**:
The staleness window between creating a duplicate topic and the revision that merges it becoming visible.

**Dependent-topic staleness window**:
The staleness window between updating a topic and the revision of the topics linked to it by extension edges.

**Non-destructive failure (E4)**:
The proposed extension that a failed input leaves the prior values of its fields unchanged, while valid parts of the same update may still commit.
_Avoid_: rollback, abort (GEM's whole-transition rule)

**Finding**:
A statement about a system's behaviour backed by a recorded run on a fresh database.
_Avoid_: observation (when no run backs it)
