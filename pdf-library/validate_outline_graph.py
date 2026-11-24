"""Check geometric invariants of the published outline graph."""
import json
from pathlib import Path

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent


def area2(points):
    return sum(a[0]*b[1]-b[0]*a[1] for a, b in zip(points, points[1:]+points[:1]))


def validate(plans):
    rings_count = 0
    for plan in plans:
        graph = plan['outline_graph']
        nodes, edges = graph['Nodes'], graph['Edges']
        assert graph['Validation'] == 'unverified'
        assert len({(n['X'], n['Y']) for n in nodes}) == len(nodes)
        for space in graph['Spaces']:
            assert any(r['id'] == space['RoomId'] for r in plan['rooms'])
            for index, loop in enumerate([space['OuterLoop'], *space['InnerLoops']]):
                assert len(loop) >= 3, (plan['id'], space['RoomId'])
                steps = []
                for edge_index, reversed_ in loop:
                    edge = edges[edge_index]
                    a, b = edge['StartNodeIndex'], edge['EndNodeIndex']
                    steps.append((b, a) if reversed_ else (a, b))
                assert all(a[1] == b[0] for a, b in zip(steps, steps[1:]+steps[:1]))
                points = [[nodes[a]['X'], nodes[a]['Y']] for a, _ in steps]
                assert (area2(points) > 0) == (index == 0)
                rings_count += 1
        for room in plan['rooms']:
            shapes = [Polygon(r['outer'], r['holes']) for r in room['rings']]
            assert shapes and all(s.is_valid and s.area > 0 for s in shapes), (plan['id'], room['id'])
            if room['geometry_source'] == 'rect_union_simplified':
                old = unary_union([box(*r) for r in room['rects']])
                new = unary_union(shapes)
                assert abs(new.area-old.area) <= old.area*0.006, (plan['id'], room['id'])
    return rings_count


if __name__ == '__main__':
    plans = json.loads((ROOT / 'db' / 'library.json').read_text(encoding='utf-8'))
    print(len(plans), 'plans,', validate(plans), 'valid directed loops')
