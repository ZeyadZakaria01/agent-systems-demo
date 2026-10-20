# Issue tracker: Local Markdown

Issues and specs for this repo live as markdown files in `.scratch/`, committed with the code.

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`
- The spec is `.scratch/<feature-slug>/spec.md`
- Implementation issues are one file per ticket at `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01`, never a single combined tickets file
- A wayfinder effort (below) gets its own `.scratch/<effort>/` directory; the spec and implementation tickets it hands off to live in a separate feature directory, so the two ticket sets never share numbering or `Status:` values
- Triage state is recorded as a `Status:` line near the top of each issue file (see `triage-labels.md` for the role strings)
- Comments and conversation history append to the bottom of the file under a `## Comments` heading

## When a skill says "publish to the issue tracker"

Create a new file under `.scratch/<feature-slug>/` (creating the directory if needed).

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path or the issue number directly.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a file with one **child** file per ticket.

- **Map**: `.scratch/<effort>/map.md` (the Destination / Notes / Decisions-so-far / Not yet specified / Out of scope body).
- **Child ticket**: `.scratch/<effort>/issues/NN-<slug>.md`, numbered from `01`, with the question in the body. A `Type:` line records the ticket type (`research`/`prototype`/`grilling`/`task`); a `Status:` line records `claimed`/`resolved`/`closed`. An open ticket has no `Status:` line.
- **Blocking**: a `Blocked by: NN, NN` line near the top. A ticket is unblocked when every file it lists is `resolved`.
- **Frontier**: scan `.scratch/<effort>/issues/` for files that are open, unblocked, and unclaimed; first by number wins.
- **Claim**: set `Status: claimed` and save before any work.
- **Resolve**: append the answer under an `## Answer` heading, set `Status: resolved`, then append a context pointer to the map's Decisions-so-far in `map.md`: a one-sentence gist (≤ 400 chars, enforced by `.githooks/pre-commit`) + link; detail stays in the ticket's Answer.
- **Filing a review**: before a review's items become a ticket, triage each against existing tickets, findings and the report: *new*, *already covered* (cite where), or *weak* (why). File only the new ones.
- **Close (out of scope)**: append the reason under `## Closed`, set `Status: closed`, and add one line to the map's Out of scope section. A closed ticket never returns to the frontier.
- **Conditional questions**: blocking references tickets only. A question that waits on a condition rather than a ticket is either resolved with its default answer (revisit by opening a new ticket) or kept as fog in Not yet specified.
