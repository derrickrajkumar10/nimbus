"""PlaceIndex seeding, against botocore's Stubber with fake keys, so nothing reaches AWS."""

import boto3
import pytest
from botocore.stub import Stubber

import driver
import place_index
from place_index import CROWD_SEGMENT, DEMO_SEGMENTS, PK, SK

RUN = "replay-michaung"
PHONE = ("f3a1c9e2-demo", "place-home")


def fake_client(service: str):
    return boto3.client(service, region_name="us-east-1", aws_access_key_id="fake", aws_secret_access_key="fake")


def keys(rows) -> list[tuple[str, str]]:
    return [(row.item()[PK]["S"], row.item()[SK]["S"]) for row in rows]


def table_param(name: str) -> dict:
    return {"Parameter": {"Name": place_index.TABLE_PARAM, "Type": "String", "Value": name}}


def test_demo_phones_are_indexed_on_both_velachery_main_road_segments():
    rows = place_index.demo_rows(RUN, [PHONE, ("b7d0-demo", "place-office")])

    assert keys(rows) == [
        ("replay-michaung#27480309-1", "f3a1c9e2-demo#place-home"),
        ("replay-michaung#27480309-4", "f3a1c9e2-demo#place-home"),
        ("replay-michaung#27480309-1", "b7d0-demo#place-office"),
        ("replay-michaung#27480309-4", "b7d0-demo#place-office"),
    ]
    assert not any(row.simulated for row in rows)


def test_150_simulated_subscribers_share_one_segment_and_are_marked():
    rows = place_index.crowd_rows(RUN)

    assert len(rows) == 150 > 100  # over Cedar's Ward Alert recipient limit
    assert {pk for pk, _ in keys(rows)} == {f"{RUN}#{CROWD_SEGMENT}"}
    assert keys(rows)[0][1] == "sim-001#sim-place"
    assert keys(rows)[-1][1] == "sim-150#sim-place"
    assert len(set(keys(rows))) == 150
    assert all(row.item()["simulated"] == {"BOOL": True} for row in rows)


def test_crowd_segment_is_not_a_demo_segment():
    assert CROWD_SEGMENT not in DEMO_SEGMENTS


@pytest.mark.parametrize(
    ("value", "expected"),
    [("f3a1c9e2#place-home", ("f3a1c9e2", "place-home")), ("dev-1#place#with#hashes", ("dev-1", "place#with#hashes"))],
)
def test_parse_phone_splits_at_the_first_hash_like_the_herald(value, expected):
    assert place_index.parse_phone(value) == expected


@pytest.mark.parametrize("value", ["dev-1", "#place-home", "dev-1#", "sim-001#place-home"])
def test_parse_phone_rejects_bad_values(value):
    with pytest.raises(ValueError):
        place_index.parse_phone(value)


def test_table_name_comes_from_ssm(monkeypatch):
    monkeypatch.delenv(place_index.TABLE_ENV, raising=False)
    ssm = fake_client("ssm")
    with Stubber(ssm) as stub:
        stub.add_response("get_parameter", table_param("NimbusShared-PlaceIndex"), {"Name": "/nimbus/tables/PlaceIndex"})
        assert place_index.table_name(lambda: ssm) == "NimbusShared-PlaceIndex"


def test_table_name_env_override_skips_ssm(monkeypatch):
    monkeypatch.setenv(place_index.TABLE_ENV, "nimbus-PlaceIndex")
    assert place_index.table_name(lambda: pytest.fail("SSM was asked")) == "nimbus-PlaceIndex"


def test_write_batches_25_at_a_time():
    rows = place_index.demo_rows(RUN, [PHONE]) + place_index.crowd_rows(RUN)  # 152 rows
    client = fake_client("dynamodb")
    with Stubber(client) as stub:
        for start in range(0, 152, 25):
            chunk = rows[start : start + 25]
            expected = {"RequestItems": {"pi": [{"PutRequest": {"Item": row.item()}} for row in chunk]}}
            stub.add_response("batch_write_item", {"UnprocessedItems": {}}, expected)
        place_index.write(client, "pi", rows)
        stub.assert_no_pending_responses()


