"""What an agent carries while handling one event.

An AgentContext is built from the event that woke the agent, so every event the
agent emits inherits that event's run_id and sim_time. Agents never read the
wall clock for domain time; emitted_at is the only wall-clock field, for logs.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from nimbus_contracts.common import Agent
from nimbus_contracts.events import AgentActivity, AgentActivityDetail, PolicyDecided, PolicyDecidedDetail

from common.bus import Bus
from common.policy import Decision, agent_uid, evaluate


@dataclass(frozen=True)
class AgentContext:
    agent: Agent
    run_id: str
    sim_time: datetime
    bus: Bus

    @classmethod
    def for_event(cls, agent: Agent, trigger: Any, bus: Bus) -> "AgentContext":
        """Context for handling `trigger`, any nimbus_contracts event."""
        return cls(agent=agent, run_id=trigger.run_id, sim_time=trigger.sim_time, bus=bus)

    def _envelope(self) -> dict[str, Any]:
        return {
            "event_id": str(uuid.uuid4()),
            "run_id": self.run_id,
            "sim_time": self.sim_time,
            "emitted_at": datetime.now(UTC),
            "source": self.agent.value,
        }

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
        self.bus.publish(
            PolicyDecided(
                **self._envelope(),
                detail=PolicyDecidedDetail(
                    principal=self.agent,
                    action=action,
                    resource=resource,
                    allowed=decision.allowed,
                    reason=decision.reason,
                ),
            )
        )
        return decision

    def activity(self, saw: str, decided: str, why: str) -> None:
        """Emit one `agent.activity` line for the console feed."""
        self.bus.publish(
            AgentActivity(
                **self._envelope(),
                detail=AgentActivityDetail(agent=self.agent, saw=saw, decided=decided, why=why),
            )
        )
