"""Add original PDF fill outlines to matching saved sheet extracts.

Only the fill and line-assisted modes use extract.py's vector room polygons.
The wall/floor mask modes continue to use rectangle-union outlines.
"""
import json
from pathlib import Path

from extract import extract as extract_fills
from extract_lines import extract as extract_lines

ROOT = Path(__file__).resolve().parent
SOURCES = {'out_barkhatnaya': extract_fills, 'out_touch_checked': extract_lines}


def signature(room):
    return room['id'], round(room['area'], 2), tuple(map(tuple, room['rects']))


def main():
    matched = skipped = 0
    for directory, extractor in SOURCES.items():
        for path in sorted((ROOT / directory).glob('*.json')):
            if path.name.startswith('_') or path.name.startswith('library'):
                continue
            saved = json.loads(path.read_text(encoding='utf-8'))
            source = saved['source']
            page = 0
            if '#' in source:
                source, page = source.rsplit('#', 1)
                page = int(page)
            result = extractor(source, page)
            if result is None:
                skipped += 1
                continue
            fresh = result[0]
            candidates = {}
            for apartment in fresh['apartments']:
                for room in apartment['rooms']:
                    candidates.setdefault(signature(room), []).append(room)
            modified = False
            for apartment in saved['apartments']:
                for room in apartment['rooms']:
                    hits = candidates.get(signature(room), [])
                    if hits and hits[0].get('rings'):
                        room['rings'] = hits[0]['rings']
                        matched += 1
                        modified = True
                    else:
                        skipped += 1
            if modified:
                path.write_text(json.dumps(saved, ensure_ascii=False, indent=1), encoding='utf-8')
            print(path.name, 'rings' if modified else 'no match')
    print('rooms matched:', matched, 'skipped:', skipped)


if __name__ == '__main__':
    main()
