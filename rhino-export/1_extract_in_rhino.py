import Rhino, json
from Rhino.Geometry import Plane, Point3d, Vector3d
from Rhino.Geometry.Intersect import Intersection
d=__rhino_doc__; tol=d.ModelAbsoluteTolerance
OUT=r"C:/VS Code/workfiles/product/ind-plan-mvp/rhino-export/rh/"
groups={'v1':'Квартира 28 — объёмная планировка','v2':'Квартира 28 — объёмный вариант 2 (+Y)','v3':'Квартира 28 — объёмный вариант 3 (+Y)','ind':'Квартира 28 — 106.21 м²','contour':'Walls'}
def pts(c):
    if c is None: return None
    pl=None
    ok,p=c.TryGetPolyline()
    if ok: pl=list(p)
    else:
        pc=c.ToPolyline(0,0,0.05,0,0,2.0,0,0,True)
        if pc is None: return None
        pl=list(pc.ToPolyline()) if hasattr(pc,'ToPolyline') else [pc.Point(i) for i in range(pc.PointCount)]
    return [(round(q.X,1),round(q.Y,1)) for q in pl], c.IsClosed
def section(b,z):
    r=Intersection.BrepPlane(b,Plane(Point3d(0,0,z),Vector3d.ZAxis),tol)
    cs=list(r[1]) if r[0] else []
    j=Rhino.Geometry.Curve.JoinCurves(cs,tol*10) if cs else []
    return list(j)
def topfaces(b):
    best=[];mz=-1e9
    for f in b.Faces:
        ok,pl=f.TryGetPlane(0.01)
        if not ok: continue
        n=pl.Normal
        if f.OrientationIsReversed: n=-n
        if n.Z<0.99: continue
        z=pl.Origin.Z
        if z>mz+1: best=[f];mz=z
        elif abs(z-mz)<=1: best.append(f)
    out=[]
    for f in best:
        for lp in f.Loops: out.append(lp.To3dCurve())
    return out
res={}
for key,root in groups.items():
    items=[]
    for o in d.Objects:
        lay=d.Layers[o.Attributes.LayerIndex]; fp=lay.FullPath
        if not (fp==root or fp.startswith(root+'::')): continue
        sub=fp.split('::')[-1]
        col=o.Attributes.DrawColor(d); col=[col.R,col.G,col.B]
        g=o.Geometry; t=str(o.ObjectType)
        e={'l':sub,'c':col}
        if t=='Brep' or t=='Extrusion':
            b=g if t=='Brep' else g.ToBrep()
            if 'ол' in sub and ('Пол' in sub or 'пол' in sub): cs=topfaces(b); e['k']='fillface'
            else:
                cs=section(b,1200); e['k']='fillsec'
                if not cs: cs=topfaces(b); e['k']='fillface'
            e['p']=[x for x in (pts(c) for c in cs) if x]
        elif t=='Curve':
            x=pts(g); 
            if not x: continue
            e['k']='curve'; e['p']=[x]
        elif t=='Hatch':
            cs=list(g.Get3dCurves(True))+list(g.Get3dCurves(False)); e['k']='hatch'; e['p']=[x for x in (pts(c) for c in cs) if x]
        elif t=='Annotation':
            tx=getattr(g,'PlainText',None) or getattr(g,'PlainUserText',None) or ''
            if not tx:
                try: tx=g.PlainText
                except: tx=''
            bb=g.GetBoundingBox(True); e['k']='text'; e['t']=tx; e['xy']=[round(bb.Center.X,1),round(bb.Center.Y,1)]; e['h']=round(bb.Max.Y-bb.Min.Y,1); e['w']=round(bb.Max.X-bb.Min.X,1)
            try: e['th']=round(g.TextHeight,1)
            except: pass
        else: continue
        items.append(e)
    res[key]=items
    print(key,len(items))
json.dump(res,open(OUT+'plans.json','w',encoding='utf-8'),ensure_ascii=False)
print('ok')
