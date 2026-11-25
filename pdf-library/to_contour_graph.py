"""Квартира из базы → ContourGraph (PLAN AI, Модель 2.0, драфт от 23.11.2026).

Комнаты в базе — контуры пола; между ними зазор = стена. Здесь:
1) растр 20 мм, пустоту внутри квартиры (стены) делим между ближайшими комнатами —
   граница проходит по оси стены, у соседних комнат она общая;
2) общие границы режем на цепочки между узлами и спрямляем (наклоны сохраняются);
3) толщина стены = расстояние от оси до пола комнаты с каждой стороны;
4) окна и двери ставим на рёбра.
Чего нет в PDF — помечаем в Assumptions (толщина наружных стен, тип снаружи, высоты проёмов).
Запуск: python -X utf8 to_contour_graph.py [db/library.json] → db/contour_graphs.json
"""
from __future__ import annotations

import json
import math
import sys
import uuid
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

RES = 20            # мм на ячейку
CLOSE_MM = 260      # закрываем зазоры до ~2*260 мм (стены внутри квартиры)
SIMPL_MM = 35
SMOOTH_MM = 150    # полуразмер квадрата спрямления контура       # спрямление цепочек
EXT_WALL = 300      # наружная стена по умолчанию (нет в PDF)
MOP_WALL = 250
NS = uuid.UUID('6f1d2a40-1c3b-4e7a-9b1e-1a2b3c4d5e6f')

FUNC = {'kg': 'KitchenLiving', 'kitchen': 'Kitchen', 'living': 'Living', 'bedroom': 'Bedroom', 'master': 'Bedroom',
        'kids': 'Bedroom', 'hall': 'Hall', 'corridor': 'Corridor', 'wardrobe': 'Wardrobe', 'bath': 'Bathroom',
        'wc': 'Toilet', 'laundry': 'Laundry', 'storage': 'Storage', 'loggia': 'Balcony', 'study': 'Study'}


def room_geom(room):
    ps = [Polygon(q['outer'], q.get('holes', [])).buffer(0) for q in room.get('rings', []) if len(q['outer']) >= 3]
    return unary_union(ps) if ps else Polygon()


def rasterize(rooms):
    geoms = [room_geom(r) for r in rooms]
    xs = [c for g in geoms if not g.is_empty for c in (g.bounds[0], g.bounds[2])]
    ys = [c for g in geoms if not g.is_empty for c in (g.bounds[1], g.bounds[3])]
    pad = CLOSE_MM * 2
    x0, y0 = min(xs) - pad, min(ys) - pad
    W, H = int((max(xs) - x0 + pad) / RES) + 1, int((max(ys) - y0 + pad) / RES) + 1
    img = Image.new('I', (W, H), 0)
    d = ImageDraw.Draw(img)
    # большие сначала, мелкие поверх (как при чистке контуров)
    for k in sorted(range(len(rooms)), key=lambda i: -geoms[i].area):
        g = geoms[k]
        for part in getattr(g, 'geoms', [g]):
            if part.is_empty:
                continue
            d.polygon([((x - x0) / RES, (y - y0) / RES) for x, y in part.exterior.coords], fill=k + 1)
            for h in part.interiors:
                d.polygon([((x - x0) / RES, (y - y0) / RES) for x, y in h.coords], fill=0)
    return np.array(img, dtype=np.int32), x0, y0, geoms


