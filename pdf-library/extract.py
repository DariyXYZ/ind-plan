# PDF-лист планировки IND (векторный) -> квартиры в формате Б (помещения прямоугольниками + двери + контур)
# Источник геометрии: цветные заливки = помещения, тёмная заливка = стены, серые квадраты = вентблоки/стояки,
# текст «Название / NN.NN м²» = подпись помещения, «1800 x 750» = окно.
import sys, os, re, json, math, collections
import fitz
from shapely.geometry import Point
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

PX = 3.0  # пикселей на единицу PDF
ENTRY_OK = {'hall', 'corr', 'kl', 'kitchen', 'living', 'room'}

AREA_RE = re.compile(r'^\s*(\d+[.,]\d+)\s*м')
WIN_RE = re.compile(r'^\s*(\d{3,4})\s*x\s*(\d{3,4})\s*$')
TYPE_RE = re.compile(r'^\s*(ST|\dE|\dК|\dk|\dС)\s*$')

FN = {'кухня-гостинная': 'kl', 'кухня-гостиная': 'kl', 'спальня': 'bed', 'санузел': 'bath', 'с/у': 'bath',
      'прихожая': 'hall', 'коридор': 'corr', 'постирочная': 'laundry', 'гардеробная': 'wr', 'балкон': 'balcony',
      'лоджия': 'balcony', 'патио': 'patio', 'кладовая': 'store', 'кухня': 'kitchen', 'гостиная': 'living',
      'терраса': 'patio', 'гардероб': 'wr', 'кабинет': 'study', 'ванная': 'bath', 'туалет': 'wc', 'жилая комната': 'bed', 'мастер-спальня': 'bed', 'мастер с/у': 'bath', 'холл': 'corr', 'спальня мастер': 'bed', 'детская': 'bed', 'гостевой с/у': 'bath', 'гардеробная мастер': 'wr'}


def fill_key(f):
    return tuple(round(c, 2) for c in f)


def is_pastel(f):
    if not f: return False
    r, g, b = f[:3]
    lo = float(os.environ.get('MIN_PASTEL', '0.7'))  # Fotieva: бежевый пол 0.80/0.78/0.69
    return max(r, g, b) - min(r, g, b) > 0.02 and min(r, g, b) > lo and not (r > 0.9 and g < 0.6)


def path_polys(d):
    polys, cur = [], []
    for it in d['items']:
        if it[0] == 'l':
            a, b = it[1], it[2]
            if not cur: cur = [(a.x, a.y)]
            elif math.dist(cur[-1], (a.x, a.y)) > 0.01:
                polys.append(cur); cur = [(a.x, a.y)]
            cur.append((b.x, b.y))
        elif it[0] == 're':
            r = it[1]; polys.append([(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1)])
        elif it[0] == 'qu':
            q = it[1]; polys.append([(q.ul.x, q.ul.y), (q.ur.x, q.ur.y), (q.lr.x, q.lr.y), (q.ll.x, q.ll.y)])
    if cur: polys.append(cur)
    return [p for p in polys if len(p) >= 3]


def room_shape(d):
    from shapely.geometry import LineString, Polygon
    from shapely.ops import polygonize, unary_union
    segs = []
    for it in d['items']:
        if it[0] == 'l': segs.append([(it[1].x, it[1].y), (it[2].x, it[2].y)])
        elif it[0] == 'c': segs.append([(it[1].x, it[1].y), (it[4].x, it[4].y)])
        elif it[0] == 're':
            r = it[1]; segs += [[(r.x0, r.y0), (r.x1, r.y0)], [(r.x1, r.y0), (r.x1, r.y1)], [(r.x1, r.y1), (r.x0, r.y1)], [(r.x0, r.y1), (r.x0, r.y0)]]
        elif it[0] == 'qu':
            q = it[1]; pts = [(q.ul.x, q.ul.y), (q.ur.x, q.ur.y), (q.lr.x, q.lr.y), (q.ll.x, q.ll.y)]
            segs += [[pts[i], pts[(i + 1) % 4]] for i in range(4)]
    segs = [s for s in segs if s[0] != s[1]]
    faces = list(polygonize([LineString(s) for s in segs]))
    if not faces: return path_polys(d)
    U = unary_union([f.buffer(0) for f in faces])
    geoms = list(U.geoms) if U.geom_type == 'MultiPolygon' else [U]
    big = max(geoms, key=lambda g: g.area)
    return [[(x, y) for x, y in list(Polygon(g.exterior).exterior.coords)[:-1]] for g in geoms if g.area > 0.05 * big.area]


