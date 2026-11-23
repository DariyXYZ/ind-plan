"""Rank validated IND apartment plans from the SQLite index."""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / 'db' / 'plans.sqlite'
MUST = {'wardrobe', 'kids', 'laundry', 'master_bath', 'separate_kitchen'}


def find(type=None, w=None, d=None, facades=None, entry=None, must=(), k=10,
         bedrooms=None, db_path=DB):
    """Return ranked plans with human-readable fit reasons; dimensions are millimetres."""
    must = set(must or ())
    unknown = must - MUST
    if unknown:
        raise ValueError(f'Unknown required traits: {sorted(unknown)}')
    if k < 1:
        return []
    where = ['1=1']
    args = []
    if type:
        where.append('kind = ?'); args.append(type)
    if bedrooms is not None:
        where.append('bedrooms = ?'); args.append(bedrooms)
    for trait in sorted(must):
        where.append(f'{trait} = 1')
    with sqlite3.connect(db_path) as db:
        rows = db.execute('SELECT payload FROM plans WHERE ' + ' AND '.join(where), args).fetchall()
    ranked = []
    for (payload,) in rows:
        plan = json.loads(payload)
        key = plan['key']
        score = 0.0
        reasons = []
        if type:
            reasons.append(f'тип {type}')
        if w and d:
            diff = min((abs(key['w'] - w) / max(w, 1) + abs(key['d'] - d) / max(d, 1),
                        abs(key['w'] - d) / max(d, 1) + abs(key['d'] - w) / max(w, 1)))
            score += diff * 100
            reasons.append(f'габарит {key["w"]}×{key["d"]} мм')
        if facades is not None:
            score += 15 * abs(key['facades'] - facades)
            if key['facades'] == facades:
                reasons.append(f'{facades} фасад(а)')
        if entry:
            if key['entry'] != entry:
                score += 12
            else:
                reasons.append(f'вход в {entry}')
        if must:
            reasons.append('есть ' + ', '.join(sorted(must)))
        score += 3 if plan['geom'] == 'approx' else 0
        ranked.append({'id': plan['id'], 'score': round(score, 2),
                       'reasons': reasons, 'plan': plan})
    ranked.sort(key=lambda x: (x['score'], -x['plan']['count'], x['id']))
    return ranked[:k]


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--type')
    p.add_argument('--w', type=int)
    p.add_argument('--d', type=int)
    p.add_argument('--facades', type=int)
    p.add_argument('--entry')
    p.add_argument('--bedrooms', type=int)
    p.add_argument('--must', nargs='*', default=[])
    p.add_argument('-k', type=int, default=10)
    a = vars(p.parse_args())
    print(json.dumps(find(**a), ensure_ascii=False, indent=2))
