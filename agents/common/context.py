"""What an agent carries while handling one event.

An AgentContext is built from the event that woke the agent, so every event the
agent emits inherits that event's run_id and sim_time. Agents never read the
wall clock for domain time; emitted_at is the only wall-clock field, for logs.

IDs are deterministic (#42): each emitted event_id, and each record ID from
`new_id`, derives from the trigger's event_id, the agent and a running count. A
retried delivery of the same trigger reproduces the same IDs, so the projector
can drop duplicates.
"""

import itertools
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from nimbus_contracts.common import Agent
from nimbus_contracts.events import AgentActivity, AgentActivityDetail, PolicyDecided, PolicyDecidedDetail

from common.bus import Bus
from common.ids import new_id as _new_id
from common.policy import Decision, agent_uid, evaluate

_NAMESPACE = uuid.UUID("6f1c2a7e-3b8d-4e51-9a0c-6e4f2d7b8c19")  # NIMBUS agent event IDs


@dataclass(frozen=True)
class AgentContext:
    agent: Agent
    run_id: str
    sim_time: datetime
    bus: Bus
    trigger_id: str = ""
    _events: Any = field(default_factory=itertools.count, repr=False, compare=False)
    _records: Any = field(default_factory=itertools.count, repr=False, compare=False)

    @classmethod
    def for_event(cls, agent: Agent, trigger: Any, bus: Bus) -> "AgentContext":
        """Context for handling `trigger`, any nimbus_contracts event."""
        return cls(agent=agent, run_id=trigger.run_id, sim_time=trigger.sim_time, bus=bus, trigger_id=trigger.event_id)

    def _seed(self, kind: str, counter: Any) -> str:
        return f"{self.trigger_id}|{self.agent.value}|{kind}|{next(counter)}"

    def new_id(self, prefix: str) -> str:
        """A record ID (e.g. "al-…", "pr-…") that a retry of this trigger reproduces."""
        return _new_id(prefix, self.sim_time, self._seed(prefix, self._records))

    def _envelope(self) -> dict[str, Any]:
        return {
            "event_id": str(uuid.uuid5(_NAMESPACE, self._seed("event", self._events))),
            "run_id": self.run_id,
            "sim_time": self.sim_time,
            "emitted_at": datetime.now(UTC),
            "source": self.agent.value,
        }

    def publish(self, event_type: type, detail: Any) -> Any:
        """Build `event_type` with this context's run_id, sim_time and source, publish it, and return it."""
        event = event_type(**self._envelope(), detail=detail)
        self.bus.publish(event)
        return event

    def cedar_check(
        self,
        action: str,
        resource: str,
        *,
        resource_attrs: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> Decision:
        """Ask the Cedar policies whether this agent may act, and emit `policy.decided` either way."""
        decision = evaluate(
            agent_uid(self.agent), action, resource, resource_attrs=resource_attrs, context=context
        )
        self.publish(
            PolicyDecided,
            PolicyDecidedDetail(
                principal=self.agent,
                action=action,
                resource=resource,
                allowed=decision.allowed,
                reason=decision.reason,
            ),
        )
        return decision

    def activity(self, saw: str, decided: str, why: str) -> None:
        """Emit one `agent.activity` line for the console feed."""
        self.publish(AgentActivity, AgentActivityDetail(agent=self.agent, saw=saw, decided=decided, why=why))
