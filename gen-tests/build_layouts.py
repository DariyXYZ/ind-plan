# Планировки из layouts.py → перегородки по границам комнат + проверка правил → layouts.json для /test
# Правила: методичка IND (Курилова) + эргономика зон действия (проходы у кровати, стулья, фронт шкафа и кухни).
import json, math, os, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location('lay', os.path.join(HERE, 'layouts.py')); lay = importlib.util.module_from_spec(sp); sp.loader.exec_module(lay)
C = {c['id']: c for c in json.load(open(os.path.join(HERE, 'contours.json'), encoding='utf-8'))}
FC = {'bed': (1600, 2000), 'sbed': (900, 2000), 'sofa': (2200, 950), 'dining': (1200, 1700), 'desk': (1200, 1100), 'coffee': (900, 500),
      'wardrobe': (1800, 600), 'base': (600, 600), 'hob': (600, 600), 'sink': (600, 600), 'fridge': (600, 650), 'washer': (600, 600),
      'wc': (380, 650), 'bidet': (360, 560), 'basin': (500, 450), 'bath': (1700, 700), 'shower': (900, 900)}
NAME = {'bed': 'кровать', 'sbed': 'кровать', 'sofa': 'диван', 'dining': 'стол со стульями', 'desk': 'рабочий стол', 'coffee': 'столик',
        'wardrobe': 'шкаф', 'base': 'кухня', 'hob': 'плита', 'sink': 'мойка', 'fridge': 'холодильник', 'washer': 'стиралка',
        'wc': 'унитаз', 'bidet': 'биде', 'basin': 'раковина', 'bath': 'ванна', 'shower': 'душ'}
PT = 100
WET = ('Ванная', 'Санузел', 'Мастер-санузел', 'Постирочная')
LIVE = ('Спальня', 'Спальня 2', 'Детская', 'Мастер-спальня', 'Гостевая', 'Кабинет', 'Кухня-гостиная')
FREE = ('dining', 'coffee', 'wc', 'basin', 'bidet')   # стоят посреди комнаты или подвесные — щели не считаем          # стоят посреди комнаты — щели к ним не считаем

def inpoly(P, x, y):
    c = False
    for i in range(len(P)):
        (x1, y1), (x2, y2) = P[i], P[(i + 1) % len(P)]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1): c = not c
    return c

def room_at(rooms, x, y):
    for n, rs in rooms.items():
        for a, b, c, d in rs:
            if a <= x <= c and b <= y <= d: return n
    return None

def edge_t(c, x1, y1, x2, y2):
    P = c['poly']
    for i in range(len(P)):
        (a, b), (e, f) = P[i], P[(i + 1) % len(P)]
        if a == e == x1 == x2 and min(max(y1, y2), max(b, f)) - max(min(y1, y2), min(b, f)) > abs(y2 - y1) / 2: return c['ts'][i]
        if b == f == y1 == y2 and min(max(x1, x2), max(a, e)) - max(min(x1, x2), min(a, e)) > abs(x2 - x1) / 2: return c['ts'][i]
    return None

def walls(c, rooms):
    xs = sorted({v for rs in rooms.values() for r in rs for v in (r[0], r[2])} | {p[0] for p in c['poly']})
    ys = sorted({v for rs in rooms.values() for r in rs for v in (r[1], r[3])} | {p[1] for p in c['poly']})
    cell, errs = {}, []
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            cx, cy = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            if not inpoly(c['poly'], cx, cy): cell[i, j] = '#out'; continue
            n = room_at(rooms, cx, cy)
            if n is None: errs.append(f'пустое место {xs[i]}..{xs[i+1]} × {ys[j]}..{ys[j+1]}'); n = '#none'
            cell[i, j] = n
    segs = []
    for i in range(len(xs) - 2):
        for j in range(len(ys) - 1):
            a, b = cell[i, j], cell[i + 1, j]
            if '#out' not in (a, b) and a != b: segs.append(('v', xs[i + 1], ys[j], ys[j + 1]))
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 2):
            a, b = cell[i, j], cell[i, j + 1]
            if '#out' not in (a, b) and a != b: segs.append(('h', ys[j + 1], xs[i], xs[i + 1]))
    segs.sort(); out = []
    for s in segs:
        if out and out[-1][0] == s[0] and out[-1][1] == s[1] and out[-1][3] == s[2]: out[-1] = (s[0], s[1], out[-1][2], s[3])
        else: out.append(s)
    return [(k, a, k, b) if o == 'v' else (a, k, b, k) for o, k, a, b in out if b - a >= 150], errs