def shoelace(p):
    return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2


def labels(page):
    spans = []
    for b in page.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            d = l.get('dir', (1, 0))
            # 'h' — горизонтально; 'u' — снизу вверх (имя левее площади); 'd' — сверху вниз (имя правее)
            o = 'h' if abs(d[0]) > 0.9 else ('u' if d[1] < -0.9 else ('d' if d[1] > 0.9 else 'x'))
            for s in l['spans']:
                if s['text'].strip(): s['o'] = o; spans.append(s)
    areas = [s for s in spans if AREA_RE.match(s['text']) and s['o'] != 'x']
    names = [s for s in spans if not AREA_RE.match(s['text']) and re.search('[а-яА-Я]', s['text']) and s['o'] != 'x']
    out = []
    for a in areas:
        ax0, ay0, ax1, ay1 = a['bbox']
        best = None
        for n in names:
            if n['o'] != a['o'] or abs(a['size'] - n['size']) >= 0.5: continue
            nx0, ny0, nx1, ny1 = n['bbox']
            if a['o'] == 'h': gap, ov = ay0 - ny1, nx0 < ax1 + 3 and ax0 < nx1 + 3
            elif a['o'] == 'u': gap, ov = ax0 - nx1, ny0 < ay1 + 3 and ay0 < ny1 + 3
            else: gap, ov = nx0 - ax1, ny0 < ay1 + 3 and ay0 < ny1 + 3
            if -2 < gap < 6 and ov:
                if best is None or gap < best[0]: best = (gap, n)
        if best:
            n = best[1]
            out.append({'fn': n['text'].strip(), 'area': float(AREA_RE.match(a['text']).group(1).replace(',', '.')),
                        'pt': ((n['bbox'][0] + n['bbox'][2]) / 2, (n['bbox'][1] + n['bbox'][3]) / 2), 'size': a['size']})
    # итоги квартир: крупные цифры площади без названия над ними
    totals = []
    for a in areas:
        if a['size'] > 8 and not any(abs(l['pt'][1] - a['bbox'][1]) < 20 and abs(l['pt'][0] - (a['bbox'][0] + a['bbox'][2]) / 2) < 40 for l in out):
            totals.append(float(AREA_RE.match(a['text']).group(1).replace(',', '.')))
    # таблички квартир (Touch): код «1.3.1», рядом числа без «м²» — общая площадь = максимум
    labels.from_table = False
    if not totals:
        codes = [s for s in spans if s['o'] == 'h' and re.match(r'^\d+\.\d+\.\d+$', s['text'].strip())]
        nums = [s for s in spans if s['o'] == 'h' and re.match(r'^\d+,\d\d$', s['text'].strip())]
        for c in codes:
            cx, cy = c['bbox'][2], (c['bbox'][1] + c['bbox'][3]) / 2
            near = [float(s['text'].replace(',', '.')) for s in nums if 0 < s['bbox'][0] - cx < 30 and abs((s['bbox'][1] + s['bbox'][3]) / 2 - cy) < 25]
            if near: totals.append(max(near)); labels.from_table = True
    wins = []
    for s in spans:
        m = WIN_RE.match(s['text'])
        if m: wins.append({'w': int(m.group(1)), 'h': int(m.group(2)), 'pt': ((s['bbox'][0] + s['bbox'][2]) / 2, (s['bbox'][1] + s['bbox'][3]) / 2)})
    return out, totals, wins


