"""DXF (из DWG) одной квартиры → квартира в формате extract.py (rooms/rings/links/contour/checks).

Слои задаются профилем (LAYERS). Стены = штриховки + замкнутые полилинии + линии с толщиной.
Комнаты = свободный пол внутри контура квартиры, разделённый водоразделом от подписей помещений
(граница уходит в двери — самые узкие места). Площадь каждой комнаты сверяется с подписью (допуск 3%).

Запуск: python -X utf8 extract_dwg.py <out_dir> <файл.dxf>=<имя листа> ...
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import ezdxf
import numpy as np
from ezdxf import path as dpath
from PIL import Image, ImageDraw
from scipy import ndimage
from shapely.geometry import LineString, MultiPolygon, Polygon, box
from shapely.ops import unary_union
from skimage.segmentation import watershed

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from extract import poly_to_rects  # noqa: E402

# профиль слоёв: QUBE (0_*) и выгрузка Revit (AIA)
LAYERS = {
    'walls_fill': ['0_WALLS', 'A-WALL-PATT', 'S-COLS', 'S-STRS'],
    'walls_line': ['0_INT WALLS', '0_WALLS LINES', '0_OUTLINES', 'A-WALL', 'A-GLAZ'],
    'doors': ['0_DOORS', 'A-DOOR'],
    'labels': ['0_ANNO', 'G-ANNO-TEXT', 'A-AREA-IDEN'],
}
RES = 20
NAMES = [  # подпись → (id, русское имя)
    (r'living|гостин|kitchen|кухн', 'kl', 'Кухня-гостиная'), (r'master bed|мастер', 'bed', 'Мастер-спальня'),
    (r'bed|спальн', 'bed', 'Спальня'), (r'entry|hall|прихож|холл', 'hall', 'Прихожая'), (r'corr|коридор', 'corr', 'Коридор'),
    (r'master bath|ensuite', 'bath', 'Мастер С/У'), (r'bath|wc|toilet|powder|с/у|санузел', 'bath', 'С/У'),
    (r'wardrobe|closet|walk|гардероб', 'wr', 'Гардеробная'), (r'laundry|постир', 'laundry', 'Постирочная'),
    (r'store|storage|кладов', 'store', 'Кладовая'), (r'terrace|balcony|террас|балкон|лодж', 'balcony', 'Терраса'),
    (r'study|office|кабинет', 'study', 'Кабинет'), (r'maid|staff', 'bed', 'Комната персонала'),
]


def text_of(e):
    t = e.plain_text() if e.dxftype() == 'MTEXT' else e.dxf.text
    return re.sub(r'\s+', ' ', t).strip()


def labels(msp):
    out = []
    for e in msp.query('TEXT MTEXT'):
        if e.dxf.layer not in LAYERS['labels']:
            continue
        t = text_of(e)
        m = re.search(r'(\d+[.,]\d+)\s*m', t, re.I)
        if not m:
            continue
        name = t[:m.start()].strip()
        p = e.dxf.insert
        out.append({'name': name, 'area': float(m.group(1).replace(',', '.')), 'at': (p.x, p.y)})
    return out


def wall_geometry(msp):
    polys, lines = [], []
    for e in msp:
        lay = e.dxf.layer
        if lay in LAYERS['walls_fill'] and e.dxftype() == 'HATCH':
            for bp in dpath.from_hatch(e):
                pts = [(v.x, v.y) for v in bp.flattening(5)]
                if len(pts) > 2:
                    polys.append(Polygon(pts).buffer(0))
        elif lay in LAYERS['walls_line'] and e.dxftype() in ('LINE', 'LWPOLYLINE', 'POLYLINE', 'ARC'):
            try:
                pts = [(v.x, v.y) for v in dpath.make_path(e).flattening(5)]
            except Exception:
                continue
            if len(pts) < 2:
                continue
            closed = getattr(e, 'is_closed', False) or (len(pts) > 3 and np.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1)
            if closed and len(pts) > 3 and Polygon(pts).buffer(0).area > 2e4:
                polys.append(Polygon(pts).buffer(0))
            lines.append(LineString(pts).buffer(15))
    return unary_union(polys + lines)


def door_geometry(msp):
    out = []
    for e in msp:
        if e.dxf.layer in LAYERS['doors'] and e.dxftype() in ('LINE', 'ARC', 'LWPOLYLINE', 'POLYLINE'):
            try:
                out.append(LineString([(v.x, v.y) for v in dpath.make_path(e).flattening(5)]))
            except Exception:
                pass
    return out


def raster(geom, x0, y0, W, H):
    img = Image.new('1', (W, H), 0)
    d = ImageDraw.Draw(img)
    for g in getattr(geom, 'geoms', [geom]):
        if g.is_empty or g.geom_type != 'Polygon':
            continue
        d.polygon([((x - x0) / RES, (y - y0) / RES) for x, y in g.exterior.coords], fill=1)
        for h in g.interiors:
            d.polygon([((x - x0) / RES, (y - y0) / RES) for x, y in h.coords], fill=0)
    return np.array(img, bool)


def vectorize(mask, x0, y0):
    """маска → многоугольники в мм (по контурам пикселей, спрямлённые)"""
    from skimage import measure
    polys = []
    for c in measure.find_contours(np.pad(mask, 1).astype(float), 0.5):
        pts = [(x0 + (x - 1) * RES, y0 + (y - 1) * RES) for y, x in c]
        if len(pts) > 3:
            polys.append(Polygon(pts).buffer(0))
    if not polys:
        return Polygon()
    polys.sort(key=lambda g: -g.area)
    out = polys[0]
    for p in polys[1:]:
        out = out.difference(p) if out.contains(p) else out.union(p)
    return out.simplify(RES * 0.75, preserve_topology=True)


def extract(dxf_path, sheet):
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    labs = labels(msp)
    walls = wall_geometry(msp)
    doors = door_geometry(msp)
    if not labs or walls.is_empty:
        return {'source': sheet, 'apartments': [], 'error': 'нет подписей или стен'}
    # окно квартиры = рамка вокруг подписей с запасом
    lx = [l['at'][0] for l in labs]; ly = [l['at'][1] for l in labs]
    frame = box(min(lx) - 12000, min(ly) - 12000, max(lx) + 12000, max(ly) + 12000)
    walls = walls.intersection(frame)
    x0, y0, x1, y1 = frame.bounds
    W, H = int((x1 - x0) / RES) + 1, int((y1 - y0) / RES) + 1
    Wm = raster(walls, x0, y0, W, H)
    # дверные полотна и дуги временно считаются стеной: так проём у входа и у фасада закрыт при поиске контура
    Dm = raster(unary_union([d.buffer(20) for d in doors]), x0, y0, W, H) if doors else np.zeros_like(Wm)
    seal = Wm | Dm
    r = int(700 / RES)
    yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
    closed = ndimage.binary_closing(np.pad(seal, r + 2), structure=xx * xx + yy * yy <= r * r)[r + 2:-r - 2, r + 2:-r - 2] | seal
    inside = ndimage.binary_fill_holes(closed) & ~Wm
    # подписи → маркеры
    markers = np.zeros(Wm.shape, np.int32)
    for k, l in enumerate(labs, 1):
        c, rr = int((l['at'][0] - x0) / RES), int((l['at'][1] - y0) / RES)
        if 0 <= rr < H and 0 <= c < W:
            # подпись могла попасть на мебель/стену — ближайшая свободная клетка
            if not inside[rr, c]:
                dist, (iy, ix) = ndimage.distance_transform_edt(~inside, return_indices=True)
                rr, c = iy[rr, c], ix[rr, c]
            markers[max(rr - 2, 0):rr + 3, max(c - 2, 0):c + 3] = k
    markers[~inside] = 0
    # двери закрываются сужением пола на 450 мм → комнаты = отдельные куски; кусок с одной подписью — её,
    # с несколькими (открытая кухня+прихожая) — делится по ближайшей подписи; потом расширяем обратно до стен
    r2 = int(150 / RES)
    yy, xx = np.ogrid[-r2:r2 + 1, -r2:r2 + 1]
    core = ndimage.binary_erosion(inside & ~Dm, structure=xx * xx + yy * yy <= r2 * r2)  # полотна/дуги/витражи-двери = разделители
    comp, nc = ndimage.label(core)
    seed = np.zeros_like(markers)
    pts = {}
    for k in range(1, len(labs) + 1):
        ys, xs = np.nonzero(markers == k)
        if len(ys):
            pts[k] = (int(ys.mean()), int(xs.mean()))
    _, (iy, ix) = ndimage.distance_transform_edt(~core, return_indices=True)
    owner = {}
    for k, (yk, xk) in pts.items():
        c = comp[iy[yk, xk], ix[yk, xk]]
        owner.setdefault(c, []).append(k)
    for c, ks in owner.items():
        m = comp == c
        if len(ks) == 1:
            seed[m] = ks[0]
        elif len(ks) == 2:
            # открытый план без линии раздела: прямой разрез, при котором площади частей ≈ подписям
            a, b = ks
            want = labs[a - 1]['area'] / (labs[a - 1]['area'] + labs[b - 1]['area'])
            full = m.sum()
            best = None
            for axis in (0, 1):
                pa, pb = pts[a][axis], pts[b][axis]
                if pa == pb:
                    continue
                prof = m.sum(axis=1 - axis).cumsum() / full  # доля площади до позиции
                lo, hi = sorted((pa, pb))
                for pos in range(lo + 1, hi):
                    share = prof[pos - 1] if pa < pb else 1 - prof[pos - 1]
                    err = abs(share - want)
                    if best is None or err < best[0]:
                        best = (err, axis, pos)
            idx = np.indices(m.shape)
            if best:
                _, axis, pos = best
                near_a = (idx[axis] < pos) if pts[a][axis] < pos else (idx[axis] >= pos)
                seed[m & near_a] = a
                seed[m & ~near_a] = b
        else:
            sub = np.zeros_like(markers)
            for k in ks:
                sub[pts[k]] = k
            _, (sy, sx) = ndimage.distance_transform_edt(sub == 0, return_indices=True)
            seed[m] = sub[sy, sx][m]
    _, (iy, ix) = ndimage.distance_transform_edt(seed == 0, return_indices=True)
    lab = np.where(inside, seed[iy, ix], 0)
    rooms, used = [], {}
    for k, l in enumerate(labs, 1):
        m = lab == k
        if not m.any():
            continue
        g = vectorize(m, x0, y0)
        rid0, ru = next(((i, n) for p, i, n in NAMES if re.search(p, l['name'], re.I)), ('room', l['name'].title()))
        used[rid0] = used.get(rid0, 0) + 1
        rid = rid0 if used[rid0] == 1 else f'{rid0}{used[rid0]}'
        parts = [g] if g.geom_type == 'Polygon' else sorted(g.geoms, key=lambda p: -p.area)
        rings = [{'outer': [[round(x / 10) * 10, round(y / 10) * 10] for x, y in list(p.exterior.coords)[:-1]],
                  'holes': [[[round(x / 10) * 10, round(y / 10) * 10] for x, y in list(h.coords)[:-1]] for h in p.interiors]}
                 for p in parts if p.area > 0.2e6]
        rects = []
        for p in parts:
            rects += poly_to_rects([list(c) for c in list(p.exterior.coords)[:-1]])
        rooms.append({'id': rid, 'fn': ru, 'name_src': l['name'], 'area': l['area'], 'area_geom': round(g.area / 1e6, 2),
                      'rects': [[round(v / 10) * 10 for v in rc] for rc in rects], 'rings': rings, 'k': k})
    # связи: общая граница водораздела; ширина = длина общей границы
    links = []
    for a in rooms:
        for b in rooms:
            if a['k'] >= b['k']:
                continue
            ma = ndimage.binary_dilation(lab == a['k'], iterations=2)
            touch = ma & (lab == b['k'])
            if touch.sum() < 3:
                continue
            ys, xs = np.nonzero(touch)
            w = int(max(np.ptp(xs), np.ptp(ys)) * RES)
            outdoor = 'balcony' in (a['id'][:7], b['id'][:7])
            links.append({'between': [a['id'], b['id']], 'type': 'balcony' if outdoor else ('open' if w > 1000 else 'door'), 'w': w})
    # контур квартиры и окна: участки контура без стены
    foot = vectorize(inside, x0, y0)
    outer = foot if foot.geom_type == 'Polygon' else max(foot.geoms, key=lambda p: p.area)
    wins = []
    ring = outer.exterior
    n = int(ring.length // 300)
    gap = []
    for i in range(n + 1):
        p = ring.interpolate(i * 300)
        free = not walls.buffer(60).contains(p)
        gap.append((p, free))
    run = []
    for p, free in gap + [(None, False)]:
        if free:
            run.append(p)
        elif len(run) >= 3:
            mid = run[len(run) // 2]
            k = lab[min(int((mid.y - y0) / RES), H - 1), min(int((mid.x - x0) / RES), W - 1)]
            near = min(rooms, key=lambda r: Polygon(r['rings'][0]['outer']).distance(mid) if r['rings'] else 1e9)
            wins.append({'room': near['id'], 'at': [round(mid.x / 10) * 10, round(mid.y / 10) * 10], 'w': len(run) * 300})
            run = []
        else:
            run = []
    entry = next((r for r in rooms if r['id'].startswith(('hall', 'corr'))), rooms[0])
    links.append({'between': ['MOP', entry['id']], 'type': 'entry', 'w': 1000})
    # проверки
    g = {}
    for l in links:
        if l['type'] in ('door', 'open', 'balcony', 'entry'):
            a, b = l['between']
            g.setdefault(a, set()).add(b); g.setdefault(b, set()).add(a)
    reach, st = set(), ['MOP']
    while st:
        u = st.pop()
        if u not in reach:
            reach.add(u); st += list(g.get(u, ()))
    dev = [(r['id'], r['area'], r['area_geom']) for r in rooms if not r['id'].startswith('balcony') and abs(r['area_geom'] - r['area']) > 0.03 * r['area'] + 0.3]
    checks = {'entries': 1, 'unreached': [r['id'] for r in rooms if r['id'] not in reach],
              'no_window': [r['id'] for r in rooms if r['id'].startswith(('bed', 'kl')) and not any(w['room'] == r['id'] for w in wins)
                            and not any(l['type'] == 'balcony' and r['id'] in l['between'] for l in links)],
              'area_total_ok': not dev, 'area_dev': dev, 'total_src': 'dwg_labels', 'source_kind': 'dwg'}
    checks['ok'] = not checks['unreached'] and not checks['no_window'] and not dev
    for r in rooms:
        r.pop('k')
    to_xy = lambda p: [[round(x / 10) * 10, round(y / 10) * 10] for x, y in list(p.exterior.coords)[:-1]]
    apt = {'contour': {'outer': to_xy(outer), 'windows': wins, 'risers': []}, 'rooms': rooms, 'links': links, 'checks': checks,
           'area_rooms': round(sum(r['area'] for r in rooms), 2), 'area_geom': round(sum(r['area_geom'] for r in rooms), 2),
           'total_on_sheet': None, 'check_total': None}
    return {"source": sheet, "mm_per_unit": 1.0, "apartments": [apt]}, (lab, x0, y0, labs, inside, Wm, Dm)


def overlay(res, png):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as P
    apt = res['apartments'][0]
    f, a = plt.subplots(figsize=(8, 8))
    cols = plt.cm.Pastel1.colors
    cen = {}
    for i, r in enumerate(apt['rooms']):
        for q in r['rings']:
            a.add_patch(P(q['outer'], fc=cols[i % 9], ec='k', lw=.6))
        c = Polygon(r['rings'][0]['outer']).representative_point() if r['rings'] else None
        if c:
            cen[r['id']] = (c.x, c.y)
            a.text(c.x, c.y, f"{r['fn']}\n{r['area']} / {r['area_geom']}", fontsize=7, ha='center')
    for l in apt['links']:
        if all(x in cen for x in l['between']):
            (x1, y1), (x2, y2) = cen[l['between'][0]], cen[l['between'][1]]
            a.plot([x1, x2], [y1, y2], {'door': 'r-', 'open': 'b--', 'balcony': 'g:'}.get(l['type'], 'k-'), lw=1)
    for w in apt['contour']['windows']:
        a.plot(*w['at'], 'o', color='#3a8fff', ms=5)
    a.plot(*zip(*(apt['contour']['outer'] + apt['contour']['outer'][:1])), 'k', lw=1.5)
    a.set_aspect('equal'); a.axis('off'); a.set_title(f"{res['source']}  ok={apt['checks']['ok']}")
    f.savefig(png, dpi=80, bbox_inches='tight')


if __name__ == '__main__':
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    for arg in sys.argv[2:]:
        dxf, sheet = arg.split('=', 1)
        res, _ = extract(dxf, sheet)
        (out / f'{sheet}.json').write_text(json.dumps(res, ensure_ascii=False), encoding='utf-8')
        overlay(res, out / f'{sheet}.png')
        c = res['apartments'][0]['checks']
        print(sheet, 'ok' if c['ok'] else 'FAIL', {k: v for k, v in c.items() if v and k not in ('ok', 'entries', 'total_src', 'source_kind', 'area_total_ok')})
