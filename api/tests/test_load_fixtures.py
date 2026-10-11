"""The fixture loader: validated rows, the right keys, and a guard against loading into `live`."""

from decimal import Decimal

import pytest

from console.store import TABLE_KEYS
from projector.core import KEYS as PROJECTOR_KEYS
from tools import load_fixtures as loader

# Keys for the tables the loader fills (storage.md), from the console and projector key maps.
KEYS = {**{t: k for t, k in TABLE_KEYS.items()}, **PROJECTOR_KEYS, "Segments": ("segment_id", None)}


def test_every_table_gets_rows_with_its_keys():
    rows = loader.rows_for("replay-michaung")
    assert set(rows) == set(loader.SOURCES)
    for table, items in rows.items():
        assert items, table
        pk, sk = KEYS[table]
        for item in items:
            assert item[pk] and (sk is None or item[sk]), (table, item)


def test_scene_matches_the_documented_demo():
    rows = loader.rows_for("replay-michaung")
    assert len(rows["Segments"]) == 21 and len(rows["SegmentRisk"]) == 21
    assert [p["status"] for p in rows["Proposals"]] == ["pending"]
    assert {r["status"] for r in rows["Resources"]} == {"free", "working"}
    assert sum(1 for r in rows["SegmentRisk"] if r["band"] == "flooded") == 1


def test_rows_go_to_the_requested_run_and_segments_stay_static():
    rows = loader.rows_for("replay-trial")
    for table, items in rows.items():
        if table == "Segments":
            assert all("run_id" not in i for i in items)
        else:
            assert {i["run_id"] for i in items} == {"replay-trial"}


def test_floats_are_decimals():
    risk = loader.rows_for("live")["Segments"][0]
    assert isinstance(risk["baseline_threshold_mm"], Decimal)


def test_bad_run_ids_are_rejected():
    with pytest.raises(ValueError):
        loader.rows_for("michaung")


class FakeBatch:
    def __init__(self, sink):
        self.sink = sink

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def put_item(self, Item):  # noqa: N803 (boto3's name)
        self.sink.append(Item)


class FakeResource:
    def __init__(self):
        self.tables = {}

    def Table(self, name):  # noqa: N802
        sink = self.tables.setdefault(name, [])
        return type("T", (), {"batch_writer": lambda self_: FakeBatch(sink)})()


def test_load_writes_every_row_to_the_prefixed_table():
    resource = FakeResource()
    rows = loader.rows_for("replay-michaung")
    written = loader.load(resource, rows, "nimbus-")
    assert written == {t: len(r) for t, r in rows.items()}
    assert len(resource.tables["nimbus-Proposals"]) == 1


def test_dry_run_writes_nothing_and_prints_counts(capsys):
    assert loader.main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "nimbus-Segments: 21 rows (dry run)" in out and "nimbus-Proposals: 1 rows" in out


def test_loading_into_live_needs_an_explicit_flag(capsys):
    with pytest.raises(SystemExit):
        loader.main(["--run-id", "live"])
    assert "refusing" in capsys.readouterr().err
    assert loader.main(["--run-id", "live", "--dry-run"]) == 0  # counting is harmless
