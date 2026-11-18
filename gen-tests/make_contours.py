# 10 тестовых контуров квартир для генерации. Единицы — мм, Y вниз.
# Ребро: 'f' фасад (наружная 350), 'm' МОП / межквартирная (монолит 250).
import json, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
TF, TM = 350, 250

A = [
 dict(id=1, name='Студия', kind='Студия', cls='Стандарт',
      poly=[(0,0),(3600,0),(3600,7800),(0,7800)], edges='mmfm',
      win=[(2,1800,1500)], door=(0,900,1000), ris=[(3220,380)]),
 dict(id=2, name='Евро-2', kind='Евро-2', cls='Комфорт',
      poly=[(0,0),(6300,0),(6300,6800),(0,6800)], edges='mmfm',
      win=[(2,1600,1800),(2,4700,1500)], door=(0,1000,1000), ris=[(3250,380)]),
 dict(id=3, name='1-комнатная, глубокая', kind='1к', cls='Стандарт',
      poly=[(0,0),(5100,0),(5100,9000),(0,9000)], edges='mmfm',
      win=[(2,1300,1500),(2,3800,1500)], door=(0,1200,1000), ris=[(4720,2600)]),
 dict(id=4, name='2-комнатная', kind='2к', cls='Комфорт',
      poly=[(0,0),(7500,0),(7500,8000),(0,8000)], edges='mmfm',
      win=[(2,1300,1500),(2,3800,1800),(2,6200,1500)], door=(0,1100,1000),
      ris=[(3800,380),(7120,3600)]),
 dict(id=5, name='Евро-3 угловая', kind='Евро-3', cls='Комфорт',
      poly=[(0,0),(8400,0),(8400,8100),(0,8100)], edges='mffm',
      win=[(1,2000,1500),(1,5600,1800),(2,2200,1800),(2,5600,1500)], door=(0,1100,1000),
      ris=[(3000,380)]),
 dict(id=6, name='2-комнатная, Г-образная угловая', kind='2к', cls='Комфорт',
      poly=[(0,0),(4800,0),(4800,3600),(9000,3600),(9000,8400),(0,8400)], edges='mmmffm',
      win=[(3,1300,1500),(3,3600,1500),(4,1800,1800),(4,5200,1500),(4,7700,1200)], door=(0,1200,1000),
      ris=[(4420,420),(5300,3980)]),
 dict(id=7, name='3-комнатная, широкий фронт', kind='3к', cls='Бизнес',
      poly=[(0,0),(11700,0),(11700,7400),(0,7400)], edges='mmfm',
      win=[(2,1500,1500),(2,4300,1800),(2,7300,1500),(2,10200,1500)], door=(0,5850,1000),
      ris=[(2800,380),(8900,380)], pyl=[(5650,3200,400,1200)]),
 dict(id=8, name='Евро-4 угловая с выступом', kind='Евро-4', cls='Бизнес',
      poly=[(0,0),(10800,0),(10800,9600),(3000,9600),(3000,8100),(0,8100)], edges='mffffm',
      win=[(1,2000,1500),(1,5000,1800),(1,8000,1500),(2,1900,1800),(2,5300,1800),(4,1500,1500)], door=(0,1300,1000),
      ris=[(4300,380),(7000,380)]),
 dict(id=9, name='3-комнатная, скошенный фасад', kind='3к', cls='Комфорт',
      poly=[(0,0),(9600,0),(9600,7200),(0,8700)], edges='mmfm',
      win=[(2,1500,1500),(2,4300,1800),(2,7100,1500)], door=(0,1200,1000),
      ris=[(3600,380),(9220,3400)]),
 dict(id=10, name='4-комнатная сквозная', kind='4к', cls='Премиум',
      poly=[(0,0),(8700,0),(8700,14400),(0,14400)], edges='fmfm',
      win=[(0,1500,1500),(0,4350,1800),(0,7200,1500),(2,1500,1500),(2,4350,1800),(2,7200,1500)], door=(3,7200,1100),
      ris=[(380,5900),(8320,8600)], pyl=[(4150,4600,400,900),(4150,8900,400,900)]),
]

