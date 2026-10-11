"""A stand-in agent that proves the runtime end to end (issue #5).

It acts as the Herald, since only the Herald may SendAlert: on any event it asks
Cedar whether it may send a one-Segment Place Alert, and logs the answer. It sends
nothing. Real agents follow the same shape: a `handle(ctx, event)` and
`handler = make_handler(...)`.
"""

from nimbus_contracts.common import Agent
from nimbus_contracts.entities import AlertScope

from common.context import AgentContext
from common.runtime import make_handler


def handle(ctx: AgentContext, event) -> None:
    decision = ctx.cedar_check(
        "SendAlert",
        f'Alert::"stub-{event.event_id}"',
        resource_attrs={"scope": AlertScope.PLACE.value, "recipient_count": 1},
    )
    ctx.activity(
        saw=f"{event.type} at {event.sim_time:%d %b %Y %H:%M}",
        decided="Would send a test Place Alert" if decision.allowed else "Held the test Place Alert",
        why=decision.reason,
    )


handler = make_handler(Agent.HERALD, handle)
