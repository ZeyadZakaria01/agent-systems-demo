# Score unimplemented conditions as absent, not fail

A condition whose required capability MemState does not implement (C3 extension-edge propagation, C2's declarative policies, C5 on the natural trajectory) gets the verdict *absent*, confirmed by a probe run, and is counted apart from *fail*, which is reserved for capabilities MemState implements but gets wrong. A missing capability is a different finding from a wrong one, and the authors declare the gaps themselves: the README heading reads "(It is Proof-of-Concept, NOT Full Implementation)" (`MemState/README.md:5`), and the paper calls the unbuilt parts "not implementation gaps; they are research directions" (`2605.26252v1.md:331`). Beside each verdict the scorecard marks whether [P1] claims the condition, so a capability that is claimed but missing reads "absent · claimed".

## Considered Options

- Skip unimplemented conditions: leaves gaps with no run behind them, against the evidence rule.
- Score them as fail: merges "not built" with "built wrong", which the prototype's own declaration keeps apart; the "claimed" marker shows the gap against the claim instead.
