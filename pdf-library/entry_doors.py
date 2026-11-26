"""Place the catalog entrance symbol on its wall opening."""
import math


# Directed endpoint IDs of source-reviewed entrance edges that the extractor
# omitted, or whose old candidate was on another wall. The source does not
# establish a reliable hinge and swing for every plan.
ENTRANCE_EDGES = {
    'bkh_025': (18, 19), 'bkh_033': (6, 7), 'bkh_034': (6, 7),
    'bkh_044': (2, 3), 'bkh_046': (0, 5), 'bkh_051': (14, 15),
    'bkh_052': (51, 47), 'bkh_053': (22, 5), 'bkh_057': (14, 4),
    'bkh_059': (51, 40), 'bkh_063': (7, 30), 'bkh_068': (22, 31),
    'fotv_003': (7, 0), 'fotv_004': (7, 11), 'fotv_005': (7, 0),
    'fotv_007': (7, 12), 'fotv_010': (21, 18), 'fotv_012': (22, 24),
    'fotv_017': (104, 98), 'qube_003': (92, 89), 'tch_009': (39, 40),
}


def entrance_opening(plan, graph):
    existing = next((o for o in graph['Openings'] if o.get('IsEntry') or
                     o['Kind'] == 'Door' and o.get('Note', '').startswith('входная')), None)
    if existing:
        door = {**existing, 'IsEntry': True}
        if plan['id'] == 'bkh_073':
            door['SwingSide'] = 'Outside'
        return door
    entry_link = next((e for e in plan.get('edges', []) if 'MOP' in e['between']), None)
    if not entry_link:
        return None
    endpoints = ENTRANCE_EDGES.get(plan['id'])
    candidates = []
    room_id = next(r for r in entry_link['between'] if r != 'MOP')
    room_edges = {i for s in graph['Spaces'] if s['RoomId'] == room_id for i, _ in s['OuterLoop']}
    for index, edge in enumerate(graph['Edges']):
        if edge['LocationType'] != 'Perimeter' or edge.get('OutsideSpaceType') == 'Shaft':
            continue
        pair = edge['StartNodeIndex'], edge['EndNodeIndex']
        if (endpoints and pair != endpoints) or (not endpoints and index not in room_edges):
            continue
        a, b = [graph['Nodes'][i] for i in pair]
        length = math.hypot(b['X'] - a['X'], b['Y'] - a['Y'])
        candidates.append((edge.get('OutsideSpaceType') != 'Exterior', length, index))
    if not candidates:
        return None
    _, length, index = max(candidates)
    return {'Kind': 'Door', 'EdgeIndex': index, 't': .40 if plan['id'] == 'qube_003' else .5,
            'WidthMm': round(min(entry_link.get('w') or 1000, length)), 'IsEntry': True}
