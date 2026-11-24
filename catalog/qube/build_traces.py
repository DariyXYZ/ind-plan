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
        room('hall','Кухня-прихожая','hall',[665,884],[[548,720],[765,720],[765,1100],[612,1100],[612,1018],[548,1018]]),
        room('bath','С/У','bath',[885,930],[[777,805],[994,805],[994,1099],[777,1099]]),
    ], [['MOP','hall','entry'],['hall','bath','door'],['hall','living','open'],['living','balcony','balcony']]),
    'qube_a2_1br': (2150, [
        room('hall','Прихожая','hall',[810,525],[[773,250],[1020,385],[902,610],[809,790],[556,663]]),
        room('bath','С/У 1','bath',[1000,735],[[942,510],[1137,607],[1137,866],[1047,926],[815,804]]),
        room('living','Гостиная','living',[620,1170],[[556,665],[809,790],[815,804],[1047,926],[1057,940],[1057,1640],[710,1640],[163,1284]]),
        room('kitchen','Кухня-столовая','kitchen',[1140,1280],[[1057,940],[1280,940],[1280,1650],[1057,1650]]),
        room('bedroom','Спальня','bedroom',[940,1870],[[596,1670],[1259,1670],[1259,2108],[596,2108]]),
        room('bath2','С/У 2','bath',[1450,1910],[[1295,1748],[1625,1748],[1625,2108],[1295,2108]]),
        room('balcony','Балкон','balcony',[295,1800],[[163,1284],[535,1475],[535,2110],[129,2110],[25,1535]]),
    ], [['MOP','hall','entry'],['hall','bath','door'],['hall','living','open'],['living','kitchen','open'],['living','bedroom','door'],['bedroom','bath2','door'],['living','balcony','balcony']]),
    'qube_a1_2br': (1180, [
        room('balcony','Балкон','balcony',[710,319],[[500,182],[834,350],[1154,161],[1180,220],[995,405],[836,500],[635,480],[450,300]]),
        room('bed1','Спальня 1','bedroom',[420,505],[[400,340],[631,478],[527,691],[258,614]]),
        room('bath1','С/У 1','bath',[300,782],[[240,646],[493,760],[386,969],[126,806]]),
        room('living','Гостиная','living',[822,620],[[634,478],[846,440],[1030,450],[1135,675],[1000,795],[530,760]]),
        room('bed2','Спальня 2','bedroom',[1160,390],[[985,344],[1180,210],[1337,484],[1165,586]]),
        room('bath2','С/У 2','bath',[1270,630],[[1180,555],[1350,494],[1437,657],[1280,731]]),
        room('kitchen','Кухня-столовая','kitchen',[1100,830],[[1000,795],[1135,675],[1280,731],[1320,980],[1156,1028],[990,1028]]),
        room('hall','Прихожая','hall',[1360,860],[[1280,731],[1437,657],[1520,810],[1320,980]]),
    ], [['MOP','hall','entry'],['hall','bath2','door'],['hall','kitchen','open'],['kitchen','living','open'],['living','bed1','door'],['bed1','bath1','door'],['living','bed2','door'],['bed2','bath2','door'],['living','balcony','balcony']]),
    'qube_a6_3br': (1090, [
        room('hall','Прихожая / коридор','hall',[705,315],[[382,248],[1010,248],[1010,365],[480,365],[480,620],[382,620]]),
        room('bath1','Гостевой С/У','bath',[300,325],[[225,248],[370,248],[370,381],[225,381]]),
        room('bath2','С/У 2','bath',[300,520],[[225,382],[370,382],[370,640],[225,640]]),
        room('bed1','Спальня 1','bedroom',[350,820],[[225,642],[470,642],[470,1030],[225,1030]]),
        room('kitchen','Кухня-столовая','kitchen',[735,460],[[518,382],[1000,382],[1000,522],[518,522]]),
        room('living','Гостиная','living',[760,710],[[518,523],[1000,523],[1000,867],[518,867]]),
        room('balcony','Балкон','balcony',[750,950],[[515,875],[990,875],[990,1031],[515,1031]]),
        room('laundry','Постирочная','laundry',[698,130],[[477,26],[1010,26],[1010,245],[477,245]]),
        room('bath3','С/У 3','bath',[1080,190],[[1017,26],[1168,26],[1168,357],[1017,357]]),
        room('bed2','Спальня 2','bedroom',[1320,235],[[1180,26],[1460,26],[1460,464],[1180,464]]),
        room('corr','Коридор','corridor',[1080,550],[[1017,365],[1166,365],[1166,738],[1017,738]]),
        room('bath4','С/У 4','bath',[1260,585],[[1172,482],[1370,482],[1370,687],[1172,687]]),
        room('bed3','Спальня 3','bedroom',[1180,860],[[1018,739],[1370,739],[1370,1030],[1018,1030]]),
    ], [['MOP','hall','entry'],['hall','bath1','door'],['hall','bath2','door'],['hall','laundry','door'],['hall','bath3','door'],['hall','kitchen','open'],['hall','bed1','door'],['kitchen','living','open'],['living','corr','door'],['corr','bed2','door'],['corr','bath4','door'],['corr','bed3','door'],['living','balcony','balcony']]),
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
    record['trace_canvas_height_px'] = height
    record['source_image_size_px'] = [1668, 2358 if record['id']=='qube_a2_1br' else 1179]
    record['graph'] = ' · '.join(f'{a}—{b} ({kind})' for a,b,kind in edges)
(ROOT/'source_refs.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
