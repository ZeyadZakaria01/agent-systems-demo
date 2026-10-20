# Judge and reference answers

Type: grilling
Status: closed
Blocked by: 03

## Question

For the one answer-level contrast case (2–3 questions answered by MemState's chat path after the bad merge), who decides whether each answer is correct, and where do the reference answers come from?

Options on the table: hand grading against reference answers from the scripted ground truth; an LLM judge from a different family (`qwen/qwen3.8-27b` on Groq free tier) with the survey's three rubrics (2602.19320 App. D.3); both, reporting agreement; `qwen3.5:2b` locally as judge.

Recommendation so far: both (hand grades are the reference, the judge demonstrates the survey protocol; a different family avoids self-preference).

## Closed

Out of scope, 2026-10-11 (ticket 21): the answer-level case is one Ollama run graded by hand. The three-rubric LLM judge with agreement is future work; `qwen/qwen3.8-27b` is confirmed available on Groq's `/models` list for when it is picked up.
