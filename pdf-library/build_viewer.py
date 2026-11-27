# Собирает db/viewer.html — просмотр базы планировок с фильтрами (данные встроены, открывается без сервера).
# Запуск: python -X utf8 build_viewer.py [папка_db]   (после rebuild.py; по умолчанию db/)
import json, os, sys
from pathlib import Path
from entry_doors import entrance_opening

HERE = os.path.dirname(os.path.abspath(__file__))
DB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'db')  # папка с library.json
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(DB, 'viewer.html')  # куда писать страницу
lib = json.load(open(os.path.join(DB, 'library.json'), encoding='utf-8'))
cg_p = os.path.join(DB, 'contour_graphs.json')
graph_fields = ('Nodes', 'Edges', 'Spaces', 'Openings', 'PerimeterLoop', 'PerimeterHoles', 'Shafts', 'VoidKinds')
cg = {x['Id']: {k: x[k] for k in graph_fields if k in x} for x in json.load(open(cg_p, encoding='utf-8')) if 'Edges' in x} if os.path.exists(cg_p) else {}
llm_p = os.path.join(DB, 'library_llm.json')
llm = {x['id']: x for x in json.load(open(llm_p, encoding='utf-8'))} if os.path.exists(llm_p) else {}
underlays_path = Path(OUT).parent / 'underlays' / 'index.json'
underlays = json.loads(underlays_path.read_text(encoding='utf-8')) if underlays_path.exists() else {}
def compact_cg(g, entry):
    """Граф стен в короткой форме для страницы: только то, что рисует каталог и передаёт генератору."""
    op = lambda o: {'k': o['Kind'], 'e': o['EdgeIndex'], 't': o['t'], 'w': o['WidthMm'], 'id': o.get('Id')}
    out = {
        'N': [[n['X'], n['Y']] for n in g['Nodes']],
        # [начало, конец, периметр, пустая, толщина]
        'E': [[e['StartNodeIndex'], e['EndNodeIndex'], int(e.get('LocationType') == 'Perimeter'), int(e.get('FillType') == 'Empty'),
               (e.get('LeftOffset') or 0) + (e.get('RightOffset') or 0)] for e in g['Edges']],
        'S': [{'r': s.get('RoomId'), 'o': s['OuterLoop'], 'i': s.get('InnerLoops') or []} for s in g.get('Spaces', [])],
        'L': g.get('PerimeterLoop') or [],
        'H': g.get('PerimeterHoles') or [],
        'VK': g.get('VoidKinds') or [],
        'SH': g.get('Shafts') or [],
        'O': [op(o) for o in g.get('Openings', [])],
    }
    if entry:
        out['ED'] = {**op(entry), 'hinge': entry.get('SwingHinge'), 'side': entry.get('SwingSide'), 'ver': bool(entry.get('SwingVerified'))}
    return out


ROOM_KEYS = ('id', 'role', 'name_src', 'area', 'rings', 'rects', 'label_at')
keep = []
for r in lib:
    k = {k: r.get(k) for k in ('id', 'kind', 'area', 'geom', 'why', 'graph', 'key', 'checks', 'count', 'source', 'edges')}
    k['rooms'] = [{x: m[x] for x in ROOM_KEYS if x in m} for m in r.get('rooms') or []]
    plan = r.get('plan') or {}
    k['plan'] = {x: plan[x] for x in ('outer', 'windows', 'risers') if x in plan}
    if r['id'] in cg:
        k['cg'] = compact_cg(cg[r['id']], entrance_opening(r, cg[r['id']]))
    if r['id'] in underlays:
        k['underlay'] = underlays[r['id']]
    keep.append(k)
# JSON для нейронки не встраиваем: страница подгружает library_llm.json, когда его открывают.
tpl = open(os.path.join(HERE, 'viewer_template.html'), encoding='utf-8').read()
out = tpl.replace('/*DATA*/[]', json.dumps(keep, ensure_ascii=False, separators=(',', ':')))
sources_path = Path(OUT).parent / 'source_refs.json'
sources = json.loads(sources_path.read_text(encoding='utf-8')) if sources_path.exists() else []
out = out.replace('/*SOURCES*/[]', json.dumps(sources, ensure_ascii=False, separators=(',', ':')))
p = OUT
open(p, 'w', encoding='utf-8').write(out)
print(p, len(keep), 'проверенных планировок,', len(sources), 'исходных листа,', round(len(out) / 1e6, 2), 'МБ')
