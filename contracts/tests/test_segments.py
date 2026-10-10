from nimbus_contracts.segments import OsmWay, split_ways


def ids(pieces):
    return {p.segment_id: p.node_ids for p in pieces}


def test_way_without_intersections_is_one_segment():
    ways = [OsmWay(way_id=10, node_ids=[1, 2, 3])]
    assert ids(split_ways(ways)) == {"10-0": [1, 2, 3]}


def test_way_is_split_at_a_node_shared_with_another_way():
    ways = [OsmWay(way_id=10, node_ids=[1, 2, 3, 4]), OsmWay(way_id=20, node_ids=[9, 3])]
    assert ids(split_ways(ways)) == {
        "10-0": [1, 2, 3],
        "10-1": [3, 4],
        "20-0": [9, 3],
    }


def test_shared_endpoints_do_not_create_empty_segments():
    ways = [OsmWay(way_id=10, node_ids=[1, 2]), OsmWay(way_id=20, node_ids=[2, 3])]
    assert ids(split_ways(ways)) == {"10-0": [1, 2], "20-0": [2, 3]}


def test_numbering_follows_way_order_and_is_deterministic():
    ways = [
        OsmWay(way_id=10, node_ids=[1, 2, 3, 4, 5]),
        OsmWay(way_id=20, node_ids=[2, 7]),
        OsmWay(way_id=30, node_ids=[4, 8]),
    ]
    first = ids(split_ways(ways))
    assert first == ids(split_ways(list(reversed(ways))))
    assert first["10-0"] == [1, 2]
    assert first["10-1"] == [2, 3, 4]
    assert first["10-2"] == [4, 5]


def test_a_way_crossing_itself_splits_at_the_repeated_node():
    ways = [OsmWay(way_id=10, node_ids=[1, 2, 3, 4, 2, 5])]
    assert ids(split_ways(ways)) == {
        "10-0": [1, 2],
        "10-1": [2, 3, 4, 2],
        "10-2": [2, 5],
    }