def partition(L, smooth=True):
    occ = L > 0
    r = int(CLOSE_MM / RES)
    yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
    disk = xx * xx + yy * yy <= r * r
    F = ndimage.binary_closing(np.pad(occ, r + 2), structure=disk)[r + 2:-r - 2, r + 2:-r - 2] | occ
    # одна квартира = одна связная область (балкон за стеной цепляется закрытием)
    lab, n = ndimage.label(F)
    if n > 1:
        sizes = ndimage.sum(F, lab, range(1, n + 1))
        keep = [i + 1 for i, s in enumerate(sizes) if s >= 0.02 * sizes.max()]
        F = np.isin(lab, keep)
    # дыры внутри квартиры: шахта отделена от полов стеной; дыра, вплотную касающаяся пола, — мебель/короб поверх заливки
    # узкая (≤760 мм — глубина гарнитура/короба) дыра — мебель поверх заливки, отдаём комнате; шахты и колонны шире — остаются дырами
    holes, nh = ndimage.label(ndimage.binary_fill_holes(F) & ~F)
    for h, sl in enumerate(ndimage.find_objects(holes), 1):
        if min(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) * RES <= 760:
            F |= holes == h
        else:  # стояк/шахта: простая форма — прямоугольник по габариту
            F |= holes == h
            F[sl] = False
    # спрямить контур квартиры: выступы/впадины мельче 30 см (заливка в оконных и дверных проёмах) — прочь, прямые углы целы
    if smooth:
        k = int(SMOOTH_MM / RES) * 2 + 1
        sq = np.ones((k, k), bool)
        F = ndimage.binary_closing(np.pad(F, k), structure=sq)[k:-k, k:-k]
        F = ndimage.binary_opening(F, structure=sq)
    _, (iy, ix) = ndimage.distance_transform_edt(~occ, return_indices=True)
    P = np.where(F, L[iy, ix], 0)
    return P, int(n)


def chains(P):
    """Единичные отрезки границ между ячейками → цепочки между узлами.
    Вершина сетки (i,j) = угол ячеек; ячейка (r,c) занимает [c,c+1]x[r,r+1]."""
    H, W = P.shape
    Q = np.pad(P, 1)  # 0 снаружи
    seg = {}  # (v1,v2) -> (left,right) в системе x=j,y=i (y вниз, но знак согласуем позже)
    adj = defaultdict(list)
    # вертикальные границы: между Q[r,c-1] и Q[r,c] → отрезок (c, r)-(c, r+1)
    dv = Q[:, 1:] != Q[:, :-1]
    for r, c in zip(*np.nonzero(dv)):
        x = c + 1  # граница между колонками c и c+1 в Q
        a, b = (x, r), (x, r + 1)
        seg[(a, b)] = (int(Q[r, c]), int(Q[r, c + 1]))
    dh = Q[1:, :] != Q[:-1, :]
    for r, c in zip(*np.nonzero(dh)):
        y = r + 1
        a, b = (c, y), (c + 1, y)
        seg[(a, b)] = (int(Q[r, c]), int(Q[r + 1, c]))
    for (a, b), lr in seg.items():
        adj[a].append((b, lr, (a, b)))
        adj[b].append((a, lr, (a, b)))

    def labels_at(v):
        x, y = v
        return {int(Q[yy, xx]) for yy in (y - 1, y) for xx in (x - 1, x) if 0 <= yy < Q.shape[0] and 0 <= xx < Q.shape[1]}

    junction = {v for v in adj if len(adj[v]) != 2 or len(labels_at(v)) > 2}
    used = set()
    out = []
    for start in list(adj):
        for nb, lr, key in adj[start]:
            if key in used or start not in junction:
                continue
            path = [start, nb]
            used.add(key)
            cur = nb
            while cur not in junction:
                nxt = [(n2, k2) for n2, l2, k2 in adj[cur] if k2 not in used]
                if not nxt:
                    break
                n2, k2 = nxt[0]
                used.add(k2)
                path.append(n2)
                cur = n2
            out.append(path)
    # замкнутые петли без узлов (остров внутри одной комнаты)
    for key in list(seg):
        if key in used:
            continue
        a, b = key
        path = [a, b]
        used.add(key)
        cur = b
        while cur != a:
            nxt = [(n2, k2) for n2, l2, k2 in adj[cur] if k2 not in used]
            if not nxt:
                break
            n2, k2 = nxt[0]
            used.add(k2)
            path.append(n2)
            cur = n2
        out.append(path)
    return out, Q


