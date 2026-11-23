# Режим «пол» (MODE=floor), развитие extract_walls: двери закрываются эрозией пола до разметки,
# отсек с несколькими подписями = одна зона, контуры по сетке 100 мм, дыры мебели заливаются.
# Режим «от стен»: листы, где заливка помещения = пол без мебели (Etalon Fotieva и похожие).
# Помещения строятся от стен: пол внутри здания минус стены, дверные проёмы закрываются морфологией,
# области с подписью — помещения, несколько подписей в области — деление водоразделом по расстоянию.
# Выход в той же схеме, что extract.extract (квартиры: rooms/rects, links, contour, checks).
import math, collections, os
import fitz
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from skimage.segmentation import watershed
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from extract import labels, is_pastel, path_polys, fill_key, poly_to_rects, FN, ENTRY_OK

PX = 2.0
WETW = ('балкон', 'патио', 'лоджия', 'терраса')


def dashed_lines(dr, color=0.502, min_n=3):
    """пунктир = ≥3 коротких серых отрезка на одной прямой с похожими длинами и промежутками"""
    segs = {'h': collections.defaultdict(list), 'v': collections.defaultdict(list)}
    for d in dr:
        if d['type'] != 's' or not d.get('color') or abs(d['color'][0] - color) > 0.02: continue
        for it in d['items']:
            if it[0] != 'l': continue
            a, b = it[1], it[2]
            if abs(a.y - b.y) < 0.05 and 0.8 < abs(a.x - b.x) < 6: segs['h'][round(a.y, 1)].append((min(a.x, b.x), max(a.x, b.x)))
            elif abs(a.x - b.x) < 0.05 and 0.8 < abs(a.y - b.y) < 6: segs['v'][round(a.x, 1)].append((min(a.y, b.y), max(a.y, b.y)))
    out = []
    for o, groups in segs.items():
        for c, ss in groups.items():
            ss.sort(); run = [ss[0]]
            for q in ss[1:] + [(1e9, 1e9)]:
                gap = q[0] - run[-1][1]
                if 0.3 < gap < 4 and abs((q[1] - q[0]) - (run[-1][1] - run[-1][0])) < 1: run.append(q); continue
                if len(run) >= min_n: out.append((o, c, run[0][0], run[-1][1]))
                run = [q]
    return out


def disk(r):
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