def sub(a,b): return (a[0]-b[0],a[1]-b[1])
def add(a,b,k=1): return (a[0]+b[0]*k,a[1]+b[1]*k)
def unit(v):
    l=math.hypot(*v); return (v[0]/l,v[1]/l)
def inter(p,u,q,v):
    d=u[0]*v[1]-u[1]*v[0]
    if abs(d)<1e-9: return p
    t=((q[0]-p[0])*v[1]-(q[1]-p[1])*v[0])/d
    return add(p,u,t)
def area(P): return sum(P[i][0]*P[(i+1)%len(P)][1]-P[(i+1)%len(P)][0]*P[i][1] for i in range(len(P)))/2

def offs(P,ts,sgn):
    n=len(P); L=[]
    for i in range(n):
        a,b=P[i],P[(i+1)%n]; u=unit(sub(b,a)); nv=(-u[1],u[0])
        L.append((add(a,nv,sgn*ts[i]/2),u))
    return [inter(*L[i-1],*L[i]) for i in range(n)]

def build(ap):
    P=ap['poly']; assert area(P)>0, ap['id']
    ts=[TF if c=='f' else TM for c in ap['edges']]; assert len(ts)==len(P), ap['id']
    inner=offs(P,ts,1); outer=offs(P,ts,-1)
    pyl=ap.get('pyl',[])
    a=area(inner)-sum(w*h for _,_,w,h in pyl)
    ap.update(ts=ts,inner=inner,outer=outer,area=a/1e6)
    return ap

def f(v): return f'{v:.0f}'
def pts(P): return ' '.join(f'{f(x)},{f(y)}' for x,y in P)

def svg(ap):
    P,ts,inner,outer=ap['poly'],ap['ts'],ap['inner'],ap['outer']
    xs=[p[0] for p in outer]; ys=[p[1] for p in outer]
    x0,x1,y0,y1=min(xs),max(xs),min(ys),max(ys); pad=1300
    vb=f'{f(x0-pad)} {f(y0-pad)} {f(x1-x0+2*pad)} {f(y1-y0+2*pad)}'
    s=[f'<svg viewBox="{vb}" role="img" aria-label="Контур {ap["id"]}">']
    s.append(f'<polygon class="fl" points="{pts(inner)}"/>')
    s.append(f'<path class="wl" fill-rule="evenodd" d="M{pts(outer)}Z M{pts(inner)}Z"/>')
    for x,y,w,h in ap.get('pyl',[]): s.append(f'<rect class="wl" x="{x}" y="{y}" width="{w}" height="{h}"/>')
    def gap(e,c,w,cls):
        a,b=P[e],P[(e+1)%len(P)]; u=unit(sub(b,a)); nv=(-u[1],u[0]); t=ts[e]
        p=add(a,u,c); q=[add(add(p,u,-w/2),nv,t/2+2),add(add(p,u,w/2),nv,t/2+2),add(add(p,u,w/2),nv,-t/2-2),add(add(p,u,-w/2),nv,-t/2-2)]
        s.append(f'<polygon class="{cls}" points="{pts(q)}"/>')
        return p,u,nv,t
    for e,c,w in ap['win']:
        p,u,nv,t=gap(e,c,w,'wn')
        for k in (-t/6,t/6):
            a2=add(add(p,u,-w/2),nv,k); b2=add(add(p,u,w/2),nv,k)
            s.append(f'<line class="gl" x1="{f(a2[0])}" y1="{f(a2[1])}" x2="{f(b2[0])}" y2="{f(b2[1])}"/>')
    e,c,w=ap['door']; p,u,nv,t=gap(e,c,w,'dr')
    tip=add(p,nv,-t/2-80); base=add(p,nv,-t/2-620)
    tri=[tip,add(base,u,260),add(base,u,-260)]
    s.append(f'<polygon class="ar" points="{pts(tri)}"/>')
    lp=add(p,nv,-t/2-1000)
    s.append(f'<text class="lb" x="{f(lp[0])}" y="{f(lp[1])}" dominant-baseline="middle" text-anchor="middle">вход</text>')
    for x,y in ap['ris']:
        s.append(f'<circle class="rs" cx="{x}" cy="{y}" r="150"/><path class="rx" d="M{x-106},{y-106}L{x+106},{y+106}M{x+106},{y-106}L{x-106},{y+106}"/>')
    # габариты по наружному контуру
    s.append(f'<text class="dm" x="{f((x0+x1)/2)}" y="{f(y1+620)}" text-anchor="middle">{(x1-x0)/1000:.2f}'.replace('.',',')+' м</text>')
    s.append(f'<text class="dm" x="{f(x1+420)}" y="{f((y0+y1)/2)}" text-anchor="middle" transform="rotate(90 {f(x1+420)} {f((y0+y1)/2)})">{(y1-y0)/1000:.2f}'.replace('.',',')+' м</text>')
    s.append('</svg>')
    return ''.join(s)

