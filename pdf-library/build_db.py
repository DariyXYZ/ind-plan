"""Build the searchable IND plan library from immutable extraction outputs."""
from __future__ import annotations

import argparse
import collections
import json
import re
import sqlite3
from pathlib import Path
from contour_graph import compact_rings, regularize_rooms, rings_from_rects, segment_graph
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parent
ROLE = {
    'kl': 'kg', 'kitchen': 'kitchen', 'living': 'living', 'bed': 'bedroom',
    'hall': 'hall', 'corr': 'corridor', 'wr': 'wardrobe', 'bath': 'bath',
    'wc': 'wc', 'laundry': 'laundry', 'store': 'storage', 'balcony': 'loggia',
    'patio': 'loggia', 'study': 'study', 'kids': 'kids',
}


def base(value: str) -> str:
    return re.sub(r'\d+$', '', value)


def role(room: dict) -> str:
    name = room.get('fn', '').casefold().replace('ё', 'е')
    if 'детская' in name:
        return 'kids'
    if 'мастер-спальня' in name or 'спальня мастер' in name:
        return 'master'
    return ROLE.get(base(room['id']), 'other')


def facade_width(entry: dict) -> int:
    outer = entry['contour']['outer']
    xs = [p[0] for p in outer]; ys = [p[1] for p in outer]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    lengths = []
    for window in entry['contour']['windows']:
        x, y = window['at']
        nearest = min(((abs(y - y0), x1 - x0), (abs(y - y1), x1 - x0),
                       (abs(x - x0), y1 - y0), (abs(x - x1), y1 - y0)))
        if nearest[0] <= 800:
            lengths.append(nearest[1])
    return round(max(lengths, default=0))


def raw_index() -> dict:
    index = collections.defaultdict(list)
    for directory in sorted(ROOT.glob('out_*')):
        if directory.name == 'out_all':
            continue
        for path in sorted(directory.glob('*.json')):
            if path.name.startswith('_') or path.name.startswith('library'):
                continue
            data = json.loads(path.read_text(encoding='utf-8'))
            for apartment in data.get('apartments', []):
                index[path.stem].append((data.get('source'), apartment))
    return index


def match_raw(entry: dict, index: dict):
    rooms = entry['plan']['rooms']
    signature = sorted((r['id'], round(entry['areas'].get(r['id'], 0), 2)) for r in rooms)
    first = (None, None)
    for sheet in entry['sheet']:
        for source, apartment in index.get(sheet, []):
            candidate = sorted((r['id'], round(r['area'], 2)) for r in apartment['rooms'])
            if candidate == signature:
                raw_rooms = {r['id']: r for r in apartment['rooms']}
                if apartment.get('checks', {}).get('ok') and all(r['id'] in raw_rooms and r['rects'] == raw_rooms[r['id']]['rects'] for r in rooms):
                    return source, apartment
                # зеркальные близнецы на одном листе: брать ту копию, что прошла проверки
                if apartment.get('checks', {}).get('ok'):
                    return source, apartment
                if first[0] is None:
                    first = (source, apartment)
    return first


def normalize(entry: dict, index: dict, engine_entry: dict) -> dict:
    source_file, raw = match_raw(entry, index)
    rooms = entry['plan']['rooms']
    roles = collections.Counter(role(r) for r in rooms)
    key = dict(entry['key'])
    beds = roles['bedroom'] + roles['kids'] + roles['master']
    bath_ids = {r['id'] for r in rooms if ROLE.get(base(r['id'])) in ('bath', 'wc')}
    bed_ids = {r['id'] for r in rooms if role(r) in ('bedroom', 'kids', 'master')}
    ensuite = any(set(d['between']) & bath_ids and set(d['between']) & bed_ids for d in entry['plan']['doors'])
    key.update(bedrooms=beds, wardrobe=roles['wardrobe'] > 0, kids=roles['kids'] > 0,
               master_bath=ensuite, laundry=roles['laundry'] > 0,
               separate_kitchen=roles['kitchen'] > 0, bathrooms=roles['bath'] + roles['wc'],
               facade_width_mm=facade_width(entry),
               entry_type=key.get('entry'), risers=bool(entry['contour'].get('risers')), levels=1)
    room_data = []
    raw_rooms = {r['id']: r for r in raw.get('rooms', [])} if raw else {}
    for room in rooms:
        original = raw_rooms.get(room['id'])
        direct = (original and original.get('rects') == room['rects'] and original.get('rings')
                  and all(len(q['outer']) >= 3 and Polygon(q['outer'], q.get('holes', [])).is_valid
                          and Polygon(q['outer'], q.get('holes', [])).area > 0 for q in original['rings']))
        room_data.append({'id': room['id'], 'role': role(room),
                          'name_src': room.get('fn', room['id']), 'area': entry['areas'].get(room['id']),
                          'rings': compact_rings(original['rings']) if direct else rings_from_rects(room['rects']),
                          'geometry_source': 'pdf_fill' if direct else 'rect_union_simplified',
                          'rects': room['rects']})
    regularize_rooms(room_data)
    checks = raw.get('checks') if raw else {'ok': True, 'origin': 'validated_legacy_library'}
    if not checks.get('ok'):
        raise ValueError(f"Legacy source failed checks: {entry['id']}")
    page = None
    if source_file and '#' in source_file:
        source_file, page = source_file.rsplit('#', 1)
        page = int(page)
    sheet = entry['sheet'][0] if entry['sheet'] else None
    names = {r['id']: r['name_src'] for r in room_data}
    balcony_links = [f"{names.get(a, a)}–{names.get(b, b)} (балкон)"
                     for link in entry['plan']['doors'] if link.get('type') == 'balcony'
                     for a, b in [link['between']]]
    full_graph = ', '.join(filter(None, [engine_entry['graph'], *balcony_links]))
    return {'schema_version': 2, 'id': entry['id'], 'kind': entry['key']['type'],
            'area': entry['key']['area'], 'src': 'проект IND (не оценено)', 'geom': entry['geom'],
            'why': '; '.join(entry['traits']) or 'планировка из проекта IND',
            'graph': full_graph, 'areas': engine_entry['areas'], 'key': key,
            'checks': checks, 'count': entry['copies'],
            'source': {'project': entry['project'], 'file': source_file, 'page': page,
                       'floor': sheet, 'section': None, 'sheets': entry['sheet']},
            'rooms': room_data, 'outline_graph': segment_graph(room_data),
            'furniture': [], 'edges': entry['plan']['doors'],
            'plan': {**engine_entry['plan'], 'doors': entry['plan']['doors']}}