def inner_rect(c, r, rooms, n):
    a, b, cc, d = r
    def off(x1, y1, x2, y2):
        t = edge_t(c, x1, y1, x2, y2)
        if t: return t / 2
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2; dx, dy = (0, 10) if y1 == y2 else (10, 0)
        if any(room_at(rooms, mx + k * dx, my + k * dy) == n and not (a < mx + k * dx < cc and b < my + k * dy < d) for k in (1, -1)): return 0
        return PT / 2
    return (a + off(a, b, a, d), b + off(a, b, cc, b), cc - off(cc, b, cc, d), d - off(a, d, cc, d))

def dims(f):
    w, d = FC[f[0]]
    if len(f) > 4 and f[4]: w = f[4]
    if len(f) > 5 and f[5]: d = f[5]
    return w, d

def frame(f):
    r = f[3]; ux, uy = round(math.cos(math.radians(r))), round(math.sin(math.radians(r)))
    return (ux, uy), (-uy, ux)

def lrect(f, s0, s1, q0, q1):
    """прямоугольник в осях мебели: s — вдоль задней грани от базы, q — от стены в комнату"""
    (ux, uy), (nx, ny) = frame(f); x, y = f[1], f[2]
    pts = [(x + ux * s + nx * q, y + uy * s + ny * q) for s in (s0, s1) for q in (q0, q1)]
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))

def body(f):
    w, d = dims(f); return lrect(f, -w / 2, w / 2, 0, d)

def zones(f, room=''):
    """зоны действия: [(название, прямоугольник, 1 — обязательна, 2 — хотя бы одна из)]"""
    k = f[0]; w, d = dims(f)
    if k == 'bed': return [('проход сбоку', lrect(f, -w / 2 - 600, -w / 2, 0, d), 1), ('проход сбоку', lrect(f, w / 2, w / 2 + 600, 0, d), 1),
                           ('проход в ногах', lrect(f, -w / 2, w / 2, d, d + 600), 1)]
    if k == 'sbed': return [('проход сбоку', lrect(f, -w / 2 - 600, -w / 2, 0, d), 2), ('проход сбоку', lrect(f, w / 2, w / 2 + 600, 0, d), 2)]
    if k == 'wardrobe':  # 700 — открыть дверцы и переодеться; углы (по 450) — общие с соседним шкафом в угловой сборке
        i = min(650, w / 3); return [('место перед шкафом', lrect(f, -w / 2 + i, w / 2 - i, d, d + 700), 1)]
    if k == 'dining': return [('место отодвинуть стулья', lrect(f, -w / 2, w / 2, -500, 0), 1), ('место отодвинуть стулья', lrect(f, -w / 2, w / 2, d, d + 500), 1)]
    if k == 'desk': return [('место для стула', lrect(f, -w / 2, w / 2, d, d + 400), 1)]
    if k == 'sofa': return [('место для ног', lrect(f, -w / 2, w / 2, d, d + 400), 1)]
    if k in ('base', 'hob', 'sink'): return [('рабочая зона кухни', lrect(f, -w / 2, w / 2, d, d + (1000 if room == 'Кухня-гостиная' else 600)), 1)]
    if k == 'fridge': return [('дверь холодильника', lrect(f, -w / 2, w / 2, d, d + 900), 1)]
    if k in ('washer', 'basin', 'shower'): return [('место перед', lrect(f, -w / 2, w / 2, d, d + 600), 1)]
    if k in ('wc', 'bidet'): return [('место перед унитазом', lrect(f, -350, 350, d, d + 600), 1)]
    if k == 'bath': return [('место у ванны', lrect(f, -w / 2, w / 2, d, d + 600), 1)]
    return []

def ov(a, b, tol=2):
    return a[0] < b[2] - tol and b[0] < a[2] - tol and a[1] < b[3] - tol and b[1] < a[3] - tol

