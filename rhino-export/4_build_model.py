# Rhino-выгрузка (rh/plans.json) → редактируемая модель для редактора MVP (rh/model.js + rh/msym.html).
# Единицы — те же, что у символов: 1 ед. = 20 мм, y вниз, отступ 300 мм.
#  fixed  — наружные / межквартирные стены и входной участок: контуры как есть (на замке, как Revit-основа)
#  walls  — перегородки: растр 10 мм → прямоугольники → отрезки по оси, склейка через проёмы
#  ops    — двери (по дуге открывания), окна (рамы+стекло → повёрнутый прямоугольник), проходы без полотна
#  furn   — мебель и сантехника: кривые, слипшиеся по габаритам, = один предмет (<g> в defs)
#  rooms  — подписи помещений (точки заливки), площади считает редактор
import json,os,math
import numpy as np
from PIL import Image,ImageDraw
D=os.path.dirname(os.path.abspath(__file__))
P=json.load(open(D+'/rh/plans.json',encoding='utf-8'))
CUT=json.load(open(D+'/rh/cuts.json',encoding='utf-8'))
ROOMS=json.load(open(D+'/rh/rooms.json',encoding='utf-8'))
S=0.05;R2=2  # растр: 2 px на единицу (10 мм)
EXT=('Фасадные','Периметр','Входной')
def num(v):
    s='%.1f'%v; s=s[:-2] if s.endswith('.0') else s; return '0' if s=='-0' else s
def cap(t):
    t=t.strip().replace('\n',' ').lower(); return 'С/У' if t=='с/у' else t[:1].upper()+t[1:]
def rect_decomp(A):
    H,W=A.shape;rem=A.copy();out=[]
    while rem.any():
        y,x=np.argwhere(rem)[0]
        def hf():
            x2=x
            while x2+1<W and A[y,x2+1]: x2+=1
            y2=y
            while y2+1<H and A[y2+1,x:x2+1].all(): y2+=1
            return x,y,x2,y2
        def vf():
            y2=y
            while y2+1<H and A[y2+1,x]: y2+=1
            x2=x
            while x2+1<W and A[y:y2+1,x2+1].all(): x2+=1
            return x,y,x2,y2
        best=max((hf(),vf()),key=lambda r:rem[r[1]:r[3]+1,r[0]:r[2]+1].sum())
        x0,y0,x1,y1=best;rem[y0:y1+1,x0:x1+1]=False
        if min(x1-x0,y1-y0)+1>=3 and max(x1-x0,y1-y0)+1>=8: out.append(best)
    # дубли: кусок, на 75%+ лежащий под остальными, выкидываем (с самых мелких)
    out.sort(key=lambda r:(r[2]-r[0]+1)*(r[3]-r[1]+1))
    keep=list(out)
    for r in out:
        others=[o for o in keep if o is not r]
        if not others: continue
        cov=np.zeros(A.shape,bool)
        for o in others: cov[o[1]:o[3]+1,o[0]:o[2]+1]=True
        if cov[r[1]:r[3]+1,r[0]:r[2]+1].mean()>=0.75: keep.remove(r)
    return keep
def obb(pts):
    pts=np.array(pts);best=None
    for a in np.arange(0,180,0.5):
        r=math.radians(a);u=np.array([math.cos(r),math.sin(r)]);n=np.array([-u[1],u[0]])
        pu=pts@u;pn=pts@n;ar=(pu.max()-pu.min())*(pn.max()-pn.min())
        if best is None or ar<best[0]-1e-6: best=(ar,a,pu.min(),pu.max(),pn.min(),pn.max(),u,n)
    _,a,u0,u1,n0,n1,u,n=best;c=u*(u0+u1)/2+n*(n0+n1)/2
    w,t=u1-u0,n1-n0
    if t>w: a=(a+90)%180;w,t=t,w
    if a>90: a-=180
    return float(c[0]),float(c[1]),float(a),float(w),float(t)
def bbox(pl): xs=[p[0] for p in pl];ys=[p[1] for p in pl];return min(xs),min(ys),max(xs),max(ys)
def ov(a,b,e): return a[0]-e<=b[2] and b[0]-e<=a[2] and a[1]-e<=b[3] and b[1]-e<=a[3]
def clusters(items,e):
    n=len(items);par=list(range(n))
    def f(i):
        while par[i]!=i: par[i]=par[par[i]];i=par[i]
        return i
    for i in range(n):
        for j in range(i+1,n):
            if ov(items[i][0],items[j][0],e): par[f(i)]=f(j)
    g={}
    for i in range(n): g.setdefault(f(i),[]).append(items[i])
    return list(g.values())