def test_write_retries_unprocessed_rows_then_gives_up():
    rows = place_index.crowd_rows(RUN, size=2)
    left = {"pi": [{"PutRequest": {"Item": rows[1].item()}}]}
    client = fake_client("dynamodb")
    waits = []
    with Stubber(client) as stub:
        stub.add_response("batch_write_item", {"UnprocessedItems": left})
        stub.add_response("batch_write_item", {"UnprocessedItems": {}}, {"RequestItems": left})
        place_index.write(client, "pi", rows, sleep=waits.append)
        stub.assert_no_pending_responses()
    assert len(waits) == 1

    with Stubber(client) as stub:
        for _ in range(3):
            stub.add_response("batch_write_item", {"UnprocessedItems": left})
        with pytest.raises(place_index.SeedError, match="1 PlaceIndex rows unwritten"):
            place_index.write(client, "pi", rows, max_retries=2, sleep=waits.append)


def test_driver_seeds_place_index_before_the_first_tick(monkeypatch, capsys):
    monkeypatch.delenv(place_index.TABLE_ENV, raising=False)
    monkeypatch.delenv("NIMBUS_TABLE_RESOURCES", raising=False)
    clients = {service: fake_client(service) for service in ("ssm", "dynamodb", "events")}
    calls = []
    monkeypatch.setattr(driver, "_aws_client", lambda service: clients[service])
    for service, client in clients.items():
        client.meta.events.register("before-parameter-build", lambda model, **_: calls.append(model.name))
    stubs = {service: Stubber(client) for service, client in clients.items()}
    stubs["ssm"].add_response("get_parameter", table_param("pi"))
    for _ in range(7):  # 2 demo rows + 150 simulated, 25 per batch
        stubs["dynamodb"].add_response("batch_write_item", {"UnprocessedItems": {}})
    stubs["ssm"].add_response("get_parameter", table_param("res"), {"Name": "/nimbus/tables/Resources"})
    stubs["dynamodb"].add_response("batch_write_item", {"UnprocessedItems": {}})  # 3 Resources
    stubs["events"].add_response("put_events", {"FailedEntryCount": 0, "Entries": [{"EventId": "aws-1"}]})
    for stub in stubs.values():
        stub.activate()

    assert driver.main(["--ticks", "1", "--demo-phone", "f3a1c9e2-demo#place-home"]) == 0

    for stub in stubs.values():
        stub.assert_no_pending_responses()
    assert calls == ["GetParameter"] + ["BatchWriteItem"] * 7 + ["GetParameter", "BatchWriteItem", "PutEvents"]
    err = capsys.readouterr().err
    assert "PlaceIndex pi: 1 demo phone(s)" in err
    assert "Resources res: 3 for Run replay-michaung" in err


def test_driver_sends_no_ticks_when_seeding_fails(monkeypatch, capsys):
    monkeypatch.setenv(place_index.TABLE_ENV, "pi")
    dynamodb = fake_client("dynamodb")

    def clients(service):
        assert service == "dynamodb", f"no {service} client should be needed"
        return dynamodb

    monkeypatch.setattr(driver, "_aws_client", clients)
    with Stubber(dynamodb) as stub:
        stub.add_client_error("batch_write_item", "ResourceNotFoundException", "no such table")
        assert driver.main(["--ticks", "3", "--speed", "0"]) == 1
    assert "seeding failed, no ticks sent" in capsys.readouterr().err


def test_dry_run_reports_the_seed_without_aws(monkeypatch, capsys):
    monkeypatch.setattr(driver, "_aws_client", lambda service: pytest.fail(f"dry run created a {service} client"))

    assert driver.main(["--dry-run", "--ticks", "1", "--speed", "0", "--demo-phone", "f3a1c9e2-demo#place-home"]) == 0

    err = capsys.readouterr().err
    assert "would index 1 demo phone(s) on 27480309-1, 27480309-4 and 150 simulated Subscribers on 27320162-0" in err