def _sig(p):
    """подпись для повторов: тип + граф по названиям (зеркало и другой этаж дают ту же) + число комнат"""
    return (p['kind'], tuple(sorted(x.strip() for x in p['graph'].split(','))), len(p['rooms']))


def _same_areas(a, b, tol=0.03):
    x = sorted(r['area'] or 0 for r in a['rooms']); y = sorted(r['area'] or 0 for r in b['rooms'])
    return len(x) == len(y) and all(abs(u - v) <= tol * max(u, v, 1) for u, v in zip(x, y))


def merge_copy(primary, duplicate):
    primary['count'] += duplicate['count']
    source, old_source = primary['source'], duplicate['source']
    copies = source.setdefault('copies', [])
    copies.append({'id': duplicate['id'], 'file': old_source['file'], 'floor': old_source['floor'],
                   'page': old_source.get('page')})
    copies.extend(old_source.get('copies', []))


def apply_reviewed_duplicates(plans):
    """Keep the reviewed drawing of this Barkhatnaya layout family."""
    by_id = {plan['id']: plan for plan in plans}
    primary, duplicate = by_id.get('bkh_073'), by_id.get('bkh_072')
    if (primary and duplicate and primary['source']['floor'] == '2024-04-04__2 корпус 4'
            and duplicate['source']['floor'] == '2024-04-02__2.4'):
        merge_copy(primary, duplicate)
        return [plan for plan in plans if plan is not duplicate]
    return plans


def dedupe(plans: list) -> list:
    """одна и та же квартира с разных этажей / зеркальная: граф совпадает, площади ±3% → одна запись"""
    out = []
    for p in sorted(apply_reviewed_duplicates(plans), key=lambda q: (q['geom'] != 'ok', q['id'])):
        twin = next((q for q in out if _sig(q) == _sig(p) and _same_areas(q, p)), None)
        if twin is None:
            p['source'].setdefault('copies', [])
            out.append(p); continue
        merge_copy(twin, p)
    return sorted(out, key=lambda q: q['id'])


def clean_rects(rects, min_side=200, snap=100):
    """для нейронки: выкинуть полоски < 200 мм, склеить соседние по высоте полосы с почти одинаковыми краями"""
    rs = [list(r) for r in rects if r[2] - r[0] >= min_side and r[3] - r[1] >= min_side] or [list(r) for r in rects]
    rs.sort(key=lambda r: (r[1], r[0]))
    changed = True
    while changed:
        changed = False
        for i in range(len(rs)):
            for j in range(len(rs)):
                a, b = rs[i], rs[j]
                if i == j or abs(a[3] - b[1]) > snap: continue
                if abs(a[0] - b[0]) <= snap and abs(a[2] - b[2]) <= snap:
                    x0 = round((a[0] * (a[3] - a[1]) + b[0] * (b[3] - b[1])) / (a[3] - a[1] + b[3] - b[1]) / 10) * 10
                    x1 = round((a[2] * (a[3] - a[1]) + b[2] * (b[3] - b[1])) / (a[3] - a[1] + b[3] - b[1]) / 10) * 10
                    rs[i] = [x0, a[1], x1, b[3]]; rs.pop(j); changed = True; break
            if changed: break
    return rs


