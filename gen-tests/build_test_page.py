# Собирает /test/index.html: тот же редактор, но в сетке примеров — 10 тестовых контуров из contours.json.
# Запуск после 6_build_pages.py: python gen-tests/build_test_page.py
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
src = open(os.path.join(ROOT, 'index.html'), encoding='utf-8', newline='').read()
C = json.load(open(os.path.join(HERE, 'contours.json'), encoding='utf-8'))
LV = json.load(open(os.path.join(HERE, 'layouts.json'), encoding='utf-8'))
TY = {'Студия': 'С', '1к': '1к', 'Евро-2': '2к', '2к': '2к', 'Евро-3': '3к', '3к': '3к', 'Евро-4': '3к', '4к': '3к'}
CL = {'Стандарт': 0, 'Комфорт': 0, 'Бизнес': 1, 'Премиум': 2}
T = [{'n': f"Тест {c['id']:02d} · {c['name']}", 't': TY[c['kind']], 'c': CL[c['cls']],
      'P': c['poly'], 'e': c['edges'], 'win': c['win'], 'door': c['door'], 'ris': c['ris'], 'pyl': c['pyl'], 'V': LV.get(str(c['id']))} for c in C]
T.sort(key=lambda t: not t['V'])  # с планировками — первыми
js = r"""<script>
/* /test: 10 тестовых контуров вместо примеров. Наружные стены 350 (ext), к МОП и соседям 250 (bear), пилоны — короткие несущие стены */
(()=>{const T=__T__;
function tM(c){const M=ipBlank(),P=c.P;
 P.forEach((p,i)=>{const q=P[(i+1)%P.length],f=c.e[i]=='f';M.walls.push({id:nid(M,'w'),x1:p[0]/MM,y1:p[1]/MM,x2:q[0]/MM,y2:q[1]/MM,t:(f?350:250)/MM,type:f?'ext':'bear',fixed:1})});
 c.pyl.forEach(([x,y,w,h])=>{const v=h>=w;M.walls.push({id:nid(M,'w'),x1:(v?x+w/2:x)/MM,y1:(v?y:y+h/2)/MM,x2:(v?x+w/2:x+w)/MM,y2:(v?y+h:y+h/2)/MM,t:(v?w:h)/MM,type:'bear',fixed:1})});
 ipFit(M);ipGrow(M);const o0=M.off,s0=ED.s;ED.s=1;
 const at=(e,d)=>{const a=P[e],b=P[(e+1)%P.length],L=Math.hypot(b[0]-a[0],b[1]-a[1]);return[a[0]+(b[0]-a[0])*d/L,a[1]+(b[1]-a[1])*d/L]};
 [...c.win.map(([e,d,w])=>['win',...at(e,d),w]),['door',...at(c.door[0],c.door[1]),c.door[2]]].forEach(([k,x,y,w])=>{const o=placeOp(M,{x:x/MM+o0[0],y:y/MM+o0[1]},k,w/MM);if(o){o.id=nid(M,'o');if(k=='door')o.h='s';M.ops.push(o);M.gv++}});
 c.ris.forEach(([x,y],i)=>M.risers.push({id:nid(M,'r'),x:x/MM+o0[0],y:y/MM+o0[1],d:110,type:i%2?'В1':'К1',fixed:1}));
 ED.s=s0;M.gv++;return M}
/* планировки: перегородки 100, двери, подписи помещений, мебель — поверх контура */
function vM(c,L){const M=tM(c),o0=M.off,s0=ED.s,P=(x,y)=>({x:x/MM+o0[0],y:y/MM+o0[1]});ED.s=1;M.rooms=[];
 L.walls.forEach(([x1,y1,x2,y2])=>{const a=P(x1,y1),b=P(x2,y2);M.walls.push({id:nid(M,'w'),x1:a.x,y1:a.y,x2:b.x,y2:b.y,t:100/MM,type:'part',fixed:0})});
 L.doors.forEach(([x,y,w,sx,sy,h,sl])=>{const o=placeOp(M,P(x+sx*20,y+sy*20),'door',w/MM);if(o){o.id=nid(M,'o');o.h=h||'s';if(sl)o.sl=1;M.ops.push(o)}});
 L.rooms.forEach(([n,x,y])=>{const p=P(x,y);M.rooms.push({n,x:p.x,y:p.y})});
 L.furn.forEach(([k,x,y,r,w,d])=>{const p=P(x,y),f={id:nid(M,'f'),c:k,x:p.x,y:p.y,r,m:0};if(w)f.w=w;if(d)f.d=d;M.furn.push(f)});
 M.furnOn=true;ED.s=s0;M.gv++;return M}
EXD.length=0;T.forEach(c=>EXD.push({n:c.n,t:c.t,c:c.c,M:()=>tM(c),V:c.V,src:c,nv:c.V?c.V.length:0}));
const _od=ipOpenDemo;ipOpenDemo=function(k){const D=EXD[k];IP.tst=D.V?D:null;_od(k);if(!D.V)return;
 V.length=0;D.V.forEach((L,i)=>{const M=vM(D.src,L);M.gv=1;M.seq=500;const v={id:i+1,run:1,q:'по методичке IND',seed:0,M,type:D.t,err:0,warn:L.warn?1:0,vote:0,ver:1,from:0,nm:L.name};syncR(v);
  v.live=v.R.filter(r=>/Спальн|Детск|Гостин|Кабинет|Гостев|гостин/.test(r.n)).reduce((s,r)=>s+ +r.a,0).toFixed(1);V.push(v)});
 run=1;$('#gempty').style.display='none';$('#glist').style.display='block';setGen('auto_awesome','Создать ещё');renderList();showVar(1);$('#expbtn').disabled=false};
/* в тестовых — без эталона кв. 28, у варианта подпись решения */
renderList=(_r=>function(){_r();if(!IP.tst)return;$$('#glist .runh').forEach(h=>{if(/Эталон/.test(h.textContent)){const n=h.nextElementSibling;h.outerHTML='';if(n)n.outerHTML=''}});
 $$('#glist .gi').forEach(g=>{const m=(g.getAttribute('onclick')||'').match(/showVar\((\d+)\)/);if(!m)return;const v=V.find(x=>x.id==+m[1]);const b=g.querySelector('.tt b');if(v&&v.nm&&b)b.textContent=v.nm})})(renderList);
for(const o of [IPTH,IPA])for(const k in o)delete o[k];
/* обложка квартиры с планировками — вариант А, а не пустая оболочка */
EXD.forEach((D,k)=>{if(D.V)try{IPTH[k]=ipThumb(vM(D.src,D.V[0]))}catch(e){}});
document.title='IND PLAN · тестовые контуры';
if($('#s-projects').classList.contains('on'))ipGrid()})();
</script>""".replace('__T__', json.dumps(T, ensure_ascii=False))
i = src.rindex('</body>')
out = src[:i] + js + src[i:]
os.makedirs(os.path.join(ROOT, 'test'), exist_ok=True)
open(os.path.join(ROOT, 'test', 'index.html'), 'w', encoding='utf-8', newline='').write(out)
print('ok', len(out))
