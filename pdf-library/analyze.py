# Признаки, схемы и приёмы по извлечённым квартирам; дедупликация; библиотека референсов в формате Б
import sys, json, glob, os, collections, math
from shapely.geometry import Polygon

# python analyze.py <выход> <папка|префикс|проект> [...]; без источников — <выход> = папка Бархатной
D = sys.argv[1]
SRC = [s.split('|') for s in sys.argv[2:]] or [[D, 'bkh', '1-25-2023 ЖК Бархатная (Владивосток)']]
apts = []
for sd, pref, proj in SRC:
    for f in sorted(glob.glob(os.path.join(sd, '*.json'))):
        if os.path.basename(f).startswith('_') or os.path.basename(f).startswith('library'): continue
        d = json.load(open(f, encoding='utf-8'))
        for i, a in enumerate(d['apartments']):
            a['sheet'] = os.path.splitext(os.path.basename(f))[0]; a['idx'] = i; a['source'] = d['source']
            a['pref'] = pref; a['project'] = proj; a.setdefault('geom', 'ok')
            apts.append(a)

WET = ('balcony', 'patio')
def base(i): return i.rstrip('0123456789')

def features(a):
    rooms = {r['id']: r for r in a['rooms'] if base(r['id']) not in WET}
    links = [l for l in a['links'] if l['type'] in ('door', 'open', 'entry')]
    beds = [i for i in rooms if base(i) == 'bed']
    baths = [i for i in rooms if base(i) in ('bath', 'wc')]
    nb = collections.defaultdict(list)
    for l in links:
        x, y = l['between']; nb[x].append((y, l['type'])); nb[y].append((x, l['type']))
    entry = next((l['between'][1] for l in links if l['type'] == 'entry'), None)
    P = Polygon(a['contour']['outer'])
    minx, miny, maxx, maxy = P.bounds
    w, h = maxx - minx, maxy - miny
    wins = a['contour']['windows']
    # фасадные стороны: окна на сторонах bbox
    sides = set()
    for wn in wins:
        x, y = wn['at']
        dd = {'S': abs(y - miny), 'N': abs(y - maxy), 'W': abs(x - minx), 'E': abs(x - maxx)}
        s = min(dd, key=dd.get)
        if dd[s] < 800: sides.add(s)
    front = sum(wn['w'] for wn in wins)
    f = {
        'type': 'ST' if not beds else f'{len(beds) + 1}E',
        'area': a['area_rooms'],
        'beds': len(beds), 'baths': len(baths),
        'bbox': [round(w), round(h)],
        'facades': len(sides),
        'glazing_m': round(front / 1000, 1),
        'entry_to': base(entry) if entry else None,
        'kl_open_to_hall': any(base(y) == 'kl' and t == 'open' for y, t in nb.get(entry, [])) if entry else False,
        'has_corr': any(base(i) == 'corr' for i in rooms),
        'beds_from': collections.Counter(base(next((y for y, t in nb[b] if base(y) in ('corr', 'hall', 'kl', 'living')), 'other')) for b in beds),
        'ensuite': sum(1 for b in beds if any(base(y) in ('bath', 'wc') for y, t in nb[b])),
        'bath_from_kl': sum(1 for x in baths if any(base(y) == 'kl' for y, t in nb[x])),
        'bed_via_kl': [b for b in beds if all(base(y) == 'kl' for y, t in nb[b] if base(y) not in ('bath', 'wc', 'wr'))],
        'laundry': any(base(i) == 'laundry' for i in rooms),
        'kl_share': round(sum(r['area'] for i, r in rooms.items() if base(i) == 'kl') / a['area_rooms'], 2),
        'circ_share': round(sum(r['area'] for i, r in rooms.items() if base(i) in ('hall', 'corr')) / a['area_rooms'], 2),
        'kl_area': round(sum(r['area'] for i, r in rooms.items() if base(i) == 'kl'), 1),
        'bed_areas': sorted(round(rooms[b]['area'], 1) for b in beds),
    }
    # подпись схемы: рёбра по базовым типам, без номеров
    sig = sorted({'-'.join(sorted((base(l['between'][0]), base(l['between'][1])))) + ('(o)' if l['type'] == 'open' else '')
                  for l in links if l['type'] != 'entry'})
    f['scheme'] = ' '.join(sig)
    # стояки рядом с санузлами
    ris = a['contour']['risers']
    dist = []
    for x in baths:
        rr = rooms[x]['rects']
        cx = sum((r[0] + r[2]) / 2 * (r[2] - r[0]) * (r[3] - r[1]) for r in rr) / sum((r[2] - r[0]) * (r[3] - r[1]) for r in rr)
        cy = sum((r[1] + r[3]) / 2 * (r[2] - r[0]) * (r[3] - r[1]) for r in rr) / sum((r[2] - r[0]) * (r[3] - r[1]) for r in rr)
        if ris: dist.append(min(math.dist((cx, cy), p) for p in ris))
    f['bath_riser_mm'] = round(max(dist)) if dist else None
    return f

