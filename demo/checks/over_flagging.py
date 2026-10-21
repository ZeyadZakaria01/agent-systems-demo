"""Over-flagging measurement (ticket 28): one chain A <- B <- C <- D over extension edges, D the anti-trap. Runs the
scenario with one-hop propagation (the system as opened) and with the transitive walk (a mode of the reference GEM used
only here), and reports flags raised, needed, missed and not needed for each. No verdict (`not-scored`), not on the
scorecard: its table sits beside the C3 row (`demo/over_flagging_tables.py`). Reference GEM only: no MemState system
propagates (F17), so none is measured.
"""

from demo.checks import Ctx, Row, check
from demo.over_flagging import load_scenario, measure
from demo.reference_gem import ReferenceGem
from demo.verdict import Verdict

ROW = "Over-flagging"
CLAIM = ("Not claimed by [P1]: flags raised against flags needed on one chain with one anti-trap, for one-hop and "
         "transitive propagation. A measurement, no verdict.")
REFERENCE_GEM_ID = "reference-gem"  # the id ticket 30 registers the reference GEM under
HOP_MODES = ("one hop", "transitive walk")


@check(rows=[Row(ROW, CLAIM, on_scorecard=False)], systems=(REFERENCE_GEM_ID,))
def over_flagging(ctx: Ctx) -> Verdict:
    scenario = load_scenario()
    one_hop = measure(ctx.system, HOP_MODES[0], scenario)
    transitive = measure(ReferenceGem("reference GEM (transitive walk)", propagation="transitive"), HOP_MODES[1],
                         scenario)
    return Verdict.not_scored(ROW, measurements={
        "over_flagging": {"scenario": scenario["name"], "chain": list(scenario["topics"]),
                          "needs_revision": scenario["needs_revision"],
                          "runs": [one_hop.to_dict(), transitive.to_dict()]}})