MODEL={};DEFS=[];ENTR=None
for key in ['v1','v2','v3','contour']:
    items=P[key]
    xs=[x for e in items for pl,_ in e.get('p',[]) for x,y in pl];ys=[y for e in items for pl,_ in e.get('p',[]) for x,y in pl]
    x0,y0,x1,y1=min(xs)-300,min(ys)-300,max(xs)+300,max(ys)+300
    T=lambda x,y:((x-x0)*S,(y1-y)*S)
    VW,VH=(x1-x0)*S,(y1-y0)*S
    fixed=[];part=[];doors=[];wins=[];furn=[]
    for e in items:
        pls=[([T(x,y) for x,y in pl],cl) for pl,cl in e.get('p',[])]
        l=e['l'];k=e['k']
        if key=='contour':
            if k=='hatch': fixed+=pls
            continue
        if k=='fillsec' and any(s in l for s in EXT): fixed+=pls
        elif k=='fillsec' and 'Внутренние' in l: part+=pls
        elif k in('fillsec','fillface') and ('рамы' in l or 'Остекл' in l): wins+=pls
        elif 'Открывание' in l: doors+=pls
        elif k=='curve' and ('Мебель' in l or 'Сантехника' in l): furn+=[(pl,cl,'PLB' if 'Сантех' in l else 'FRN') for pl,cl in pls]
    fd=''.join('M'+' '.join('%s %s'%(num(x),num(y)) for x,y in pl)+'Z' for pl,cl in fixed if len(pl)>2)
    # растры: перегородки и все стены (для толщины у дверей)
    W2,H2=int(VW*R2)+2,int(VH*R2)+2
    imP=Image.new('L',(W2,H2),0);dP=ImageDraw.Draw(imP)
    for pl,cl in part:
        if len(pl)>2: dP.polygon([(x*R2,y*R2) for x,y in pl],fill=255)
    imA=imP.copy();dA=ImageDraw.Draw(imA)
    for pl,cl in fixed:
        if len(pl)>2: dA.polygon([(x*R2,y*R2) for x,y in pl],fill=255)
    AP=np.array(imP)>127;AA=np.array(imA)>127
    walls=[]
    for (rx0,ry0,rx1,ry1) in rect_decomp(AP):
        a0,b0,a1,b1=rx0/R2,ry0/R2,(rx1+1)/R2,(ry1+1)/R2
        if a1-a0>=b1-b0: walls.append({'x1':a0,'y1':(b0+b1)/2,'x2':a1,'y2':(b0+b1)/2,'t':b1-b0})
        else: walls.append({'x1':(a0+a1)/2,'y1':b0,'x2':(a0+a1)/2,'y2':b1,'t':a1-a0})
    # двери: дуга (много точек) + полотно (2 точки) с общей точкой
    arcs=[pl for pl,cl in doors if len(pl)>4];leafs=[pl for pl,cl in doors if len(pl)==2]
    ops=[]
    def inwall(x,y):
        i,j=int(round(y*R2)),int(round(x*R2))
        return 0<=i<AA.shape[0] and 0<=j<AA.shape[1] and AA[i,j]
    for lf in leafs:
        p,q=np.array(lf[0]),np.array(lf[1])
        arc=min(arcs,key=lambda a:min(np.hypot(*(np.array(a[0])-q)),np.hypot(*(np.array(a[-1])-q)),np.hypot(*(np.array(a[0])-p)),np.hypot(*(np.array(a[-1])-p))))
        ends=[np.array(arc[0]),np.array(arc[-1])]
        # петля = конец полотна, не лежащий на дуге
        if min(np.hypot(*(e-q)) for e in ends)<min(np.hypot(*(e-p)) for e in ends): H,L=p,q
        else: H,L=q,p
        A=max(ends,key=lambda e:np.hypot(*(e-L)))
        w=float(np.hypot(*(L-H)));u=(A-H)/np.hypot(*(A-H));n=(L-H)/w
        t=0
        for s in range(1,80):
            pt=H-u*1.0-n*(s/R2)
            if inwall(*pt): t=s/R2
            elif t: break
        t=t or 5
        C=H+u*w/2-n*t/2
        side=1 if u[0]*n[1]-u[1]*n[0]>0 else -1
        ops.append({'k':'door','x':float(C[0]),'y':float(C[1]),'a':math.degrees(math.atan2(u[1],u[0])),'w':w,'t':t,'side':side,'h':'s'})
    # окна: рамы и стекло, слипшиеся в кучки
    wb=[(bbox(pl),pl) for pl,cl in wins if len(pl)>1]
    for cl in clusters(wb,1.0):
        pts=[p for _,pl in cl for p in pl]
        cx,cy,a,w,t=obb(pts)
        if w<10: continue
        ops.append({'k':'win','x':cx,'y':cy,'a':a,'w':w,'t':t})
    # склейка коллинеарных кусков перегородок через проёмы
    def orient(wl): return 'h' if abs(wl['y1']-wl['y2'])<1e-6 else 'v'
    def axis(wl): return wl['y1'] if orient(wl)=='h' else wl['x1']
    def span(wl): return (wl['x1'],wl['x2']) if orient(wl)=='h' else (wl['y1'],wl['y2'])
    def setspan(wl,s,e):
        if orient(wl)=='h': wl['x1'],wl['x2']=s,e
        else: wl['y1'],wl['y2']=s,e
    def opax(o):
        a=((o['a']%180)+180)%180
        return ('h' if a<45 or a>135 else 'v'),(o['y'] if (a<45 or a>135) else o['x']),(o['x'] if (a<45 or a>135) else o['y'])
    changed=True
    while changed:
        changed=False
        for i,a in enumerate(walls):
            sa,ea=span(a)
            cand=[(span(b)[0],j) for j,b in enumerate(walls) if j!=i and orient(a)==orient(b) and abs(axis(a)-axis(b))<=0.75 and abs(a['t']-b['t'])<=1 and span(b)[0]>=ea-0.5]
            for _,j in sorted(cand)[:1]:
                b=walls[j];sb,eb=span(b)
                g0,g1=ea,sb
                hit=[o for o in ops if o['k']=='door' and opax(o)[0]==orient(a) and abs(opax(o)[1]-axis(a))<a['t']/2+4 and g0-1<=opax(o)[2]<=g1+1]
                if hit or g1-g0<=60:
                    setspan(a,sa,max(ea,eb))
                    if not hit: ops.append({'k':'pass','x':0,'y':0,'a':0,'w':g1-g0,'t':a['t'],'_on':(orient(a),axis(a),(g0+g1)/2)})
                    walls.pop(j);changed=True;break
            if changed: break
    for o in ops:
        if o['k']=='pass':
            ori,ax,c=o.pop('_on');o['x'],o['y']=(c,ax) if ori=='h' else (ax,c);o['a']=0 if ori=='h' else 90
    # привязка дверей/проходов к стенам (дверь у торца стены — продлеваем стену до дальнего косяка)
    for wid,wl in enumerate(walls): wl['id']='w%d'%wid
    for o in ops:
        if o['k']=='win': continue
        ori,ax,c=opax(o)
        for wl in walls:
            if orient(wl)!=ori or abs(axis(wl)-ax)>1.5: continue
            s,e=span(wl)
            if s-0.5<=c<=e+0.5: o['wall']=wl['id'];break
            if 0<=s-c<=o['w']/2+3: setspan(wl,c-o['w']/2,e);o['wall']=wl['id'];break
            if 0<=c-e<=o['w']/2+3: setspan(wl,s,c+o['w']/2);o['wall']=wl['id'];break
        if 'wall' in o:
            wl=next(x for x in walls if x['id']==o['wall']);o['t']=wl['t']
            if ori=='h': o['y']=axis(wl)
            else: o['x']=axis(wl)
    # мебель: кривые, касающиеся друг друга, = один предмет
    fb=[(bbox(pl),(pl,cl,cat)) for pl,cl,cat in furn if len(pl)>1]
    F=[]
    for gi,cl in enumerate(sorted(clusters(fb,0.6),key=lambda c:min(b[0][0] for b in c))):
        bx0=min(b[0][0] for b in cl);by0=min(b[0][1] for b in cl);bx1=max(b[0][2] for b in cl);by1=max(b[0][3] for b in cl)
        cx,cy=(bx0+bx1)/2,(by0+by1)/2
        d=''.join('M'+' '.join('%s %s'%(num(x-cx),num(y-cy)) for x,y in pl)+('Z' if c else '') for _,(pl,c,cat) in cl)
        cat='PLB' if any(b[1][2]=='PLB' for b in cl) else 'FRN'
        gid='rf-%s-%d'%(key,gi)
        DEFS.append(f'<path id="{gid}" d="{d}"/>')
        F.append({'id':'f%d'%gi,'src':gid,'x':round(cx,1),'y':round(cy,1),'r':0,'m':0,'w':round((bx1-bx0)*20),'d':round((by1-by0)*20),'cat':cat})
    if key=='v1':
        e=next(o for o in ops if o['k']=='door' and 'wall' not in o);ENTR=dict(e)  # варианты и контур — копии одного этажа со сдвигом, единицы совпадают
    if key=='contour' and ENTR:
        ops.append(dict(ENTR))
    rooms=[]
    if key in ROOMS:
        for r in ROOMS[key]:
            if r['n'].strip()=='DW': continue
            rooms.append({'n':cap(r['n']),'x':r['x'],'y':r['y']})
    R=lambda v:round(v,1)
    for wl in walls:
        for k2 in('x1','y1','x2','y2','t'): wl[k2]=R(wl[k2])
        wl['type']='part'
    for i,o in enumerate(ops):
        o['id']='o%d'%i
        for k2 in('x','y','a','w','t'):
            if k2 in o: o[k2]=R(o[k2])
    MODEL[key]={'vb':'0 0 %s %s'%(num(VW),num(VH)),'W':R(VW),'H':R(VH),'fixed':fd,'walls':walls,'ops':ops,'furn':F,'risers':[],'rooms':rooms,'cut':CUT.get(key,{}).get('cut',[])}
    print(key,'walls',len(walls),'ops',[(o['k'],o.get('wall'),o['w']) for o in ops],'furn',len(F),'rooms',len(rooms))
open(D+'/rh/msym.html','w',encoding='utf-8').write('<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>'+''.join(DEFS)+'</defs></svg>')
open(D+'/rh/model.js','w',encoding='utf-8').write('const RHM='+json.dumps(MODEL,ensure_ascii=False,separators=(',',':'))+';')
print('defs',sum(len(x) for x in DEFS),'model',os.path.getsize(D+'/rh/model.js'))
