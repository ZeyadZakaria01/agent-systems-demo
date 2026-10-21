# Chat series

Repeated takes of the two chat cases, 10 per folder, each graded by Sonnet (`model_grade`) and open for a hand grade (`demo/grading/hand-grading-sheet.csv`). Cite a folder only with its finding; the run of record's single takes are in `demo/recordings/`.

| Folder | Model | Reasoning | Patch (two-weeks on step 3) | Finding | Use it for |
|---|---|---|---|---|---|
| `qwen3.5-4b/bad-merge`, `qwen3.5-4b/two-weeks` | `qwen3.5:4b` | off | `cb5d48c`, no resolver | F37 | the router and the question rewording; the baseline |
| `qwen3.5-4b-resolver/two-weeks` | `qwen3.5:4b` | off | `22fc89a`, first resolver | F38 | the resolver's effect on the stored date |
| `qwen3.5-4b-think/bad-merge`, `qwen3.5-4b-think/two-weeks` | `qwen3.5:4b` | on | `22fc89a`, first resolver | F39 | the effect of reasoning |
| `qwen3.5-4b-think-final/two-weeks` | `qwen3.5:4b` | on | `9bd471e`, final resolver | F40 | **the result to cite** for "two weeks ago" |

The bad merge runs on unmodified upstream (`945d7c4`) in every folder, so the resolver does not affect it; cite `qwen3.5-4b-think/bad-merge` with F39 for the reasoning-on setting. Old patch commits stay resolvable under `refs/superseded/` in the MemState submodule.

Recording more: `scripts/chat_series.py` (one take at a time, stops at the first error, refuses a provider whose per-minute token limit is below one MemState request).