def door_geom(c, rooms, W, d):
    """распашка (None у раздвижной), проём ±550 по обе стороны, сторона открывания"""
    x, y, w, into = d[:4]; sl = len(d) > 5 and d[5] == 'sl'
    for x1, y1, x2, y2 in W + [(p[0], p[1], q[0], q[1]) for p, q in zip(c['poly'], c['poly'][1:] + c['poly'][:1])]:
        if x1 == x2 == x and min(y1, y2) <= y <= max(y1, y2):
            s = 1 if room_at(rooms, x + 200, y) == into else -1 if room_at(rooms, x - 200, y) == into else 0
            if not s: return None, None, 'дверь не между нужными комнатами', None
            f = x + s * PT / 2
            return (None if sl else (min(f, f + s * w), y - w / 2, max(f, f + s * w), y + w / 2)), (x - 550, y - w / 2, x + 550, y + w / 2), None, (s, 0)
        if y1 == y2 == y and min(x1, x2) <= x <= max(x1, x2):
            s = 1 if room_at(rooms, x, y + 200) == into else -1 if room_at(rooms, x, y - 200) == into else 0
            if not s: return None, None, 'дверь не между нужными комнатами', None
            f = y + s * PT / 2
            return (None if sl else (x - w / 2, min(f, f + s * w), x + w / 2, max(f, f + s * w))), (x - w / 2, y - 550, x + w / 2, y + 550), None, (0, s)
    return None, None, 'нет стены под дверью', None

CORR = ('Прихожая', 'Коридор', 'Холл')

def door_hinge(c, rooms, W, d, bodies=()):
    """(комната с другой стороны, направление петель (hx, hy), зазор от петли до стены в мм)"""
    x, y, w, into = d[:4]
    segs = [(x1, y1, x2, y2, PT) for x1, y1, x2, y2 in W] + \
           [(p[0], p[1], q[0], q[1], t) for p, q, t in zip(c['poly'], c['poly'][1:] + c['poly'][:1], c['ts'])] +            [e for a, b, cc, dd in bodies for e in ((a, b, cc, b, 0), (a, dd, cc, dd, 0), (a, b, a, dd, 0), (cc, b, cc, dd, 0))]
    vert = any(x1 == x2 == x and min(y1, y2) <= y <= max(y1, y2) for x1, y1, x2, y2 in W + [(p[0], p[1], q[0], q[1]) for p, q in zip(c['poly'], c['poly'][1:] + c['poly'][:1])])
    if vert:
        s_ = 1 if room_at(rooms, x + 200, y) == into else -1
        other = room_at(rooms, x - s_ * 200, y)
        best = None
        for hd in (-1, 1):
            ye = y + hd * w / 2; g = None
            for x1, y1, x2, y2, t in segs:
                if y1 == y2 and (y1 - ye) * hd >= 0:
                    lo, hi = sorted((x, x + s_ * w))
                    if min(x1, x2) < hi - 1 and max(x1, x2) > lo + 1:
                        gg = abs(y1 - ye) - t / 2
                        g = gg if g is None else min(g, gg)
            if g is not None and (best is None or g < best[1]): best = ((0, hd), g)
    else:
        s_ = 1 if room_at(rooms, x, y + 200) == into else -1
        other = room_at(rooms, x, y - s_ * 200)
        best = None
        for hd in (-1, 1):
            xe = x + hd * w / 2; g = None
            for x1, y1, x2, y2, t in segs:
                if x1 == x2 and (x1 - xe) * hd >= 0:
                    lo, hi = sorted((y, y + s_ * w))
                    if min(y1, y2) < hi - 1 and max(y1, y2) > lo + 1:
                        gg = abs(x1 - xe) - t / 2
                        g = gg if g is None else min(g, gg)
            if g is not None and (best is None or g < best[1]): best = ((hd, 0), g)
    if best is None: best = (((0, 1) if vert else (1, 0)), 9999)
    return other, best[0], round(best[1])

def obst(c, V):
    return [body(f) for f in V['furn']] + [(x - 130, y - 130, x + 130, y + 130) for x, y in c['ris']] + [(x, y, x + w, y + h) for x, y, w, h in c['pyl']]

