"""Evaluate agent actions against the Cedar policies in agents/policies/.

Fails closed: if any policy errors while evaluating (a missing attribute, a wrong
type), the action is denied. Cedar itself skips a policy that errors, so without
this a forbid that couldn't be evaluated would let a permit win.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cedarpy
from nimbus_contracts.common import Agent

POLICY_FILE = Path(__file__).resolve().parent.parent / "policies" / "nimbus.cedar"

_UID = re.compile(r'^(\w+)::"([^"]*)"$')


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    rules: tuple[str, ...] = field(default=())  # @id of each policy that decided


def load_policies(path: Path = POLICY_FILE) -> tuple[str, list[str]]:
    """The policy text, and each policy's @id in file order."""
    text = path.read_text()
    return text, re.findall(r'@id\("([^"]+)"\)', text)


_POLICIES, _POLICY_NAMES = load_policies()


def agent_uid(agent: Agent) -> str:
    return f'Agent::"{agent.value}"'


def officer_uid(officer_id: str) -> str:
    return f'Officer::"{officer_id}"'


OFFICER_ROLE = 'Role::"Officer"'


def _entity_ref(uid: str) -> dict[str, Any]:
    match = _UID.match(uid)
    if not match:
        raise ValueError(f"not a Cedar entity UID: {uid!r}")
    return {"__entity": {"type": match[1], "id": match[2]}}


def _rule_name(cedar_id: str) -> str:
    # cedarpy ignores @id and numbers policies policy0, policy1, ... in file order.
    index = int(cedar_id.removeprefix("policy"))
    return _POLICY_NAMES[index]


def evaluate(
    principal: str,
    action: str,
    resource: str,
    *,
    resource_attrs: dict[str, Any] | None = None,
    principal_parents: tuple[str, ...] = (),
    context: dict[str, Any] | None = None,
) -> Decision:
    """Ask Cedar whether `principal` may take `action` on `resource`.

    UIDs are Cedar strings such as 'Agent::"herald"' and 'Alert::"a-17"'.
    `officer_approved` defaults to False when the context doesn't set it.
    """
    entities = [
        {"uid": _entity_ref(principal), "attrs": {}, "parents": [_entity_ref(p) for p in principal_parents]},
        {"uid": _entity_ref(resource), "attrs": resource_attrs or {}, "parents": []},
    ]
    request = {
        "principal": principal,
        "action": f'Action::"{action}"',
        "resource": resource,
        "context": {"officer_approved": False, **(context or {})},
    }
    result = cedarpy.is_authorized(request, _POLICIES, entities)

    if result.diagnostics.errors:
        return Decision(False, f"blocked: rule check failed ({result.diagnostics.errors[0]})")

    rules = tuple(_rule_name(r) for r in result.diagnostics.reasons)
    if result.allowed:
        return Decision(True, f"allowed by {', '.join(rules)}", rules)
    if rules:
        return Decision(False, f"blocked by {', '.join(rules)}", rules)
    return Decision(False, "blocked: no rule allows this")