def dp(points, tol):
    """Douglas–Peucker с сохранением концов."""
    if len(points) < 3:
        return points
    if points[0] == points[-1]:
        mid = len(points) // 2
        return dp(points[:mid + 1], tol)[:-1] + dp(points[mid:], tol)
    a, b = np.array(points[0], float), np.array(points[-1], float)
    pts = np.array(points, float)
    ab = b - a
    n = np.hypot(*ab) or 1
    d = np.abs(ab[0] * (pts[:, 1] - a[1]) - ab[1] * (pts[:, 0] - a[0])) / n
    i = int(np.argmax(d))
    if d[i] <= tol:
        return [points[0], points[-1]]
    return dp(points[:i + 1], tol)[:-1] + dp(points[i:], tol)


def signed_area(pts):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1])) / 2


def convert(plan, snap=40, ang=15):
    rooms = [r for r in plan.get('rooms', []) if r.get('rings')]
    if not rooms:
        return None
    L, x0, y0, geoms = rasterize(rooms)
    cad = str((plan.get('source') or {}).get('file') or '').lower().endswith('.dwg')  # CAD уже точный: без выправки и спрямления
    if cad:
        ang = 0
    P, comps = partition(L, smooth=not cad)
    paths, Q = chains(P)
    tol = SIMPL_MM / RES
    to_mm = lambda v: [int(round((x0 + (v[0] - 1) * RES) / 10) * 10), int(round((y0 + (v[1] - 1) * RES) / 10) * 10)]

    nodes, node_id = [], {}

    def node(pt):
        k = tuple(pt)
        if k not in node_id:
            node_id[k] = len(nodes)
            nodes.append({'X': k[0], 'Y': k[1]})
        return node_id[k]

    def side(path):
        """метки слева/справа от первого шага цепочки (сетка Q, ось y = номер строки)"""
        (vx, vy), (wx, wy) = path[0], path[1]
        dx, dy = wx - vx, wy - vy
        mx, my = vx + dx / 2, vy + dy / 2
        lx, ly = mx - dy * 0.5, my + dx * 0.5
        rx, ry = mx + dy * 0.5, my - dx * 0.5
        g = lambda x, y: int(Q[int(math.floor(y)), int(math.floor(x))]) if 0 <= y < Q.shape[0] and 0 <= x < Q.shape[1] else 0
        return g(lx, ly), g(rx, ry)

    edges, seen = [], set()
    for path in paths:
        if len(path) < 2:
            continue
        left, right = side(path)
        if left == right:
            continue
        if left == 0:  # периметр: квартира слева
            path = path[::-1]
            left, right = right, left
        for t in ((tol * 4, tol * 2.5, tol, tol / 3, 0) if right == 0 else (tol, tol / 3, 0)):
            simp = dp(path, t) if t else path
            ids = []
            for v in simp:
                k = node(to_mm(v))
                if not ids or ids[-1] != k:
                    ids.append(k)
            keys = [(min(a, b), max(a, b)) for a, b in zip(ids, ids[1:]) if a != b]
            if len(ids) >= 2 and len(set(keys)) == len(keys) and not (set(keys) & seen) and not (ids[0] == ids[-1] and len(ids) < 4):
                break
        for a, b in zip(ids, ids[1:]):
            if a == b or (min(a, b), max(a, b)) in seen:
                continue
            seen.add((min(a, b), max(a, b)))
            edges.append({'i': a, 'j': b, 'L': left, 'R': right})

    # выправка: почти вертикальные/горизонтальные (до 5°) — строго по осям, стены на одной линии — в одну
    def orthogonalize(nodes, edges, ang=math.radians(5), snap=40):
        par = list(range(len(nodes)))
        def f(a):
            while par[a] != a:
                par[a] = par[par[a]]; a = par[a]
            return a
        for axis in ('X', 'Y'):
            par[:] = range(len(nodes))
            for e in edges:
                A, B = nodes[e['i']], nodes[e['j']]
                dx, dy = abs(B['X'] - A['X']), abs(B['Y'] - A['Y'])
                t = 1.0 if math.hypot(dx, dy) < 600 else math.tan(ang)  # короткие (< 0.6 м) — до 45°
                if (axis == 'X' and dx <= t * dy) or (axis == 'Y' and dy <= t * dx):
                    par[f(e['i'])] = f(e['j'])
            groups = defaultdict(list)
            for k in range(len(nodes)):
                groups[f(k)].append(k)
            vals = sorted((sum(nodes[k][axis] for k in g) / len(g), g) for g in groups.values())
            cl, cur = [], []
            for v, g in vals:  # соседние линии ближе snap мм — одна линия
                if cur and v - cur[-1][0] > snap:
                    cl.append(cur); cur = []
                cur.append((v, g))
            if cur:
                cl.append(cur)
            for c in cl:
                w = sum(len(g) for v, g in c)
                m = int(round(sum(v * len(g) for v, g in c) / w / 10) * 10)
                for v, g in c:
                    for k in g:
                        nodes[k][axis] = m
        # фаски-артефакты растра: короткое косое ребро между вертикалью и горизонталью → прямой угол (шахты, углы комнат)
        adj = defaultdict(list)
        for e in edges:
            adj[e['i']].append(e['j']); adj[e['j']].append(e['i'])
        for e in edges:
            i, j = e['i'], e['j']
            A, B = nodes[i], nodes[j]
            dx, dy = B['X'] - A['X'], B['Y'] - A['Y']
            if not dx or not dy or math.hypot(dx, dy) > 800:
                continue
            ax = lambda n, o: ('v' if nodes[o]['X'] == nodes[n]['X'] else 'h' if nodes[o]['Y'] == nodes[n]['Y'] else None)
            si = {ax(i, k) for k in adj[i] if k != j} - {None}
            sj = {ax(j, k) for k in adj[j] if k != i} - {None}
            if 'v' in si and 'h' in sj:
                c = (A['X'], B['Y'])
            elif 'h' in si and 'v' in sj:
                c = (B['X'], A['Y'])
            else:
                continue
            for k in (i, j):
                nodes[k]['X'], nodes[k]['Y'] = c
        # склеить совпавшие узлы, выкинуть нулевые и повторные рёбра
        canon, remap = {}, {}
        for k, n in enumerate(nodes):
            remap[k] = canon.setdefault((n['X'], n['Y']), k)
        out, seen2 = [], set()
        for e in edges:
            i, j = remap[e['i']], remap[e['j']]
            key = (min(i, j), max(i, j))
            if i == j or key in seen2:
                continue
            seen2.add(key)
            out.append({**e, 'i': i, 'j': j})
        used = sorted({k for e in out for k in (e['i'], e['j'])})
        idx = {k: n for n, k in enumerate(used)}
        new_nodes = [nodes[k] for k in used]
        for e in out:
            e['i'], e['j'] = idx[e['i']], idx[e['j']]
        return new_nodes, out

    if ang:
        nodes, edges = orthogonalize(nodes, edges, math.radians(ang), snap)

    # толщины: от оси до пола комнаты
    def off(e, lab):
        if lab == 0:
            return None
        A, B = nodes[e['i']], nodes[e['j']]
        line = LineString([(A['X'], A['Y']), (B['X'], B['Y'])])
        g = geoms[lab - 1]
        pts = [line.interpolate(t, normalized=True) for t in (0.25, 0.5, 0.75)]
        ds = sorted(0 if g.contains(p) else g.distance(p) for p in pts)
        return int(round(ds[1] / 10) * 10)

    # периметр: цепочка против часовой (квартира слева)
    per = [k for k, e in enumerate(edges) if e['R'] == 0]
    nxt = defaultdict(list)
    for k in per:
        nxt[edges[k]['i']].append(k)
    loops, left = [], set(per)
    while left:
        k = min(left)
        loop = []
        while k in left:
            left.discard(k)
            loop.append(k)
            cands = [c for c in nxt[edges[k]['j']] if c in left]
            if not cands:
                break
            k = cands[0]
        loops.append(loop)
    loops.sort(key=lambda lp: -abs(signed_area([[nodes[edges[k]['i']]['X'], nodes[edges[k]['i']]['Y']] for k in lp])))
    area_of = lambda lp: signed_area([[nodes[edges[k]['i']]['X'], nodes[edges[k]['i']]['Y']] for k in lp])
    perimeter = loops[0] if loops else []
    holes = [lp for lp in loops[1:] if area_of(lp) < 0]      # шахты, колонны внутри квартиры
    extra = [lp for lp in loops[1:] if area_of(lp) >= 0]     # отдельные куски — ошибка
    hole_edges = [k for lp in holes for k in lp]
    # окна → ближайшее периметровое ребро своей комнаты
    rid = {i + 1: r['id'] for i, r in enumerate(rooms)}
    lab_of = {r['id']: i + 1 for i, r in enumerate(rooms)}
    win_edges = defaultdict(list)
    openings = []
    seg = lambda e: LineString([(nodes[e['i']]['X'], nodes[e['i']]['Y']), (nodes[e['j']]['X'], nodes[e['j']]['Y'])])
    for w in plan.get('plan', {}).get('windows') or []:
        if not w.get('at'):
            continue
        lab = lab_of.get(w.get('room'))
        outdoor = {i + 1 for i, r in enumerate(rooms) if r.get('role') == 'loggia'}
        hole_e = set(hole_edges)
        cands = [(k, e) for k, e in enumerate(edges) if k not in hole_e and lab is not None and lab in (e['L'], e['R'])
                 and ({e['L'], e['R']} - {lab}) <= ({0} | outdoor)] or \
                [(k, e) for k, e in enumerate(edges) if e['R'] == 0 and k not in hole_e]
        if not cands:
            continue
        p = Point(*w['at'])
        width = int(w.get('w') or 1200)
        # ближайшее ребро, на которое окно помещается хотя бы наполовину
        k, e = min(cands, key=lambda ke: seg(ke[1]).distance(p) + (2000 if seg(ke[1]).length < width * 0.5 else 0))
        s = seg(e)
        width = min(width, int(s.length) - 100) if s.length > 300 else width
        h = width / 2 / s.length
        t = min(max(s.project(p, normalized=True), h), 1 - h) if h < 0.5 else 0.5
        win_edges[k].append(w)
        openings.append({'Kind': 'Window', 'EdgeIndex': k, 't': round(t, 3),
                         'WidthMm': width, 'BottomMm': 900, 'HeightMm': 1500})

    # тип снаружи: окно → улица; у прихожей самое длинное глухое ребро → МОП; остальное — не известно
    entry_room = next((r for r in rooms if r.get('role') in ('hall', 'corridor')), None)
    for k, e in enumerate(edges):
        e['out'] = None
        if e['R'] == 0:
            e['out'] = 'Exterior' if k in win_edges else None
    if entry_room:
        cand = [(seg(e).length, k) for k, e in enumerate(edges) if e['R'] == 0 and e['L'] == lab_of[entry_room['id']] and e['out'] is None]
        if cand:
            k = max(cand)[1]
            edges[k]['out'] = 'CommonArea'
            s = seg(edges[k])
            openings.append({'Kind': 'Door', 'EdgeIndex': k, 't': 0.5, 'WidthMm': min(1000, int(s.length) - 100),
                             'BottomMm': 0, 'HeightMm': 2100, 'Note': 'входная, место на ребре условно'})

    # двери между комнатами → самое длинное общее ребро
    for d in plan.get('edges') or []:
        a, b = d['between']
        la, lb = lab_of.get(a), lab_of.get(b)
        if not la or not lb:
            continue
        shared = [(seg(e).length, k) for k, e in enumerate(edges) if {e['L'], e['R']} == {la, lb}]
        if not shared:
            continue
        ln, k = max(shared)
        e = edges[k]
        e['open'] = d.get('type') == 'open'
        if d.get('type') == 'open':
            continue
        w = int(d.get('w') or 800)
        openings.append({'Kind': 'Door', 'EdgeIndex': k, 't': 0.5, 'WidthMm': min(w, int(ln)),
                         'BottomMm': 0, 'HeightMm': 2100})

    # порядок рёбер: периметр первым по ходу обхода, потом остальные
    order = perimeter + hole_edges + [k for k in range(len(edges)) if k not in set(perimeter) | set(hole_edges)]
    remap = {old: new for new, old in enumerate(order)}
    E = []
    for old in order:
        e = edges[old]
        lo, ro = off(e, e['L']), off(e, e['R'])
        if e['R'] == 0:
            out = 'Shaft' if old in hole_edges else e['out']
            thick = EXT_WALL if out == 'Exterior' else MOP_WALL
            item = {'StartNodeIndex': e['i'], 'EndNodeIndex': e['j'], 'LocationType': 'Perimeter', 'FillType': 'Wall',
                    'OutsideSpaceType': out, 'LeftOffset': 0, 'RightOffset': thick}
        else:
            wall = (lo or 0) + (ro or 0) >= 40 and not e.get('open')
            if wall:  # толщина к ближайшему стандарту, ось посередине
                t = min((80, 100, 120, 150, 200, 250, 300), key=lambda v: abs(v - (lo or 0) - (ro or 0)))
                lo = ro = t // 2
            item = {'StartNodeIndex': e['i'], 'EndNodeIndex': e['j'], 'LocationType': 'Interior',
                    'FillType': 'Wall' if wall else 'Empty',
                    'LeftOffset': (lo or 0) if wall else 0, 'RightOffset': (ro or 0) if wall else 0}
        E.append(item)
    for o in openings:
        o['EdgeIndex'] = remap[o['EdgeIndex']]

    # пространства: обходы, комната слева
    def loops_of(lab):
        use = []
        for k, e in enumerate(E):
            old = order[k]
            if edges[old]['L'] == lab:
                use.append((k, False, E[k]['StartNodeIndex'], E[k]['EndNodeIndex']))
            elif edges[old]['R'] == lab:
                use.append((k, True, E[k]['EndNodeIndex'], E[k]['StartNodeIndex']))
        by_start = defaultdict(list)
        for u in use:
            by_start[u[2]].append(u)
        rest, res = set(use), []
        while rest:
            u = min(rest)
            lp = []
            while u in rest:
                rest.discard(u)
                lp.append(u)
                c = [v for v in by_start[u[3]] if v in rest]
                if not c:
                    break
                u = c[0]
            pts = [[nodes[v[2]]['X'], nodes[v[2]]['Y']] for v in lp]
            res.append((signed_area(pts), [[v[0], v[1]] for v in lp]))
        res.sort(key=lambda t: -t[0])
        return res

    spaces = []
    for lab, r in rid.items():
        ls = loops_of(lab)
        if not ls:
            continue
        room = rooms[lab - 1]
        spaces.append({'Name': f"{room['name_src']} {room.get('area') or ''}".strip(), 'Function': FUNC.get(room.get('role')),
                       'RoomId': room['id'], 'OuterLoop': ls[0][1], 'InnerLoops': [l for a, l in ls[1:] if a < 0]})
    for k, o in enumerate(openings):
        o['Id'] = str(uuid.uuid5(NS, f"{plan['id']}:{k}"))

    # проверки
    issues = []
    if not loops or extra:
        issues.append(f'периметр из {1 + len(extra)} отдельных частей')
    if comps > 1:
        issues.append(f'квартира из {comps} частей до склейки')
    for s in spaces:
        lp = s['OuterLoop']
        ends = [(E[k]['EndNodeIndex'] if not rv else E[k]['StartNodeIndex']) for k, rv in lp]
        starts = [(E[k]['StartNodeIndex'] if not rv else E[k]['EndNodeIndex']) for k, rv in lp]
        if ends != starts[1:] + starts[:1]:
            issues.append(f"не замкнут обход {s['RoomId']}")
    lost = [r['id'] for i, r in enumerate(rooms) if not any(s['RoomId'] == r['id'] for s in spaces)]
    if lost:
        issues.append('нет пространства: ' + ', '.join(lost))
    return {'Id': plan['id'], 'Nodes': nodes, 'Edges': E, 'PerimeterLoop': [[k, False] for k in range(len(perimeter))],
            'PerimeterHoles': [[[remap[k], False] for k in lp] for lp in holes],  # стояки (мокрая зона)
            'Spaces': spaces, 'Openings': openings,
            'Assumptions': ['ось стены = середина зазора между заливками пола (PDF)',
                            f'толщина периметра снаружи не известна: улица {EXT_WALL}, остальное {MOP_WALL} мм',
                            'OutsideSpaceType: Exterior там, где окно; CommonArea — глухое ребро прихожей; иначе null',
                            'двери — по середине общего ребра; высоты проёмов типовые', 'выступы и впадины наружного контура мельче 30 см спрямлены', 'узкие дыры (≤760 мм) считаются мебелью и отданы комнате', 'стены до 15° выправлены по осям, толщины приведены к 80/100/120/150/200/250/300'],
            'Issues': issues}


