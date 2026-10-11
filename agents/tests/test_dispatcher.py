"""Dispatcher (#18). Done when: on fixtures, a tick proposes Pump 2 to Velachery Main Road as a
Work Order, and only an officer's approval moves it. All local: MemoryBus, the fixture
Resources, an in-memory Proposals table filled the way the projector fills the real one."""

from datetime import UTC, datetime

from dispatch import rank_work_orders
from nimbus_contracts.common import Agent, RiskBand
from nimbus_contracts.entities import ProposalStatus, ResourceStatus
from nimbus_contracts.events import ProposalDecided, ProposalDecidedDetail

from common.bus import MemoryBus
from common.context import AgentContext
from common.ids import new_id
from common.runtime import make_handler
from dispatcher.core import Dispatcher
from dispatcher.handler import _fixture_resources
from dispatcher.store import MemoryProposals
from sentinel.core import MemoryRiskStore, run_tick
from sentinel.fixtures import FixtureScorer, load_segments
from sentinel.reasons import ReasonWriter
from tests.test_sentinel import tick

PUMP_2 = "rs-pump-2"
FLOODED_VMR = "27480309-1"  # Velachery Main Road, flooded in fixtures


class World:
    """Sentinel, then Dispatcher, sharing one bus and risk store, like the deployed system."""

    def __init__(self, run_id="replay-michaung"):
        self.run_id = run_id
        self.bus = MemoryBus()
        self.risks = MemoryRiskStore()
        self.resources = _fixture_resources()
        self.proposals = MemoryProposals()
        self.dispatcher = Dispatcher(
            segments=load_segments(), risks=self.risks, resources=self.resources, proposals=self.proposals, solver=rank_work_orders
        )
        self.ticks = 0

    def sentinel_tick(self, scorer=None, project=True):
        t = tick(8 + self.ticks, minutes_later=15 * self.ticks).model_copy(update={"run_id": self.run_id})
        self.ticks += 1
        ctx = AgentContext.for_event(Agent.SENTINEL, t, self.bus)
        run_tick(ctx, t, segments=load_segments(), scorer=scorer or FixtureScorer(), store=self.risks, reasons=ReasonWriter(lambda text: text))
        line = self.bus.of_type("agent.activity")[-1]
        before = len(self.bus.events)
        self.dispatcher.on_sentinel_tick(AgentContext.for_event(Agent.DISPATCHER, line, self.bus), line)
        if project:
            self.project()
        return self.bus.events[before:]

    def project(self):
        """What the projector does: proposal.created into the Proposals table, first write wins."""
        known = {p.proposal_id for p in self.proposals.rows}
        for e in self.bus.of_type("proposal.created"):
            if e.detail.proposal_id not in known:
                self.proposals.rows.append(e.detail)
                known.add(e.detail.proposal_id)

    def decide(self, proposal, decision):
        self.proposals.rows = [
            p.model_copy(update={"status": decision}) if p.proposal_id == proposal.proposal_id else p for p in self.proposals.rows
        ]
        at = proposal.created_at
        event = ProposalDecided(
            event_id=new_id("ev", at), run_id=self.run_id, sim_time=at, emitted_at=datetime.now(UTC), source="console",
            detail=ProposalDecidedDetail(proposal_id=proposal.proposal_id, decision=decision, decided_by="officer-priya", proposal=proposal),
        )
        before = len(self.bus.events)
        self.dispatcher.on_proposal_decided(AgentContext.for_event(Agent.DISPATCHER, event, self.bus), event)
        return self.bus.events[before:]


def of_type(events, kind):
    return [e for e in events if e.type == kind]


def test_fixture_tick_proposes_pump_2_to_velachery_main_road():
    w = World()
    events = w.sentinel_tick()

    [created] = of_type(events, "proposal.created")
    p = created.detail
    assert p.proposed_by == "dispatcher" and p.status == ProposalStatus.PENDING and p.rank == 1
    assert (p.action.kind, p.action.resource_id, p.action.segment_id) == ("work_order", PUMP_2, FLOODED_VMR)
    assert p.action.buildings_affected == 17
    assert p.reason.startswith("Send Pump 2 to Velachery Main Road: flooded")
    assert "Score" in p.reason and "min travel" in p.reason  # the numbers behind the pick

    [check] = of_type(events, "policy.decided")
    assert check.detail.action == "ProposeWorkOrder" and check.detail.allowed
    [line] = of_type(events, "agent.activity")
    assert line.detail.agent == "dispatcher"
    assert line.detail.decided == "Proposed 1 Work Order for officer approval"


def test_events_carry_the_ticks_run_and_storm_time():
    w = World(run_id="replay-test")
    events = w.sentinel_tick()
    assert events and all(e.run_id == "replay-test" and e.source == "dispatcher" for e in events)
    sentinel_time = w.bus.of_type("agent.activity")[0].sim_time
    assert all(e.sim_time == sentinel_time for e in events)


def test_the_next_tick_proposes_nothing_new():
    w = World()
    w.sentinel_tick()
    assert w.sentinel_tick() == []  # Pump 2 is spoken for; the feed stays quiet


def test_no_duplicate_while_the_projector_lags():
    w = World()
    w.sentinel_tick(project=False)
    assert of_type(w.sentinel_tick(project=False), "proposal.created") == []


