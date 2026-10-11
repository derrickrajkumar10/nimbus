"""Nova Lite rewrites a Segment's top reason as one plain sentence (#9).

Rewrites are cached by reason text, since the same reason recurs tick after tick.
Each rewrite uses a fresh Strands agent: a reused one keeps its conversation and
would resend every earlier rewrite, so each call would cost more than the last.
If the model call fails, the original text is kept so risk.changed still goes out.
"""

import logging
from collections.abc import Callable
from typing import Any

from nimbus_contracts.common import Agent, Reason

from common.models import build_agent

log = logging.getLogger(__name__)

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

    def _nova_rewrite(self, text: str) -> str:
        agent = build_agent(Agent.SENTINEL, SYSTEM_PROMPT, boto_session=self._boto_session)
        return str(agent(text))

    def plain(self, reason: Reason) -> Reason:
        if reason.text not in self._cache:
            try:
                self._cache[reason.text] = self._rewrite(reason.text).strip() or reason.text
            except Exception:
                log.exception("reason rewrite failed; keeping the original text")
                return reason  # not cached, so the next tick retries
        return Reason(code=reason.code, text=self._cache[reason.text])
