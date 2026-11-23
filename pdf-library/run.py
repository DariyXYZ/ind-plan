import sys, json, os, glob, colorsys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
from extract import extract
if os.environ.get('MODE') == 'walls': from extract_walls import extract
if os.environ.get('MODE') == 'lines': from extract_lines import extract
if os.environ.get('MODE') == 'floor': from extract_floor import extract

OUT = sys.argv[1]
files = sys.argv[2:]
os.makedirs(OUT, exist_ok=True)
try: F = ImageFont.truetype('arialbd.ttf', 22)
except Exception: F = ImageFont.load_default()
COL = {'door': (220, 40, 40), 'open': (40, 120, 220), 'entry': (20, 150, 60), 'balcony': (170, 170, 170)}
summary = []
for f in files:
    name = os.path.basename(os.path.dirname(f))[:10] + '__' + os.path.splitext(os.path.basename(f))[0]
    try:
        pno = 0
        if '#' in f: f, pno = f.rsplit('#', 1); pno = int(pno); name += f'_p{pno}'
        r = extract(f, pno)
    except Exception as e:
        summary.append({'file': f, 'error': repr(e)}); print('ERR', f, e); continue
    if not r: summary.append({'file': f, 'error': 'нет заливок/подписей'}); continue
    data, dbg = r
    data['source'] = f
    json.dump(data, open(f'{OUT}/{name}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # картинка проверки
    R, W = dbg['R'], dbg['W']
    H_, W_ = R.shape
    img = np.full((H_, W_, 3), 255, np.uint8)
    rng = np.random.default_rng(1)
    pal = {r['k']: tuple(int(c * 255) for c in colorsys.hsv_to_rgb(rng.random(), 0.25, 0.97)) for r in dbg['rooms']}
    for k, c in pal.items(): img[R == k] = c
    img[W] = (70, 70, 70)
    im = Image.fromarray(img); d = ImageDraw.Draw(im)
    rooms = {r['k']: r for r in dbg['rooms']}
    ctr = {k: dbg['tp'](r['lab']['pt']) for k, r in rooms.items()}
    for a, b, kind, w in dbg['edges']:
        if a == 'MOP':
            p = ctr[b]; d.line([p, (p[0], p[1] - 0)], fill=COL[kind], width=6)
            d.ellipse([p[0] - 26, p[1] - 26, p[0] + 26, p[1] + 26], outline=COL['entry'], width=6)
            continue
        d.line([ctr[a], ctr[b]], fill=COL[kind], width=6 if kind == 'door' else 4)
    for k, r in rooms.items():
        x, y = ctr[k]
        bad = abs(r['dev']) > 0.03 and not any(w in r['lab']['fn'].lower() for w in ('балкон','патио'))
        d.ellipse([x - 14, y - 14, x + 14, y + 14], fill=(200, 0, 0) if bad else (40, 40, 40))
        d.text((x, y + 30), f"{r['lab']['fn'][:10]} {r['lab']['area']}", fill='black', font=F, anchor='mm')
    for ap in data['apartments']:
        pass
    im.thumbnail((2400, 2400)); im.save(f'{OUT}/{name}.png')
    m = data['meta']
    ok = sum(a['check_total'] for a in data['apartments']); n = len(data['apartments'])
    summary.append({'file': f, 'name': name, **m, 'apartments': n, 'apartments_total_ok': ok,
                    'apts': [(round(a['area_rooms'], 2), a['total_on_sheet'], len(a['rooms']),
                              sum(1 for l in a['links'] if l['type'] == 'entry')) for a in data['apartments']]})
    print(name, 'кв', n, 'итог сошёлся', ok, '| мм/ед', m['mm_per_unit'], 'макс.откл.площ', m['area_dev_max'], '| 2 подписи в заливке', m['labels_in_one_fill'])
json.dump(summary, open(f'{OUT}/_summary.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
