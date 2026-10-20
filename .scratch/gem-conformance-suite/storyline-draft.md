# Storyline draft: the Website Redesign example (for review)

Generated from `demo/storyline.py` by `python -m demo.storyline_draft`; edit the data there and regenerate. Recorded-run numbers (triage counts, reinforcement precision, unexpected-state counts) live in `docs/findings.md` under the storyline F-entry for the date of that run; they are not copied here.

**29 events** (each one `/v1/ingest` placement) and **15 questions** (each with a LongMemEval ability, a ground-truth answer and the topic that holds the answer), on the paper's example.

## From the paper, and where this draft departs

Kept: Deadline March 15 → April 20 after a vendor delay; Team `[Alice (Frontend), Bob (Backend)]`; Status ending at `Complete` ("Project completed"); Alice split out of Website Redesign with an extension edge; a new project idea with an association edge; a lunch-preferences note as noise.

Departures:
- The paper's `Meeting` field (Figure 3(a), Feb 10, low salience) is its own topic, Weekly Sync Meeting, with a recurring time instead of a date.
- "Discussed lunch preferences" is a Lunch Preferences topic with invented content (cuisine, dietary note).
- Invented: the design vendor, milestones, budgets, brand guidelines, analytics, hiring, Phase 2 and Design Review topics, and the dates, names and amounts in them. Phase 2, Marketing Budget and Design Review Meeting are deliberate look-alikes of Website Redesign, Redesign Budget and Weekly Sync Meeting.
- Events are only `/v1` placements: no re-explained duplicate (the paper's "stored twice" at Week 1), because a same-title topic would be merged and C2 tests that.

## How the storyline is used

- Every system receives the same events, in order, on a fresh database. The `When` label on each event is for the reader only; no dates are sent.
- After every event the run compares title, current field values, and (where the system reports them) the topic's outgoing related edges with the folded expected state; the baseline has no edges, so those are n/a.
- Each question is asked as a plain read: default stages, `top_k` 8 on MemState and on the baseline. **Answered** = the read returned the answer topic and the ground-truth value is current in the labelled field. A wrong answer is a **search failure** if the answer topic was not returned, a **memory failure** if it was returned with a wrong stored value.
- **Reinforcement precision** = salience increments to the answer topic ÷ all increments over the questions (equals Precision@k because every returned topic is bumped); no verdict, n/a on the baseline.

## Topics

| Key | Title | Kind | Created by | Summary (embedded with the title) |
|---|---|---|---|---|
| `redesign` | Website Redesign | project | E01 | Project to redesign the company website: deadline, status and team. |
| `lunch` | Lunch Preferences | note | E03 | What the team likes to eat when ordering lunch together. |
| `newproj` | New Project Idea: Mobile App | project | E04 | Early brainstorm for a possible mobile app; nothing is planned yet. |
| `meeting` | Weekly Sync Meeting | meeting | E05 | Recurring weekly team meeting: day, time and room. |
| `budget` | Redesign Budget | budget | E06 | Money approved for the website redesign and who signs it off. |
| `vendor` | Design Vendor: Pixel Forge | vendor | E07 | External agency producing the website mockups. |
| `milestones` | Redesign Milestones | schedule | E08 | Dated milestones that depend on the Website Redesign deadline. |
| `brand` | Brand Guidelines | guidelines | E09 | Colours and logo files the website has to follow. |
| `phase2` | Website Redesign Phase 2 | project | E10 | Follow-up project after the Website Redesign: deadline, status and team. |
| `marketing` | Marketing Budget | budget | E11 | Money approved for the website launch campaign and who signs it off. |
| `designreview` | Design Review Meeting | meeting | E12 | Recurring design review meeting: day, time and room. |
| `alice` | Alice | person | E19 | Alice, frontend developer on the Website Redesign team. |
| `analytics` | Website Analytics Report | report | E24 | Monthly traffic numbers for the current website. |
| `hiring` | Backend Engineer Hiring | hiring | E28 | Open backend engineer position and the interview pipeline. |

## Events

| Event | The user says | Topic | Fields written | Edges |
|---|---|---|---|---|
| E01 | Kickoff: the website redesign is due March 15 and is in planning. | Website Redesign | Deadline = March 15 (provenance kickoff-notes)<br>Status = Planning (provenance kickoff-notes) | — |
| E02 | The team is Alice on the frontend and Bob on the backend. | Website Redesign | Team = Alice (Frontend), Bob (Backend) (provenance kickoff-notes) | — |
| E03 | Lunch preferences: the team likes Thai food, and two people are vegetarian. | Lunch Preferences | Favorite cuisine = Thai (provenance chat)<br>Dietary note = Two vegetarians (provenance chat) | — |
| E04 | Carol floats an idea for a mobile app, unrelated to the redesign for now. | New Project Idea: Mobile App | Status = Brainstorming (provenance chat)<br>Owner = Carol (provenance chat) | → Website Redesign (association) |
| E05 | The weekly sync is on Tuesdays at 10:00 in Room 4B. | Weekly Sync Meeting | Day = Tuesday (provenance calendar)<br>Time = 10:00 (provenance calendar)<br>Location = Room 4B (provenance calendar) | — |
| E06 | The redesign budget is $40,000, approved by Dana. | Redesign Budget | Total = $40,000 (provenance finance-email)<br>Approver = Dana (provenance finance-email) | → Website Redesign (association) |
| E07 | The design vendor Pixel Forge, contact Priya, delivers the mockups by February 15. | Design Vendor: Pixel Forge | Mockups due = February 15 (provenance vendor-email)<br>Contact = Priya (provenance vendor-email)<br>Delivery status = Pending (provenance vendor-email) | — |
| E08 | Milestones follow the deadline: content freeze March 1, user testing March 8, launch March 15. | Redesign Milestones | Content freeze = March 1 (provenance pm-email)<br>User testing start = March 8 (provenance pm-email)<br>Launch = March 15 (provenance pm-email) | → Website Redesign (extension) |
| E09 | Brand guidelines: primary colour #1A73E8, logo version 3. | Brand Guidelines | Primary color = #1A73E8 (provenance design-wiki)<br>Logo version = v3 (provenance design-wiki) | — |
| E10 | A second phase is planned for later: Website Redesign Phase 2, due September 30. | Website Redesign Phase 2 | Deadline = September 30 (provenance pm-email)<br>Status = Not started (provenance pm-email)<br>Team = Alice (Frontend), Carol (Design) (provenance pm-email) | → Website Redesign (association) |
| E11 | Marketing has its own budget: $15,000, approved by Frank. | Marketing Budget | Total = $15,000 (provenance finance-email)<br>Approver = Frank (provenance finance-email) | — |
| E12 | Design reviews are on Thursdays at 14:00 in Room 2A. | Design Review Meeting | Day = Thursday (provenance calendar)<br>Time = 14:00 (provenance calendar)<br>Location = Room 2A (provenance calendar) | — |
| E13 | The vendor is late: mockups now due March 22. | Design Vendor: Pixel Forge | Mockups due = March 22 (provenance vendor-email; why: vendor delay) | — |
| E14 | Because of the vendor delay the redesign deadline moves to April 20. | Website Redesign | Deadline = April 20 (provenance pm-email; why: vendor delay; impact: milestones slip about five weeks) | — |
| E15 | The launch milestone moves to April 20 with the deadline. | Redesign Milestones | Launch = April 20 (provenance pm-email; why: deadline moved) | — |
| E16 | User testing now starts April 13. | Redesign Milestones | User testing start = April 13 (provenance pm-email; why: deadline moved) | — |
| E17 | Content freeze moves to April 6. | Redesign Milestones | Content freeze = April 6 (provenance pm-email; why: deadline moved) | — |
| E18 | The vendor charges a rush fee, so the budget grows to $46,500. | Redesign Budget | Total = $46,500 (provenance finance-email; why: vendor rush fee) | — |
| E19 | Alice comes up in every thread, so she gets her own topic: frontend developer, prototyping the homepage. | Alice | Role = Frontend developer (provenance standup)<br>Working on = Homepage prototype (provenance standup) | → Website Redesign (extension) |
| E20 | Alice is promoted to frontend lead. | Alice | Role = Frontend lead (provenance standup; why: promoted after the homepage prototype) | — |
| E21 | Erin joins as QA, and Alice is now the frontend lead on the team. | Website Redesign | Team = Alice (Frontend lead), Bob (Backend), Erin (QA) (provenance standup; why: Erin joined) | — |
| E22 | The weekly sync moves to 11:30 because of a design review. | Weekly Sync Meeting | Time = 11:30 (provenance calendar; why: clash with the design review) | — |
| E23 | The redesign is now in progress. | Website Redesign | Status = In progress (provenance standup) | — |
| E24 | Website traffic: about 48,000 visitors a month, the pricing page is the top page. | Website Analytics Report | Monthly visitors = 48,000 (provenance analytics-export)<br>Top page = Pricing (provenance analytics-export) | — |
| E25 | Phase 2 slips to October 15 until phase 1 is done. | Website Redesign Phase 2 | Deadline = October 15 (provenance pm-email; why: waiting for phase 1) | — |
| E26 | The vendor delivered the mockups. | Design Vendor: Pixel Forge | Delivery status = Delivered (provenance vendor-email) | — |
| E27 | Project completed. | Website Redesign | Status = Complete (provenance standup) | — |
| E28 | Hiring: three candidates are being interviewed for a backend engineer. | Backend Engineer Hiring | Status = Interviewing (provenance recruiter-email)<br>Candidates = 3 (provenance recruiter-email) | — |
| E29 | The team now wants Mexican for lunch. | Lunch Preferences | Favorite cuisine = Mexican (provenance chat; why: tired of Thai) | — |

## Expected state at the end (one row per topic)

| Topic | Title | Current fields | Outgoing edges |
|---|---|---|---|
| `redesign` | Website Redesign | Deadline = April 20; Status = Complete; Team = Alice (Frontend lead), Bob (Backend), Erin (QA) | — |
| `lunch` | Lunch Preferences | Favorite cuisine = Mexican; Dietary note = Two vegetarians | — |
| `newproj` | New Project Idea: Mobile App | Status = Brainstorming; Owner = Carol | → Website Redesign (association) |
| `meeting` | Weekly Sync Meeting | Day = Tuesday; Time = 11:30; Location = Room 4B | — |
| `budget` | Redesign Budget | Total = $46,500; Approver = Dana | → Website Redesign (association) |
| `vendor` | Design Vendor: Pixel Forge | Mockups due = March 22; Contact = Priya; Delivery status = Delivered | — |
| `milestones` | Redesign Milestones | Content freeze = April 6; User testing start = April 13; Launch = April 20 | → Website Redesign (extension) |
| `brand` | Brand Guidelines | Primary color = #1A73E8; Logo version = v3 | — |
| `phase2` | Website Redesign Phase 2 | Deadline = October 15; Status = Not started; Team = Alice (Frontend), Carol (Design) | → Website Redesign (association) |
| `marketing` | Marketing Budget | Total = $15,000; Approver = Frank | — |
| `designreview` | Design Review Meeting | Day = Thursday; Time = 14:00; Location = Room 2A | — |
| `alice` | Alice | Role = Frontend lead; Working on = Homepage prototype | → Website Redesign (extension) |
| `analytics` | Website Analytics Report | Monthly visitors = 48,000; Top page = Pricing | — |
| `hiring` | Backend Engineer Hiring | Status = Interviewing; Candidates = 3 | — |

## Questions

| Q | Ability | Question | Ground-truth answer | Answer topic | Field |
|---|---|---|---|---|---|
| Q01 | information extraction | Who is our contact at the design vendor? | Priya | Design Vendor: Pixel Forge (`vendor`) | Contact |
| Q02 | knowledge update | What is the deadline of the Website Redesign? | April 20 | Website Redesign (`redesign`) | Deadline |
| Q03 | knowledge update | What is the total budget for the website redesign? | $46,500 | Redesign Budget (`budget`) | Total |
| Q04 | knowledge update | What time is the weekly sync meeting? | 11:30 | Weekly Sync Meeting (`meeting`) | Time |
| Q05 | information extraction | On which day is the weekly sync meeting held? | Tuesday | Weekly Sync Meeting (`meeting`) | Day |
| Q06 | knowledge update | Who is on the website redesign team? | Alice (Frontend lead), Bob (Backend), Erin (QA) | Website Redesign (`redesign`) | Team |
| Q07 | knowledge update | What is Alice's role on the website project? | Frontend lead | Alice (`alice`) | Role |
| Q08 | knowledge update | When does user testing start for the website redesign? | April 13 | Redesign Milestones (`milestones`) | User testing start |
| Q09 | knowledge update | When is the website launch milestone? | April 20 | Redesign Milestones (`milestones`) | Launch |
| Q10 | information extraction | Who approves the redesign budget? | Dana | Redesign Budget (`budget`) | Approver |
| Q11 | knowledge update | What is the current status of the website redesign project? | Complete | Website Redesign (`redesign`) | Status |
| Q12 | knowledge update | How much money is set aside for the site revamp? | $46,500 | Redesign Budget (`budget`) | Total |
| Q13 | information extraction | Which room do the weekly team gatherings use? | Room 4B | Weekly Sync Meeting (`meeting`) | Location |
| Q14 | knowledge update | What cuisine does the team want for lunch? | Mexican | Lunch Preferences (`lunch`) | Favorite cuisine |
| Q15 | knowledge update | When is the design vendor's mockup delivery due? | March 22 | Design Vendor: Pixel Forge (`vendor`) | Mockups due |

Abilities: information extraction 4, knowledge update 11. Every answer is one stored value. Temporal reasoning and multi-session reasoning are not asked: time validity is tested by the six time probes and the "two weeks ago" chat run, and multi-session reasoning is not measured. Abstention (answer: "not stored") is not asked: it has no answer topic, so search-vs-memory triage cannot sort it.

## Notes

- Several questions share ground-truth strings with other topics (April 20 is on Website Redesign and Redesign Milestones); the labelled topic decides which one counts.
- Dependent topics (milestones, Alice's role in the team list) are updated by explicit events here, because every event is a perfect placement; whether MemState would propagate a deadline change by itself is C3's question, not this one.
- All values are strings so a read is judged by exact match; changing a value's wording changes the ground truth in the same place.
- **The store is small.** The storyline creates 14 topics, so a `top_k` 8 read returns most of them, and so does the baseline's top 8. Phase 2, Marketing Budget and Design Review Meeting are look-alikes so a paraphrased question can rank the wrong topic; they do not guarantee a search failure. Report whatever the recorded run gives.