def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).with_name('db') / 'library.json')
    L = json.loads(src.read_text(encoding='utf-8'))
    out, bad = [], 0
    for p in L:
        try:
            g = convert(p)
            for snap, ang in ((40, 10), (0, 5), (0, 2), (0, 0)):  # мягче, если выправка порвала обходы
                if not g or not g['Issues']:
                    break
                g = convert(p, snap, ang)
        except Exception as ex:  # одна квартира не должна ронять сборку
            g = {'Id': p['id'], 'Issues': [f'ошибка: {ex!r}']}
        if g:
            out.append(g)
            bad += bool(g['Issues'])
    # чистые контуры комнат (по осям стен, без артефактов заливки) — обратно в базу и в JSON для нейронки
    def clean_rings(g):
        N, E = g['Nodes'], g['Edges']
        pts = lambda lp: [[N[E[k]['EndNodeIndex'] if rv else E[k]['StartNodeIndex']]['X'], N[E[k]['EndNodeIndex'] if rv else E[k]['StartNodeIndex']]['Y']] for k, rv in lp]
        return {s['RoomId']: [{'outer': pts(s['OuterLoop']), 'holes': [pts(h) for h in s['InnerLoops']]}] for s in g['Spaces']}
    cg = {g['Id']: clean_rings(g) for g in out if 'Spaces' in g}
    for p in L:
        for r in p['rooms']:
            if r['id'] in cg.get(p['id'], {}):
                r['axis_rings'] = cg[p['id']][r['id']]  # исходные полы (rings) не трогаем — из них строится граф
    src.write_text(json.dumps(L, ensure_ascii=False, indent=1), encoding='utf-8')
    llm_p = src.with_name('library_llm.json')
    if llm_p.exists():
        llm = json.loads(llm_p.read_text(encoding='utf-8'))
        for x in llm:
            for r in x['plan']['rooms']:
                if r['id'] in cg.get(x['id'], {}):
                    r['rings'] = cg[x['id']][r['id']]
        llm_p.write_text(json.dumps(llm, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    dst = src.with_name('contour_graphs.json')
    dst.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(dst, len(out), 'квартир, с замечаниями', bad)


if __name__ == '__main__':
    main()
