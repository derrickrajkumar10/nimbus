"""Herald Lambda: wakes on risk.changed and proposal.decided.

Reads Subscribers from PlaceIndex and current risk from SegmentRisk when their
table env vars are set (always, when deployed); otherwise practice Subscribers and
an in-memory risk view, for local runs. The per-place alert log is still in memory
(#42). With NIMBUS_SEND_PUSH_FUNCTION set, alerts go to the send-push Lambda (#6),
looked up on the first send; without it the Herald records alerts only and says
"push not connected".
"""

import os
from functools import cache

from nimbus_contracts.common import Agent

from common.context import AgentContext
from common.push import SEND_PUSH_ENV, LambdaPushSender, RecordOnlySender
from common.runtime import make_handler
from herald.core import Herald
from herald.subscribers import DynamoSubscribers, practice_subscribers
from sentinel.core import MemoryRiskStore
from sentinel.fixtures import load_segments
from sentinel.store import DynamoRiskStore


class _LazyLambdaSender:
    def __init__(self) -> None:
        self._sender: LambdaPushSender | None = None

    def send(self, push):
        if self._sender is None:
            self._sender = LambdaPushSender()
        return self._sender.send(push)


@cache
def _herald() -> Herald:
    return Herald(
        segments=load_segments(),
        subscribers=DynamoSubscribers.from_env() or practice_subscribers(),
        sender=_LazyLambdaSender() if os.environ.get(SEND_PUSH_ENV) else RecordOnlySender(),
        risks=DynamoRiskStore.from_env() or MemoryRiskStore(),
    )


def handle(ctx: AgentContext, event) -> None:
    if event.type == "risk.changed":
        _herald().on_risk_changed(ctx, event)
    elif event.type == "proposal.decided":
        _herald().on_proposal_decided(ctx, event)


handler = make_handler(Agent.HERALD, handle)
