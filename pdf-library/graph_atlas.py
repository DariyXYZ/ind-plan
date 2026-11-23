# Атлас графов: все квартиры библиотеки маленькими графами поверх силуэта плана, по типам и схемам.
import sys, os, json, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'engine'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import fit as F

OUT = sys.argv[1] if len(sys.argv) > 1 else 'graph_atlas.png'
plt.rcParams['font.family'] = 'Arial'

COL = {'kl': '#E8833A', 'bed': '#7B61C9', 'wet': '#2C9CC9', 'hall': '#5B6573', 'corr': '#8A94A3', 'laundry': '#2C9CC9', 'wr': '#A3A07A', 'store': '#A3A07A', 'other': '#A3A07A'}
LAB = [('kl', 'кухня-гостиная'), ('bed', 'спальня'), ('wet', 'санузел / постирочная'), ('hall', 'прихожая'), ('corr', 'коридор')]
TYPES = ['ST', '2E', '3E', '4E', '5E']
TNAME = {'ST': 'Студии', '2E': 'Евро-2', '3E': 'Евро-3', '4E': 'Евро-4', '5E': 'Евро-5'}

lib = {e['id']: e for e in json.load(open(F.PDF_LIB, encoding='utf-8'))}
refs = {r['id']: r for r in F.load_refs()}
TYPE = {'ст': 'ST', '2к': '2E', '3к': '3E', 'Евро-4': '4E', '5к': '5E'}


def scheme(r):
    return ' '.join(sorted({'-'.join(sorted((F.kind_of(a), F.kind_of(b)))) + ('o' if op else '') for a, b, op in r['links']}))


groups = collections.defaultdict(list)
for i, r in refs.items():
    groups[TYPE.get(lib[i]['kind'], '?')].append(r)

COLS = 12
rows_per = {t: -(-len(groups[t]) // COLS) for t in TYPES}
cell = 1.0
H = sum(rows_per[t] for t in TYPES) * cell + len(TYPES) * 0.55 + 1.2
fig = plt.figure(figsize=(COLS * 1.25, H * 1.25), dpi=170)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, COLS); ax.set_ylim(H, 0); ax.axis('off')
fig.patch.set_facecolor('white')

ax.text(0.15, 0.42, f'Как устроены квартиры IND: {len(refs)} планировок — ЖК Бархатная и Etalon Fotieva (рамка)', fontsize=17, fontweight='bold', color='#1F2329', va='center')
x = 0.15
for k, lab in LAB:
    ax.add_patch(plt.Circle((x + 0.07, 0.85), 0.06, color=COL[k])); ax.text(x + 0.18, 0.85, lab, fontsize=9, va='center', color='#3A3F47'); x += 1.55
ax.plot([x + 0.05, x + 0.35], [0.85, 0.85], color='#3A3F47', lw=1.4); ax.text(x + 0.42, 0.85, 'дверь', fontsize=9, va='center', color='#3A3F47'); x += 1.0
ax.plot([x + 0.05, x + 0.35], [0.85, 0.85], color='#3A3F47', lw=1.4, ls=(0, (2, 1.5))); ax.text(x + 0.42, 0.85, 'проём', fontsize=9, va='center', color='#3A3F47')

y = 1.2
for t in TYPES:
    G = groups[t]
    if not G: continue
    cnt = collections.Counter(scheme(r) for r in G)
    G.sort(key=lambda r: (-cnt[scheme(r)], scheme(r), lib[r['id']]['key']['area']))
    top = cnt.most_common(1)[0][1]
    ax.text(0.15, y + 0.22, f'{TNAME[t]} · {len(G)}', fontsize=12, fontweight='bold', color='#1F2329', va='center')
    ax.text(2.2, y + 0.22, f'самая частая схема — {top} из {len(G)}', fontsize=9, color='#6B7280', va='center')
    y += 0.45
    for i, r in enumerate(G):
        cx, cy = i % COLS, y + (i // COLS) * cell
        s = 0.86 / max(r['W'], r['D'])
        ox = cx + (1 - r['W'] * s) / 2; oy = cy + (cell - r['D'] * s) / 2 - 0.03
        same = cnt[scheme(r)] > 1
        if r['id'].startswith('fot'):
            ax.add_patch(Rectangle((cx + 0.04, cy + 0.02), 0.92, cell - 0.04, fc='none', ec='#E8833A', lw=1.2, zorder=4))
        for n, rs in r['rooms'].items():
            for q in rs:
                ax.add_patch(Rectangle((ox + q[0] * s, oy + q[1] * s), (q[2] - q[0]) * s, (q[3] - q[1]) * s, fc='#F3F4F6', ec='#D9DCE1', lw=0.4))
        ctr = {}
        for n, rs in r['rooms'].items():
            A = sum((q[2] - q[0]) * (q[3] - q[1]) for q in rs)
            q = max(rs, key=lambda q: (q[2] - q[0]) * (q[3] - q[1]))
            ctr[n] = (ox + (q[0] + q[2]) / 2 * s, oy + (q[1] + q[3]) / 2 * s, A)
        for a, b, op in r['links']:
            if a in ctr and b in ctr:
                ax.plot([ctr[a][0], ctr[b][0]], [ctr[a][1], ctr[b][1]], color='#3A3F47', lw=0.9, ls=(0, (2, 1.5)) if op else '-', zorder=2)
        for n, (px, py, A) in ctr.items():
            ax.add_patch(plt.Circle((px, py), 0.025 + 0.012 * min(A / 2e7, 1.5), color=COL.get(F.kind_of(n), '#A3A07A'), zorder=3))
        ax.text(cx + 0.5, cy + cell - 0.06, f"{lib[r['id']]['key']['area']:.1f} м²", fontsize=6.5, ha='center', color='#6B7280')
    y += rows_per[t] * cell + 0.1
fig.savefig(OUT, facecolor='white')
print(OUT)