for a in apts:
    a['f'] = features(a)

# дедупликация: тип + площади помещений + bbox до 100 мм
def key(a):
    rs = (a['pref'],) + tuple(sorted((base(r['id']), round(r['area'], 1)) for r in a['rooms'] if base(r['id']) not in WET))
    return (a['f']['type'], rs)
uniq = {}
for a in apts:
    k = key(a)
    uniq.setdefault(k, []).append(a)

ok_all = [a for a in apts if a['checks']['ok']]
U = [v[0] | {'copies': len(v), 'sheets': sorted({x['sheet'] for x in v})} if False else dict(v[0], copies=len(v), sheets=sorted({x['sheet'] for x in v})) for v in uniq.values()]
Uok = [a for a in U if a['checks']['ok'] and any(base(r['id']) in ('kl', 'kitchen', 'living') for r in a['rooms'])]
no_kitchen = [a for a in U if a['checks']['ok'] and a not in Uok]

def by(fn, items):
    c = collections.Counter(fn(a) for a in items); return c.most_common()

rep = {
    'sheets': len({a['sheet'] for a in apts}),
    'apartments_found': len(apts), 'apartments_ok': len(ok_all),
    'fail_reasons': by(lambda a: ','.join(k for k in ('entries', 'unreached', 'no_window', 'area_total_ok')
                                          if (k == 'entries' and a['checks']['entries'] != 1) or (k in ('unreached', 'no_window') and a['checks'][k]) or (k == 'area_total_ok' and not a['checks'][k])) or 'ok', apts),
    'unique': len(U), 'unique_ok': len(Uok), 'unique_ok_but_no_kitchen': len(no_kitchen),
    'types': by(lambda a: a['f']['type'], Uok),
}
# приёмы по типам
tech = collections.defaultdict(dict)
for t in sorted({a['f']['type'] for a in Uok}):
    G = [a for a in Uok if a['f']['type'] == t]
    n = len(G)
    tech[t] = {
        'n': n,
        'area': [min(a['area_rooms'] for a in G), round(sum(a['area_rooms'] for a in G) / n, 1), max(a['area_rooms'] for a in G)],
        'kl_open_to_hall': sum(a['f']['kl_open_to_hall'] for a in G),
        'has_corr': sum(a['f']['has_corr'] for a in G),
        'ensuite_any': sum(a['f']['ensuite'] > 0 for a in G),
        'baths': by(lambda a: a['f']['baths'], G),
        'bed_via_kl': sum(bool(a['f']['bed_via_kl']) for a in G),
        'bath_from_kl': sum(a['f']['bath_from_kl'] > 0 for a in G),
        'laundry': sum(a['f']['laundry'] for a in G),
        'facades': by(lambda a: a['f']['facades'], G),
        'kl_share': [min(a['f']['kl_share'] for a in G), max(a['f']['kl_share'] for a in G)],
        'circ_share': [min(a['f']['circ_share'] for a in G), max(a['f']['circ_share'] for a in G)],
        'bbox_w': sorted({round(min(a['f']['bbox']) / 100) * 100 for a in G}),
        'bbox_d': sorted({round(max(a['f']['bbox']) / 100) * 100 for a in G}),
        'schemes': by(lambda a: a['f']['scheme'], G),
        'bath_riser_mm_max': max((a['f']['bath_riser_mm'] or 0) for a in G),
    }
rep['techniques'] = tech

