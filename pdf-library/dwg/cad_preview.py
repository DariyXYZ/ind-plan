"""Чертёж квартиры из DXF для каталога: стены, двери, подписи — как в DWG, без распознавания комнат.
Пишет поле `cad_svg` в catalog/source_refs.json (координаты мм, ось Y вверх → в SVG перевёрнута).
Запуск: python -X utf8 cad_preview.py <файл.dxf>=<id в source_refs> ...
"""
import json
import sys
from pathlib import Path

import ezdxf
from shapely.geometry import box
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_dwg as X  # noqa: E402

REFS = Path(__file__).resolve().parents[2] / 'catalog' / 'source_refs.json'


def d_poly(g, f):
    out = []
    for p in getattr(g, 'geoms', [g]):
        if p.geom_type != 'Polygon' or p.is_empty:
            continue
        for ring in [p.exterior, *p.interiors]:
            out.append('M' + 'L'.join(f(x, y) for x, y in ring.coords) + 'Z')
    return ''.join(out)


def preview(dxf):
    m = ezdxf.readfile(dxf).modelspace()
    labs = X.labels(m)
    walls = X.wall_geometry(m)
    lx = [l['at'][0] for l in labs]; ly = [l['at'][1] for l in labs]
    # рамка = стены, связанные с подписями
    frame = box(min(lx) - 6000, min(ly) - 6000, max(lx) + 6000, max(ly) + 6000)
    walls = walls.intersection(frame)
    near = unary_union([p for p in getattr(walls, 'geoms', [walls]) if p.distance(box(min(lx), min(ly), max(lx), max(ly))) < 3000])
    x0, y0, x1, y1 = near.bounds
    pad = 300
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    f = lambda x, y: f'{round(x - x0)} {round(y1 - y)}'
    walls_d = d_poly(near.simplify(5), f)
    doors_d = ''.join('M' + 'L'.join(f(x, y) for x, y in l.coords) for l in X.door_geometry(m)
                      if l.intersects(box(x0, y0, x1, y1)))
    texts = [{'x': round(l['at'][0] - x0), 'y': round(y1 - l['at'][1]), 'name': l['name'].title(), 'area': l['area']} for l in labs]
    return {'w': round(x1 - x0), 'h': round(y1 - y0), 'walls': walls_d, 'doors': doors_d, 'labels': texts}


if __name__ == '__main__':
    refs = json.loads(REFS.read_text(encoding='utf-8'))
    by = {r['id']: r for r in refs}
    for arg in sys.argv[1:]:
        dxf, rid = arg.split('=', 1)
        by[rid]['cad_svg'] = preview(dxf)
        print(rid, by[rid]['cad_svg']['w'], by[rid]['cad_svg']['h'], len(by[rid]['cad_svg']['walls']))
    REFS.write_text(json.dumps(refs, ensure_ascii=False, indent=1), encoding='utf-8')
