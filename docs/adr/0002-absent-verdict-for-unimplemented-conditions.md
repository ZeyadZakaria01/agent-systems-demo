# Score unimplemented conditions as absent, not fail

A condition whose required capability MemState does not implement (C3 extension-edge propagation, C2's declarative policies, C5 on the natural trajectory) gets the verdict *absent*, confirmed by a probe run, and is counted apart from *fail*, which is reserved for capabilities MemState implements but gets wrong. Scoring missing features as fails would fix the outcome before the run, inflate the fail count, and read to the paper's author as a gotcha rather than a map of open research.

## Considered Options

- Skip unimplemented conditions: leaves gaps with no run behind them, against the evidence rule.
- Score them as fail: rejected for the reasons above.
