import json,os
from PIL import Image,ImageDraw,ImageFilter
import numpy as np
from skimage import measure
D=os.path.dirname(os.path.abspath(__file__))
P=json.load(open(D+'/rh/plans.json',encoding='utf-8'))
PX=20.0 # mm per px
CUT=json.load(open(D+'/rh/cuts.json',encoding='utf-8'))  # условные границы (пунктир) и доп. подписи, в единицах svg = px
out={}
for key in ['v1','v2','v3']:
    items=P[key]
    xs=[x for e in items for pl,_ in e.get('p',[]) for x,y in pl]; ys=[y for e in items for pl,_ in e.get('p',[]) for x,y in pl]
    x0,y0,x1,y1=min(xs)-300,min(ys)-300,max(xs)+300,max(ys)+300
    W=int((x1-x0)/PX)+1;H=int((y1-y0)/PX)+1
    im=Image.new('L',(W,H),0);dr=ImageDraw.Draw(im)
    for e in items:
        if e['k']=='fillsec':
            for pl,cl in e['p']:
                pts=[((x-x0)/PX,(y1-y)/PX) for x,y in pl]
                if len(pts)>2: dr.polygon(pts,fill=255)
    for x1_,y1_,x2_,y2_ in CUT.get(key,{}).get('cut',[]): dr.line([(x1_,y1_),(x2_,y2_)],fill=255,width=2)
    IT=34 if key=="v1" else 26
    for _ in range(IT): im=im.filter(ImageFilter.MaxFilter(3))
    for _ in range(IT): im=im.filter(ImageFilter.MinFilter(3))
    ImageDraw.floodfill(im,(1,1),100)
    rooms=[];seen={}
    extra=[{'k':'text','t':t,'xy':[x0+ux*PX,y1-uy*PX]} for t,ux,uy in CUT.get(key,{}).get('lab',[])]
    for e in items+extra:
        if e['k']!='text' or not e['t'].strip(): continue
        x,y=e['xy'];px=(int((x-x0)/PX),int((y1-y)/PX))
        v=im.getpixel(px)
        name=e['t'].strip().replace('\n',' ')
        sx,sy=round((x-x0)*0.05,1),round((y1-y)*0.05,1)
        if v==0:
            col=len(seen)+1; ImageDraw.floodfill(im,px,col)
            n=sum(1 for p in im.get_flattened_data() if p==col)
            seen[col]=len(rooms); rooms.append({'n':name,'a':round(n*PX*PX/1e6,1),'x':sx,'y':sy})
        elif v in seen:
            rooms.append({'n':name,'a':None,'x':sx,'y':sy,'g':seen[v]})
        else: rooms.append({'n':name,'a':None,'x':sx,'y':sy,'bad':v})
    A=np.array(im)
    for col,ri in seen.items():
        cs=measure.find_contours((A==col).astype(float),0.5)
        cs=[measure.approximate_polygon(c,1.0) for c in cs if len(c)>8]
        d=''.join('M'+' '.join('%g %g'%(round(x+.5,1),round(y+.5,1)) for y,x in c)+'Z' for c in cs)
        rooms[ri]['p']=d
    im.save(D+f'/rh/{key}_mask.png')
    out[key]=rooms
    print(key,[(r['n'],r['a'],r.get('g'),r.get('bad')) for r in rooms], 'sum',round(sum(r['a'] or 0 for r in rooms),1))
json.dump(out,open(D+'/rh/rooms.json','w',encoding='utf-8'),ensure_ascii=False)
