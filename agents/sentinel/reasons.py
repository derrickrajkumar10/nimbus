"""Nova Lite rewrites a Segment's top reason as one plain sentence (#9).

Rewrites are cached by reason text, since the same reason recurs tick after tick.
Each rewrite uses a fresh Strands agent: a reused one keeps its conversation and
would resend every earlier rewrite, so each call would cost more than the last.
If the model call fails, the original text is kept so risk.changed still goes out.
A refusal that won't change on retry (the account isn't authorized for the model)
switches rewriting off for the rest of the Lambda's life, so ticks don't keep asking.
"""

import logging
from collections.abc import Callable
from typing import Any

from nimbus_contracts.common import Agent, Reason

from common.models import build_agent

log = logging.getLogger(__name__)

# Bedrock errors that mean "this account can't use the model", not "try again".
PERMANENT_REFUSALS = ("AccessDeniedException", "Operation not allowed", "not authorized")

SYSTEM_PROMPT = (
    "You rewrite one technical flood-risk reason for a Chennai street as one short, plain "
    "English sentence a resident understands. Keep every number and unit. Add no facts. "
    "Say a street is 'likely to waterlog', never that it 'will flood'. Reply with the sentence only."
)


class ReasonWriter:
    def __init__(self, rewrite: Callable[[str], str] | None = None, *, boto_session: Any = None) -> None:
        self._rewrite = rewrite or self._nova_rewrite
        self._boto_session = boto_session
        self._cache: dict[str, str] = {}
        self.disabled = False

    def _nova_rewrite(self, text: str) -> str:
        agent = build_agent(Agent.SENTINEL, SYSTEM_PROMPT, boto_session=self._boto_session)
        return str(agent(text))

    def plain(self, reason: Reason) -> Reason:
        if self.disabled:
            return reason
        if reason.text not in self._cache:
            try:
                self._cache[reason.text] = self._rewrite(reason.text).strip() or reason.text
            except Exception as exc:
                if any(marker in f"{type(exc).__name__} {exc}" for marker in PERMANENT_REFUSALS):
                    self.disabled = True
                    log.warning("Nova unavailable (%s); keeping original reason text from now on", exc)
                else:
                    log.exception("reason rewrite failed; keeping the original text")
                return reason  # not cached, so a transient failure is retried next tick
        return Reason(code=reason.code, text=self._cache[reason.text])
