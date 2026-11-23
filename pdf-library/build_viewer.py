# Собирает db/viewer.html — просмотр базы планировок с фильтрами (данные встроены, открывается без сервера).
# Запуск: python -X utf8 build_viewer.py [папка_db]   (после rebuild.py; по умолчанию db/)
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'db')  # папка с library.json
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(DB, 'viewer.html')  # куда писать страницу
lib = json.load(open(os.path.join(DB, 'library.json'), encoding='utf-8'))
llm_p = os.path.join(DB, 'library_llm.json')
llm = {x['id']: x for x in json.load(open(llm_p, encoding='utf-8'))} if os.path.exists(llm_p) else {}
keep = []
for r in lib:
    k = {k: r.get(k) for k in ('id', 'kind', 'area', 'geom', 'why', 'graph', 'key', 'checks', 'count', 'source', 'rooms', 'edges', 'plan')}
    k['llm'] = llm.get(r['id'])
    keep.append(k)
tpl = open(os.path.join(HERE, 'viewer_template.html'), encoding='utf-8').read()
out = tpl.replace('/*DATA*/[]', json.dumps(keep, ensure_ascii=False, separators=(',', ':')))
p = OUT
open(p, 'w', encoding='utf-8').write(out)
print(p, len(keep), 'планировок', round(len(out) / 1e6, 2), 'МБ')