for ap in A: build(ap)
# id 8: рёбра — 0 МОП, 1–4 фасад, 5 межквартирная (уже 'mffffm')

def card(ap):
    nw=len(ap['win'])
    meta=[f"{ap['area']:.1f} м²".replace('.',','), ap['cls'], f"{nw} {'окно' if nw==1 else 'окна' if nw<5 else 'окон'}", f"{len(ap['ris'])} {'стояк' if len(ap['ris'])==1 else 'стояка'}"]
    if ap.get('pyl'): meta.append(f"{len(ap['pyl'])} {'пилон' if len(ap['pyl'])==1 else 'пилона'}")
    return f'''<article class="card"><div class="plan">{svg(ap)}</div>
<div class="txt"><div class="row"><span class="no">{ap['id']:02d}</span><h2>{ap['name']}</h2></div>
<p class="meta">{' · '.join(meta)}</p><p class="note">{ap['note']}</p></div></article>'''

NOTES={
 1:'Узкая ячейка 3,6 м, одно окно в торце. Кухня у входа, санузел к стояку.',
 2:'Почти квадрат, 2 окна на один фасад: кухня-гостиная + спальня.',
 3:'Глубина 9 м, стояк в середине боковой стены — тёмная середина.',
 4:'Классическая двушка, стояки в двух местах — можно развести кухню и санузел.',
 5:'Угол: окна на два фасада, один стояк у входа.',
 6:'Г-образная, вход в узком крыле, свет в широком.',
 7:'Фронт 11,7 м, вход по центру, пилон посреди квартиры.',
 8:'Угловая с выступом: 6 окон на три грани, два стояка у входа.',
 9:'Фасад скошен на 1,5 м — комнаты-трапеции.',
 10:'Сквозная: окна на две стороны, вход сбоку посередине, два пилона.',
}
for ap in A: ap['note']=NOTES[ap['id']]