def llm_record(p: dict) -> dict:
    """короткая запись для Claude (формат «Б» из «IND PLAN — формат обмена с Claude»): граф + площади + why + план прямоугольниками"""
    pl = p.get('plan') or {}
    return {'id': p['id'], 'type': p['kind'], 'area': p['area'], 'why': p['why'], 'graph': p['graph'],
            'areas': {r['id']: r['area'] for r in p['rooms']},
            'plan': {'outer': pl.get('outer'),
                     'rooms': [{'id': r['id'], 'fn': r['name_src'], 'rings': r['rings']} for r in p['rooms']],
                     'doors': [{k: v for k, v in d.items() if k in ('between', 'type', 'w')} for d in p['edges']],
                     'windows': [{'room': w.get('room'), 'at': w.get('at'), 'w': w.get('w')} for w in pl.get('windows') or []]}}


def build(source: Path = ROOT / 'out_all' / '_library.json', destination: Path = ROOT / 'db') -> list:
    import jsonschema
    destination.mkdir(parents=True, exist_ok=True)
    schema = json.loads((ROOT / 'library.schema.json').read_text(encoding='utf-8'))
    entries = json.loads(source.read_text(encoding='utf-8'))
    engine_entries = {e['id']: e for e in json.loads(
        (source.parent / 'library_ind_projects.json').read_text(encoding='utf-8'))}
    index = raw_index()
    plans = dedupe([normalize(e, index, engine_entries[e['id']]) for e in entries])
    for plan in plans:
        jsonschema.validate(plan, schema)
    # Build into a temporary file and replace only after all rows validate.
    temp = destination / 'plans.sqlite.tmp'
    if temp.exists():
        temp.unlink()
    db = sqlite3.connect(temp)
    try:
        db.executescript('''
            CREATE TABLE plans (id TEXT PRIMARY KEY, kind TEXT, area REAL, w INTEGER, d INTEGER,
                facades INTEGER, entry TEXT, bedrooms INTEGER, bathrooms INTEGER,
                wardrobe INTEGER, kids INTEGER, laundry INTEGER, master_bath INTEGER,
                separate_kitchen INTEGER, levels INTEGER, count INTEGER, geom TEXT, payload TEXT);
            CREATE TABLE rooms (plan_id TEXT, room_id TEXT, role TEXT, name_src TEXT, area REAL,
                PRIMARY KEY(plan_id, room_id));
            CREATE TABLE edges (plan_id TEXT, room_a TEXT, room_b TEXT, kind TEXT, width_mm REAL);
            CREATE TABLE sources (plan_id TEXT PRIMARY KEY, project TEXT, file TEXT, page INTEGER,
                floor TEXT, section TEXT);
            CREATE INDEX plans_lookup ON plans(kind, bedrooms, wardrobe, kids, w, d, facades);
            CREATE INDEX rooms_role ON rooms(role, plan_id);
            CREATE INDEX sources_project ON sources(project);
        ''')
        for p in plans:
            k, s = p['key'], p['source']
            db.execute('INSERT INTO plans VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (p['id'], p['kind'], p['area'], k['w'], k['d'], k['facades'], k['entry'],
                 k['bedrooms'], k['bathrooms'], int(k['wardrobe']), int(k['kids']),
                 int(k['laundry']), int(k['master_bath']), int(k['separate_kitchen']),
                 k['levels'], p['count'], p['geom'], json.dumps(p, ensure_ascii=False)))
            db.executemany('INSERT INTO rooms VALUES (?,?,?,?,?)',
                [(p['id'], r['id'], r['role'], r['name_src'], r['area']) for r in p['rooms']])
            db.executemany('INSERT INTO edges VALUES (?,?,?,?,?)',
                [(p['id'], d['between'][0], d['between'][1], d.get('type', 'door'), d.get('w'))
                 for d in p['edges']])
            db.execute('INSERT INTO sources VALUES (?,?,?,?,?,?)',
                (p['id'], s['project'], s['file'], s['page'], s['floor'], s['section']))
        db.commit()
    finally:
        db.close()
    temp.replace(destination / 'plans.sqlite')
    (destination / 'library.json').write_text(json.dumps(plans, ensure_ascii=False, indent=1), encoding='utf-8')
    # Keep the old engine reader's field names while adding provenance and quality.
    legacy = []
    for p in plans:
        q = {k: p[k] for k in ('id', 'kind', 'area', 'src', 'geom', 'why', 'graph', 'areas', 'key', 'plan', 'source')}
        q.update(cid=None, count=p['count'], checks=p['checks'], schema_version=1)
        legacy.append(q)
    (destination / 'library_engine.json').write_text(json.dumps(legacy, ensure_ascii=False, indent=1), encoding='utf-8')
    llm = [llm_record(p) for p in plans]
    (destination / 'library_llm.json').write_text(json.dumps(llm, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    return plans


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=ROOT / 'out_all' / '_library.json')
    args = parser.parse_args()
    result = build(args.source)
    print(f'Validated and indexed {len(result)} plans in {ROOT / "db"}')
