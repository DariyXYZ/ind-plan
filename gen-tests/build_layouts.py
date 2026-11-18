# Планировки из layouts.py → перегородки по границам комнат + проверка правил → layouts.json для /test
import json, math, os, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location('lay', os.path.join(HERE, 'layouts.py')); lay = importlib.util.module_from_spec(sp); sp.loader.exec_module(lay)
C = {c['id']: c for c in json.load(open(os.path.join(HERE, 'contours.json'), encoding='utf-8'))}
FC = {'bed': (1600, 2000), 'sbed': (900, 2000), 'sofa': (2200, 950), 'dining': (1200, 1700), 'desk': (1200, 1100), 'coffee': (900, 500),
      'wardrobe': (1800, 600), 'base': (600, 600), 'hob': (600, 600), 'sink': (600, 600), 'fridge': (600, 650), 'washer': (600, 600),
      'wc': (380, 650), 'bidet': (360, 560), 'basin': (500, 450), 'bath': (1700, 700), 'shower': (900, 900)}
PT = 100  # перегородка
WET = ('Ванная', 'Санузел', 'Мастер-санузел', 'Постирочная')
LIVE = ('Спальня', 'Спальня 2', 'Детская', 'Мастер-спальня', 'Гостевая', 'Кабинет', 'Кухня-гостиная')

def inpoly(P, x, y):
    c = False
    for i in range(len(P)):
        (x1, y1), (x2, y2) = P[i], P[(i + 1) % len(P)]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1): c = not c
    return c

def room_at(rooms, x, y):
    for n, rs in rooms.items():
        for a, b, c, d in rs:
            if a < x < c and b < y < d: return n
    return None

def edge_t(c, x1, y1, x2, y2):
    """толщина наружной стены, на оси которой лежит отрезок (или None)"""
    P = c['poly']
    for i in range(len(P)):
        (a, b), (e, f) = P[i], P[(i + 1) % len(P)]
        if a == e == x1 == x2 and min(b, f) <= min(y1, y2) and max(y1, y2) <= max(b, f): return c['ts'][i]
        if b == f == y1 == y2 and min(a, e) <= min(x1, x2) and max(x1, x2) <= max(a, e): return c['ts'][i]
    return None

def walls(c, rooms):
    xs = sorted({v for rs in rooms.values() for r in rs for v in (r[0], r[2])} | {p[0] for p in c['poly']})
    ys = sorted({v for rs in rooms.values() for r in rs for v in (r[1], r[3])} | {p[1] for p in c['poly']})
    cell = {}
    errs = []
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            cx, cy = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            if not inpoly(c['poly'], cx, cy): cell[i, j] = '#out'; continue
            n = room_at(rooms, cx, cy)
            if n is None: errs.append(f'пустое место {xs[i]}..{xs[i+1]} × {ys[j]}..{ys[j+1]}'); n = '#none'
            cell[i, j] = n
    segs = []  # (ось, координата, from, to)
    for i in range(len(xs) - 2):
        for j in range(len(ys) - 1):
            a, b = cell[i, j], cell[i + 1, j]
            if '#out' not in (a, b) and a != b: segs.append(('v', xs[i + 1], ys[j], ys[j + 1]))
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 2):
            a, b = cell[i, j], cell[i, j + 1]
            if '#out' not in (a, b) and a != b: segs.append(('h', ys[j + 1], xs[i], xs[i + 1]))
    segs.sort()
    out = []
    for s in segs:
        if out and out[-1][0] == s[0] and out[-1][1] == s[1] and out[-1][3] == s[2]: out[-1] = (s[0], s[1], out[-1][2], s[3])
        else: out.append(s)
    W = []
    for o, k, a, b in out:
        if b - a < 150: continue
        W.append((k, a, k, b) if o == 'v' else (a, k, b, k))
    return W, errs

def inner_rect(c, r, rooms=None, n=None):
    a, b, cc, d = r
    def off(x1, y1, x2, y2):
        t = edge_t(c, x1, y1, x2, y2)
        if t: return t / 2
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2; dx, dy = (0, 10) if y1 == y2 else (10, 0)
        if rooms and n and any(room_at(rooms, mx + k * dx, my + k * dy) == n and not (a < mx + k * dx < cc and b < my + k * dy < d) for k in (1, -1)): return 0
        return PT / 2
    return (a + off(a, b, a, d), b + off(a, b, cc, b), cc - off(cc, b, cc, d), d - off(a, d, cc, d))

