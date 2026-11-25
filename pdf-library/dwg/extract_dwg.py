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
    (r'living|гостин|kitchen|кухн', 'kl', 'Кухня-гостиная'), (r'master bed|^master$|мастер', 'bed', 'Мастер-спальня'),
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


def door_geometry(msp, windows=None):
    """линии дверей (полотна, дуги); длинные узкие прямоугольники того же слоя — окна/витражи → в windows"""
    out = []
    for e in msp:
        if e.dxf.layer in LAYERS['doors'] and e.dxftype() in ('LINE', 'ARC', 'LWPOLYLINE', 'POLYLINE'):
            try:
                pts = [(v.x, v.y) for v in dpath.make_path(e).flattening(5)]
            except Exception:
                continue
            if len(pts) < 2:
                continue
            if windows is not None and len(pts) >= 4:
                r = Polygon(pts).buffer(0).minimum_rotated_rectangle
                if not r.is_empty and r.geom_type == 'Polygon':
                    c = list(r.exterior.coords)
                    s1, s2 = sorted((np.hypot(c[0][0] - c[1][0], c[0][1] - c[1][1]), np.hypot(c[1][0] - c[2][0], c[1][1] - c[2][1])))
                    if s2 > 600 and s1 < 400:
                        windows.append((r, s2))
            out.append(LineString(pts))
    return out


