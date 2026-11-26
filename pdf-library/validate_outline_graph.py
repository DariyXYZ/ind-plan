"""Check geometric invariants of the published outline graph."""
import json
from pathlib import Path
from math import dist

from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from entry_doors import entrance_opening
from to_contour_graph import clean_rings

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


def validate_catalog(plans, graphs):
    by_id = {plan['id']: plan for plan in plans}
    assert len(by_id) == len(plans) == len(graphs)
    assert {g['Id'] for g in graphs} == set(by_id)
    spaces = 0
    for graph in graphs:
        plan_id = graph['Id']
        plan = by_id[plan_id]
        nodes = [(n['X'], n['Y']) for n in graph['Nodes']]
        edges = [(e['StartNodeIndex'], e['EndNodeIndex']) for e in graph['Edges']]
        assert all(0 <= a < len(nodes) and 0 <= b < len(nodes) and nodes[a] != nodes[b]
                   for a, b in edges), (plan_id, 'degenerate edge')
        loops = [graph['PerimeterLoop'], *graph['PerimeterHoles']]
        for space in graph['Spaces']:
            loops.extend([space['OuterLoop'], *space['InnerLoops']])
        for loop in loops:
            steps = [edges[i][::-1] if reverse else edges[i] for i, reverse in loop]
            assert len(steps) >= 3 and all(a[1] == b[0] for a, b in zip(steps, steps[1:]+steps[:1])), (plan_id, 'open contour')
        rings = clean_rings(graph)
        rooms = {room['id'] for room in plan['rooms']}
        assert rings.keys() == rooms and len(graph['Spaces']) == len(rooms), (plan_id, 'room coverage')
        shapes = [Polygon(r['outer'], r['holes']) for rs in rings.values() for r in rs]
        assert all(p.is_valid and p.area > 0 for p in shapes), (plan_id, 'invalid room polygon')
        assert sum(p.area for p in shapes)-unary_union(shapes).area < 100, (plan_id, 'room overlap')
        links = {frozenset(e['between']) for e in plan['edges']}
        reachable = {'MOP'}
        for _ in rooms:
            for link in links:
                if link & reachable:
                    reachable.update(link)
        assert reachable == rooms | {'MOP'}, (plan_id, 'invalid room connectivity')
        entry = entrance_opening(plan, graph)
        assert entry and entry['WidthMm'] > 0, (plan_id, 'missing entrance')
        for opening in [*graph['Openings'], entry]:
            i = opening['EdgeIndex']
            assert 0 <= i < len(edges) and 0 <= opening['t'] <= 1 and opening['WidthMm'] > 0, (plan_id, 'invalid opening')
        a, b = edges[entry['EdgeIndex']]
        assert graph['Edges'][entry['EdgeIndex']]['LocationType'] == 'Perimeter' and dist(nodes[a], nodes[b]) >= 650, (plan_id, 'entrance wall too short')
        spaces += len(rooms)
    return spaces


if __name__ == '__main__':
    plans = json.loads((ROOT / 'db' / 'library.json').read_text(encoding='utf-8'))
    print(len(plans), 'plans,', validate(plans), 'valid directed loops')
    catalog = ROOT.parent / 'catalog'
    plans = json.loads((catalog / 'library.json').read_text(encoding='utf-8'))
    graphs = json.loads((catalog / 'contour_graphs.json').read_text(encoding='utf-8'))
    print(len(plans), 'catalog plans,', validate_catalog(plans, graphs), 'valid room polygons')
