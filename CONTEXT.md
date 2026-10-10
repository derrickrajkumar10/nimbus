# NIMBUS

NIMBUS predicts which Chennai segments will flood in the next few hours, routes people around them, and gives ward officers a ranked list of actions to approve.

## Language

### Place

**Segment**:
A stretch of road between two intersections, derived from an OpenStreetMap way. The unit that carries a Flood Threshold, risk, Readings and ledger history.
_Avoid_: street (when you mean a segment), road, link, edge

**Street**:
A named road made up of one or more Segments. Used only for display, in alerts and reports.
_Avoid_: segment

**Ward**:
The administrative area an officer is responsible for (Velachery for the demo).

**Locality**:
A named neighbourhood (Ram Nagar, Vijayanagar) as news coverage and residents name it. Used to compare predictions with reported flooding.

### Prediction

**Baseline Threshold**:
The Flood Threshold computed for a Segment from terrain alone, before any Reading has corrected it.

**Flood Threshold**:
The accumulated rainfall (mm) over a rolling window after which a Segment floods. Starts at the Baseline Threshold and is nudged by Readings within a Run.
_Avoid_: fill rate, capacity, mm/hr threshold

**Antecedent Rain**:
Rain over the past 72 hours. Wet ground lowers the effective Flood Threshold.

**Risk Score**:
A 0–100 prediction of how likely a Segment is to flood soon, with an estimated time to flood and its top three reasons.

**Risk Band**:
The bucket a Segment is in: **low**, **watch** or **likely** come from the Risk Score; **flooded** comes only from a Reading and overrides the score until the water drains.
_Avoid_: calling a predicted Segment "flooded"

### Observation

**Reporter**:
A citizen who submits Reports, identified by their NIMBUS app install (an anonymous identity, no sign-up).

**Report**:
One citizen submission: a photo, a GPS fix and a time, with an optional note.
_Avoid_: reading, observation

**Reading**:
A verified water depth on a Segment, derived by the Verifier from one or more merged Reports. Only Readings affect risk and Flood Thresholds.
_Avoid_: verified report, depth report

**Trust Score**:
How much weight a Reporter's Reports carry, earned by agreeing with other Readings.

**SOS**:
A request for rescue from people who are stranded. Its photo can yield a Reading, but an SOS is not a Report.

### Response

**Saved Place**:
A place a citizen cares about (home, office, school, where the bike is parked), covering one or more Segments. Alerts are addressed to Saved Places.

**Hazard**:
A danger hidden under water (open manhole, live wire, fallen tree, stranded vehicle) at a location. Routes keep clear of it.

**Resource**:
Something an officer can send: a pump, a desilting crew or a tree crew.

**Subscriber**:
An app install that receives alerts for its Saved Places within a Run.

**Place Alert**:
An alert to Subscribers whose Saved Places sit on affected Segments. Goes out without approval.

**Ward Alert**:
An alert to everyone in a Ward, or to more than 100 Subscribers at once. Always a Proposal first.
_Avoid_: broadcast, mass alert

**Proposal**:
An agent action that policy holds until a ward officer approves, edits or rejects it.
_Avoid_: task, action item, to-do

**Work Order**:
A Proposal to send a Resource to a Segment.
_Avoid_: dispatch order, order (alone)

### Runs

**Run**:
An isolated timeline of NIMBUS state: either **live** or a named **Replay**. Every Flood Threshold nudge, Trust Score, Reading and ledger entry belongs to exactly one Run.

**Replay**:
A Run that feeds a past storm's rainfall through the same pipeline on a fast clock, starting from Baseline Thresholds.
_Avoid_: simulation, demo mode

**Prior-only Run**:
A Replay with no Reports, used to measure the hit rate against reported flooding without the team's simulated Reports influencing the result.

**Hit Rate**:
The share of Localities reported flooded that a Prior-only Run predicted. A Locality counts as predicted when at least 20% of its Segments reach **likely**. Always shown alongside false alarms.
