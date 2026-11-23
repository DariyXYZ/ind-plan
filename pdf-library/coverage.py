"""Generate a compact, repeatable coverage report for the indexed plans."""
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    plans = json.loads((ROOT / 'db' / 'library.json').read_text(encoding='utf-8'))
    by_type = collections.defaultdict(list)
    for p in plans:
        by_type[p['kind']].append(p)
    lines = ['# Покрытие библиотеки IND', '',
             f'Планировок: **{len(plans)}**. Источники: ' + ', '.join(
                 f'{name} — {n}' for name, n in collections.Counter(
                     p['source']['project'] for p in plans).most_common()) + '.', '',
             '| Тип | До 40 м² | 40–60 | 60–80 | 80–120 | Более 120 | Всего |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for kind, group in sorted(by_type.items()):
        bins = [sum(lo <= p['area'] < hi for p in group)
                for lo, hi in ((0, 40), (40, 60), (60, 80), (80, 120), (120, float('inf')))]
        lines.append(f'| {kind} | ' + ' | '.join(map(str, bins)) + f' | {len(group)} |')
    lines += ['', '## Признаки', '', '| Признак | Есть | Нет |', '|---|---:|---:|']
    traits = ('wardrobe', 'kids', 'master_bath', 'laundry', 'separate_kitchen')
    for trait in traits:
        yes = sum(bool(p['key'][trait]) for p in plans)
        lines.append(f'| {trait} | {yes} | {len(plans) - yes} |')
    lines += ['', '## Пустые сочетания', '']
    for kind in sorted(by_type):
        for trait in traits:
            if not any(p['key'][trait] for p in by_type[kind]):
                lines.append(f'- {kind} + {trait}')
    (ROOT / 'coverage.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