def fill_voids(R, Wm, rooms, X0, Y0, max_void_u2=900.0):
    """Пол нарисован без мебели (Fotieva): кровать/ванна у стены = выемка в заливке.
    Пустоты, закрытые со всех сторон стенами и полом, отдаются соседней комнате (самая длинная граница),
    затем контур комнаты = ортогональный многоугольник из клеток 50 мм (углы по стенам, без рваных краёв)."""
    from shapely.geometry import box
    from shapely.ops import unary_union
    occ = (R > 0) | Wm
    voids = ndi.binary_fill_holes(occ) & ~occ
    vl, nv = ndi.label(voids)
    lim = max_void_u2 * PX * PX  # пикселей; ~900 ед² ≈ 6 м² при 80 мм/ед
    for c, sl in enumerate(ndi.find_objects(vl), 1):
        sub = vl[sl] == c
        if sub.sum() > lim: continue  # большие пустоты — МОП/шахты, не мебель
        sl2 = tuple(slice(max(0, q.start - 4), q.stop + 4) for q in sl)
        s2 = vl[sl2] == c
        ring = ndi.binary_dilation(s2, iterations=4) & ~s2
        nb = R[sl2][ring]; nb = nb[nb > 0]
        if len(nb): R[sl2][s2] = int(np.bincount(nb).argmax())
    # выемки у фасада (кровать у витража — пустота не замкнута стеной): закрытие ~2.6 м внутри здания
    occ = (R > 0) | Wm
    bld = ndi.binary_fill_holes(ndi.binary_closing(occ, structure=np.ones((3, 3)), iterations=int(20 * PX)))
    side = int(37 * PX)  # ~2.6 м при ~70 мм/ед
    for r in rooms:
        m = R == r['k']
        if not m.any(): continue
        ys, xs = np.nonzero(m)
        y0, y1, x0, x1 = max(0, ys.min() - side), ys.max() + side + 1, max(0, xs.min() - side), xs.max() + side + 1
        sub = m[y0:y1, x0:x1]
        q = 4  # закрытие на маске ×1/4 — в ~16 раз быстрее, точность ±4 px (контур потом всё равно по клеткам)
        hh, ww = sub.shape[0] // q * q, sub.shape[1] // q * q
        small = sub[:hh, :ww].reshape(hh // q, q, ww // q, q).any(axis=(1, 3))
        cs = ndi.binary_closing(small, structure=np.ones((side // q, side // q)))
        cl = np.zeros_like(sub); cl[:hh, :ww] = np.repeat(np.repeat(cs, q, 0), q, 1)
        add = cl & ~sub & (R[y0:y1, x0:x1] == 0) & ~Wm[y0:y1, x0:x1] & bld[y0:y1, x0:x1]
        R[y0:y1, x0:x1][add] = r['k']
    g = max(1, int(round(PX * 0.6)))  # клетка ~0.6 ед. PDF (~50 мм)
    for r in rooms:
        m = R == r['k']
        if not m.any(): continue
        ys, xs = np.nonzero(m)
        cells = {(x // g, y // g) for x, y in zip(xs, ys)}
        cnt = collections.Counter((x // g, y // g) for x, y in zip(xs, ys))
        boxes = [box(cx * g, cy * g, (cx + 1) * g, (cy + 1) * g) for (cx, cy), n in cnt.items() if n * 2 >= g * g]
        if not boxes: continue
        U = unary_union(boxes).buffer(g * 0.6, join_style=2).buffer(-g * 0.6, join_style=2).simplify(g * 0.9)
        geoms = list(U.geoms) if U.geom_type == 'MultiPolygon' else [U]
        polys = []
        for G in geoms:
            if G.area < 4 * g * g: continue
            polys.append([(x / PX + X0, y / PX + Y0) for x, y in list(G.exterior.coords)[:-1]])
        if polys: r['polys'] = polys
    return R


def extract(pdf, pno=0, extra_wall_axes=None):
    page = fitz.open(pdf)[pno]
    dr = page.get_drawings()
    labs, totals, wins = labels(page)
    room_paths = [d for d in dr if d['type'] == 'f' and is_pastel(d['fill'])]
    wall_paths = [d for d in dr if d['type'] == 'f' and d['fill'] and len(set(fill_key(d['fill'])[:3])) == 1 and d['fill'][0] <= 0.4]
    riser_paths = [d for d in dr if d['type'] == 'f' and d['fill'] and fill_key(d['fill'])[:3] in ((0.89, 0.89, 0.89),) and d['rect'].width < 12 and d['rect'].height < 12]
    if not room_paths or not labs: return None
    # окно растра — по заливкам помещений
    xs = [v for d in room_paths for v in (d['rect'].x0, d['rect'].x1)]
    ys = [v for d in room_paths for v in (d['rect'].y0, d['rect'].y1)]
    X0, Y0, X1, Y1 = min(xs) - 40, min(ys) - 40, max(xs) + 40, max(ys) + 40
    W, H = int((X1 - X0) * PX) + 1, int((Y1 - Y0) * PX) + 1
    tp = lambda p: ((p[0] - X0) * PX, (p[1] - Y0) * PX)

    # помещения
    rid = Image.new('I', (W, H), 0); dd = ImageDraw.Draw(rid)
    rooms = []
    for d in room_paths:
        if os.environ.get('OUTER_ONLY'):  # пол с вырезами под мебель (Fotieva): контур = самое большое кольцо
            rings = [p for p in path_polys(d) if len(p) >= 3]
            polys = [max(rings, key=shoelace)] if rings else []
        else:
            polys = room_shape(d) if len(d['items']) > 12 else path_polys(d)
        if not polys: continue
        k = len(rooms) + 1
        for p in polys: dd.polygon([tp(q) for q in p], fill=k)
        rooms.append({'k': k, 'polys': polys, 'color': fill_key(d['fill']), 'area_u': sum(shoelace(p) for p in polys)})
    R = np.array(rid)
    wall = Image.new('L', (W, H), 0); dw = ImageDraw.Draw(wall)
    for d in wall_paths:
        for p in path_polys(d): dw.polygon([tp(q) for q in p], fill=255)
    if extra_wall_axes:
        for y, x0, x1, thickness in extra_wall_axes.get('h', []):
            dw.line([tp((x0, y)), tp((x1, y))], fill=255, width=max(1, round(thickness * PX)))
        for x, y0, y1, thickness in extra_wall_axes.get('v', []):
            dw.line([tp((x, y0)), tp((x, y1))], fill=255, width=max(1, round(thickness * PX)))
    Wm = np.array(wall) > 0
    if os.environ.get('FILL_VOIDS'):
        R = fill_voids(R, Wm, rooms, X0, Y0)

    # подписи -> помещения
    for l in labs:
        x, y = tp(l['pt'])
        if 0 <= int(y) < H and 0 <= int(x) < W:
            k = R[int(y), int(x)]
            if k: rooms[k - 1].setdefault('labs', []).append(l)
    # куски без подписи → к соседнему подписанному помещению по самой длинной границе без стены
    labeled = {r['k'] for r in rooms if r.get('labs')}
    for _ in range(4):
        cont = collections.Counter()
        for sh in ((0, 1), (1, 0)):
            A = R[:H - sh[0], :W - sh[1]]; B = R[sh[0]:, sh[1]:]
            unc = ~Wm[:H - sh[0], :W - sh[1]] & ~Wm[sh[0]:, sh[1]:]
            m = (A != B) & (A > 0) & (B > 0) & unc
            for u, v in zip(A[m], B[m]):
                u, v = int(u), int(v)
                if (u in labeled) != (v in labeled): cont[(v, u) if u in labeled else (u, v)] += 1
        best = {}
        for (un, lb), n in cont.items():
            if n > 6 and (un not in best or n > best[un][1]): best[un] = (lb, n)
        if not best: break
        for un, (lb, n) in best.items():
            R[R == un] = lb
            rooms[lb - 1]['polys'] += rooms[un - 1]['polys']; rooms[un - 1]['merged_into'] = lb
        labeled |= set(best)
        labeled = {k for k in labeled if 'merged_into' not in rooms[k - 1]}
    rooms = [r for r in rooms if r.get('labs') and 'merged_into' not in r]
    for r in rooms:
        r['lab'] = dict(r['labs'][0])
        wet = any(w in r['lab']['fn'].lower() for w in ('балкон', 'патио', 'лоджия', 'терраса'))
        if len(r['labs']) > 1 and not wet:  # одна заливка — несколько подписей: общая зона
            r['lab']['area'] = round(sum(x['area'] for x in r['labs']), 2)
            r['lab']['merged'] = [x['fn'] for x in r['labs']]
    # масштаб: чистая площадь (заливка минус стены) против подписи
    keep = {r['k'] for r in rooms}
    Rk = np.where(np.isin(R, list(keep)), R, 0)
    clean = np.bincount(Rk[~Wm].ravel(), minlength=len(R.ravel()) and (max(keep) + 1))
    for r in rooms: r['clean_u'] = clean[r['k']] / PX / PX
    WET = lambda r: any(w in r['lab']['fn'].lower() for w in ('балкон', 'патио', 'лоджия', 'терраса'))
    ks = sorted(r['lab']['area'] / r['clean_u'] for r in rooms if r['clean_u'] > 0 and not WET(r))
    if not ks: return None
    kmed = ks[len(ks) // 2]
    mm = math.sqrt(kmed) * 1000  # мм на единицу PDF
    for r in rooms:
        r['area_calc'] = r['clean_u'] * kmed
        r['dev'] = r['area_calc'] / r['lab']['area'] - 1
    # свободное пространство: МОП = крупные компоненты не у края
    free = (Rk == 0) & ~Wm
    lab_free, nfree = ndi.label(free)
    sizes = np.bincount(lab_free.ravel())
    border = set(np.unique(np.concatenate([lab_free[0], lab_free[-1], lab_free[:, 0], lab_free[:, -1]]))) - {0}
    unit_m2 = kmed / PX / PX
    # контур здания: стены+помещения, закрытие ~3 м, заливка дыр; МОП = свободное внутри здания
    rr = int(3000 / mm * PX / 2)
    bld = ndi.binary_fill_holes(ndi.binary_closing((Rk > 0) | Wm, structure=np.ones((3, 3)), iterations=rr))
    inside = np.bincount(lab_free[bld & free].ravel(), minlength=nfree + 1)
    mop = np.zeros(nfree + 1, bool)
    for c in range(1, nfree + 1):
        if inside[c] * unit_m2 > 3.0 and inside[c] > 0.5 * sizes[c] or (c in border and inside[c] * unit_m2 > 6.0): mop[c] = True
    # границы: пары пикселей с разными помещениями; открыта = ни один пиксель не стена
    tot, opn = collections.Counter(), collections.Counter()
    for sh in ((0, 1), (1, 0)):
        A = Rk[:H - sh[0], :W - sh[1]]; B = Rk[sh[0]:, sh[1]:]
        wa = Wm[:H - sh[0], :W - sh[1]]; wb = Wm[sh[0]:, sh[1]:]
        fa = lab_free[:H - sh[0], :W - sh[1]]; fb = lab_free[sh[0]:, sh[1]:]
        bldS = bld[:H - sh[0], :W - sh[1]] & bld[sh[0]:, sh[1]:]
        unc = ~wa & ~wb
        m = (A != B) & (A > 0) & (B > 0)
        for u, v, o in zip(A[m], B[m], unc[m]):
            key = (min(int(u), int(v)), max(int(u), int(v))); tot[key] += 1; opn[key] += int(o)
    rmap = {r['k']: r for r in rooms}
    wetk = np.zeros(int(Rk.max()) + 1, bool)
    for r in rooms: wetk[r['k']] = WET(r)
    # разрывы «помещение | свободное или балкон» без стены
    other = free | wetk[Rk]
    gap = np.zeros_like(free); groom = np.zeros(Rk.shape, np.int32)
    for sh in ((0, 1), (1, 0)):
        A = Rk[:H - sh[0], :W - sh[1]]; B = Rk[sh[0]:, sh[1]:]
        oa = other[:H - sh[0], :W - sh[1]] & (B != A); ob = other[sh[0]:, sh[1]:] & (A != B)
        unc = ~Wm[:H - sh[0], :W - sh[1]] & ~Wm[sh[0]:, sh[1]:]
        m1 = (A > 0) & ~wetk[A] & ob & unc
        gap[:H - sh[0], :W - sh[1]] |= m1; groom[:H - sh[0], :W - sh[1]][m1] = A[m1]
        m2 = (B > 0) & ~wetk[B] & oa & unc
        gap[sh[0]:, sh[1]:] |= m2; groom[sh[0]:, sh[1]:][m2] = B[m2]
    exterior = free & ~bld
    rad = int(1200 / mm * PX)
    wl, nw = ndi.label(ndi.binary_dilation(gap, iterations=2))
    windows_px, entries_px = [], []
    for c, sl in enumerate(ndi.find_objects(wl), 1):
        sub = (wl[sl] == c) & gap[sl]
        if not sub.any(): continue
        yy, xx = np.nonzero(sub); ln = max(np.ptp(xx), np.ptp(yy)) / PX * mm
        if ln < 400: continue
        rk = int(np.bincount(groom[sl][sub]).argmax())
        y0, x0 = max(sl[0].start - rad, 0), max(sl[1].start - rad, 0)
        y1, x1 = min(sl[0].stop + rad, H), min(sl[1].stop + rad, W)
        loc = np.zeros((y1 - y0, x1 - x0), bool); loc[sl[0].start - y0:sl[0].stop - y0, sl[1].start - x0:sl[1].stop - x0] = sub
        near = ndi.distance_transform_edt(~loc) <= rad
        near_wet = (wetk[Rk[y0:y1, x0:x1]] & near).sum()
        near_ext = (exterior[y0:y1, x0:x1] & near).sum()
        item = {'k': rk, 'cx': xx.mean() + sl[1].start, 'cy': yy.mean() + sl[0].start, 'w': round(ln / 10) * 10}
        if near_ext > 0.02 * near.sum() or near_wet > 0.02 * near.sum(): windows_px.append(item)
        else: entries_px.append(item)
    # витражи (Touch): тонкие серые заливки 0.75 по фасаду = остекление → окно соседнего помещения
    for d in dr:
        f = d.get('fill') if d['type'] == 'f' else None
        if not f or len(set(fill_key(f)[:3])) != 1 or abs(f[0] - 0.753) > 0.02: continue
        r = d['rect']; lo, hi = min(r.width, r.height), max(r.width, r.height)
        if lo > 3 or hi < 8: continue
        x0, y0 = tp((r.x0 - 8, r.y0 - 8)); x1, y1 = tp((r.x1 + 8, r.y1 + 8))
        sub = Rk[max(int(y0), 0):min(int(y1), H), max(int(x0), 0):min(int(x1), W)]
        ks = sub[(sub > 0) & ~wetk[sub]]
        if not len(ks): continue
        cx, cy = tp(((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2))
        windows_px.append({'k': int(np.bincount(ks).argmax()), 'cx': cx, 'cy': cy, 'w': round(hi * mm / 10) * 10})
    L = lambda n: n / PX * mm
    edges = []
    for key, n in opn.items():
        l = L(n)
        if l < 300: continue
        a_, b_ = key
        if a_ not in rmap or b_ not in rmap: continue
        if WET(rmap[a_]) or WET(rmap[b_]): kind = 'balcony'
        elif l <= 1000: kind = 'door'
        else: kind = 'open'
        edges.append((a_, b_, kind, round(l)))
    for e in entries_px:
        if e['k'] in rmap and 600 <= e['w'] <= 1600 and FN.get(rmap[e['k']]['lab']['fn'].lower(), 'room') in ENTRY_OK:
            edges.append(('MOP', e['k'], 'entry', e['w']))
    mop_comps = set(np.nonzero(mop)[0])
    multi = [r['lab']['fn'] + '/' + ','.join(x['fn'] for x in r['labs'][1:]) for r in rooms if len(r['labs']) > 1]

    # квартиры = компоненты связности без МОП и балконов-узлов
    adj = collections.defaultdict(set)
    for a, b, kind, _ in edges:
        if a != 'MOP' and kind != 'balcony': adj[a].add(b); adj[b].add(a)
    seen, apts = set(), []
    for r in rooms:
        if r['k'] in seen: continue
        st, comp = [r['k']], []
        while st:
            u = st.pop()
            if u in seen: continue
            seen.add(u); comp.append(u); st += list(adj[u])
        apts.append(sorted(comp))
    # балконы/патио — к квартире с самой длинной связью
    best = {}
    for a, b, kind, l in edges:
        if kind != 'balcony': continue
        bal, room = (a, b) if WET(rmap[a]) else (b, a)
        if WET(rmap[room]): continue
        if bal not in best or l > best[bal][1]: best[bal] = (room, l)
    apts = [c for c in apts if not all(WET(rmap[k]) for k in c)]
    for bal, (room, l) in best.items():
        for c in apts:
            if room in c and bal not in c: c.append(bal)
    edges = [e for e in edges if e[2] != 'balcony' or (e[0] in best and best[e[0]][0] == e[1]) or (e[1] in best and best[e[1]][0] == e[0])]

    def to_mm(p):  # ось Y вверх, начало — левый нижний угол квартиры (сдвиг ниже)
        return ((p[0] - X0) * mm, (Y1 - p[1]) * mm)

    result = []
    for comp in apts:
        rs = [rmap[k] for k in comp]
        living = [r for r in rs if 'балкон' not in r['lab']['fn'].lower() and 'патио' not in r['lab']['fn'].lower()]
        if not living: continue
        s_lab = round(sum(r['lab']['area'] for r in living), 2)
        s_calc = round(sum(r['area_calc'] for r in living), 2)
        match = min(totals, key=lambda t: abs(t - s_lab)) if totals else None
        # итог из таблички квартиры считается по неокруглённым площадям → допуск 0.3% (пропавшая комната ≥ 2 м² всё равно ловится)
        tol = max(0.06, 0.003 * s_lab) if getattr(labels, 'from_table', False) else 0.06
        ok_total = (match is not None and abs(match - s_lab) <= tol) if totals else all(abs(r['dev']) <= float(os.environ.get('ROOM_TOL', '0.06')) for r in living)
        # прямоугольники помещений в мм
        allp = [to_mm(q) for r in living for p in r['polys'] for q in p]
        ox, oy = min(p[0] for p in allp), min(p[1] for p in allp)
        rid_of = {}
        cnt = collections.Counter()
        out_rooms = []
        for r in rs:
            base = FN.get(r['lab']['fn'].lower().replace('ё', 'е'), 'room')
            cnt[base] += 1
            rid_of[r['k']] = base if cnt[base] == 1 else f'{base}{cnt[base]}'
        for r in rs:
            rects = []
            for p in r['polys']:
                q = [(round((to_mm(v)[0] - ox) / 10) * 10, round((to_mm(v)[1] - oy) / 10) * 10) for v in p]
                rects += poly_to_rects(q)
            out_rooms.append({'id': rid_of[r['k']], 'fn': r['lab']['fn'], 'area': r['lab']['area'], **({'merged': r['lab']['merged']} if 'merged' in r['lab'] else {}),
                              'area_geom': round(r['area_calc'], 2), 'rects': rects})
        es = []
        for a, b, kind, w in edges:
            if a == 'MOP' and b in rid_of: es.append({'between': ['MOP', rid_of[b]], 'type': kind})
            elif a in rid_of and b in rid_of:
                es.append({'between': [rid_of[a], rid_of[b]], 'type': kind, **({'w': w} if w else {})})
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        U = unary_union([Polygon([((to_mm(v)[0] - ox), (to_mm(v)[1] - oy)) for v in p]).buffer(0) for r in living for p in r['polys']])
        U = U.buffer(60, join_style=2).buffer(-60, join_style=2).simplify(30)
        if U.geom_type != 'Polygon': U = max(U.geoms, key=lambda g: g.area)
        outer = [[round(x / 10) * 10, round(y / 10) * 10] for x, y in list(U.exterior.coords)[:-1]]
        px2mm = lambda x, y: (round(((x / PX + X0) - X0) * mm - ox), round((Y1 - (y / PX + Y0)) * mm - oy))
        wins_o = []
        for w in windows_px:
            if w['k'] in rid_of and not WET(rmap[w['k']]):
                x, y = px2mm(w['cx'], w['cy'])
                wins_o.append({'room': rid_of[w['k']], 'at': [round(x / 10) * 10, round(y / 10) * 10], 'w': w['w']})
        ris = []
        for d in riser_paths:
            c = d['rect']; x, y = to_mm(((c.x0 + c.x1) / 2, (c.y0 + c.y1) / 2)); x -= ox; y -= oy
            if U.buffer(400).contains(Point(x, y)): ris.append([round(x / 10) * 10, round(y / 10) * 10])
        # проверки
        ent = [l for l in es if l['type'] == 'entry']
        g = collections.defaultdict(set)
        for l in es:
            if l['type'] in ('door', 'open', 'balcony'): g[l['between'][0]].add(l['between'][1]); g[l['between'][1]].add(l['between'][0])
        reach = set()
        if ent:
            st = [ent[0]['between'][1]]
            while st:
                u = st.pop()
                if u in reach: continue
                reach.add(u); st += list(g[u])
        liv_ids = [rid_of[r['k']] for r in living]
        checks = {'entries': len(ent), 'unreached': [i for i in liv_ids if i not in reach],
                  'no_window': [i for i in liv_ids if i.startswith(('bed', 'kl')) and not any(w['room'] == i for w in wins_o)],
                  'area_total_ok': ok_total, 'total_src': ('table' if getattr(labels, 'from_table', False) else 'sheet') if totals else 'rooms',
                  'total_dev': round(match - s_lab, 2) if match is not None else None}
        checks['ok'] = checks['entries'] == 1 and not checks['unreached'] and not checks['no_window'] and ok_total
        result.append({'contour': {'outer': outer, 'windows': wins_o, 'risers': ris},
                       'rooms': out_rooms, 'links': es, 'checks': checks, 'area_rooms': s_lab, 'area_geom': s_calc,
                       'total_on_sheet': match if ok_total else None, 'check_total': ok_total,
                       'origin_pdf_units': [X0 + ox / mm, Y1 - oy / mm]})
    meta = {'mm_per_unit': round(mm, 2), 'rooms_found': len(rooms), 'labels': len(labs), 'room_fills': len(room_paths),
            'labels_in_one_fill': multi, 'risers': len(riser_paths), 'windows_text': len(wins), 'totals_on_sheet': totals,
            'area_dev_max': round(max(abs(r['dev']) for r in rooms if not WET(r)), 3)}
    dbg = {'R': Rk, 'W': Wm, 'rooms': rooms, 'edges': edges, 'tp': tp, 'apts': apts, 'X0': X0, 'Y0': Y0, 'mop': mop_comps, 'free': lab_free}
    return {'meta': meta, 'apartments': result}, dbg


def poly_to_rects(q):
    """прямоугольный контур -> прямоугольники [x1,y1,x2,y2] (полосы по Y, слитые по X)"""
    xs = sorted({p[0] for p in q}); ys = sorted({p[1] for p in q})
    def inside(x, y):
        c = False
        for i in range(len(q)):
            (x1, y1), (x2, y2) = q[i], q[(i + 1) % len(q)]
            if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1): c = not c
        return c
    rows = []
    for j in range(len(ys) - 1):
        cy = (ys[j] + ys[j + 1]) / 2; segs = []; start = None
        for i in range(len(xs) - 1):
            ins = inside((xs[i] + xs[i + 1]) / 2, cy)
            if ins and start is None: start = xs[i]
            if not ins and start is not None: segs.append((start, xs[i])); start = None
        if start is not None: segs.append((start, xs[-1]))
        rows.append((ys[j], ys[j + 1], segs))
    rects, open_ = [], {}
    for y0, y1, segs in rows:
        nxt = {}
        for s in segs:
            if s in open_: nxt[s] = open_.pop(s)
            else: nxt[s] = y0
        for s, ys0 in open_.items(): rects.append([s[0], ys0, s[1], y0])
        open_ = {s: nxt[s] for s in segs}
        last = y1
    for s, ys0 in open_.items(): rects.append([s[0], ys0, s[1], last])
    # отбросить тонкие полоски < 50 мм (дрожание контура)
    return [r for r in rects if r[2] - r[0] >= 50 and r[3] - r[1] >= 50]
