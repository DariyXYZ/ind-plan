"""Diagnostic for Touch Dovzhenko: candidate double-line walls, not an extractor.

Run on a PDF and page index. The overlay highlights only candidate wall axes;
it must be checked against the PDF before any plan enters the library.
"""
from __future__ import annotations

import argparse
import collections
from pathlib import Path

import fitz
from PIL import Image, ImageDraw


def segments(page):
    out = {'h': [], 'v': []}
    for drawing in page.get_drawings():
        if drawing['type'] != 's' or drawing['color'] != (0.0, 0.0, 0.0):
            continue
        if not 0.20 <= (drawing['width'] or 0) <= 1.10:
            continue
        for item in drawing['items']:
            if item[0] != 'l':
                continue
            a, b = item[1:3]
            if abs(a.y - b.y) < 0.05 and abs(a.x - b.x) >= 10:
                out['h'].append((a.y, min(a.x, b.x), max(a.x, b.x)))
            elif abs(a.x - b.x) < 0.05 and abs(a.y - b.y) >= 10:
                out['v'].append((a.x, min(a.y, b.y), max(a.y, b.y)))
    return out


def pairs(lines, min_sep=1.6, max_sep=5.0, min_overlap=10):
    lines = sorted(lines)
    out = []
    for i, (p, a, b) in enumerate(lines):
        for q, c, d in lines[i + 1:]:
            if q - p > max_sep:
                break
            overlap = min(b, d) - max(a, c)
            if min_sep <= q - p and overlap >= min_overlap:
                out.append(((p + q) / 2, max(a, c), min(b, d), q - p))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('pdf', type=Path)
    p.add_argument('page', type=int)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    page = fitz.open(args.pdf)[args.page]
    lines = segments(page)
    pair_axes = {axis: pairs(items) for axis, items in lines.items()}
    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
    image = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
    draw = ImageDraw.Draw(image, 'RGBA')
    scale = 1.5
    for y, x0, x1, _ in pair_axes['h']:
        draw.line((x0 * scale, y * scale, x1 * scale, y * scale), fill=(255, 0, 0, 160), width=3)
    for x, y0, y1, _ in pair_axes['v']:
        draw.line((x * scale, y0 * scale, x * scale, y1 * scale), fill=(255, 0, 0, 160), width=3)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output)
    print(f'raw segments: {sum(map(len, lines.values()))}; pairs: '
          f'{collections.Counter({axis: len(v) for axis, v in pair_axes.items()})}')


if __name__ == '__main__':
    main()
