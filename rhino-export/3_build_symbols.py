import json,os
D=os.path.dirname(os.path.abspath(__file__))
P=json.load(open(D+'/rh/plans.json',encoding='utf-8'))
CUT=json.load(open(D+'/rh/cuts.json',encoding='utf-8'))
ROOMS=json.load(open(D+'/rh/rooms.json',encoding='utf-8'))
S=0.05
def hexc(c): return '#%02x%02x%02x'%tuple(c)
def num(v): 
    s='%.1f'%v; return s[:-2] if s.endswith('.0') else s
def cap(t):
    t=t.strip().lower(); return t[:1].upper()+t[1:] if t!='с/у' else 'С/У'
VAR={'Пол':'--fw','Деревянный пол':'--fw','Плитка — зоны пола':'--ft','Швы деревянного пола':'--sw','Швы плитки':'--st'}
def order(e):
    l=e['l'];k=e['k']
    if k=='fillface': return 0 if 'Плитка' not in l else 1
    if 'Швы' in l: return 2
    if k=='curve': return 3
    if k in('hatch','fillsec'):
        return 7 if 'Остекл' in l else 6 if 'рамы' in l else 5
    return 9
def sym(key,keeptext):
    items=P[key]
    xs=[x for e in items for pl,_ in e.get('p',[]) for x,y in pl]; ys=[y for e in items for pl,_ in e.get('p',[]) for x,y in pl]
    pad=300;x0,y0,x1,y1=min(xs)-pad,min(ys)-pad,max(xs)+pad,max(ys)+pad;H=y1-y0
    T=lambda x,y:'%s %s'%(num((x-x0)*S),num((y1-y)*S))
    by={}
    for e in items:
        if e['k']=='text': continue
        by.setdefault((order(e),e['k'],e['l'],tuple(e['c'])),[]).extend(e['p'])
    out=[];flo=[]
    EXT=('Фасадные','Периметр','Входной')
    for (o,k,l,c),pls in sorted(by.items()):
        d=''.join('M'+' '.join(T(x,y) for x,y in pl)+('Z' if cl else '') for pl,cl in pls if len(pl)>1)
        col=hexc(c)
        if key=='ind':  # эталон IND — как есть
            if k in('fillsec','hatch','fillface'): out.append(f'<path d="{d}" fill="{col}" fill-rule="evenodd"/>')
            else: out.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width=".5" stroke-linejoin="round" stroke-linecap="round"/>')
            continue
        if key=='contour':
            out.append(f'<path d="{d}" fill="#1F2328" fill-rule="evenodd"/>' if k=='hatch' else f'<path d="{d}" fill="none" stroke="#1F2328" stroke-width=".6"/>'); continue
        if 'Швы' in l or 'Плитка' in l: continue
        if k=='fillface': flo.append(f'<path d="{d}" fill="#F4F4F2" fill-rule="evenodd"/>'); continue
        if k in('fillsec','hatch'):
            if 'Остекл' in l or 'рамы' in l: out.append(f'<path d="{d}" fill="#fff" stroke="#2563EB" stroke-width=".6" stroke-linejoin="round"/>')
            else: out.append(f'<path d="{d}" fill="{"#1F2328" if any(e in l for e in EXT) else "#6B7280"}" fill-rule="evenodd"/>')
            continue
        if 'Открывание' in l: out.append(f'<path d="{d}" fill="none" stroke="#1F2328" stroke-width=".75" stroke-linecap="round"/>'); continue
        st='stroke:#374151'+(';display:var(--fd,inline)' if 'Мебель' in l else '')
        out.append(f'<path d="{d}" fill="none" style="{st}" stroke-width=".7" stroke-linejoin="round" stroke-linecap="round"/>')
    if flo: out.insert(0,f'</symbol><symbol id="rh-{key}-f" viewBox="VB">'+''.join(flo)) if False else None
    FLO[key]=''.join(flo)
    labs=[]
    for e in items:
        if e['k']!='text' or not e['t'].strip(): continue
        x,y=e['xy']; fs=max(e.get('th',150),150)*S
        if keeptext or e['t'].strip()=='DW':
            lines=e['t'].split('\n'); ty=(y1-y)*S-(len(lines)-1)*fs*0.6
            tsp=''.join(f'<tspan x="{num((x-x0)*S)}" dy="{0 if i==0 else num(fs*1.2)}">{t}</tspan>' for i,t in enumerate(lines))
            out.append(f'<text y="{num(ty+fs*0.35)}" font-size="{num(fs)}" fill="{hexc(e["c"]) if key=="ind" else "#374151"}" text-anchor="middle" font-family="Inter,Arial,sans-serif">{tsp}</text>')
    vb=f'0 0 {num((x1-x0)*S)} {num(H*S)}'
    return f'<symbol id="rh-{key}" viewBox="{vb}">'+''.join(out)+'</symbol>',vb,fsz(items)
def fsz(items):
    t=[e for e in items if e['k']=='text' and e['t'].strip() and e['t'].strip()!='DW']
    return round(max(t[0].get('th',150),150)*S,1) if t else 10
syms=[];RH={};FLO={}
for k in ['v1','v2','v3','ind','contour']:
    s,vb,fs=sym(k,k in('ind',)); syms.append(s.replace('rh-contour','rh-ct'))
    if FLO.get(k): syms.append(f'<symbol id="rh-{k}-f" viewBox="{vb}">'+FLO[k]+'</symbol>')
    if k in ROOMS:
        regs=[];lab=[];gmap={}
        for i,r in enumerate(ROOMS[k]):
            if r['n']=='DW': continue
            if r.get('g') is not None and r['a'] is None and not r.get('bad'):
                ri=gmap[r['g']]; regs[ri]['n']+=' · '+cap(r['n']); lab.append({'t':r['n'],'x':r['x'],'y':r['y'],'r':ri,'f':0}); continue
            a=r['a']
            if r.get('bad'): a=2.1 # гардероб v1: разница двух прогонов заливки
            gmap[i]=len(regs); regs.append({'n':cap(r['n']),'a':a,'p':r.get('p','')}); lab.append({'t':r['n'],'x':r['x'],'y':r['y'],'r':len(regs)-1,'f':1})
        RH[k]={'vb':vb,'fs':fs,'R':regs,'L':lab,'cut':CUT.get(k,{}).get('cut',[])}
    else: RH[k]={'vb':vb}
SYM='<svg width="0" height="0" style="position:absolute" aria-hidden="true">'+''.join(syms)+'</svg>'
open(D+'/rh/sym.html','w',encoding='utf-8').write(SYM)
open(D+'/rh/rh.js','w',encoding='utf-8').write('const RH='+json.dumps(RH,ensure_ascii=False,separators=(',',':'))+';')
print(len(SYM)); print(json.dumps({k:v.get('R') for k,v in RH.items()},ensure_ascii=False))
