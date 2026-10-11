"""A Run's current time. Domain records carry storm time, never the phone's or the server's clock.

`live` runs on the wall clock. A Replay's clock is `Runs.sim_time`, else the newest `sim_time`
seen in the Run's agent activity (the Replay Driver doesn't write `Runs` yet). A Replay with
neither hasn't started, and a Report or SOS made then would have no storm time to carry.
"""

from collections.abc import Callable
from datetime import datetime

from citizen.store import Store

RECENT_ACTIVITY = 20


class RunNotStarted(Exception):
    pass


def run_sim_time(store: Store, run_id: str, now: Callable[[], datetime]) -> datetime:
    if run_id == "live":
        return now()
    row = store.get("Runs", run_id)
    if row and row.get("sim_time"):
        return datetime.fromisoformat(str(row["sim_time"]))
    recent = store.query("Activity", run_id, newest_first=True, limit=RECENT_ACTIVITY)
    times = [datetime.fromisoformat(str(r["sim_time"])) for r in recent if r.get("sim_time")]
    if not times:
        raise RunNotStarted(run_id)
    return max(times)
