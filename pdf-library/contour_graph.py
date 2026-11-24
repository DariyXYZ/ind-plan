"""Compact room outlines and an indexed segment graph for extracted plans.

This is a geometric subset of PLAN AI ContourGraph.  PDF floor fills do not
provide reliable wall axes, thicknesses, outside context, or opening anchors.
"""
from __future__ import annotations

from shapely.geometry import Polygon, box
from shapely.ops import unary_union


def _pieces(geometry):
    if geometry.geom_type == 'Polygon':
        return [geometry]
    return [part for part in geometry.geoms if part.geom_type == 'Polygon']


def _clean_ring(coords):
    points = [[round(x / 10) * 10, round(y / 10) * 10] for x, y in list(coords)[:-1]]
    points = [p for i, p in enumerate(points) if p != points[i - 1]]
    if len(points) > 2:
        changed = True
        while changed and len(points) > 3:
            changed = False
            for i in range(len(points)):
                a, b, c = points[i - 1], points[i], points[(i + 1) % len(points)]
                if (b[0]-a[0])*(c[1]-b[1]) == (b[1]-a[1])*(c[0]-b[0]):
                    points.pop(i); changed = True; break
    return points


def rings_from_rects(rects, max_error=0.005):
    """Recover compact approximate outlines from legacy rectangle unions.

    A simplified outline must stay within 0.5% of the original union area.
    This does not recreate an oblique wall that was lost during rasterization.
    """
    shapes = [box(*r) for r in rects if r[2] > r[0] and r[3] > r[1]]
    if not shapes:
        return []
    original = unary_union(shapes)
    simplified = original
    for tolerance in (150, 100, 70, 40, 20):
        candidate = original.simplify(tolerance, preserve_topology=True)
        if candidate.is_valid and abs(candidate.area-original.area) <= original.area*max_error:
            simplified = candidate
            break
    rings = []
    for part in sorted(_pieces(simplified), key=lambda g: -g.area):
        outer = _clean_ring(part.exterior.coords)
        if len(outer) < 3:
            continue
        holes = [_clean_ring(h.coords) for h in part.interiors]
        rings.append({'outer': outer, 'holes': [h for h in holes if len(h) >= 3]})
    return rings


def compact_rings(rings):
    """Drop closure duplicates and collinear vertices without changing shape."""
    output = []
    for ring in rings:
        outer = _clean_ring(ring['outer'] + [ring['outer'][0]])
        holes = [_clean_ring(h + [h[0]]) for h in ring.get('holes', [])]
        output.append({'outer': outer, 'holes': holes})
    return output


def segment_graph(rooms):
    """Index repeated coordinates/segments and retain directed room loops.

    Unlike full ContourGraph, the source contours trace floor faces.  Adjacent
    rooms may be separated by wall thickness, so no G1-G9 validity is claimed.
    """
    nodes, edges, node_ids, edge_ids, spaces = [], [], {}, {}, []

    def node(point):
        key = tuple(point)
        if key not in node_ids:
            node_ids[key] = len(nodes)
            nodes.append({'X': key[0], 'Y': key[1]})
        return node_ids[key]

    def loop(points, counterclockwise=True):
        signed = sum(a[0]*b[1]-b[0]*a[1] for a, b in zip(points, points[1:]+points[:1]))
        if (signed > 0) != counterclockwise:
            points = list(reversed(points))
        result = []
        for a, b in zip(points, points[1:] + points[:1]):
            start, end = node(a), node(b)
            if start == end:
                continue
            key = tuple(sorted((start, end)))
            if key not in edge_ids:
                edge_ids[key] = len(edges)
                edges.append({'StartNodeIndex': start, 'EndNodeIndex': end})
            index = edge_ids[key]
            result.append([index, edges[index]['StartNodeIndex'] != start])
        return result

    for room in rooms:
        for ring in room.get('rings', []):
            spaces.append({'RoomId': room['id'], 'OuterLoop': loop(ring['outer']),
                           'InnerLoops': [loop(h, False) for h in ring['holes']]})
    return {'Nodes': nodes, 'Edges': edges, 'Spaces': spaces,
            'Geometry': 'floor_face_boundaries', 'Validation': 'unverified'}