def test_nothing_at_risk_means_silence():
    w = World()
    calm = lambda segs, run_id, t: [r.model_copy(update={"band": RiskBand.WATCH}) for r in FixtureScorer()(segs, run_id, t)]  # noqa: E731
    assert w.sentinel_tick(scorer=calm) == []


def test_approval_sends_the_pump_en_route():
    w = World()
    [created] = of_type(w.sentinel_tick(), "proposal.created")
    events = w.decide(created.detail, ProposalStatus.APPROVED)

    [check] = of_type(events, "policy.decided")
    assert check.detail.action == "DispatchCrew" and check.detail.allowed
    [line] = of_type(events, "agent.activity")
    assert line.detail.decided == "Pump 2 en route to Velachery Main Road"
    pump = next(r for r in w.resources.for_run(w.run_id) if r.resource_id == PUMP_2)
    assert pump.status == ResourceStatus.EN_ROUTE


def test_rejection_keeps_the_pump_free_and_never_repeats_that_pair():
    w = World()
    [created] = of_type(w.sentinel_tick(), "proposal.created")
    [line] = of_type(w.decide(created.detail, ProposalStatus.REJECTED), "agent.activity")
    assert line.detail.decided == "No crew moved"
    assert next(r for r in w.resources.for_run(w.run_id) if r.resource_id == PUMP_2).status == ResourceStatus.FREE

    [again] = of_type(w.sentinel_tick(), "proposal.created")
    assert again.detail.action.resource_id == PUMP_2
    assert again.detail.action.segment_id != FLOODED_VMR  # the next-best Segment instead


def test_only_an_officer_can_move_a_crew():
    from common.policy import agent_uid, evaluate

    unapproved = evaluate(agent_uid(Agent.DISPATCHER), "DispatchCrew", 'WorkOrder::"pr-1"')
    assert not unapproved.allowed


def test_ward_alert_decisions_are_not_the_dispatchers():
    w = World()
    from tests.test_herald import World as HeraldWorld, crowd

    h = HeraldWorld(subscribers=crowd(150))
    h.risk_changed("27480309-4", "watch", "likely")
    [ward] = h.bus.of_type("proposal.created")
    assert w.decide(ward.detail, ProposalStatus.APPROVED) == []


def test_lambda_handler_wakes_on_the_sentinels_line_only(monkeypatch):
    import dispatcher.handler as dh

    for table in ("RESOURCES", "PROPOSALS", "SEGMENTRISK"):
        monkeypatch.delenv(f"NIMBUS_TABLE_{table}", raising=False)
    dh._dispatcher.cache_clear()
    bus = MemoryBus()
    handler = make_handler(Agent.DISPATCHER, dh.handle, bus=bus)

    # Seed the in-memory risk view the way a Sentinel tick would.
    t = tick()
    run_tick(AgentContext.for_event(Agent.SENTINEL, t, MemoryBus()), t, segments=load_segments(), scorer=FixtureScorer(),
             store=dh._dispatcher().risks, reasons=ReasonWriter(lambda text: text))
    sentinel_bus = MemoryBus()
    run_tick(AgentContext.for_event(Agent.SENTINEL, t, sentinel_bus), t, segments=load_segments(), scorer=FixtureScorer(),
             store=MemoryRiskStore(), reasons=ReasonWriter(lambda text: text))
    [line] = sentinel_bus.of_type("agent.activity")

    herald_line = line.model_copy(update={"detail": line.detail.model_copy(update={"agent": Agent.HERALD})})
    handler({"detail-type": "agent.activity", "source": "nimbus.herald", "detail": herald_line.model_dump(mode="json")})
    assert bus.events == []

    handler({"detail-type": "agent.activity", "source": "nimbus.sentinel", "detail": line.model_dump(mode="json")})
    [created] = bus.of_type("proposal.created")
    assert created.detail.action.resource_id == PUMP_2
    dh._dispatcher.cache_clear()


def test_dynamo_stores_query_the_run_and_update_only_existing_resources():
    import boto3
    from botocore.stub import Stubber

    from common.dynamo import to_item
    from dispatcher.store import DynamoProposals, DynamoResources

    client = boto3.client("dynamodb", region_name="us-east-1", aws_access_key_id="fake", aws_secret_access_key="fake")
    w = World()
    [created] = of_type(w.sentinel_tick(), "proposal.created")
    pump = w.resources.for_run(w.run_id)[1]
    query = {"TableName": "t", "KeyConditionExpression": "run_id = :run", "ExpressionAttributeValues": {":run": {"S": w.run_id}}}
    with Stubber(client) as stub:
        stub.add_response("query", {"Items": [to_item(created.detail)]}, query)
        stub.add_response("query", {"Items": [to_item(pump)]}, query)
        stub.add_response("update_item", {})
        stub.add_client_error("update_item", "ConditionalCheckFailedException")
        assert [p.proposal_id for p in DynamoProposals("t", client).by_agent(w.run_id, "dispatcher")] == [created.detail.proposal_id]
        resources = DynamoResources("t", client)
        assert resources.for_run(w.run_id) == [pump]
        assert resources.set_status(w.run_id, PUMP_2, ResourceStatus.EN_ROUTE) is True
        assert resources.set_status(w.run_id, "rs-nope", ResourceStatus.EN_ROUTE) is False