css='''<meta charset="utf-8"><title>Тестовые контуры IND PLAN</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500&display=swap">
<style>
/* серый холст + белые листы, как в редакторе IND PLAN; стены чёрные, акцент синий */
:root{--bg:#EEF0F3;--sheet:#FFFFFF;--ink:#16181D;--mut:#6B7180;--line:#D9DDE4;--acc:#2F5BEA;--floor:#F6F7F9;
 --sans:Inter,system-ui,sans-serif;--mono:"JetBrains Mono",ui-monospace,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#121418;--sheet:#1B1E24;--ink:#E8EAEE;--mut:#9399A6;--line:#2C313A;--acc:#7C9BFF;--floor:#22262D;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#121418;--sheet:#1B1E24;--ink:#E8EAEE;--mut:#9399A6;--line:#2C313A;--acc:#7C9BFF;--floor:#22262D;color-scheme:dark}
body{background:var(--bg);color:var(--ink);font-family:var(--sans)}
main{max-width:1240px;margin:0 auto;padding-block:32px 48px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:grid;gap:24px}
header{display:grid;gap:8px}h1{font-size:24px;font-weight:600;margin:0;text-wrap:balance}
.lead{margin:0;color:var(--mut);max-width:70ch;line-height:1.5}
.leg{display:flex;flex-wrap:wrap;gap:16px;color:var(--mut);font-size:13px;align-items:center}
.leg span{display:inline-flex;gap:6px;align-items:center}.leg svg{width:22px;height:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:16px}
.card{background:var(--sheet);border-radius:12px;display:grid;grid-template-rows:auto 1fr;overflow:hidden}
.plan{aspect-ratio:1/1;display:grid;place-items:center;padding:8px;max-width:100%}
.plan svg{width:100%;height:100%}
.txt{padding:4px 16px 16px;display:grid;gap:6px;align-content:start;min-width:0}
.row{display:flex;gap:10px;align-items:baseline}.no{font-family:var(--mono);color:var(--acc);font-size:15px}
h2{font-size:16px;font-weight:600;margin:0}
.meta{margin:0;font-size:13px;font-variant-numeric:tabular-nums}.note{margin:0;font-size:13px;color:var(--mut);line-height:1.45}
.fl{fill:var(--floor)}.wl{fill:var(--ink)}.wn{fill:var(--sheet);stroke:var(--ink);stroke-width:22}.gl{stroke:var(--ink);stroke-width:18}
.dr{fill:var(--sheet)}.ar{fill:var(--acc)}.lb{fill:var(--acc);font:500 340px var(--sans)}
.rs{fill:var(--sheet);stroke:var(--ink);stroke-width:28}.rx{stroke:var(--ink);stroke-width:22}
.dm{fill:var(--mut);font:400 300px var(--sans);font-variant-numeric:tabular-nums}
</style>'''
legend='''<div class="leg"><span><svg viewBox="0 0 22 14"><rect y="4" width="22" height="6" fill="var(--ink)"/></svg>несущие стены</span>
<span><svg viewBox="0 0 22 14"><rect y="4" width="22" height="6" fill="var(--ink)"/><rect x="5" y="3" width="12" height="8" fill="var(--sheet)" stroke="var(--ink)" stroke-width="1"/><line x1="5" x2="17" y1="7" y2="7" stroke="var(--ink)" stroke-width="1"/></svg>окно</span>
<span><svg viewBox="0 0 22 14"><circle cx="11" cy="7" r="5" fill="var(--sheet)" stroke="var(--ink)" stroke-width="1.4"/><path d="M7.5 3.5l7 7M14.5 3.5l-7 7" stroke="var(--ink)" stroke-width="1.2"/></svg>стояк</span>
<span><svg viewBox="0 0 22 14"><path d="M11 12L6 3h10z" fill="var(--acc)"/></svg>вход</span></div>'''
html=css+f'''<main><header><h1>10 тестовых контуров квартир</h1>
<p class="lead">Оболочки современного ЖК: наружные стены 350 мм, стены к МОП и соседям 250 мм, проёмы окон, вход и стояки на замке. Внутри пусто — это поле для генератора. Площадь — по внутренним граням стен, без пилонов. Выберите три номера.</p>{legend}</header>
<section class="grid">{''.join(card(a) for a in A)}</section></main>'''
open(os.path.join(HERE,'contours.html'),'w',encoding='utf-8').write(html)
# данные для генерации
out=[{k:a[k] for k in ('id','name','kind','cls','poly','edges','ts','win','door','ris')}|{'pyl':a.get('pyl',[]),'area_m2':round(a['area'],2)} for a in A]
json.dump(out,open(os.path.join(HERE,'contours.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=1)
for a in A: print(a['id'],a['name'],round(a['area'],1))
