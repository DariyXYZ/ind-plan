"""Experimental Touch Dovzhenko extraction using paired vector wall strokes.

The candidate wall axes are added to the filled-wall mask. The unchanged
apartment checks in extract.py decide whether a result is usable.
"""
import fitz

from extract import extract as extract_fills
from probe_line_pairs import pairs, segments


def extract(pdf, pno=0):
    page = fitz.open(pdf)[pno]
    lines = segments(page)
    axes = {direction: pairs(items) for direction, items in lines.items()}
    return extract_fills(pdf, pno, extra_wall_axes=axes)