def fbox(f):
    code, x, y, r = f; w, d = FC[code]
    ux, uy = round(math.cos(math.radians(r))), round(math.sin(math.radians(r)))
    # тело уходит по нормали (-uy, ux) от базы, вдоль стены — (ux, uy)
    nx, ny = -uy, ux
    pts = [(x + ux * w / 2, y + uy * w / 2), (x - ux * w / 2, y - uy * w / 2)]
    pts += [(px + nx * d, py + ny * d) for px, py in pts]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))

def ov(a, b, tol=2):
    return a[0] < b[2] - tol and b[0] < a[2] - tol and a[1] < b[3] - tol and b[1] < a[3] - tol

def door_sweep(c, rooms, W, d):
    x, y, w, into, h = d
    for x1, y1, x2, y2 in W + [(p[0], p[1], q[0], q[1]) for p, q in zip(c['poly'], c['poly'][1:] + c['poly'][:1])]:
        if x1 == x2 == x and min(y1, y2) <= y <= max(y1, y2):
            s = 1 if room_at(rooms, x + 200, y) == into else -1 if room_at(rooms, x - 200, y) == into else 0
            if not s: return None, 'дверь не между нужными комнатами'
            f = x + s * PT / 2
            return (min(f, f + s * w), y - w / 2, max(f, f + s * w), y + w / 2), None
        if y1 == y2 == y and min(x1, x2) <= x <= max(x1, x2):
            s = 1 if room_at(rooms, x, y + 200) == into else -1 if room_at(rooms, x, y - 200) == into else 0
            if not s: return None, 'дверь не между нужными комнатами'
            f = y + s * PT / 2
            return (x - w / 2, min(f, f + s * w), x + w / 2, max(f, f + s * w)), None
    return None, 'нет стены под дверью'