def place_doors(c, V, W):
    """достройка дверей: из коридора — внутрь комнаты; петли у угла, створка к стене; без мебели под распашкой"""
    rooms = V['rooms']; out = []
    bodies = obst(c, V)
    polyW = W + [(p[0], p[1], q[0], q[1]) for p, q in zip(c['poly'], c['poly'][1:] + c['poly'][:1])]
    for d in V['doors']:
        d = list(d)
        sl = len(d) > 5 and d[5] == 'sl'
        x, y, w, into = d[:4]
        vert = any(x1 == x2 == x and min(y1, y2) <= y <= max(y1, y2) for x1, y1, x2, y2 in polyW)
        def side_rooms(xx, yy, sgn):
            return (room_at(rooms, xx + 200 * sgn, yy), room_at(rooms, xx - 200 * sgn, yy)) if vert else (room_at(rooms, xx, yy + 200 * sgn), room_at(rooms, xx, yy - 200 * sgn))
        sgn = 1 if side_rooms(x, y, 1)[0] == into else -1
        other = side_rooms(x, y, sgn)[1]
        if into in CORR and other not in CORR:
            into, other, sgn = other, into, -sgn; d[3] = into
        if not sl:
            best = None
            for k in range(-80, 81):
                t0 = k * 25
                nx, ny = (x, y + t0) if vert else (x + t0, y)
                if not all(side_rooms(*((nx, ny + t) if vert else (nx + t, ny)), sgn) == (into, other) for t in (-w / 2 + 20, 0, w / 2 - 20)):
                    continue
                dd = (nx, ny, w, into) + tuple(d[4:])
                sw, cl, e, _ = door_geom(c, rooms, W, dd)
                if e: continue
                conf = sum(1 for b in bodies if (sw and ov(b, sw, 10)) or ov(b, cl, 10))
                g = door_hinge(c, rooms, W, dd, bodies)[2]
                sc = (conf, 0 if g <= 300 else 1, g if g > 300 else 0, abs(t0))
                if best is None or sc < best[0]: best = (sc, nx, ny)
            if best: d[0], d[1] = round(best[1]), round(best[2])
        out.append(tuple(d))
    V['doors'] = out

