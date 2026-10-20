# A reference GEM beside MemState, not a completed MemState

Upstream MemState fails several of its own conditions as well as the time probes, so its time failures could be blamed on an incomplete prototype. The suite therefore adds a reference GEM: a small in-process system of our own, built to the paper's definitions of C1–C6, with its simplifications declared.

It is scored twice:
- **Phase 1** reads Definition 4 as kindly as its words allow: a value's one timestamp is when it became true, and "current" is judged at the question date. It is expected to fail the time probes that need an end date or a second timestamp, which Definition 4 has no place for.
- **Phase 2** adds C1′, the amendment of report §9.5.

This follows MemTX's method of comparing declared reimplementations, with the official code run beside them as a check. MemState itself stays unmodified upstream, and the real-MemState patch remains the port plus the time fix (ADR 0006); the missing conditions are not built into its server.

## Considered Options

- Complete C2(c), C3 and C5 inside the real MemState server before adding the time model. Rejected: it means three research-sized features (a policy language, LLM-driven repair, decay) built into its LLM-driven Reasoner, and the claim would be tied to one prototype's code rather than to the conditions.
- Keep only the real-MemState patch. Rejected: it leaves the objection open.
- Build phase 1 under both readings of the timestamp (arrival time and "became true"). Rejected: upstream MemState already measures the arrival-time reading, and the kindest reading is the one that settles whether the conditions themselves fall short.

## Consequences

- The C3 and C2(c) checks need pass criteria strict enough to certify an implementation, not only to detect an absence. These checks, the reference GEM's parameters and each probe's expected result are written down before the build. Each check is tested against a deliberately broken version.
- The reference GEM's simplified C2(c) (restricted policy conditions) and C3 (flagging, no repair) are declared in the report. Its result is worded "passes the suite's checks, with declared simplifications", never "satisfies C1–C6".