def check(cid, V):
    c = C[cid]; rooms = V['rooms']; W, errs = walls(c, rooms); warn = []
    # ширина и площадь
    for n, rs in rooms.items():
        ir = [inner_rect(c, r, rooms, n) for r in rs]
        area = sum((r[2] - r[0]) * (r[3] - r[1]) for r in ir) / 1e6
        main = max(ir, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
        wmin = min(main[2] - main[0], main[3] - main[1]) / 1000
        if n in LIVE and n != 'Кухня-гостиная' and wmin < 2.99: errs.append(f'{n}: ширина {wmin:.2f} м < 3,0')
        if n == 'Кухня-гостиная' and wmin < 3.09: errs.append(f'{n}: ширина {wmin:.2f} м < 3,1')
        if n in WET[:3] and area < 2.5: errs.append(f'{n}: {area:.1f} м² мало')
        if n == 'Прихожая':
            for r in ir[1:]:
                if min(r[2] - r[0], r[3] - r[1]) < 1090: errs.append(f'коридор {min(r[2]-r[0], r[3]-r[1]):.0f} мм < 1100')
        # окно
        if n in LIVE:
            has = False
            for e, off, w in c['win']:
                (x1, y1), (x2, y2) = c['poly'][e], c['poly'][(e + 1) % len(c['poly'])]
                L = math.hypot(x2 - x1, y2 - y1); px, py = x1 + (x2 - x1) * off / L, y1 + (y2 - y1) * off / L
                for a, b, cc, d in rs:
                    if a - 1 <= px <= cc + 1 and b - 1 <= py <= d + 1 and (abs(px - a) < 2 or abs(px - cc) < 2 or abs(py - b) < 2 or abs(py - d) < 2 or True): has = has or (a - 1 <= px <= cc + 1 and b - 1 <= py <= d + 1)
            if not has: errs.append(f'{n}: нет окна')
        # стояк
        if n in WET or n == 'Кухня-гостиная':
            dmin = min(max(a - x, 0, x - cc) + max(b - y, 0, y - d) for x, y in c['ris'] for a, b, cc, d in rs)
            lim = 2000 if n == 'Постирочная' else 400
            if n != 'Кухня-гостиная' and dmin > lim: errs.append(f'{n}: до стояка {dmin/1000:.1f} м')
    # двери
    sweeps = []; clr = []
    for d in V['doors']:
        sw, e = door_sweep(c, rooms, W, d)
        if e: errs.append(f'дверь {d[:2]}: {e}')
        else:
            sweeps.append((d, sw))
            x, y, w = d[0], d[1], d[2]
            vert = sw[2] - sw[0] == w and sw[3] - sw[1] == w and abs((sw[1] + sw[3]) / 2 - y) < 1
            clr.append((d, (x - 550, y - w / 2, x + 550, y + w / 2) if vert else (x - w / 2, y - 550, x + w / 2, y + 550)))
    # мебель
    boxes = []
    for f in V['furn']:
        b = fbox(f); cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2; n = room_at(rooms, cx, cy)
        if n is None: errs.append(f'{f[0]} {f[1:3]} вне комнат'); continue
        inn = [inner_rect(c, r, rooms, n) for r in rooms[n]]
        # внутри объединения внутренних прямоугольников (по углам)
        def inside(px, py): return any(r[0] - 3 <= px <= r[2] + 3 and r[1] - 3 <= py <= r[3] + 3 for r in inn)
        if not all(inside(px, py) for px, py in ((b[0], b[1]), (b[2], b[1]), (b[0], b[3]), (b[2], b[3]))): errs.append(f'{n}: {f[0]} {f[1:3]} вылезает из комнаты')
        for x0, y0, x1, y1 in [(p[0], p[1], q[0], q[1]) for p, q in [((x, y), (x + w, y + h)) for x, y, w, h in c['pyl']]]:
            if ov(b, (x0, y0, x1, y1)): errs.append(f'{n}: {f[0]} упирается в пилон')
        for (g, gb) in boxes:
            if ov(b, gb): errs.append(f'{n}: {f[0]} пересекает {g[0]}')
        for d, sw in sweeps:
            if ov(b, sw, 10): errs.append(f'{n}: {f[0]} под распашкой двери {d[3]}')
        for x, y in c['ris']:
            if b[0] < x < b[2] and b[1] < y < b[3]: errs.append(f'{n}: {f[0]} на стояке')
        for d, cb in clr:
            if ov(b, cb, 10): errs.append(f'{n}: {f[0]} загораживает проём {d[3]} {d[:2]}')
        boxes.append((f, b))
    for n, rs in rooms.items():
        if n == 'Кухня-гостиная':
            sinks = [fbox(f) for f in V['furn'] if f[0] == 'sink']
            if sinks:
                s = sinks[0]; dmin = min(math.hypot((s[0] + s[2]) / 2 - x, (s[1] + s[3]) / 2 - y) for x, y in c['ris'])
                if dmin > 2500: warn.append(f'мойка в {dmin/1000:.1f} м от стояка')
    return W, errs, warn

out = {}
for cid, VS in lay.L.items():
    out[cid] = []
    for k, V in enumerate(VS):
        W, errs, warn = check(cid, V)
        print(f'{cid}-{k+1} {V["name"]}: {len(W)} стен, ошибок {len(errs)}')
        for e in errs: print('   ✗', e)
        for e in warn: print('   ! ', e)
        lab = []
        for n, rs in V['rooms'].items():
            r = max(rs, key=lambda r: (r[2] - r[0]) * (r[3] - r[1])); lab.append([n, (r[0] + r[2]) / 2, (r[1] + r[3]) / 2])
        DD = []
        for d in V['doors']:
            sw, _ = door_sweep(C[cid], V['rooms'], W, d)
            cx, cy = (sw[0] + sw[2]) / 2 - d[0], (sw[1] + sw[3]) / 2 - d[1]
            sx, sy = (0, 1 if cy > 0 else -1) if abs(cy) > abs(cx) else (1 if cx > 0 else -1, 0)
            DD.append([d[0], d[1], d[2], sx, sy, d[4]])
        out[cid].append({'name': V['name'], 'walls': W, 'doors': DD, 'rooms': lab,
                         'furn': [list(f) for f in V['furn']], 'warn': len(warn)})
json.dump(out, open(os.path.join(HERE, 'layouts.json'), 'w', encoding='utf-8'), ensure_ascii=False)
