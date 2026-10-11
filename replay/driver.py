"""Replay Driver (#14), minimal: plays a storm's clock by publishing clock.tick events.

Each tick advances sim_time by 15 storm-minutes; --speed is the real seconds between
ticks. The agents are Lambdas that wake on these events. Events go to EventBridge as
contracts/README.md specifies: detail-type = event.type, source = "nimbus.<source>",
detail = the whole event.

    uv run python driver.py --dry-run --ticks 4 --speed 0
    NIMBUS_EVENT_BUS=nimbus uv run python driver.py --ticks 96

Not yet: Step Functions, the console start button, pause/resume, simulated Reports.
"""

import argparse
import os
import sys
import time
import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from nimbus_contracts.events import ClockTick

SOURCE = "replay-driver"
BUS_NAME_ENV = "NIMBUS_EVENT_BUS"
DEFAULT_BUS = "nimbus"
DEFAULT_RUN = "replay-michaung"  # the demo phones are subscribed to this Run
DEFAULT_START = "2023-12-03T18:00:00+05:30"
DEFAULT_TICKS = 96  # 24 storm-hours: through the heaviest Michaung rain on 4 Dec
DEFAULT_SPEED = 2.0  # real seconds per tick, so about 1 storm-hour per 8 s
STEP_MINUTES = 15


class PublishError(RuntimeError):
    pass


def make_tick(run_id: str, start: datetime, index: int, emitted_at: datetime) -> ClockTick:
    return ClockTick(
        event_id=str(uuid.uuid4()),
        run_id=run_id,
        sim_time=start + timedelta(minutes=STEP_MINUTES * index),
        emitted_at=emitted_at,
        source=SOURCE,
        tick_index=index,
        step_minutes=STEP_MINUTES,
    )


def entry(tick: ClockTick, bus_name: str) -> dict[str, str]:
    return {
        "EventBusName": bus_name,
        "Source": f"nimbus.{tick.source}",
        "DetailType": tick.type,
        "Detail": tick.model_dump_json(),
    }


def publish(client: Any, bus_name: str, tick: ClockTick) -> None:
    response = client.put_events(Entries=[entry(tick, bus_name)])
    # put_events reports rejected entries in the response instead of raising.
    if response.get("FailedEntryCount", 0):
        failed = response["Entries"][0]
        raise PublishError(
            f"EventBridge rejected tick {tick.tick_index}: {failed.get('ErrorCode')} {failed.get('ErrorMessage')}"
        )


def drive(
    run_id: str,
    start: datetime,
    ticks: int,
    speed: float,
    send: Callable[[ClockTick], None],
    *,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> int:
    """Send `ticks` ticks, `speed` seconds apart. Returns how many were sent."""
    for index in range(ticks):
        if index:
            sleep(speed)
        # Built just before sending, so emitted_at is the real send time.
        send(make_tick(run_id, start, index, now()))
    return ticks


def _events_client() -> Any:
    import boto3

    return boto3.client("events")


def _parse(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Play a storm's clock as clock.tick events.")
    parser.add_argument("--run-id", default=DEFAULT_RUN, help=f"Run to tick (default {DEFAULT_RUN})")
    parser.add_argument("--start", default=DEFAULT_START, help=f"first sim_time, with UTC offset (default {DEFAULT_START})")
    parser.add_argument("--ticks", type=int, default=DEFAULT_TICKS, help=f"how many ticks (default {DEFAULT_TICKS})")
    parser.add_argument("--speed", type=float, default=DEFAULT_SPEED, help=f"real seconds between ticks (default {DEFAULT_SPEED:g})")
    parser.add_argument("--dry-run", action="store_true", help="print each tick's JSON instead of sending it")
    args = parser.parse_args(argv)

    try:
        args.start = datetime.fromisoformat(args.start)
    except ValueError:
        parser.error(f"--start is not an ISO datetime: {args.start}")
    if args.start.tzinfo is None:
        parser.error("--start needs a UTC offset, e.g. 2023-12-03T18:00:00+05:30")
    if args.ticks < 1:
        parser.error("--ticks must be at least 1")
    if args.speed < 0:
        parser.error("--speed can't be negative")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse(argv)

    if args.dry_run:
        def send(tick: ClockTick) -> None:
            print(tick.model_dump_json(), flush=True)
    else:
        bus_name = os.environ.get(BUS_NAME_ENV, DEFAULT_BUS)
        client = _events_client()

        def send(tick: ClockTick) -> None:
            publish(client, bus_name, tick)
            print(f"tick {tick.tick_index} {tick.sim_time:%d %b %H:%M} -> {bus_name}", file=sys.stderr, flush=True)

    try:
        drive(args.run_id, args.start, args.ticks, args.speed, send)
    except PublishError as error:
        print(error, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("stopped", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