# библиотека: формат Б + граф строкой + ключ подбора
lib = []
cnt_p = collections.Counter()
for a in sorted(Uok, key=lambda a: (a['pref'], a['f']['type'], a['area_rooms'])):
    cnt_p[a['pref']] += 1; i = cnt_p[a['pref']] - 1
    f = a['f']
    graph = ', '.join(f"{l['between'][0]}–{l['between'][1]}" + ('(проём)' if l['type'] == 'open' else '')
                      for l in a['links'] if l['type'] in ('door', 'open'))
    lib.append({
        'id': f"{a['pref']}_{i + 1:03d}", 'project': a['project'], 'geom': a['geom'], 'sheet': a['sheets'], 'copies': a['copies'],
        'status': 'из проекта IND, архитекторы не оценивали',
        'key': {'type': f['type'], 'area': f['area'], 'w': min(f['bbox']), 'd': max(f['bbox']), 'facades': f['facades'], 'entry': f['entry_to']},
        'graph': graph,
        'areas': {r['id']: r['area'] for r in a['rooms']},
        'traits': [t for t, v in (('прихожая открыта в КГ', f['kl_open_to_hall']), ('коридор в тихую зону', f['has_corr']),
                                  (f"мастер-спальня с с/у ×{f['ensuite']}", f['ensuite']), ('постирочная', f['laundry']),
                                  ('спальня через КГ', bool(f['bed_via_kl'])), ('санузел из КГ', f['bath_from_kl'] > 0)) if v],
        'contour': a['contour'],
        'plan': {'rooms': [{'id': r['id'], 'fn': r['fn'], 'rects': r['rects']} for r in a['rooms']],
                 'doors': [{'between': l['between'], **({'type': 'open'} if l['type'] == 'open' else {}), **({'w': l['w']} if 'w' in l else {})}
                           for l in a['links'] if l['type'] in ('door', 'open', 'entry')]},
    })
json.dump(lib, open(os.path.join(D, '_library.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(rep, open(os.path.join(D, '_report.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in rep.items() if k != 'techniques'}, ensure_ascii=False))
for t, v in tech.items():
    print(t, json.dumps({k: x for k, x in v.items() if k != 'schemes'}, ensure_ascii=False))
    for s, n in v['schemes'][:4]: print('   ', n, s)
# размер записи
ex = lib[len(lib) // 2]
print('символов на референс: полный', len(json.dumps(ex, ensure_ascii=False, separators=(',', ':'))),
      '| граф+площади+приёмы', len(json.dumps({k: ex[k] for k in ('key', 'graph', 'areas', 'traits')}, ensure_ascii=False, separators=(',', ':'))))

K = {'ST': 'ст', '2E': '2к', '3E': '3к', '4E': 'Евро-4', '5E': '5к', '6E': '6к'}
FNM = {'kl': 'Кухня-гостиная', 'kitchen': 'Кухня', 'living': 'Гостиная', 'bed': 'Спальня', 'bath': 'Санузел', 'hall': 'Прихожая', 'corr': 'Коридор',
       'laundry': 'Постирочная', 'wr': 'Гардеробная', 'balcony': 'Балкон', 'patio': 'Патио', 'store': 'Кладовая', 'study': 'Кабинет', 'wc': 'Санузел'}
def nm(i):
    b = i.rstrip('0123456789'); n = i[len(b):]
    return FNM.get(b, b) + (' ' + n if n else '')
eng = []
for e in lib:
    rooms = {nm(r['id']): r['rects'] for r in e['plan']['rooms'] if not r['id'].startswith(('balcony', 'patio'))}
    links = [d_ for d_ in e['plan']['doors'] if 'MOP' not in d_['between']]
    eng.append({'id': e['id'], 'cid': None, 'kind': K.get(e['key']['type'], e['key']['type']), 'area': e['key']['area'], 'src': 'проект IND (не оценено)',
                'geom': e['geom'], 'why': '; '.join(e['traits']) or 'типовая схема',
                'graph': ', '.join(nm(d_['between'][0]) + '–' + nm(d_['between'][1]) + ('(проём)' if d_.get('type') == 'open' else '') for d_ in links),
                'areas': {nm(k): v for k, v in e['areas'].items() if not k.startswith(('balcony', 'patio'))},
                'key': e['key'], 'plan': {'outer': e['contour']['outer'], 'windows': e['contour']['windows'], 'risers': e['contour']['risers'], 'rooms': rooms},
                'source': {'project': e['project'], 'sheets': e['sheet']}})
json.dump(eng, open(os.path.join(D, 'library_ind_projects.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('в схеме движка:', len(eng), collections.Counter(e['source']['project'] for e in eng))
