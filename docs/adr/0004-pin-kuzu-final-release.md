# Pin Kuzu at its final release, 0.11.3

Kuzu, MemState's embedded graph database, was archived upstream in October 2025, so the environment pins `kuzu==0.11.3`, its final release, which installs from a prebuilt wheel and needs no extensions (MemState's vector search is in-process). Moving to a fork or another database would change the system under test (ADR 0001); the archived substrate is instead reported as a limitation of the prototype.

The pin applies to upstream; the bitemporal patch runs on LadybugDB (ADR 0006).
