"""Rank plan geometry that merits source-overlay review.

Scores are triage signals, not automatic proof that a wall is wrong.
"""
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from shapely.geometry import LineString

ROOT = Path(__file__).resolve().parents[1]
graphs = json.loads((ROOT / 'catalog/contour_graphs.json').read_text(encoding='utf-8'))
plans = {p['id']: p for p in json.loads((ROOT / 'catalog/library.json').read_text(encoding='utf-8'))}
rows = []

for graph in graphs:
    plan_id = graph['Id']
    plan = plans[plan_id]
    nodes = graph['Nodes']
    incident = defaultdict(list)
    edges = []
    for index, edge in enumerate(graph['Edges']):
        start, end = edge['StartNodeIndex'], edge['EndNodeIndex']
        a, b = nodes[start], nodes[end]
        dx, dy = b['X'] - a['X'], b['Y'] - a['Y']
        length = math.hypot(dx, dy)
        if length < 1:
            continue
        angle = math.degrees(math.atan2(dy, dx)) % 180
        obliquity = min(angle % 90, 90 - angle % 90)
        interior = edge['LocationType'] != 'Perimeter'
        item = dict(index=index, length=length, angle=round(angle, 1),
                    obliquity=obliquity, interior=interior, start=start, end=end,
                    location=edge['LocationType'],
                    line=LineString(((a['X'], a['Y']), (b['X'], b['Y']))))
        edges.append(item)
        incident[start].append(item)
        incident[end].append(item)

    long_axes = [e for e in edges if e['length'] >= 1800]

    def straight_run(edge):
        """Short edges can carry openings along a single long, sloping wall."""
        visited = {edge['index']}
        queue = [edge]
        length = 0
        for segment in queue:
            length += segment['length']
            if length >= 1500:
                return True
            for endpoint in (segment['start'], segment['end']):
                for neighbor in incident[endpoint]:
                    angle = abs(neighbor['angle'] - edge['angle'])
                    if neighbor['index'] not in visited and min(angle, 180 - angle) <= 3:
                        visited.add(neighbor['index'])
                        queue.append(neighbor)
        return False

    def local_deviation(edge):
        if not long_axes:
            return edge['obliquity']
        center = edge['line'].interpolate(.5, normalized=True)
        reference = min(long_axes, key=lambda axis: center.distance(axis['line']))
        difference = abs(edge['angle'] - reference['angle']) % 90
        return min(difference, 90 - difference)

    short_oblique = [e for e in edges if e['interior'] and e['length'] < 800 and local_deviation(e) > 8 and not straight_run(e)]
    mid_oblique = [e for e in edges if e['interior'] and 800 <= e['length'] < 1800 and local_deviation(e) > 8 and not straight_run(e)]
    micro = [e for e in edges if e['interior'] and e['length'] < 250]
    odd_turns = []
    for node, neighbors in incident.items():
        if len(neighbors) != 2 or not all(e['interior'] for e in neighbors):
            continue
        e1, e2 = neighbors
        if min(e1['length'], e2['length']) > 800:
            continue
        def vector(e):
            other = e['end'] if e['start'] == node else e['start']
            return (nodes[other]['X'] - nodes[node]['X'], nodes[other]['Y'] - nodes[node]['Y'])
        v1, v2 = vector(e1), vector(e2)
        theta = math.degrees(math.acos(max(-1, min(1, (v1[0]*v2[0]+v1[1]*v2[1]) /
                                                  (e1['length']*e2['length'])))))
        if min(abs(theta - target) for target in (90, 180)) > 8:
            odd_turns.append(node)

    score = 6*len(short_oblique) + 3*len(mid_oblique) + 2*len(odd_turns) + min(20, len(micro))
    if plan.get('geom') == 'approx':
        score += 10
    source = plan.get('source', {}).get('file', '')
    source_path = Path(source)
    source_available = source_path.is_file() or (ROOT / source).is_file()
    rows.append(dict(id=plan_id, score=score, short_oblique=len(short_oblique),
                     mid_oblique=len(mid_oblique), odd_turns=len(odd_turns),
                     micro_edges=len(micro), edges=len(edges),
                     geometry=plan.get('geom', ''), source_available=source_available,
                     source=source, example_edges=' '.join(str(e['index']) for e in short_oblique[:8])))

rows.sort(key=lambda row: (-row['score'], row['id']))
out = ROOT / 'catalog/geometry_audit.csv'
with out.open('w', newline='', encoding='utf-8-sig') as stream:
    writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
print(f'{len(rows)} plans ranked: {out}')
for row in rows[:20]:
    print(f"{row['id']:12} score={row['score']:3} short={row['short_oblique']:2} "
          f"turns={row['odd_turns']:2} source={row['source_available']}")
