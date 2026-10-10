"""The one rule for turning OSM ways into Segments.

F1 and the fixtures both call split_ways, so Segment IDs can't drift between lanes.
A Segment ID is "{osm_way_id}-{n}": the way is split at every interior node that is an
intersection (shared with another way, or visited twice by the same way), and n counts
the pieces from 0 in the way's node order.
"""

from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class OsmWay:
    way_id: int
    node_ids: list[int]


@dataclass(frozen=True)
class SegmentPiece:
    segment_id: str
    osm_way_id: int
    node_ids: list[int]


def split_ways(ways: list[OsmWay]) -> list[SegmentPiece]:
    # A node is an intersection if it appears more than once across all ways' node lists.
    usage = Counter(node for way in ways for node in way.node_ids)

    pieces: list[SegmentPiece] = []
    for way in sorted(ways, key=lambda w: w.way_id):
        runs, current = [], [way.node_ids[0]]
        for node in way.node_ids[1:-1]:
            current.append(node)
            if usage[node] > 1:
                runs.append(current)
                current = [node]
        current.append(way.node_ids[-1])
        runs.append(current)
        pieces += [SegmentPiece(f"{way.way_id}-{n}", way.way_id, nodes) for n, nodes in enumerate(runs)]
    return pieces
