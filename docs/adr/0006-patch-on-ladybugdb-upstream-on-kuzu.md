# The patch runs on LadybugDB; upstream stays on Kuzu

Upstream MemState is measured as published on `kuzu==0.11.3` (ADR 0001, ADR 0004), while the bitemporal patch runs on LadybugDB (`ladybug==0.21.2`), a maintained fork of Kuzu, because an extension meant to outlive the demo should not be built on an archived engine. Both engines are pinned exactly and installed side by side in the root venv (finding F11: the process loads only the engine it imports). The port is the patch's first commit, an import change plus the dependency line with no renames, and the conformance suite runs on it alone so the engine change is shown to leave every verdict unchanged before the bitemporal commit is measured.

## Consequences

- Database files are not interchangeable between the engines (F12): every database is fresh and belongs to one engine, and its folder name says which.
- Upstream vs. patch differs in two things, engine and data model; the commit 1 → commit 2 comparison isolates the data model.
