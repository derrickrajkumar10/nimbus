// NIMBUS Cedar policies, from the design lock ("Guardrails and human-in-the-loop").
// Names follow nimbus_contracts: Agent values are lowercase and AlertScope.WARD is "ward".
// Cedar denies anything no policy permits, and a forbid beats any permit.
// Every policy needs an @id: common/policy.py uses it to name the deciding rule.

// The Herald may send alerts...
@id("herald-may-send-alerts")
permit (principal == Agent::"herald", action == Action::"SendAlert", resource);

// ...but a Ward Alert (ward scope, or more than WARD_ALERT_RECIPIENT_THRESHOLD = 100
// recipients) needs an officer's approval.
@id("ward-alerts-need-approval")
forbid (principal, action == Action::"SendAlert", resource)
  when { resource.scope == "ward" || resource.recipient_count > 100 }
  unless { context.officer_approved };

// Only the Dispatcher touches Work Orders...
@id("dispatcher-may-handle-work-orders")
permit (
  principal == Agent::"dispatcher",
  action in [Action::"ProposeWorkOrder", Action::"DispatchCrew"],
  resource
);

// ...and crews move only after an officer approves.
@id("crew-dispatch-needs-approval")
forbid (principal, action == Action::"DispatchCrew", resource)
  unless { context.officer_approved };

// SOS personal data: the Triage agent and officers only.
@id("triage-may-read-sos")
permit (principal == Agent::"triage", action == Action::"ReadSOS", resource);

@id("officers-may-read-sos")
permit (principal in Role::"Officer", action == Action::"ReadSOS", resource);
