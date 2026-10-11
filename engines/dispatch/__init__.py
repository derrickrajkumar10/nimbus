"""Dispatch solver (#16). Standard library and nimbus_contracts only: it is bundled into the Dispatcher's Lambda."""

from dispatch.solver import Candidate, rank_work_orders

__all__ = ["Candidate", "rank_work_orders"]