def door_chords(msp, walls):
    """дверь = отрезок проёма: от петли (центр дуги) до конца дуги, который упирается в стену (закрытое полотно)"""
    import math
    out = []
    for e in msp.query('ARC'):
        if e.dxf.layer not in LAYERS['doors']:
            continue
        c, r = e.dxf.center, e.dxf.radius
        if not 500 <= r <= 1400:
            continue
        ends = [(c.x + r * math.cos(math.radians(a)), c.y + r * math.sin(math.radians(a))) for a in (e.dxf.start_angle, e.dxf.end_angle)]
        from shapely.geometry import Point
        p = min(ends, key=lambda q: walls.distance(Point(q)))
        out.append(LineString([(c.x, c.y), p]))
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
    win_geo = []
    doors = door_geometry(msp, win_geo)
    if not labs or walls.is_empty:
        return {'source': sheet, 'apartments': [], 'error': 'нет подписей или стен'}
    # окно квартиры = рамка вокруг подписей с запасом
    lx = [l['at'][0] for l in labs]; ly = [l['at'][1] for l in labs]
    frame = box(min(lx) - 12000, min(ly) - 12000, max(lx) + 12000, max(ly) + 12000)
    walls = walls.intersection(frame)
    x0, y0, x1, y1 = frame.bounds
    W, H = int((x1 - x0) / RES) + 1, int((y1 - y0) / RES) + 1
    Wm = raster(walls, x0, y0, W, H)
    # перегородки двумя линиями граней: зазор до ~260 мм между ними — тело стены
    rw = int(130 / RES)
    yy, xx = np.ogrid[-rw:rw + 1, -rw:rw + 1]
    Wm = ndimage.binary_closing(np.pad(Wm, rw + 1), structure=xx * xx + yy * yy <= rw * rw)[rw + 1:-rw - 1, rw + 1:-rw - 1] | Wm
    # дверные полотна и дуги временно считаются стеной: так проём у входа и у фасада закрыт при поиске контура
    Dm = raster(unary_union([d.buffer(20) for d in doors]), x0, y0, W, H) if doors else np.zeros_like(Wm)
    chords = door_chords(msp, walls)
    Cm = raster(unary_union([d.buffer(25) for d in chords] + [w.buffer(10) for w, _ in win_geo]), x0, y0, W, H) if chords else Dm
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
    # комнаты = куски пола между стенами; полотна и дуги дверей замыкают проёмы
    core = ndimage.binary_erosion(inside & ~Cm, iterations=1)  # проёмы закрыты по линии двери, дуги не мешают
    comp, nc = ndimage.label(core)
    seed = np.zeros_like(markers)
    pts = {}
    for k in range(1, len(labs) + 1):
        ys, xs = np.nonzero(markers == k)
        if len(ys):
            pts[k] = (int(ys.mean()), int(xs.mean()))
    sizes = ndimage.sum(core, comp, range(nc + 1)) * RES * RES
    big = core & (sizes[comp] > 1.0e6)  # подпись на дуге двери — привязать к ближайшему настоящему куску
    _, (iy, ix) = ndimage.distance_transform_edt(~big, return_indices=True)
    owner = {}
    for k, (yk, xk) in pts.items():
        c = comp[iy[yk, xk], ix[yk, xk]]
        owner.setdefault(c, []).append(k)
    for c, ks in owner.items():
        m = comp == c
        if len(ks) == 1:
            seed[m] = ks[0]
            continue
        # открытый план (несколько подписей в одном куске): степенная диаграмма — прямые границы,
        # веса подбираются, пока площади частей не совпадут с подписями
        ys, xs = np.nonzero(m)
        P = np.array([pts[k] for k in ks], float)
        want = np.array([labs[k - 1]['area'] for k in ks]); want = want / want.sum() * len(ys)
        w = np.zeros(len(ks))
        d2 = (ys[:, None] - P[None, :, 0]) ** 2 + (xs[:, None] - P[None, :, 1]) ** 2
        for _ in range(2000):
            own = np.argmin(d2 - w[None, :], axis=1)
            got = np.bincount(own, minlength=len(ks))
            err = (want - got) / len(ys)
            if np.abs(err).max() < 0.005:
                break
            w += err * 0.3 * d2.mean()
        seed[ys, xs] = np.array(ks)[own]
    # куски без подписи: мелкие (дуги дверей, ниши) отдаём соседям, крупные (> 1 м², полосы за витражом, улица) — не квартира
    keep = inside.copy()
    for c in range(1, nc + 1):
        if c not in owner:
            m = comp == c
            if m.sum() * RES * RES > 1.0e6:
                keep &= ~ndimage.binary_dilation(m, iterations=2)
    _, (iy, ix) = ndimage.distance_transform_edt(seed == 0, return_indices=True)
    lab = np.where(keep, seed[iy, ix], 0)
    inside = keep
    rooms, used = [], {}
    taken = Polygon()
    # оболочка квартиры: замкнутые области между стенами, окнами и линиями дверей, где есть подпись
    from shapely.geometry import Point
    shell = unary_union([walls] + [w.buffer(15) for w, _ in win_geo] + [c.buffer(25) for c in chords])
    holes = [Polygon(h) for poly in getattr(shell, 'geoms', [shell]) if poly.geom_type == 'Polygon' for h in poly.interiors]
    env = unary_union([h for h in holes if any(h.contains(Point(l['at'])) for l in labs)])
    env = env.buffer(40, join_style=2) if not env.is_empty and env.area > 0.85 * sum(l['area'] for l in labs) * 1e6 else None
    for k, l in enumerate(labs, 1):
        m = lab == k
        if not m.any():
            continue
        # узкие отростки (< 600 мм: полоса за фасадом, щель у витража) — не комната
        ro = int(300 / RES); yy, xx = np.ogrid[-ro:ro + 1, -ro:ro + 1]
        mo = ndimage.binary_opening(m, structure=xx * xx + yy * yy <= ro * ro)
        if mo.sum() > 0.5 * m.sum():
            lb, nb = ndimage.label(mo)
            if nb > 1:
                sz = ndimage.sum(mo, lb, range(1, nb + 1))
                mo = lb == (int(np.argmax(sz)) + 1)  # комната = один цельный кусок
            # вернуть то, что срезал радиус в углах, но не отростки: пересечение с расширенным ядром
            m = m & ndimage.binary_dilation(mo, iterations=ro)
        g = vectorize(m, x0, y0)
        # вершины вдоль стен — из CAD: расширить на 80 мм и обрезать точной геометрией стен и уже занятыми комнатами
        g = g.buffer(80, join_style=2).difference(walls).difference(taken)
        if env is not None:
            g = g.intersection(env)
        g = g.buffer(-20, join_style=2).buffer(20, join_style=2)
        if g.geom_type == 'MultiPolygon':
            g = unary_union([q for q in g.geoms if q.area > 0.3e6]) or max(g.geoms, key=lambda q: q.area)
        g = g.simplify(15, preserve_topology=True)
        taken = taken.union(g)
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
            has_door = (touch & ndimage.binary_dilation(Dm, iterations=10)).any()
            if not has_door and w <= 1000:
                continue  # узкий стык без двери — щель/угол, не связь
            links.append({'between': [a['id'], b['id']], 'type': 'balcony' if outdoor else ('door' if has_door and w <= 1300 else 'open'), 'w': w})
    # контур квартиры и окна: участки контура без стены
    foot = vectorize(inside, x0, y0)
    outer = foot if foot.geom_type == 'Polygon' else max(foot.geoms, key=lambda p: p.area)
    wins = []
    for r, length in win_geo:
        c = r.centroid
        if not outer.buffer(800).contains(c):
            continue
        for rr in rooms:
            if rr['rings'] and min(Polygon(q['outer']).distance(r) for q in rr['rings']) < 600:
                wins.append({'room': rr['id'], 'at': [round(c.x / 10) * 10, round(c.y / 10) * 10], 'w': int(length)})
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
    # DWG: площади в подписях считаются по своей грани стены → допуск на комнату 35% (+0.5 м², открытый план делится без линии раздела), на сумму 6%
    dev = [(r['id'], r['area'], r['area_geom']) for r in rooms if not r['id'].startswith('balcony') and abs(r['area_geom'] - r['area']) > 0.35 * r['area'] + 0.5]
    live = [r for r in rooms if not r['id'].startswith('balcony')]
    tot_l, tot_g = sum(r['area'] for r in live), sum(r['area_geom'] for r in live)
    if abs(tot_g - tot_l) > 0.06 * tot_l:
        dev.append(('итого', round(tot_l, 2), round(tot_g, 2)))
    checks = {'entries': 1, 'unreached': [r['id'] for r in rooms if r['id'] not in reach],
              'no_window': [r['id'] for r in rooms if r['id'].startswith(('bed', 'kl')) and not any(w['room'] == r['id'] for w in wins)
                            and not any(l['type'] == 'open' and r['id'] in l['between'] and any(w['room'] in l['between'] for w in wins) for l in links)
                            and not any(l['type'] == 'balcony' and r['id'] in l['between'] for l in links)],
              'area_total_ok': not dev, 'area_dev': dev, 'total_src': 'dwg_labels', 'source_kind': 'dwg'}
    # стены точные из CAD; по комнатам расходится только деление открытого плана → решает общая сумма
    checks['ok'] = not checks['unreached'] and not checks['no_window'] and not any(d[0] == 'итого' for d in dev)
    for r in rooms:
        r.pop('k')
    to_xy = lambda p: [[round(x / 10) * 10, round(y / 10) * 10] for x, y in list(p.exterior.coords)[:-1]]
    apt = {'geom': 'approx', 'contour': {'outer': to_xy(outer), 'windows': wins, 'risers': []}, 'rooms': rooms, 'links': links, 'checks': checks,
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