def check(cid, V):
    c = C[cid]; rooms = V['rooms']; W, errs = walls(c, rooms); warn = []
    place_doors(c, V, W)
    INN = {n: [inner_rect(c, r, rooms, n) for r in rs] for n, rs in rooms.items()}
    pyl = [(x, y, x + w, y + h) for x, y, w, h in c['pyl']] + [(x - 130, y - 130, x + 130, y + 130) for x, y in c['ris']]  # стояк в коробе — тоже препятствие
    SEG = [(x1, y1, x2, y2, PT / 2) for x1, y1, x2, y2 in W] + \
          [(p[0], p[1], q[0], q[1], t / 2) for p, q, t in zip(c['poly'], c['poly'][1:] + c['poly'][:1], c['ts'])]
    def dseg(px, py, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1; L2 = dx * dx + dy * dy or 1; t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L2))
        return math.hypot(px - x1 - t * dx, py - y1 - t * dy)
    def inside(n, px, py):  # точно: в комнате по осям и не ближе полутолщины к любой стене
        return room_at(rooms, px, py) == n and all(dseg(px, py, *sg[:4]) >= sg[4] - 3 for sg in SEG)
    def rect_in(n, b): return all(inside(n, px, py) for px in (b[0], (b[0] + b[2]) / 2, b[2]) for py in (b[1], (b[1] + b[3]) / 2, b[3]))
    for n, rs in rooms.items():
        ir = INN[n]; area = sum((r[2] - r[0]) * (r[3] - r[1]) for r in ir) / 1e6
        main = max(ir, key=lambda r: (r[2] - r[0]) * (r[3] - r[1])); wmin = min(main[2] - main[0], main[3] - main[1]) / 1000
        if n in LIVE and n != 'Кухня-гостиная' and wmin < 2.99: errs.append(f'{n}: ширина {wmin:.2f} м < 3,0')
        if n == 'Кухня-гостиная' and wmin < 3.09: errs.append(f'{n}: ширина {wmin:.2f} м < 3,1')
        if n in WET[:3] and area < 2.5: errs.append(f'{n}: {area:.1f} м² мало')
        if n == 'Прихожая':
            for r in ir[1:]:
                if min(r[2] - r[0], r[3] - r[1]) < 1090: errs.append(f'коридор {min(r[2]-r[0], r[3]-r[1]):.0f} мм < 1100')
        if n in LIVE:
            has = False
            for e, off, w in c['win']:
                (x1, y1), (x2, y2) = c['poly'][e], c['poly'][(e + 1) % len(c['poly'])]
                L = math.hypot(x2 - x1, y2 - y1); px, py = x1 + (x2 - x1) * off / L, y1 + (y2 - y1) * off / L
                has = has or any(a - 1 <= px <= cc + 1 and b - 1 <= py <= d + 1 for a, b, cc, d in rs)
            if not has: errs.append(f'{n}: нет окна')
        if n in WET:
            dmin = min(max(a - x, 0, x - cc) + max(b - y, 0, y - d) for x, y in c['ris'] for a, b, cc, d in rs)
            lim = 2000 if n == 'Постирочная' else 400
            if dmin > lim: errs.append(f'{n}: до стояка {dmin/1000:.1f} м')
    D = []
    for d in V['doors']:
        sw, cl, e, s = door_geom(c, rooms, W, d)
        if e: errs.append(f'дверь {d[:2]}: {e}')
        else:
            D.append((d, sw, cl))
            other, hv, gap = door_hinge(c, rooms, W, d, obst(c, V))
            sl = len(d) > 5 and d[5] == 'sl'
            if not sl and d[3] in CORR and other not in CORR:
                errs.append(f'дверь {d[:2]} ({other}) открывается в коридор — открывать внутрь комнаты')
            if not sl and gap > 300:
                errs.append(f'дверь {d[:2]}: петли не у стены, створка в {gap} мм от стены')
    for i in range(len(D)):
        for j in range(i + 1, len(D)):
            if D[i][1] and D[j][1] and ov(D[i][1], D[j][1], 10): errs.append(f'двери {D[i][0][:2]} и {D[j][0][:2]} бьются друг о друга')
    WB = []
    for e, off, w in c['win']:
        (x1, y1), (x2, y2) = c['poly'][e], c['poly'][(e + 1) % len(c['poly'])]
        L = math.hypot(x2 - x1, y2 - y1); ux, uy = (x2 - x1) / L, (y2 - y1) / L; nx, ny = -uy, ux; t = c['ts'][e] / 2
        px, py = x1 + ux * off, y1 + uy * off
        pts = [(px + ux * s + nx * q, py + uy * s + ny * q) for s in (-w / 2, w / 2) for q in (t, t + 300)]
        WB.append((min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)))
    F = []
    for f in V['furn']:
        b = body(f); cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2; n = room_at(rooms, cx, cy); nm = NAME[f[0]]
        if n is None: errs.append(f'{nm} {f[1:3]} вне комнат'); continue
        if not rect_in(n, b): errs.append(f'{n}: {nm} {f[1:3]} вылезает из комнаты')
        for p in pyl:
            if ov(b, p): errs.append(f'{n}: {nm} {f[1:3]} упирается в пилон или стояк')
        for g, gb, _ in F:
            if ov(b, gb): errs.append(f'{n}: {nm} пересекает {NAME[g[0]]}')
        for d, sw, cl in D:
            if sw and ov(b, sw, 10): errs.append(f'{n}: {nm} {f[1:3]} под распашкой двери')
            if ov(b, cl, 10): errs.append(f'{n}: {nm} {f[1:3]} загораживает проём')
        for wb in WB:
            if ov(b, wb, 5) and f[0] != 'desk': errs.append(f'{n}: {nm} {f[1:3]} ближе 300 мм к окну')
        F.append((f, b, n))
    bodies = [b for _, b, _ in F]
    for f, b, n in F:
        opt = [z for z in zones(f, n) if z[2] == 2]; ok_opt = False
        for nm, z, req in zones(f, n):
            bad = not rect_in(n, z) or any(ov(z, ob, 5) for ob in bodies if ob is not b) or any(ov(z, p, 5) for p in pyl)
            if req == 1 and bad: errs.append(f'{n}: {NAME[f[0]]} {f[1:3]} — нет места: {nm}')
            if req == 2 and not bad: ok_opt = True
        if opt and not ok_opt: errs.append(f'{n}: к кровати {f[1:3]} не подойти')
    hard = [b for f, b, n in F if f[0] not in FREE]
    for f, b, n in F:
        if f[0] in FREE: continue
        for side in range(4):
            for dd in range(10, 310, 10):
                pts = []
                for k in (0.1, 0.3, 0.5, 0.7, 0.9):
                    if side == 0: pts.append((b[0] - dd, b[1] + (b[3] - b[1]) * k))
                    if side == 1: pts.append((b[2] + dd, b[1] + (b[3] - b[1]) * k))
                    if side == 2: pts.append((b[0] + (b[2] - b[0]) * k, b[1] - dd))
                    if side == 3: pts.append((b[0] + (b[2] - b[0]) * k, b[3] + dd))
                blk = sum(1 for px, py in pts if not inside(n, px, py) or any(o[0] < px < o[2] and o[1] < py < o[3] for o in hard if o is not b) or any(p[0] < px < p[2] and p[1] < py < p[3] for p in pyl))
                if blk >= 2:
                    if 40 <= dd < 300: errs.append(f'{n}: щель {dd} мм у «{NAME[f[0]]}» {f[1:3]} — не убраться')
                    break
    sinks = [body(f) for f in V['furn'] if f[0] == 'sink']
    if sinks:
        s = sinks[0]; dmin = min(math.hypot((s[0] + s[2]) / 2 - x, (s[1] + s[3]) / 2 - y) for x, y in c['ris'])
        if dmin > 2500: warn.append(f'мойка в {dmin/1000:.1f} м от стояка')
    lab = []
    for n, rs in rooms.items():
        W_ = 145 * len(n) + 200; best = None
        for r in INN[n]:
            for x in range(int(r[0] + W_ / 2), int(r[2] - W_ / 2) + 1, 100):
                for y in range(int(r[1] + 350), int(r[3] - 300) + 1, 100):
                    box = (x - W_ / 2, y - 330, x + W_ / 2, y + 280)
                    if any(ov(box, ob, 0) for ob in bodies) or any(ov(box, p, 0) for p in pyl) or any(dd[1] and ov(box, dd[1], 0) for dd in D): continue
                    dist = min([math.hypot(x - (ob[0] + ob[2]) / 2, y - (ob[1] + ob[3]) / 2) for ob in bodies] + [1e5])
                    cen = math.hypot(x - (r[0] + r[2]) / 2, y - (r[1] + r[3]) / 2)
                    score = min(dist, 1500) - cen * 0.6 + (r[2] - r[0]) * (r[3] - r[1]) / 1e5
                    if best is None or score > best[0]: best = (score, x, y)
        if best is None:
            r = max(rs, key=lambda r: (r[2] - r[0]) * (r[3] - r[1])); best = (0, (r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
            if n in LIVE or n == 'Прихожая': warn.append(f'{n}: подпись легла на мебель')
        lab.append([n, best[1], best[2]])
    return W, errs, warn, lab

out = {}; total = 0
for cid, VS in lay.L.items():
    out[cid] = []
    for k, V in enumerate(VS):
        W, errs, warn, lab = check(cid, V); total += len(errs)
        print(f'{cid}-{k+1} {V["name"]}: ошибок {len(errs)}')
        for e in errs: print('   ✗', e)
        for e in warn: print('   ! ', e)
        DD = []
        for d in V['doors']:
            sw, cl, e, s = door_geom(C[cid], V['rooms'], W, d)
            hv = door_hinge(C[cid], V['rooms'], W, d, obst(C[cid], V))[1]
            DD.append([d[0], d[1], d[2], s[0], s[1], list(hv), 1 if len(d) > 5 and d[5] == 'sl' else 0])
        out[cid].append({'name': V['name'], 'walls': W, 'doors': DD, 'rooms': lab,
                         'furn': [[f[0], f[1], f[2], f[3], f[4] if len(f) > 4 else 0, f[5] if len(f) > 5 else 0] for f in V['furn']], 'warn': len(warn)})
json.dump(out, open(os.path.join(HERE, 'layouts.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print('всего ошибок', total)
