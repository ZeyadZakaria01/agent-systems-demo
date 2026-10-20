"""C1 (query soundness), the control: store `Deadline: March 15`, update it to `April 20` through
`version_field`; the default read returns only April 20, a temporal read returns the full history."""

from demo.checks import Ctx, check
from demo.reads import current_value, field_in_response, history_values, read_request
from demo.verdict import Case, Verdict

CLAIM = ("C1 (query soundness): the response reflects the most recent non-archived value as current; "
         "prior values appear only when the query explicitly requests historical context.")


@check(row="C1", claim=CLAIM, control=True)
def c1(ctx: Ctx) -> Verdict:
    s = ctx.system
    topic = s.ingest({"placement": "new_topic", "title": "Website Redesign", "topic_kind": "project",
                      "fields": [{"name": "Deadline", "value": "March 15", "provenance": "kickoff-notes"}]})
    topic_id = topic["topic_id"]
    s.ingest({"placement": "version_field", "topic_id": topic_id,
              "fields": [{"name": "Deadline", "value": "April 20", "provenance": "pm-email",
                          "why_changed": "vendor delay"}]})

    default = s.query(read_request(topic_id))
    default_field = field_in_response(default, topic_id, "Deadline")
    default_values = history_values(default_field) or [current_value(default_field)]
    default_case = Case(
        "default read returns only April 20",
        held=current_value(default_field) == "April 20" and default_values == ["April 20"],
        observation=f"current={current_value(default_field)!r}, values returned={default_values!r}",
    )

    temporal = s.query(read_request(topic_id, explain=True))
    temporal_field = field_in_response(temporal, topic_id, "Deadline")
    values = history_values(temporal_field)
    if s.describe()["keeps_history"] is False:
        temporal_case = Case("temporal read returns the full history", held=None,
                             observation=f"the system declares it keeps no history; its temporal read gives current="
                                         f"{current_value(temporal_field)!r} only (history is C4's concern)")
    else:
        temporal_case = Case("temporal read returns the full history",
                             held=current_value(temporal_field) == "April 20" and values == ["April 20", "March 15"],
                             observation=f"current={current_value(temporal_field)!r}, history newest first={values!r}"
                                         + (" (no history returned)" if values is None else ""))
    return Verdict.from_cases("C1", [default_case, temporal_case])
