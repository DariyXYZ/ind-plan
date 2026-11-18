# Собирает /test/index.html: тот же редактор, но в сетке примеров — 10 тестовых контуров из contours.json.
# Запуск после 6_build_pages.py: python gen-tests/build_test_page.py
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
src = open(os.path.join(ROOT, 'index.html'), encoding='utf-8', newline='').read()
C = json.load(open(os.path.join(HERE, 'contours.json'), encoding='utf-8'))
TY = {'Студия': 'С', '1к': '1к', 'Евро-2': '2к', '2к': '2к', 'Евро-3': '3к', '3к': '3к', 'Евро-4': '3к', '4к': '3к'}
CL = {'Стандарт': 0, 'Комфорт': 0, 'Бизнес': 1, 'Премиум': 2}
T = [{'n': f"Тест {c['id']:02d} · {c['name']}", 't': TY[c['kind']], 'c': CL[c['cls']],
      'P': c['poly'], 'e': c['edges'], 'win': c['win'], 'door': c['door'], 'ris': c['ris'], 'pyl': c['pyl']} for c in C]
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
EXD.length=0;T.forEach(c=>EXD.push({n:c.n,t:c.t,c:c.c,M:()=>tM(c)}));
for(const o of [IPTH,IPA])for(const k in o)delete o[k];
document.title='IND PLAN · тестовые контуры';
if($('#s-projects').classList.contains('on'))ipGrid()})();
</script>""".replace('__T__', json.dumps(T, ensure_ascii=False))
i = src.rindex('</body>')
out = src[:i] + js + src[i:]
os.makedirs(os.path.join(ROOT, 'test'), exist_ok=True)
open(os.path.join(ROOT, 'test', 'index.html'), 'w', encoding='utf-8', newline='').write(out)
print('ok', len(out))
