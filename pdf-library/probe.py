# Быстрая проверка PDF: похож ли лист на планировку IND, которую читает extract.py
# (цветные заливки помещений + подписи «Название / NN.NN м²»). Вход — список путей в файле, выход — TSV.
import sys, os, re, random, collections
import fitz
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import labels, is_pastel

lst, out = sys.argv[1], sys.argv[2]
paths = [l.strip() for l in open(lst, encoding='utf-8') if l.strip()]
with open(out, 'w', encoding='utf-8') as fo:
    for p in paths:
        try:
            d = fitz.open('X:/' + p if not p.startswith(('X:', '/')) else p)
            best = (0, 0, 0, 0)
            for pno in range(min(len(d), 4)):
                pg = d[pno]
                labs, totals, wins = labels(pg)
                fills = sum(1 for x in pg.get_drawings() if x['type'] == 'f' and is_pastel(x.get('fill')))
                sc = min(len(labs), fills)
                if sc > best[0]: best = (sc, len(labs), fills, pno)
            fo.write(f'{p}\t{len(d)}\t{best[1]}\t{best[2]}\t{best[3]}\n'); fo.flush()
        except Exception as e:
            fo.write(f'{p}\terr\t{type(e).__name__}\n'); fo.flush()
