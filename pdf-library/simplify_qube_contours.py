"""Remove raster stair steps from the two QUBE plans shown in the catalog review."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parent.parent
TARGETS = {'qube_001': 'qube_a2_1br', 'qube_003': 'qube_a6_3br'}
ORIGINAL_OUTER_COUNTS = {'qube_001': 150, 'qube_003': 227}
SIMPLIFIED_OUTER_COUNTS = {'qube_001': 60, 'qube_003': 117}


def simplify_ring(points: list[list[int]]) -> list[list[int]]:
    original = Polygon(points)
    if not original.is_valid or original.area <= 0:
        return points
    for tolerance in (80, 60, 40, 20):
        result = original.simplify(tolerance, preserve_topology=True)
        if (result.geom_type == 'Polygon' and result.is_valid
                and abs(result.area - original.area) / original.area <= 0.01):
            return [[round(x), round(y)] for x, y in list(result.exterior.coords)[:-1]]
    return points


def update_geometry(plan: dict) -> None:
    plan['plan']['outer'] = simplify_ring(plan['plan']['outer'])
    for room in plan['rooms']:
        for ring in room['rings']:
            ring['outer'] = simplify_ring(ring['outer'])
            ring['holes'] = [simplify_ring(hole) for hole in ring.get('holes', [])]


def write_json(path: Path, data: object, compact: bool = False) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False,
        separators=(',', ':') if compact else None, indent=None if compact else 1), encoding='utf-8')


def main() -> None:
    current = {plan['id']: len(plan['plan']['outer']) for plan in
        json.loads((ROOT / 'catalog' / 'library.json').read_text(encoding='utf-8'))
        if plan['id'] in TARGETS}
    if current == SIMPLIFIED_OUTER_COUNTS:
        return
    if current != ORIGINAL_OUTER_COUNTS:
        raise ValueError(f'Unexpected QUBE contour state: {current}')
    # The raw extract and normalized catalog have different room rings; simplify each.
    for plan_id, sheet in TARGETS.items():
        path = ROOT / 'pdf-library' / 'out_qube_dwg' / f'{sheet}.json'
        raw = json.loads(path.read_text(encoding='utf-8'))
        apartment = raw['apartments'][0]
        apartment['contour']['outer'] = simplify_ring(apartment['contour']['outer'])
        for room in apartment['rooms']:
            for ring in room['rings']:
                ring['outer'] = simplify_ring(ring['outer'])
        write_json(path, raw, compact=True)

    for directory in (ROOT / 'pdf-library' / 'db', ROOT / 'catalog'):
        path = directory / 'library.json'
        plans = json.loads(path.read_text(encoding='utf-8'))
        for plan in plans:
            if plan['id'] in TARGETS:
                update_geometry(plan)
        write_json(path, plans)

    # Derived wall graphs and download payloads use the same two edited plans.
    sys.path.insert(0, str(ROOT / 'pdf-library'))
    from to_contour_graph import convert

    catalog = ROOT / 'catalog'
    plans = json.loads((catalog / 'library.json').read_text(encoding='utf-8'))
    graphs = json.loads((catalog / 'contour_graphs.json').read_text(encoding='utf-8'))
    by_id = {plan['id']: plan for plan in plans}
    for index, graph in enumerate(graphs):
        if graph['Id'] not in TARGETS:
            continue
        plan = by_id[graph['Id']]
        replacement = convert(plan)
        for snap, angle in ((40, 10), (0, 5), (0, 2), (0, 0)):
            if replacement and not replacement['Issues']:
                break
            replacement = convert(plan, snap, angle)
        if not replacement or replacement['Issues']:
            raise ValueError(f"Cannot rebuild {graph['Id']}: {replacement and replacement['Issues']}")
        graphs[index] = replacement
    for directory in (ROOT / 'pdf-library' / 'db', catalog):
        write_json(directory / 'contour_graphs.json', graphs, compact=True)

    def axis_rings(graph: dict) -> dict:
        nodes, edges = graph['Nodes'], graph['Edges']
        def points(loop: list) -> list[list[int]]:
            return [[nodes[edges[edge]['EndNodeIndex' if reverse else 'StartNodeIndex']]['X'],
                     nodes[edges[edge]['EndNodeIndex' if reverse else 'StartNodeIndex']]['Y']]
                    for edge, reverse in loop]
        return {space['RoomId']: [{'outer': points(space['OuterLoop']),
                'holes': [points(hole) for hole in space['InnerLoops']]}]
                for space in graph['Spaces']}

    graph_by_id = {graph['Id']: graph for graph in graphs if graph['Id'] in TARGETS}
    axis_by_id = {plan_id: axis_rings(graph) for plan_id, graph in graph_by_id.items()}
    for directory in (ROOT / 'pdf-library' / 'db', catalog):
        path = directory / 'library.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        for plan in data:
            if plan['id'] in TARGETS:
                for room in plan['rooms']:
                    if room['id'] in axis_by_id[plan['id']]:
                        room['axis_rings'] = axis_by_id[plan['id']][room['id']]
        write_json(path, data)
        llm_path = directory / 'library_llm.json'
        llm = json.loads(llm_path.read_text(encoding='utf-8'))
        for item in llm:
            if item['id'] in TARGETS:
                item['plan']['outer'] = by_id[item['id']]['plan']['outer']
                for room in item['plan']['rooms']:
                    if room['id'] in axis_by_id[item['id']]:
                        room['rings'] = axis_by_id[item['id']][room['id']]
        write_json(llm_path, llm, compact=True)

    engine_path = ROOT / 'pdf-library' / 'db' / 'library_engine.json'
    engine = json.loads(engine_path.read_text(encoding='utf-8'))
    for plan in engine:
        if plan['id'] in TARGETS:
            plan['plan']['outer'] = by_id[plan['id']]['plan']['outer']
    write_json(engine_path, engine)


if __name__ == '__main__':
    main()