def extract(pdf, pno=0, door_mm=950):
    page = fitz.open(pdf)[pno]
    dr = page.get_drawings()
    labs, totals, wins = labels(page)
    room_paths = [d for d in dr if d['type'] == 'f' and is_pastel(d['fill'])]
    wall_paths = [d for d in dr if d['type'] == 'f' and d['fill'] and len(set(fill_key(d['fill'])[:3])) == 1 and d['fill'][0] <= 0.4]
    riser_paths = [d for d in dr if d['type'] == 'f' and d['fill'] and fill_key(d['fill'])[:3] in ((0.89, 0.89, 0.89),) and d['rect'].width < 12 and d['rect'].height < 12]
    if not room_paths or not labs or not wall_paths: return None
    xs = [v for d in room_paths for v in (d['rect'].x0, d['rect'].x1)]
    ys = [v for d in room_paths for v in (d['rect'].y0, d['rect'].y1)]
    X0, Y0, X1, Y1 = min(xs) - 30, min(ys) - 30, max(xs) + 30, max(ys) + 30
    W, H = int((X1 - X0) * PX) + 1, int((Y1 - Y0) * PX) + 1
    tp = lambda p: ((p[0] - X0) * PX, (p[1] - Y0) * PX)
    def raster(paths):
        im = Image.new('L', (W, H), 0); dd = ImageDraw.Draw(im)
        for d in paths:
            for p in path_polys(d):
                if len(p) >= 3: dd.polygon([tp(q) for q in p], fill=255)
        return np.array(im) > 0
    Wm = raster(wall_paths)
    if os.environ.get('WALL_STROKES'):  # перегородки контуром: чёрные линии толщиной ≥ 0.27
        im = Image.new('L', (W, H), 0); dd = ImageDraw.Draw(im)
        for d in dr:
            closed = d.get('closePath') or any(it[0] in ('re', 'qu') for it in d['items'])
            if d['type'] == 's' and closed and d.get('color') and max(d['color'][:3]) <= 0.05 and (d.get('width') or 0) >= 0.27:
                for it in d['items']:
                    if it[0] == 'l': dd.line([tp((it[1].x, it[1].y)), tp((it[2].x, it[2].y))], fill=255, width=2)
                    elif it[0] == 're':
                        r_ = it[1]; dd.rectangle([tp((r_.x0, r_.y0)), tp((r_.x1, r_.y1))], outline=255, width=2)
        Wm |= np.array(im) > 0
    Fm = np.zeros((H, W), bool)  # пол квартир: заливки помещений (с вырезами под мебель) → закрытие + заливка дыр
    for d in room_paths:
        Fm |= raster([d])
    # грубый масштаб по подписям, чтобы задать размеры в пикселях (уточним ниже)
    # квартирные стены ~ 100–300 мм; на листах IND 1 ед. ≈ 35–80 мм → берём из подписей позже
    lab_pts = [(l, tp(l['pt'])) for l in labs]
    # пол: заливки + мебель внутри них (дыры) + выемки у стен (закрытие до стены)
    floor0 = ndi.binary_fill_holes(Fm | Wm) & ~Wm
    # первая оценка масштаба: площади областей без закрытия дверей
    reg0, n0 = ndi.label(floor0)
    ratios = []
    cnt0 = collections.Counter(reg0[int(y), int(x)] for _, (x, y) in lab_pts if 0 <= int(y) < H and 0 <= int(x) < W)
    sizes0 = np.bincount(reg0.ravel())
    for l, (x, y) in lab_pts:
        if not (0 <= int(y) < H and 0 <= int(x) < W): continue
        k = reg0[int(y), int(x)]
        if k and cnt0[k] == 1 and not any(w in l['fn'].lower() for w in WETW):
            ratios.append(l['area'] / (sizes0[k] / PX / PX))
    if not ratios:  # пол связан целиком (двери открыты) → грубо по заливкам с одной подписью
        for d in room_paths:
            ps = path_polys(d)
            inside = [l for l in labs if any(Polygon(p).buffer(0).contains(Point(*l['pt'])) for p in ps if len(p) >= 3)]
            if len(inside) == 1 and not any(w in inside[0]['fn'].lower() for w in WETW):
                a_u = d['rect'].width * d['rect'].height
                if a_u > 0: ratios.append(inside[0]['area'] / a_u)
    if not ratios: return None
    k0 = sorted(ratios)[len(ratios) // 2]; mm = math.sqrt(k0) * 1000
    # пол квартир: заливки + выемки под мебель (закрытие ~700 мм) + дыры, без стен
    lim = (2500 / mm) ** 2  # мебель: белые заливки до ~6 м²
    furn = [d for d in dr if d['type'] == 'f' and d['fill'] and fill_key(d['fill'])[:3] == (1.0, 1.0, 1.0) and (800 / mm) ** 2 < d['rect'].width * d['rect'].height < lim]
    Fu = raster(furn) & ndi.binary_dilation(Fm, iterations=int(1500 / mm * PX))
    rf = max(2, int(300 / mm * PX))
    base_ = Fm | Fu
    floor = ndi.binary_fill_holes((ndi.binary_closing(base_, structure=disk(rf)) | base_) & ~Wm) & ~Wm
    markers = np.zeros((H, W), np.int32); lab_of = {}
    for i, (l, (x, y)) in enumerate(lab_pts, 1):
        xi, yi = int(x), int(y)
        if 0 <= yi < H and 0 <= xi < W and floor[yi, xi]:
            markers[max(0, yi - 1):yi + 2, max(0, xi - 1):xi + 2] = i; lab_of[i] = l
    # пунктир зон (кухня|гостиная, коридор|прихожая): мягкая граница — делит зоны, но не стена
    dm = Image.new('L', (W, H), 0); ddm = ImageDraw.Draw(dm)
    for o, c, a0, a1 in dashed_lines(dr):
        pts = [tp((a0, c)), tp((a1, c))] if o == 'h' else [tp((c, a0)), tp((c, a1))]
        ddm.line(pts, fill=255, width=2)
    Dm = np.array(dm) > 0
    dist = ndi.distance_transform_edt(floor & ~Dm)
    comp, _ = ndi.label(floor)
    # отсеки: пол, сжатый на ~520 мм (двери ≤ 1 м закрываются), подписи внутри → один маркер на отсек
    er = max(2, int(round(520 / mm * PX)))
    core = dist > er
    cl, ncl = ndi.label(core)
    zone_labs = collections.defaultdict(list)
    for i, l in lab_of.items():
        x, y = lab_pts[i - 1][1]; xi, yi = int(x), int(y)
        c = cl[yi, xi]
        if not c:  # подпись в узком месте (гардероб, тамбур) — ближайший отсек в радиусе 0.6 м, иначе свой маркер
            win = cl[max(0, yi - er):yi + er + 1, max(0, xi - er):xi + er + 1]
            cs = win[win > 0]
            c = int(np.bincount(cs).argmax()) if len(cs) else -i
        zone_labs[c].append(i)
    mk = np.zeros((H, W), np.int32); zone_of = {}
    for z, (c, ids) in enumerate(zone_labs.items(), 1):
        if c > 0: mk[cl == c] = z
        else: mk[markers == ids[0]] = z
        zone_of[z] = ids
    seg = watershed(-dist, mk, mask=floor & np.isin(comp, np.unique(comp[mk > 0])))
    rooms = []
    # отсек с несколькими подписями (открытая планировка без стены/пунктира) → делим между подписями,
    # части связаны проёмом; площадь проверяется по сумме группы (zid по open)
    if os.environ.get('SPLIT', '1') == '1':
        nz = max(zone_of) + 1; new_zone = {}
        for z, ids in list(zone_of.items()):
            if len(ids) < 2 or any(any(w in lab_of[i]['fn'].lower() for w in WETW) for i in ids): new_zone[z] = ids; continue
            zm = seg == z; sd = np.zeros((H, W), np.int32)
            for i in ids:
                x, y = lab_pts[i - 1][1]; xi, yi = int(x), int(y)
                sd[max(0, yi - 2):yi + 3, max(0, xi - 2):xi + 3] = nz
                sd[~zm] = 0; new_zone[nz] = [i]; nz += 1
            sub = watershed(np.zeros((H, W)), sd, mask=zm)
            seg[zm] = sub[zm]
        zone_of = new_zone
    for z, ids in zone_of.items():
        m = ndi.binary_fill_holes(seg == z)
        if not m.any(): continue
        ls = [lab_of[i] for i in ids]
        wet = [l for l in ls if any(w in l['fn'].lower() for w in WETW)]
        main = max(ls, key=lambda l: l['area'])
        lab = dict(main)
        if len(ls) > 1:
            lab['area'] = round(sum(l['area'] for l in ls), 2); lab['merged'] = [l['fn'] for l in ls]
        rooms.append({'k': z, 'lab': lab, 'mask': m, 'area_px': int(m.sum())})
    # пустоты под сантехникой/мебелью у стен (не стена, не пол, < 3 м², не у края листа) → соседней комнате
    S0 = np.zeros((H, W), np.int32)
    for r in rooms: S0[r['mask']] = r['k']
    vl, nv = ndi.label((S0 == 0) & ~Wm)
    vsz = np.bincount(vl.ravel())
    edge_ids = set(np.unique(np.concatenate([vl[0], vl[-1], vl[:, 0], vl[:, -1]])))
    lim_px = 3.0 / (k0 / PX / PX)
    rk = {r['k']: r for r in rooms}
    for c, sl in enumerate(ndi.find_objects(vl), 1):
        if c in edge_ids or vsz[c] > lim_px: continue
        sl2 = tuple(slice(max(0, q.start - 3), q.stop + 3) for q in sl)
        sub = vl[sl2] == c
        ring = ndi.binary_dilation(sub, iterations=3) & ~sub
        nb = S0[sl2][ring]; nb = nb[nb > 0]
        if not len(nb): continue
        k = int(np.bincount(nb).argmax())
        rk[k]['mask'][sl2] |= sub
    for r in rooms: r['area_px'] = int(r['mask'].sum())
    WET = lambda r: any(w in r['lab']['fn'].lower() for w in WETW)
    ks = sorted(r['lab']['area'] / (r['area_px'] / PX / PX) for r in rooms if not WET(r))
    kmed = ks[len(ks) // 2]; mm = math.sqrt(kmed) * 1000
    for r in rooms:
        r['area_calc'] = r['area_px'] / PX / PX * kmed; r['dev'] = r['area_calc'] / r['lab']['area'] - 1
    rmap = {r['k']: r for r in rooms}
    S = np.zeros((H, W), np.int32)
    for r in rooms: S[r['mask']] = r['k']
    L = lambda npx: npx / PX * mm
    bld = ndi.binary_fill_holes(ndi.binary_closing(Wm | Fm, structure=np.ones((3, 3)), iterations=int(3000 / mm * PX / 2)))
    free = ~Wm & ~floor
    # стыки помещений (водораздел прошёл по проёму): длина ≤ 1000 мм — дверь, больше — проём
    arc = Image.new('L', (W, H), 0); da = ImageDraw.Draw(arc)
    for d in dr:
        if d['type'] == 's' and d.get('color') and fill_key(d['color'])[:3] == (0.86, 0.86, 0.86):
            for it in d['items']:
                if it[0] == 'l': da.line([tp((it[1].x, it[1].y)), tp((it[2].x, it[2].y))], fill=255, width=2)
                elif it[0] == 'c': da.line([tp((it[1].x, it[1].y)), tp((it[4].x, it[4].y))], fill=255, width=2)
    arcd = ndi.distance_transform_edt(~(np.array(arc) > 0)) / PX * mm  # мм до ближайшей дуги
    have_arcs = bool((np.array(arc) > 0).any())
    tot = collections.Counter(); near_arc = collections.Counter()
    for sh in ((0, 1), (1, 0)):
        A = S[:H - sh[0], :W - sh[1]]; B = S[sh[0]:, sh[1]:]
        m = (A != B) & (A > 0) & (B > 0)
        ad = arcd[:H - sh[0], :W - sh[1]]
        for u, v, dd_ in zip(A[m], B[m], ad[m]):
            key = (min(int(u), int(v)), max(int(u), int(v))); tot[key] += 1
            if dd_ <= 250: near_arc[key] += 1
    edges = []
    for (a_, b_), cnt in tot.items():
        ln = L(cnt)
        if ln < 450: continue
        if WET(rmap[a_]) or WET(rmap[b_]): kind = 'balcony'
        elif have_arcs:
            kind = 'door' if near_arc[(a_, b_)] > 2 else 'open'
            wet_ = any(FN.get(rmap[x]['lab']['fn'].lower(), 'room') in ('bath', 'wc', 'laundry') for x in (a_, b_))
            if kind == 'open' and wet_: continue  # к санузлу без дуги двери — это стена, нарисованная не заливкой
        else: kind = 'door' if ln <= 1000 else 'open'
        edges.append((a_, b_, kind, round(ln)))
    # разрывы к свободному: МОП (внутри здания) — вход, улица — окно
    gapm = np.zeros((H, W), bool); groom = np.zeros((H, W), np.int32)
    for sh in ((0, 1), (1, 0), (0, -1), (-1, 0)):
        Sf = np.roll(free, sh, axis=(0, 1))
        m = (S > 0) & Sf
        gapm |= m; groom[m] = S[m]
    fl, nf = ndi.label(free)
    fsz = np.bincount(fl.ravel()) / PX / PX * kmed  # м² свободных областей
    big_free = np.zeros(nf + 1, bool); big_free[1:] = fsz[1:] > 4.0
    gl, ng = ndi.label(ndi.binary_dilation(gapm, iterations=1))
    windows_px = []
    rad = int(1200 / mm * PX)
    for c, sl in enumerate(ndi.find_objects(gl), 1):
        sub = (gl[sl] == c) & gapm[sl]
        if not sub.any(): continue
        yy, xx = np.nonzero(sub); ln = L(max(np.ptp(xx), np.ptp(yy)) + 1)
        if ln < 450: continue
        k = int(np.bincount(groom[sl][sub]).argmax())
        y0, y1 = max(sl[0].start - rad, 0), min(sl[0].stop + rad, H); x0, x1 = max(sl[1].start - rad, 0), min(sl[1].stop + rad, W)
        outside = (~bld[y0:y1, x0:x1]).mean()
        item = {'k': k, 'cx': xx.mean() + sl[1].start, 'cy': yy.mean() + sl[0].start, 'w': round(ln / 10) * 10}
        if outside > 0.02: windows_px.append(item)
        elif 600 <= ln <= 1600 and FN.get(rmap[k]['lab']['fn'].lower(), 'room') in ENTRY_OK:
            nb = fl[y0:y1, x0:x1]; ids = np.unique(nb[nb > 0])
            if any(big_free[i] and (~bld[y0:y1, x0:x1]).mean() == 0 for i in ids): edges.append(('MOP', k, 'entry', round(ln)))
    # квартиры
    adj = collections.defaultdict(set)
    for a, b, kind, _ in edges:
        if a != 'MOP' and kind != 'balcony': adj[a].add(b); adj[b].add(a)
    seen, apts = set(), []
    for r in rooms:
        if r['k'] in seen or WET(r): continue
        st, comp = [r['k']], []
        while st:
            u = st.pop()
            if u in seen: continue
            seen.add(u); comp.append(u); st += list(adj[u])
        apts.append(sorted(comp))
    result = []
    to_mm = lambda x, y: (x / PX * mm, (H - y) / PX * mm)  # Y вверх
    for comp in apts:
        rs = [rmap[k] for k in comp]
        living = [r for r in rs if not WET(r)]
        s_lab = round(sum(r['lab']['area'] for r in living), 2)
        zid = {r['k']: r['k'] for r in living}  # зоны, связанные проёмами
        def fz(x):
            while zid[x] != x: x = zid[x]
            return x
        for a_, b_, kind, _ in edges:
            if kind == 'open' and a_ in zid and b_ in zid: zid[fz(a_)] = fz(b_)
        zs = collections.defaultdict(lambda: [0.0, 0.0])
        for r in living: zs[fz(r['k'])][0] += r['lab']['area']; zs[fz(r['k'])][1] += r['area_calc']
        ok_area = all(abs(g / l - 1) <= float(os.environ.get('ZTOL', '0.15')) for l, g in zs.values())
        zdev = sorted(round(g / l - 1, 2) for l, g in zs.values())
        rid_of, cnt = {}, collections.Counter()
        for r in rs:
            base = FN.get(r['lab']['fn'].lower().replace('ё', 'е'), 'room'); cnt[base] += 1
            rid_of[r['k']] = base if cnt[base] == 1 else f'{base}{cnt[base]}'
        # маска → прямоугольники (сетка 50 мм)
        g = max(1, int(round(100 / mm * PX)))
        allm = np.zeros((H, W), bool)
        for r in living: allm |= r['mask']
        yy, xx = np.nonzero(allm); ox, oy = xx.min(), yy.max()
        out_rooms = []
        for r in rs:
            # клетка g×g = пол, если покрыта > 50% (прореживание [::g] теряло строки на тонких щелях мебели)
            mm_ = ndi.binary_fill_holes(ndi.binary_closing(r['mask'], structure=disk(max(1, g // 2))) | r['mask'])
            hh, ww = (H // g) * g, (W // g) * g
            m = mm_[:hh, :ww].reshape(hh // g, g, ww // g, g).mean(axis=(1, 3)) > 0.5
            rects = []
            for j in range(m.shape[0]):
                row = m[j]; i = 0
                while i < len(row):
                    if not row[i]: i += 1; continue
                    k2 = i
                    while k2 + 1 < len(row) and row[k2 + 1]: k2 += 1
                    x0m, y1m = to_mm(i * g, j * g); x1m, y0m = to_mm((k2 + 1) * g, (j + 1) * g)
                    rects.append([x0m, y0m, x1m, y1m]); i = k2 + 1
            # слить полосы с одинаковыми x
            rects.sort(key=lambda q: (q[0], q[2], q[1])); merged = []
            for q in rects:
                if merged and abs(merged[-1][0] - q[0]) < 1 and abs(merged[-1][2] - q[2]) < 1 and abs(merged[-1][3] - q[1]) < 1: merged[-1][3] = q[3]
                else: merged.append(list(q))
            bx, by = to_mm(ox, oy)
            merged = [[round((q[0] - bx) / 10) * 10, round((q[1] - by) / 10) * 10, round((q[2] - bx) / 10) * 10, round((q[3] - by) / 10) * 10] for q in merged
                      if (q[2] - q[0]) >= 250 and (q[3] - q[1]) >= 250]
            out_rooms.append({'id': rid_of[r['k']], 'fn': r['lab']['fn'], 'merged': r['lab'].get('merged'), 'area': r['lab']['area'], 'area_geom': round(r['area_calc'], 2), 'rects': merged})
        es = []
        for a, b, kind, w in edges:
            if a == 'MOP' and b in rid_of: es.append({'between': ['MOP', rid_of[b]], 'type': 'entry'})
            elif a in rid_of and b in rid_of: es.append({'between': [rid_of[a], rid_of[b]], 'type': kind, 'w': w})
        bx, by = to_mm(ox, oy)
        wins_o = [{'room': rid_of[w['k']], 'at': [round((to_mm(w['cx'], w['cy'])[0] - bx) / 10) * 10, round((to_mm(w['cx'], w['cy'])[1] - by) / 10) * 10], 'w': w['w']}
                  for w in windows_px if w['k'] in rid_of and not WET(rmap[w['k']])]
        U = unary_union([Polygon([(q[0], q[1]), (q[2], q[1]), (q[2], q[3]), (q[0], q[3])]) for o in out_rooms if o['id'].rstrip('0123456789') not in ('balcony', 'patio') for q in o['rects']])
        U = U.buffer(80, join_style=2).buffer(-80, join_style=2).simplify(30)
        if U.geom_type != 'Polygon': U = max(U.geoms, key=lambda g_: g_.area)
        outer = [[round(x / 10) * 10, round(y / 10) * 10] for x, y in list(U.exterior.coords)[:-1]]
        ris = []
        for d in riser_paths:
            c = d['rect']; x, y = tp(((c.x0 + c.x1) / 2, (c.y0 + c.y1) / 2)); x, y = to_mm(x, y); x -= bx; y -= by
            if U.buffer(400).contains(Point(x, y)): ris.append([round(x / 10) * 10, round(y / 10) * 10])
        ent = [l for l in es if l['type'] == 'entry']
        gg = collections.defaultdict(set)
        for l in es:
            if l['type'] in ('door', 'open'): gg[l['between'][0]].add(l['between'][1]); gg[l['between'][1]].add(l['between'][0])
        reach = set()
        if ent:
            st = [ent[0]['between'][1]]
            while st:
                u = st.pop()
                if u in reach: continue
                reach.add(u); st += list(gg[u])
        liv_ids = [rid_of[r['k']] for r in living]
        checks = {'entries': len(ent), 'unreached': [i for i in liv_ids if i not in reach],
                  'no_window': [i for i in liv_ids if i.startswith(('bed', 'kl', 'living')) and not any(w['room'] == i for w in wins_o)],
                  'area_total_ok': ok_area, 'zone_dev': zdev}
        sus = [l['between'] for l in es if l['type'] == 'open' and any(x.rstrip('0123456789') in ('bath', 'wc', 'laundry') for x in l['between'])]
        checks['suspicious_open'] = sus
        LIVE, PASS = ('кухня', 'гостин'), ('прихож', 'коридор', 'холл')
        mz = [r['lab']['merged'] for r in living if r['lab'].get('merged')]
        checks['merged_zones'] = mz
        bad_mz = [m for m in mz if any(any(w in x.lower() for w in LIVE) for x in m) and any(any(w in x.lower() for w in PASS) for x in m)]
        checks['ok'] = checks['entries'] == 1 and not checks['unreached'] and ok_area and not sus and not bad_mz
        result.append({'geom': 'ok' if all(abs(z) <= 0.10 for z in zdev) else 'approx', 'contour': {'outer': outer, 'windows': wins_o, 'risers': ris}, 'rooms': out_rooms, 'links': es, 'checks': checks,
                       'area_rooms': s_lab, 'area_geom': round(sum(r['area_calc'] for r in living), 2), 'total_on_sheet': None, 'check_total': ok_area})
    meta = {'mode': 'floor', 'mm_per_unit': round(mm, 2), 'rooms_found': len(rooms), 'labels': len(labs), 'room_fills': len(room_paths),
            'labels_in_one_fill': [], 'risers': len(riser_paths), 'windows_text': len(wins), 'totals_on_sheet': totals,
            'area_dev_max': round(max(abs(r['dev']) for r in rooms if not WET(r)), 3)}
    dbg = {'R': S, 'W': Wm, 'rooms': rooms, 'edges': edges, 'tp': tp, 'apts': apts}
    return {'meta': meta, 'apartments': result}, dbg
