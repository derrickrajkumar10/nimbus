import re

import pytest
from nimbus_contracts.common import Agent
from nimbus_contracts.entities import WARD_ALERT_RECIPIENT_THRESHOLD, AlertScope

from common.policy import OFFICER_ROLE, POLICY_FILE, agent_uid, evaluate, load_policies, officer_uid

HERALD = agent_uid(Agent.HERALD)
SENTINEL = agent_uid(Agent.SENTINEL)
DISPATCHER = agent_uid(Agent.DISPATCHER)
TRIAGE = agent_uid(Agent.TRIAGE)
OFFICER = officer_uid("priya")

ALERT = 'Alert::"a-1"'
WORK_ORDER = 'WorkOrder::"wo-1"'
SOS = 'Sos::"sos-1"'


def place_alert(recipients: int = 12) -> dict:
    return {"scope": AlertScope.PLACE.value, "recipient_count": recipients}


def ward_alert() -> dict:
    return {"scope": AlertScope.WARD.value, "recipient_count": 4000}


def check(principal, action, resource, attrs=None, approved=None, parents=()):
    context = {} if approved is None else {"officer_approved": approved}
    return evaluate(principal, action, resource, resource_attrs=attrs, principal_parents=parents, context=context)


CASES = [
    # (description, principal, action, resource, attrs, officer_approved, parents, allowed, deciding rule or None)
    ("Herald alerts one street", HERALD, "SendAlert", ALERT, place_alert(), None, (), True, "herald-may-send-alerts"),
    ("Herald ward alert, no approval", HERALD, "SendAlert", ALERT, ward_alert(), None, (), False, "ward-alerts-need-approval"),
    ("Herald ward alert, approved", HERALD, "SendAlert", ALERT, ward_alert(), True, (), True, "herald-may-send-alerts"),
    ("Herald place alert over 100 people, no approval", HERALD, "SendAlert", ALERT,
     place_alert(WARD_ALERT_RECIPIENT_THRESHOLD + 1), None, (), False, "ward-alerts-need-approval"),
    ("Herald place alert at exactly 100 people", HERALD, "SendAlert", ALERT,
     place_alert(WARD_ALERT_RECIPIENT_THRESHOLD), None, (), True, "herald-may-send-alerts"),
    ("Sentinel tries to send an alert", SENTINEL, "SendAlert", ALERT, place_alert(), None, (), False, None),
    ("Dispatcher proposes a Work Order", DISPATCHER, "ProposeWorkOrder", WORK_ORDER, None, None, (), True,
     "dispatcher-may-handle-work-orders"),
    ("Dispatcher dispatches a crew, no approval", DISPATCHER, "DispatchCrew", WORK_ORDER, None, None, (), False,
     "crew-dispatch-needs-approval"),
    ("Dispatcher dispatches a crew, approved", DISPATCHER, "DispatchCrew", WORK_ORDER, None, True, (), True,
     "dispatcher-may-handle-work-orders"),
    ("Herald tries to propose a Work Order", HERALD, "ProposeWorkOrder", WORK_ORDER, None, None, (), False, None),
    ("Triage reads an SOS", TRIAGE, "ReadSOS", SOS, None, None, (), True, "triage-may-read-sos"),
    ("Officer reads an SOS", OFFICER, "ReadSOS", SOS, None, None, (OFFICER_ROLE,), True, "officers-may-read-sos"),
    ("Herald tries to read an SOS", HERALD, "ReadSOS", SOS, None, None, (), False, None),
    ("Non-officer person tries to read an SOS", OFFICER, "ReadSOS", SOS, None, None, (), False, None),
]


@pytest.mark.parametrize(
    "principal, action, resource, attrs, approved, parents, allowed, rule",
    [case[1:] for case in CASES],
    ids=[case[0] for case in CASES],
)
def test_policy_decisions(principal, action, resource, attrs, approved, parents, allowed, rule):
    decision = check(principal, action, resource, attrs, approved, parents)
    assert decision.allowed is allowed, decision.reason
    if rule is None:
        assert decision.rules == ()
        assert decision.reason == "blocked: no rule allows this"
    else:
        assert rule in decision.rules, decision.reason


def test_alert_missing_scope_fails_closed():
    # Without `scope`, Cedar can't evaluate the Ward Alert forbid and would skip it,
    # letting the Herald's permit win. evaluate() must block instead.
    decision = check(HERALD, "SendAlert", ALERT, {"recipient_count": 5000})
    assert decision.allowed is False
    assert decision.reason.startswith("blocked: rule check failed")


def test_every_policy_has_an_id():
    text, names = load_policies(POLICY_FILE)
    statements = re.findall(r"^\s*(?:permit|forbid)\s*\(", text, flags=re.MULTILINE)
    assert len(names) == len(statements)
    assert len(set(names)) == len(names)


def test_policy_text_matches_contract_values():
    # The design lock wrote "ward_wide" and "Herald"; the contracts use "ward" and "herald".
    text, _ = load_policies(POLICY_FILE)
    assert f'resource.scope == "{AlertScope.WARD.value}"' in text
    assert f"recipient_count > {WARD_ALERT_RECIPIENT_THRESHOLD}" in text
    for agent in (Agent.HERALD, Agent.DISPATCHER, Agent.TRIAGE):
        assert agent_uid(agent) in text
