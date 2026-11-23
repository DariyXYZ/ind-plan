# Проверка PDF на «планировку с комнатами»: подписи помещений жилых типов на странице (до 6 стр.).
import sys, re
import fitz
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from extract import labels, is_pastel

ROOM = re.compile(r'спальн|жилая|санузел|с/у|прихож|кухн|гостин|детск|гардероб|ванн', re.I)
lst, out = sys.argv[1], sys.argv[2]
with open(out, 'w', encoding='utf-8') as fo:
    for p in (l.strip() for l in open(lst, encoding='utf-8') if l.strip()):
        try:
            d = fitz.open(p if p.startswith('X:') else 'X:/' + p)
            best = (0, 0, 0)
            for pno in range(min(len(d), 6)):
                pg = d[pno]
                labs, _, _ = labels(pg)
                nroom = sum(1 for l in labs if ROOM.search(l['fn']))
                if nroom > best[0]:
                    fills = sum(1 for x in pg.get_drawings() if x['type'] == 'f' and is_pastel(x.get('fill')))
                    best = (nroom, fills, pno)
            fo.write(f'{p}\t{best[0]}\t{best[1]}\t{best[2]}\n'); fo.flush()
        except Exception as e:
            fo.write(f'{p}\terr\t{type(e).__name__}\t0\n'); fo.flush()
