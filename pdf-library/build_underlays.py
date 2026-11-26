"""Render source PDF crops in catalog coordinates. Run before build_viewer.py."""
import io
import json
import re
from collections import defaultdict
from pathlib import Path

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'catalog'
OUTPUT = CATALOG / 'underlays'

# Registration against the illustrated QUBE PDFs. A1/A2/A3 use older
# drawings than their catalog graphs, so their alignment is approximate.
# Each tuple gives source rotation (None keeps it), PDF origin and mm per point.
def qube_registration(plan_id, sheet):
    if plan_id == 'qube_003':
        sx, sy = 660 / 11940, 571 / 11020
        origin = ((315 - sx * 4040) / .923, (110 + sy * 11160) / .923)
        return CATALOG / 'qube' / f'{sheet}.pdf', 0, None, origin, (.923 / sx, .923 / sy), False
    if plan_id == 'qube_002':
        sx, sy = 803 / 18040, 488 / 10920
        origin = ((72 - sx * 2430) / .8, (588 + sy * 1490) / .8)
        rotation = None
    elif plan_id == 'qube_001':
        sx, sy = 1078 / 12700, 890 / 10460
        origin = ((134 - sx * 2340) / .8, 1191 - (39 - sy * 1600) / .8)
        rotation = 270
    else:
        sx = sy = .063
        origin = ((307 - sx * 1610) / .8, (30 + sy * 11590) / .8)
        rotation = None
    return CATALOG / 'qube' / f'{sheet}.pdf', 0, rotation, origin, (.8 / sx, .8 / sy), True


def registrations():
    index = defaultdict(list)
    for path in sorted((ROOT / 'pdf-library').glob('out_*/*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            continue
        scale = data.get('meta', {}).get('mm_per_unit')
        for apt in data.get('apartments', []):
            if scale and apt.get('origin_pdf_units'):
                index[path.stem].append((data['source'], apt, scale))
    return index


def registration(plan, index):
    source = plan['source']
    sheet = source['floor']
    if plan['id'].startswith('qube_'):
        return qube_registration(plan['id'], sheet)
    file = Path(source['file'])
    matches = set()
    signature = {r['id']: r['rects'] for r in plan['rooms']}
    for original, apt, scale in index[sheet]:
        if Path(original.split('#')[0]) == file and signature == {r['id']: r['rects'] for r in apt['rooms']}:
            matches.add((tuple(apt['origin_pdf_units']), scale))
    if len(matches) != 1:
        raise ValueError(f'{plan["id"]}: ambiguous or missing apartment origin')
    origin, scale = matches.pop()
    suffix = re.search(r'_p(\d+)$', sheet)
    page = source.get('page')
    if page is None:
        page = int(suffix[1]) if suffix else 0
    return file, page, 0, origin, (scale, scale), False


def render(plan, graph, source, documents):
    file, page_number, rotation, (ox, oy), (sx, sy), approximate = source
    if file not in documents:
        documents[file] = fitz.open(file)
    page = documents[file][page_number]
    if rotation is not None:
        page.set_rotation(rotation)
    xs = [node['X'] for node in graph['Nodes']]
    ys = [node['Y'] for node in graph['Nodes']]
    clip = fitz.Rect(ox + (min(xs) - 750) / sx, oy - (max(ys) + 750) / sy,
                     ox + (max(xs) + 750) / sx, oy - (min(ys) - 750) / sy)
    clip &= page.rect
    if clip.is_empty:
        raise ValueError(f'{plan["id"]}: crop outside of page')
    zoom = 1500 / max(clip.width, clip.height)
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip, alpha=False)
    left, top = pix.x / zoom, pix.y / zoom
    image = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
    buffer = io.BytesIO()
    image.save(buffer, format='WEBP', quality=88)
    name = f'{plan["id"]}.webp'
    data = buffer.getvalue()
    return name, data, {'file': f'underlays/{name}', 'x': round((left - ox) * sx, 2),
                        'y': round((oy - top) * sy, 2),
                        'w': round(pix.width * sx / zoom, 2), 'h': round(pix.height * sy / zoom, 2),
                        'approximate': approximate}


def main():
    plans = json.loads((CATALOG / 'library.json').read_text(encoding='utf-8'))
    graphs = {g['Id']: g for g in json.loads((CATALOG / 'contour_graphs.json').read_text(encoding='utf-8'))}
    index = registrations()
    documents, manifest = {}, {}
    OUTPUT.mkdir(exist_ok=True)
    for plan in plans:
        plan_id = plan['id']
        name, data, entry = render(plan, graphs[plan_id], registration(plan, index), documents)
        (OUTPUT / name).write_bytes(data)
        manifest[plan_id] = entry
    (OUTPUT / 'index.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'{len(manifest)} underlays')


if __name__ == '__main__':
    main()
