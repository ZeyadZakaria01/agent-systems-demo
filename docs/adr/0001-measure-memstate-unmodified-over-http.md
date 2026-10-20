# Measure MemState as published, over HTTP only

MemState is evaluated exactly as its authors released it (commit `945d7c4`), driven only through its HTTP API, because the audience is the system's own author and any change we make to it would muddy which behaviour is theirs. Workarounds for running it (the Groq key variable, the think-off proxy, the egg-info restore) live outside the clone, and our one improvement (the bitemporal extension, on LadybugDB per ADR 0006) runs as a separate patched copy measured beside the unmodified one.

## Considered Options

- In-process calls into the store or Reasoner: more control, but tests internals the paper does not promise.
- Patching thresholds such as the 500-topic forget gate to make tests easier: rejected, since the gate itself is a finding.
