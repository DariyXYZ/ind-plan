"""Hand traced, schematic room zones for the four September QUBE PDFs.

Coordinates are pixels on the review renders, not surveyed dimensions. The
source PDFs remain authoritative; do not feed these zones to the generator.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def room(id, name, role, label, points):
    return dict(id=id, name_src=name, role=role, label_at=label,
                rings=[dict(outer=points, holes=[])], area=None)

TRACES = {
    'qube_a3_studio': (1180, [
        room('balcony','Балкон','balcony',[770,145],[[560,55],[1018,55],[1018,227],[560,227]]),
        room('living','Жилая комната','living',[790,480],[[548,264],[994,264],[994,718],[548,718]]),
        room('kitchen','Кухня','kitchen',[640,870],[[548,720],[765,720],[765,991],[548,991]]),
        room('hall','Прихожая','hall',[670,1050],[[612,992],[765,992],[765,1100],[612,1100]]),
        room('bath','С/У','bath',[885,930],[[777,805],[994,805],[994,1099],[777,1099]]),
    ], [['MOP','hall','entry'],['hall','kitchen','open'],['hall','bath','door'],['kitchen','living','open'],['living','balcony','balcony']]),
    'qube_a2_1br': (2150, [
        room('hall','Прихожая','hall',[800,525],[[773,270],[1020,395],[905,610],[680,740],[500,695]]),
        room('bath','С/У','bath',[1000,760],[[942,514],[1135,610],[1135,870],[1040,920],[826,800]]),
        room('living','Гостиная','living',[570,1110],[[451,670],[803,850],[1030,940],[1050,1450],[710,1550],[163,1284]]),
        room('kitchen','Кухня-столовая','kitchen',[1100,1250],[[1057,940],[1280,940],[1280,1650],[1057,1650]]),
        room('bedroom','Спальня','bedroom',[880,1870],[[595,1680],[1257,1680],[1257,2090],[595,2090]]),
        room('balcony','Балкон','balcony',[300,1750],[[25,1470],[503,1470],[503,2110],[125,2110]]),
    ], [['MOP','hall','entry'],['hall','bath','door'],['hall','living','open'],['living','kitchen','open'],['living','bedroom','door'],['living','balcony','balcony']]),
    'qube_a1_2br': (1180, [
        room('balcony','Балкон','balcony',[715,285],[[500,182],[834,350],[1154,161],[1172,190],[836,385],[485,210]]),
        room('bed1','Спальня 1','bedroom',[420,505],[[400,340],[631,478],[527,691],[258,614]]),
        room('bath1','С/У 1','bath',[300,782],[[240,646],[493,760],[386,969],[126,806]]),
        room('living','Гостиная','living',[822,620],[[634,478],[846,396],[1030,450],[1135,675],[1000,795],[530,760]]),
        room('bed2','Спальня 2','bedroom',[1160,390],[[985,344],[1180,210],[1337,484],[1165,586]]),
        room('bath2','С/У 2','bath',[1270,630],[[1180,555],[1350,494],[1437,657],[1280,731]]),
        room('kitchen','Кухня-столовая','kitchen',[1100,830],[[1000,795],[1135,675],[1280,731],[1320,980],[1156,1028],[990,1028]]),
        room('hall','Прихожая','hall',[1360,860],[[1280,731],[1437,657],[1520,810],[1320,980]]),
    ], [['MOP','hall','entry'],['hall','bath2','door'],['hall','kitchen','open'],['kitchen','living','open'],['living','bed1','door'],['bed1','bath1','door'],['living','bed2','door'],['bed2','bath2','door'],['living','balcony','balcony']]),
    'qube_a6_3br': (1090, [
        room('hall','Прихожая / коридор','hall',[710,230],[[383,38],[1010,38],[1010,355],[383,355]]),
        room('bath1','Гостевой С/У','bath',[298,225],[[224,65],[370,65],[370,355],[224,355]]),
        room('bed1','Спальня 1','bedroom',[350,790],[[226,640],[468,640],[468,1010],[226,1010]]),
        room('living','Гостиная','living',[760,670],[[518,382],[1000,382],[1000,860],[518,860]]),
        room('kitchen','Кухня-столовая','kitchen',[730,480],[[518,383],[1000,383],[1000,580],[518,580]]),
        room('balcony','Балкон','balcony',[750,950],[[515,880],[990,880],[990,1031],[515,1031]]),
        room('bath2','С/У 2','bath',[1085,198],[[1017,31],[1170,31],[1170,357],[1017,357]]),
        room('bed2','Спальня 2','bedroom',[1320,270],[[1180,31],[1460,31],[1460,464],[1180,464]]),
        room('bath3','С/У 3','bath',[1270,590],[[1172,482],[1370,482],[1370,688],[1172,688]]),
        room('bed3','Спальня 3','bedroom',[1170,861],[[1018,739],[1370,739],[1370,1030],[1018,1030]]),
    ], [['MOP','hall','entry'],['hall','bath1','door'],['hall','bath2','door'],['hall','living','open'],['hall','bed2','door'],['living','bed1','door'],['living','bed3','door'],['bed3','bath3','door'],['living','kitchen','open'],['living','balcony','balcony']]),
}

def transform(p, height):
    return [p[0]*10, (height-p[1])*10]

records = json.loads((ROOT/'source_refs.json').read_text(encoding='utf-8'))
for record in records:
    height, rooms, edges = TRACES[record['id']]
    for r in rooms:
        r['label_at'] = transform(r['label_at'], height)
        for ring in r['rings']:
            ring['outer'] = [transform(p, height) for p in ring['outer']]
    record['rooms'] = rooms
    record['edges'] = [dict(between=[a,b],type=kind) for a,b,kind in edges]
    record['geom'] = 'approx'
    record['trace'] = 'schematic hand trace of September interior PDF; coordinates are not millimetres'
    record['graph'] = ' · '.join(f'{a}—{b} ({kind})' for a,b,kind in edges)
(ROOT/'source_refs.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
