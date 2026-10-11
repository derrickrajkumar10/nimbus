"""Replay Driver. Publishing runs against botocore's Stubber with fake keys, so nothing reaches AWS."""

import json
from datetime import UTC, datetime, timedelta, timezone

import boto3
import pytest
from botocore.stub import Stubber
from nimbus_contracts.events import ClockTick

import driver

IST = timezone(timedelta(hours=5, minutes=30))
START = datetime(2023, 12, 3, 18, 0, tzinfo=IST)
NOW = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)


def fake_events_client():
    return boto3.client("events", region_name="us-east-1", aws_access_key_id="fake", aws_secret_access_key="fake")


def no_aws(service):
    raise AssertionError(f"the dry run must not create an AWS client, asked for {service}")


def dry_run(monkeypatch, capsys, *args: str) -> list[ClockTick]:
    monkeypatch.setattr(driver, "_aws_client", no_aws)
    assert driver.main(["--dry-run", "--speed", "0", *args]) == 0
    return [ClockTick.model_validate_json(line) for line in capsys.readouterr().out.splitlines()]


def test_dry_run_prints_valid_ticks_with_the_defaults(monkeypatch, capsys):
    ticks = dry_run(monkeypatch, capsys, "--ticks", "5")

    assert len(ticks) == 5
    assert [t.tick_index for t in ticks] == [0, 1, 2, 3, 4]
    assert ticks[0].sim_time == START
    assert all(t.run_id == "replay-michaung" for t in ticks)
    assert all(t.source == "replay-driver" and t.step_minutes == 15 for t in ticks)
    assert len({t.event_id for t in ticks}) == 5


def test_sim_time_steps_by_15_minutes_and_keeps_ist(monkeypatch, capsys):
    ticks = dry_run(monkeypatch, capsys, "--ticks", "9")

    steps = {b.sim_time - a.sim_time for a, b in zip(ticks, ticks[1:])}
    assert steps == {timedelta(minutes=15)}
    assert ticks[-1].sim_time == START + timedelta(hours=2)
    assert all(t.sim_time.utcoffset() == timedelta(hours=5, minutes=30) for t in ticks)


def test_run_id_and_start_are_flags(monkeypatch, capsys):
    ticks = dry_run(monkeypatch, capsys, "--ticks", "2", "--run-id", "replay-michaung-2", "--start", "2023-12-04T02:00:00+05:30")

    assert [t.run_id for t in ticks] == ["replay-michaung-2"] * 2
    assert ticks[0].sim_time == datetime(2023, 12, 4, 2, 0, tzinfo=IST)


def test_bad_flags_are_rejected(monkeypatch):
    monkeypatch.setattr(driver, "_aws_client", no_aws)
    for bad in (
        ["--start", "2023-12-03T18:00:00"],
        ["--start", "yesterday"],
        ["--ticks", "0"],
        ["--speed", "-1"],
        ["--run-id", "live"],
        ["--demo-phone", "no-place-id"],
        ["--demo-phone", "sim-007#home"],
    ):
        with pytest.raises(SystemExit):
            driver.main(["--dry-run", *bad])


def test_drive_waits_speed_seconds_between_ticks():
    sent, slept = [], []
    driver.drive("replay-michaung", START, 4, 2.0, sent.append, sleep=slept.append, now=lambda: NOW)

    assert len(sent) == 4
    assert slept == [2.0, 2.0, 2.0]
    assert all(t.emitted_at == NOW for t in sent)


def test_publish_sends_the_agreed_envelope():
    client = fake_events_client()
    tick = driver.make_tick("replay-michaung", START, 0, NOW)
    expected = {
        "Entries": [
            {
                "EventBusName": "nimbus",
                "Source": "nimbus.replay-driver",
                "DetailType": "clock.tick",
                "Detail": tick.model_dump_json(),
            }
        ]
    }
    with Stubber(client) as stub:
        stub.add_response("put_events", {"FailedEntryCount": 0, "Entries": [{"EventId": "aws-1"}]}, expected)
        driver.publish(client, "nimbus", tick)
        stub.assert_no_pending_responses()
    assert ClockTick.model_validate(json.loads(expected["Entries"][0]["Detail"])) == tick


def test_publish_raises_when_eventbridge_rejects_the_entry():
    client = fake_events_client()
    tick = driver.make_tick("replay-michaung", START, 3, NOW)
    rejected = {"FailedEntryCount": 1, "Entries": [{"ErrorCode": "InternalFailure", "ErrorMessage": "try again"}]}
    with Stubber(client) as stub:
        stub.add_response("put_events", rejected)
        with pytest.raises(driver.PublishError, match="tick 3: InternalFailure try again"):
            driver.publish(client, "nimbus", tick)


def test_main_sends_to_the_bus_from_the_environment_and_stops_on_rejection(monkeypatch, capsys):
    client = fake_events_client()
    monkeypatch.setattr(driver, "_aws_client", lambda service: client)
    monkeypatch.setenv(driver.BUS_NAME_ENV, "nimbus-test")
    ok = {"FailedEntryCount": 0, "Entries": [{"EventId": "aws-1"}]}
    rejected = {"FailedEntryCount": 1, "Entries": [{"ErrorCode": "AccessDenied", "ErrorMessage": "no"}]}
    with Stubber(client) as stub:
        stub.add_response("put_events", ok)
        stub.add_response("put_events", rejected)
        assert driver.main(["--ticks", "5", "--speed", "0", "--no-seed"]) == 1
        stub.assert_no_pending_responses()
    err = capsys.readouterr().err
    assert "-> nimbus-test" in err
    assert "AccessDenied" in err
