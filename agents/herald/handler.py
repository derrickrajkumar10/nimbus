"""Herald Lambda: wakes on risk.changed and proposal.decided.

Runs on practice Subscribers until PlaceIndex is wired up (#32), with an
in-memory alert log and risk view. The send-push Lambda is looked up only when
the first alert is sent, because its SSM name ships later with #6.
"""

from functools import cache

from nimbus_contracts.common import Agent

from common.context import AgentContext
from common.push import LambdaPushSender
from common.runtime import make_handler
from herald.core import Herald
from herald.subscribers import practice_subscribers
from sentinel.core import MemoryRiskStore
from sentinel.fixtures import load_segments


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
        subscribers=practice_subscribers(),
        sender=_LazyLambdaSender(),
        risks=MemoryRiskStore(),
    )


def handle(ctx: AgentContext, event) -> None:
    if event.type == "risk.changed":
        _herald().on_risk_changed(ctx, event)
    elif event.type == "proposal.decided":
        _herald().on_proposal_decided(ctx, event)


handler = make_handler(Agent.HERALD, handle)
