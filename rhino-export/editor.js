/* ===== Редактор плана — перенесён из IND PLAN editor (OpenPencil): стены, двери, окна, проходы, мебель, стояки, помещения.
   Правка открывается на том же поле; справа вместо «Генераций» временно — «Свойства», как в прошлом редакторе.
   Модель — rh/model.js (4_build_model.py): 1 ед. = 20 мм. Наружный контур из Rhino на замке, как Revit-основа. ===== */
const EC={ext:'#1F2328',bear:'#4B5563',part:'#6B7280',win:'#2563EB',door:'#1F2328',furn:'#374151',floor:'#F4F4F2',riser:'#1D4ED8',riserFill:'#DBEAFE'};
const WT={ext:['Наружная',300],bear:['Несущая',200],part:['Перегородка',100]};
const MM=20,cl=o=>JSON.parse(JSON.stringify(o,(k,v)=>k[0]=='_'?undefined:v)),q2=v=>Math.round(v*2)/2,mmv=v=>Math.round(v*MM),f2=p=>p[0].toFixed(2)+' '+p[1].toFixed(2);
FU.sbed=()=>pr(-450,0,450,2000)+pl(-450,80,450,80)+rr(-370,150,370,500,60)+pl(-450,700,450,700)+pl(-450,700,-150,1000);
FU.washer=()=>pr(-300,0,300,600)+ci(0,320,200)+ci(0,320,150);
FU.basin=()=>rr(-250,0,250,450,60)+el(0,250,180,140)+ci(0,250,22)+pl(0,30,0,110);
FU.shower=()=>pr(-450,0,450,900)+pl(-450,0,450,900)+pl(450,0,-450,900)+ci(0,450,40);
const FCAT=[['bed','Кровать двуспальная',1600,2000],['sbed','Кровать односпальная',900,2000],['sofa','Диван трёхместный',2200,950],['dining','Стол обеденный, 4 стула',1200,1700],['desk','Рабочий стол со стулом',1200,1100],['coffee','Столик журнальный',900,500],['wardrobe','Шкаф',1800,600],['base','Кухонный модуль',600,600],['hob','Варочная панель',600,600],['sink','Мойка кухонная',600,600],['fridge','Холодильник',600,650],['washer','Стиральная машина',600,600],['wc','Унитаз',380,650],['basin','Раковина',500,450],['bath','Ванна',1700,700],['shower','Душевой поддон',900,900]];
const FC=Object.fromEntries(FCAT.map(c=>[c[0],c])),FUP={};const fup=c=>FUP[c]||(FUP[c]=FU[c]());
const RT=['К1','В1','Т3','Т4','ВК'],RTL={К1:'канализация',В1:'водопровод',Т3:'горячая вода',Т4:'циркуляция',ВК:'вентканал'};
const RNAMES=['Спальня','Детская','Гостиная','Кухня-гостиная','Кухня','Кабинет','Прихожая','Коридор','Холл','Санузел','Ванная','С/У','Гардероб','Постирочная','Кладовая'];
const ang=a=>[Math.cos(a*Math.PI/180),Math.sin(a*Math.PI/180)];
function obox(cx,cy,a,l,t){const [ux,uy]=ang(a),nx=-uy,ny=ux,h=l/2,k=t/2,P=(s,q)=>(cx+ux*s+nx*q).toFixed(2)+' '+(cy+uy*s+ny*q).toFixed(2);return `M${P(-h,-k)}L${P(h,-k)}L${P(h,k)}L${P(-h,k)}Z`}
function wgeo(w){const dx=w.x2-w.x1,dy=w.y2-w.y1,L=Math.hypot(dx,dy)||1e-6;return {cx:(w.x1+w.x2)/2,cy:(w.y1+w.y2)/2,a:Math.atan2(dy,dx)*180/Math.PI,L:L+(w.cap?w.t:0),len:L,ux:dx/L,uy:dy/L}}
function loc(px,py,cx,cy,a){const [ux,uy]=ang(a),dx=px-cx,dy=py-cy;return [dx*ux+dy*uy,-dx*uy+dy*ux]}
function inBox(px,py,cx,cy,a,l,t,e){const [s,q]=loc(px,py,cx,cy,a);return Math.abs(s)<=l/2+e&&Math.abs(q)<=t/2+e}
function doorP(o){const [ux,uy]=ang(o.a),nx=-uy*o.side,ny=ux*o.side,h=o.w/2,k=o.t/2,sg=o.h=='s'?-1:1;
 const H=[o.x+ux*sg*h+nx*k,o.y+uy*sg*h+ny*k],F=[o.x-ux*sg*h+nx*k,o.y-uy*sg*h+ny*k],E=[H[0]+nx*o.w,H[1]+ny*o.w];
 const cr=(E[0]-H[0])*(F[1]-H[1])-(E[1]-H[1])*(F[0]-H[0]);return `M${f2(H)}L${f2(E)}A${o.w} ${o.w} 0 0 ${cr>0?1:0} ${f2(F)}`}
function fbox(f){if(f.src)return {cx:f.x,cy:f.y,a:f.r,l:f.w/MM,t:f.d/MM};const c=FC[f.c],[ux,uy]=ang(f.r),h=c[3]/MM/2;return {cx:f.x-uy*h,cy:f.y+ux*h,a:f.r,l:c[2]/MM,t:c[3]/MM}}
const fixedPolys=M=>M._fx||(M._fx=(M.fixed||'').split('M').filter(Boolean).map(s=>{const n=s.replace(/Z/g,'').trim().split(/[\s,]+/).map(Number),o=[];for(let i=0;i+1<n.length;i+=2)o.push([n[i],n[i+1]]);return o}));
const HC=document.createElement('canvas').getContext('2d');const fixedPath=M=>M._fp||(M._fp=new Path2D(M.fixed||'M0 0'));
const inFixed=(M,x,y)=>!!M.fixed&&HC.isPointInPath(fixedPath(M),x,y,'evenodd');
function mkModel(lay){const M=cl(RHM[lay]);M.lay=lay;M.gv=1;M.seq=500;return M}
/* ---- помещения: растр 1 px = 20 мм, двери и окна закрыты, заливка от подписей ---- */
function dil(A,W,H,r){const B=new Uint8Array(W*H),C=new Uint8Array(W*H);
 for(let y=0;y<H;y++){let c=0;const o=y*W;for(let x=-r;x<W;x++){const a=x+r;if(a<W&&A[o+a])c++;const m=x-r-1;if(m>=0&&A[o+m])c--;if(x>=0)B[o+x]=c>0?1:0}}
 for(let x=0;x<W;x++){let c=0;for(let y=-r;y<H;y++){const a=y+r;if(a<H&&B[a*W+x])c++;const m=y-r-1;if(m>=0&&B[m*W+x])c--;if(y>=0)C[y*W+x]=c>0?1:0}}return C}
function mclose(A,W,H,r){const D=dil(A,W,H,r);for(let i=0;i<D.length;i++)D[i]^=1;const E=dil(D,W,H,r);for(let i=0;i<E.length;i++)E[i]^=1;return E}
function flood(L,W,H,s,v){const st=[s];let n=0;L[s]=v;while(st.length){const i=st.pop();n++;const x=i%W;
 if(x>0&&L[i-1]===0){L[i-1]=v;st.push(i-1)}if(x<W-1&&L[i+1]===0){L[i+1]=v;st.push(i+1)}if(i>=W&&L[i-W]===0){L[i-W]=v;st.push(i-W)}if(i+W<L.length&&L[i+W]===0){L[i+W]=v;st.push(i+W)}}return n}
const hex=c=>[1,3,5].map(i=>parseInt(c.slice(i,i+2),16));
function rasterWalls(M,W,H){const c=document.createElement('canvas');c.width=W;c.height=H;const g=c.getContext('2d');g.fillStyle=g.strokeStyle='#000';
 if(M.fixed)g.fill(fixedPath(M),'evenodd');M.walls.forEach(w=>{const G=wgeo(w);g.fill(new Path2D(obox(G.cx,G.cy,G.a,G.L,w.t)))});
 M.ops.forEach(o=>g.fill(new Path2D(obox(o.x,o.y,o.a,o.w+1,Math.max(o.t,3)))));g.lineWidth=2;(M.cut||[]).forEach(([a,b,c2,d])=>{g.beginPath();g.moveTo(a,b);g.lineTo(c2,d);g.stroke()});return [c,g]}
function calcRooms(M){if(M._K&&M._kv===M.gv)return M._K;const W=Math.ceil(M.W),H=Math.ceil(M.H),N=W*H,[c,g]=rasterWalls(M,W,H),D=g.getImageData(0,0,W,H).data;
 let A=new Uint8Array(N);for(let i=0;i<N;i++)A[i]=D[i*4+3]>90?1:0;A=mclose(A,W,H,3);
 const L=new Int32Array(N);for(let i=0;i<N;i++)if(A[i])L[i]=-1;flood(L,W,H,0,-2);const regs=[],lab2=[];
 M.rooms.forEach((r,i)=>{const px=Math.round(r.x),py=Math.round(r.y);lab2[i]=-1;if(px<1||py<1||px>=W-1||py>=H-1)return;let idx=py*W+px;
  if(L[idx]==-1)out:for(let d=1;d<10;d++)for(let dy=-d;dy<=d;dy++)for(let dx=-d;dx<=d;dx++){const j=(py+dy)*W+px+dx;if(j>=0&&j<N&&L[j]!=-1){idx=j;break out}}
  const v=L[idx];if(v===0){regs.push({labs:[i],px:flood(L,W,H,idx,regs.length+1)});lab2[i]=regs.length-1}else if(v>0){regs[v-1].labs.push(i);lab2[i]=v-1}});
 regs.forEach(R=>{const g2=R.labs.find(i=>/Гостин/.test(M.rooms[i].n));R.main=g2??R.labs[0];R.n=R.labs.map(i=>M.rooms[i].n).join(' · ');R.a=+(R.px*MM*MM/1e6).toFixed(1)});
 const img=g.createImageData(W,H),P=img.data,cols=regs.map(R=>hex(RCOL(R.n)));
 for(let i=0;i<N;i++){const v=L[i];if(v>0){const k=cols[v-1];P[i*4]=k[0];P[i*4+1]=k[1];P[i*4+2]=k[2];P[i*4+3]=255}}
 g.clearRect(0,0,W,H);g.putImageData(img,0,0);M._K={W,H,L,regs,lab2,url:c.toDataURL(),sel:{}};M._kv=M.gv;return M._K}
function selURL(M,i){const K=calcRooms(M);if(K.sel[i])return K.sel[i];const c=document.createElement('canvas');c.width=K.W;c.height=K.H;const g=c.getContext('2d'),img=g.createImageData(K.W,K.H),P=img.data;
 for(let j=0;j<K.L.length;j++)if(K.L[j]===i+1){P[j*4]=61;P[j*4+1]=90;P[j*4+2]=254;P[j*4+3]=46}g.putImageData(img,0,0);return K.sel[i]=c.toDataURL()}
const regAt=(M,x,y)=>{const K=calcRooms(M),px=Math.round(x),py=Math.round(y);if(px<0||py<0||px>=K.W||py>=K.H)return -1;const v=K.L[py*K.W+px];return v>0?v-1:v};
/* ---- отрисовка ---- */
function opG(o){if(o.k=='blank')return `<path d="${obox(o.x,o.y,o.a,o.w,o.t)}" fill="${EC.ext}"/>`;
 if(o.k=='win'){const [ux,uy]=ang(o.a),nx=-uy,ny=ux,h=o.w/2,q=o.t*.17,ln=k=>`M${(o.x-ux*h+nx*k).toFixed(2)} ${(o.y-uy*h+ny*k).toFixed(2)}L${(o.x+ux*h+nx*k).toFixed(2)} ${(o.y+uy*h+ny*k).toFixed(2)}`;
  return `<path d="${obox(o.x,o.y,o.a,o.w,o.t)}${ln(q)}${ln(-q)}" fill="#fff" stroke="${EC.win}" stroke-width=".6" stroke-linejoin="round"/>`}
 let s=`<path d="${obox(o.x,o.y,o.a,o.w,o.t+.6)}" fill="${EC.floor}"/>`;if(o.k=='door')s+=`<path d="${doorP(o)}" fill="none" stroke="${EC.door}" stroke-width=".75" stroke-linecap="round"/>`;return s}
function furG(f){if(f.src)return `<use href="#${f.src}" transform="translate(${f.x} ${f.y}) rotate(${f.r})${f.m?' scale(-1 1)':''}" fill="none" stroke="${EC.furn}" stroke-width=".7" stroke-linejoin="round" stroke-linecap="round"/>`;
 return `<path d="${fup(f.c)}" transform="translate(${f.x} ${f.y}) rotate(${f.r}) scale(${f.m?-.05:.05} .05)" fill="#fff" stroke="${EC.furn}" stroke-width="14" stroke-linejoin="round" stroke-linecap="round"/>`}
function riserG(r){const R=Math.max(r.d/MM/2,4),d=R*.7;return `<circle cx="${r.x}" cy="${r.y}" r="${R}" fill="${EC.riserFill}" stroke="${EC.riser}" stroke-width=".7"/><path d="M${r.x-d} ${r.y-d}L${r.x+d} ${r.y+d}M${r.x-d} ${r.y+d}L${r.x+d} ${r.y-d}" stroke="${EC.riser}" stroke-width=".7"/><text x="${r.x+R+2}" y="${r.y+3}" font-size="9" font-family="Inter,sans-serif" fill="${EC.riser}" font-weight="600">${r.type}</text>`}
const outl=(d,dash)=>`<path d="${d}" fill="var(--acc)" fill-opacity="${dash?0:.1}" stroke="var(--acc)" stroke-width="${dash?1.2:2}" ${dash?'stroke-dasharray="4 3"':''} vector-effect="non-scaling-stroke" style="pointer-events:none"/>`;
function elOutline(M,h,dash){if(!h)return '';const s=ED.s||1;
 if(h.t=='wall'){const w=M.walls.find(x=>x.id==h.id);if(!w)return '';const G=wgeo(w);return outl(obox(G.cx,G.cy,G.a,G.L,w.t),dash)+(dash?'':[[w.x1,w.y1],[w.x2,w.y2]].map(([x,y])=>`<circle cx="${x}" cy="${y}" r="${4*s}" fill="#fff" stroke="var(--acc)" stroke-width="1.5" vector-effect="non-scaling-stroke"/>`).join(''))}
 if(h.t=='op'){const o=M.ops.find(x=>x.id==h.id);return o?outl(obox(o.x,o.y,o.a,o.w,o.t+1),dash):''}
 if(h.t=='furn'){const f=M.furn.find(x=>x.id==h.id);if(!f)return '';const b=fbox(f);return outl(obox(b.cx,b.cy,b.a,b.l+1,b.t+1),dash)}
 if(h.t=='riser'){const r=M.risers.find(x=>x.id==h.id);return r?`<circle cx="${r.x}" cy="${r.y}" r="${Math.max(r.d/MM/2,4)+2}" fill="none" stroke="var(--acc)" stroke-width="2" ${dash?'stroke-dasharray="4 3"':''} vector-effect="non-scaling-stroke"/>`:''}
 if(h.t=='fixed')return `<path d="${M.fixed}" fill="var(--acc)" fill-opacity=".12" stroke="var(--acc)" stroke-width="${dash?1.2:2}" ${dash?'stroke-dasharray="4 3"':''} fill-rule="evenodd" vector-effect="non-scaling-stroke" style="pointer-events:none"/>`;
 return ''}
function msvg(M,o={}){const K=calcRooms(M),fs=13,ed=o.ed&&ED.on;let s='';
 if(M.lay!='contour')s+=`<use href="#rh-${M.lay}-f"/>`;
 s+=`<image href="${K.url}" x="0" y="0" width="${K.W}" height="${K.H}" preserveAspectRatio="none"/>`;
 const rs=ed?(ED.sel&&ED.sel.t=='room'?ED.sel.i:null):o.sel;if(rs!=null&&K.regs[rs])s+=`<image href="${selURL(M,rs)}" x="0" y="0" width="${K.W}" height="${K.H}" preserveAspectRatio="none"/>`;
 s+=(M.cut||[]).map(c=>`<path d="M${c[0]} ${c[1]}L${c[2]} ${c[3]}" stroke="#6B7280" stroke-width="1.2" stroke-dasharray="5 4"/>`).join('');
 if(M.furnOn!==false)s+=M.furn.map(furG).join('');
 if(M.fixed)s+=`<path d="${M.fixed}" fill="${EC.ext}" fill-rule="evenodd"/>`;
 s+=M.walls.map(w=>{const G=wgeo(w);return `<path d="${obox(G.cx,G.cy,G.a,G.L,w.t)}" fill="${EC[w.type]||EC.part}"/>`}).join('');
 s+=M.ops.map(opG).join('')+M.risers.map(riserG).join('');
 if(o.label!==false&&(!ed||ED.lbl))M.rooms.forEach((l,i)=>{const r=K.regs[K.lab2[i]],on=r&&K.lab2[i]===rs,bg=on?'#E3E8FD':r?RCOL(r.n):'#fff';
  s+=`<g style="pointer-events:none" font-family="Inter,sans-serif" text-anchor="middle" paint-order="stroke" stroke="${bg}" stroke-width="4" stroke-linejoin="round"><text x="${l.x}" y="${l.y+fs*.35}" font-size="${fs}" font-weight="600" fill="${on?'var(--acc-text)':r?'#1F2328':'#9CA3AF'}">${l.n}</text>${(o.area||ed)&&r&&r.main===i?`<text x="${l.x}" y="${l.y+fs*1.5}" font-size="${fs*.85}" fill="#1F2328">${r.a.toFixed(1)} м²</text>`:''}</g>`});
 if(ed){s+=elOutline(M,ED.hover&&!(ED.sel&&ED.hover.t==ED.sel.t&&ED.hover.id==ED.sel.id)?ED.hover:null,1)+elOutline(M,ED.sel);s+=previewG(M)}
 return `<svg viewBox="${M.vb}" width="100%" style="display:block;overflow:visible" data-m="1">${s}</svg>`}
function previewG(M){const t=ED.tool,P=ED.pt;if(!P)return '';let s='';const g='fill="var(--acc)" fill-opacity=".35" stroke="var(--acc)" stroke-width="1.2" vector-effect="non-scaling-stroke"';
 if(t=='wall'){const th=ED.wth/MM;if(ED.chain){const w={x1:ED.chain.x,y1:ED.chain.y,x2:P.x,y2:P.y,t:th,cap:1},G=wgeo(w);if(G.len>.5)s+=`<path d="${obox(G.cx,G.cy,G.a,G.L,th)}" ${g}/><text x="${G.cx}" y="${G.cy-th/2-4}" font-size="${11*ED.s}" text-anchor="middle" font-family="Inter,sans-serif" fill="var(--acc-text)" font-weight="600" paint-order="stroke" stroke="#fff" stroke-width="${3*ED.s}">${mmv(G.len).toLocaleString('ru-RU')}</text>`}
  s+=`<circle cx="${P.x}" cy="${P.y}" r="${4*ED.s}" fill="var(--acc)"/>`}
 if((t=='door'||t=='window')&&ED.prev){const o=ED.prev;s+=`<g opacity=".85">${opG(o)}</g>`+outl(obox(o.x,o.y,o.a,o.w,o.t+1))}
 if(t=='furn'&&ED.fg)s+=`<g opacity=".7">${furG(ED.fg)}</g>`;
 if(t=='riser')s+=`<g opacity=".6">${riserG({x:P.x,y:P.y,d:110,type:ED.rt})}</g>`;
 return s}
/* ---- состояние правки ---- */
let ED={on:0,tool:'select',sel:null,hover:null,hist:[],fut:[],chain:null,pt:null,prev:null,fg:null,s:1,lbl:1,ft:'bed',frot:0,wt:'part',wth:100,dw:800,ww:1400,rt:'К1',dirty:0};
let CM=null;const curM=()=>refOn?null:sel?sel.M:contour?(CM||(CM=mkModel('contour'))):null;
const snap=M=>cl({walls:M.walls,ops:M.ops,furn:M.furn,risers:M.risers,rooms:M.rooms,furnOn:M.furnOn});
function syncR(v){const K=calcRooms(v.M);v.R=K.regs.map(R=>({n:R.n,a:R.a,p:''}));v.R.rh={lay:v.M.lay,furn:v.M.furnOn!==false};v.R.M=v.M;
 v.live=v.R.filter(m=>/Спальн|Гостин/.test(m.n)).reduce((s,m)=>s+m.a,0).toFixed(1)}
let _rl=0;function changed(geo){const M=curM();if(geo)M.gv++;if(sel){if(!ED.dirty){sel.ver++;ED.dirty=1}syncR(sel);clearTimeout(_rl);_rl=setTimeout(()=>{renderList();if(sel)$('#vinfo .m')&&showVinfo()},250)}saved();draw();renderProps()}
function mut(fn,geo){const M=curM();ED.hist.push(snap(M));if(ED.hist.length>80)ED.hist.shift();ED.fut=[];fn(M);changed(geo)}
function restore(st){const M=curM();Object.assign(M,cl(st));M.gv++;M.seq+=50}
function undo(){if(!ED.hist.length)return toast('Нечего отменять');const M=curM();ED.fut.push(snap(M));restore(ED.hist.pop());ED.sel=null;changed(0)}
function redo(){if(!ED.fut.length)return;const M=curM();ED.hist.push(snap(M));restore(ED.fut.pop());ED.sel=null;changed(0)}
const nid=(M,p)=>p+(++M.seq);
function draw(){const M=curM();if(!M)return;if(ED.on){$('#plan').innerHTML=msvg(M,{ed:1,area:1});return}if(sel)drawSel();else $('#plan').innerHTML=msvg(M,{})}
function edStart(){const M=curM();if(!M){if(refOn)toast('Эталон бюро не редактируется — выберите вариант');return}
 if(!ED.on){ED.on=1;ED.hist=[];ED.fut=[];ED.dirty=0;ED.sel=null}$('.right').classList.add('ed');$('#insp').style.display='none';rSel=null;
 $('#ptitle').textContent='Правка';$('#pedit .rsub').textContent=sel?`Вариант ${sel.id} · свойства`:'Контур квартиры · свойства';$('#sheettag').innerHTML=`<span class="i" style="font-size:15px">edit</span><b>Правка</b>· ${sel?'Вариант '+sel.id:'контур квартиры'} · клик — выбрать, тянуть — сдвинуть`;draw();renderProps()}
function edDone(){if(!ED.on)return;const was=ED.dirty;ED.on=0;ED.sel=null;ED.chain=null;ED.prev=null;ED.fg=null;tool='select';renderTb();hint('');$('.right').classList.remove('ed');
 if(sel){showVar(sel.id);if(was)toast(`Правки сохранены · вариант ${sel.id} v${sel.ver}`)}else if(contour){$('#sheettag').innerHTML=CT;draw();if(was)toast('Контур сохранён')}ED.dirty=0}
/* ---- поиск под курсором ---- */
function hit(M,p){const e=5*ED.s;
 for(const r of M.risers)if(Math.hypot(p.x-r.x,p.y-r.y)<=Math.max(r.d/MM/2,4)+e)return {t:'riser',id:r.id};
 for(const o of M.ops)if(inBox(p.x,p.y,o.x,o.y,o.a,o.w,o.t,e*.6))return {t:'op',id:o.id};
 for(const w of M.walls){const G=wgeo(w);if(inBox(p.x,p.y,G.cx,G.cy,G.a,G.L,w.t,e*.6))return {t:'wall',id:w.id}}
 if(inFixed(M,p.x,p.y))return {t:'fixed'};
 if(M.furnOn!==false)for(let i=M.furn.length-1;i>=0;i--){const f=M.furn[i],b=fbox(f);if(inBox(p.x,p.y,b.cx,b.cy,b.a,b.l,b.t,0))return {t:'furn',id:f.id}}
 const r=regAt(M,p.x,p.y);if(r>=0)return {t:'room',i:r};return null}
/* привязка: концы и оси стен, ортогональность от начала */
function snapPt(M,p,from){let x=p.x,y=p.y,best=10*ED.s;
 M.walls.forEach(w=>[[w.x1,w.y1],[w.x2,w.y2]].forEach(([a,b])=>{const d=Math.hypot(a-p.x,b-p.y);if(d<best){best=d;x=a;y=b}}));
 if(best==10*ED.s){if(from){const dx=x-from.x,dy=y-from.y;if(Math.abs(dy)<Math.abs(dx)*.18)y=from.y;else if(Math.abs(dx)<Math.abs(dy)*.18)x=from.x}
  let bw=8*ED.s;M.walls.forEach(w=>{const G=wgeo(w),[s,q]=loc(x,y,G.cx,G.cy,G.a);if(Math.abs(q)<bw&&Math.abs(s)<=G.len/2+w.t){bw=Math.abs(q);x=G.cx+G.ux*s;y=G.cy+G.uy*s}});
  if(bw==8*ED.s){x=q2(x);y=q2(y)}}
 return {x,y}}
/* проём под курсором: перегородка (по оси) или наружная стена из модели (по ближайшей грани) */
function placeOp(M,p,k){const w0=(k=='door'?ED.dw:ED.ww)/MM;let best=null,bd=1e9;
 M.walls.forEach(w=>{const G=wgeo(w),[s,q]=loc(p.x,p.y,G.cx,G.cy,G.a);if(Math.abs(s)>G.len/2+2||Math.abs(q)>w.t/2+8*ED.s)return;if(Math.abs(q)<bd){bd=Math.abs(q);const ww=Math.min(w0,G.len-1),c=Math.max(-G.len/2+ww/2,Math.min(G.len/2-ww/2,s));
  best={k:k=='door'?'door':'win',x:G.cx+G.ux*c,y:G.cy+G.uy*c,a:G.a,w:ww,t:w.t,side:q<0?-1:1,h:ED.hg||'s',wall:w.id}}});
 if(best)return best;if(!M.fixed)return null;
 let fe=null;fixedPolys(M).forEach(pg=>pg.forEach((a,i)=>{const b=pg[(i+1)%pg.length],dx=b[0]-a[0],dy=b[1]-a[1],L2=dx*dx+dy*dy;if(L2<4)return;let t=((p.x-a[0])*dx+(p.y-a[1])*dy)/L2;t=Math.max(0,Math.min(1,t));const fx=a[0]+dx*t,fy=a[1]+dy*t,d=Math.hypot(p.x-fx,p.y-fy);if(d<bd){bd=d;fe={fx,fy,dx,dy,L:Math.sqrt(L2)}}}));
 if(!fe||(bd>10*ED.s&&!inFixed(M,p.x,p.y)))return null;const ux=fe.dx/fe.L,uy=fe.dy/fe.L;let nx=-uy,ny=ux;if(!inFixed(M,fe.fx+nx*1,fe.fy+ny*1)){nx=-nx;ny=-ny}
 let t=0;for(let s=.5;s<40;s+=.5){if(inFixed(M,fe.fx+nx*s,fe.fy+ny*s))t=s;else if(t)break}if(t<3)return null;
 const cx=fe.fx+nx*t/2,cy=fe.fy+ny*t/2;let a=Math.atan2(uy,ux)*180/Math.PI;if(a>90)a-=180;if(a<=-90)a+=180;const [ax,ay]=ang(a),mx=-ay,my=ax;
 const side=regAt(M,cx+mx*(t/2+4),cy+my*(t/2+4))>=0?1:-1;return {k:k=='door'?'door':'win',x:cx,y:cy,a,w:w0,t,side,h:ED.hg||'s'}}
/* мебель «спинкой к стене» */
function placeFurn(M,p){const c=FC[ED.ft];let best=null,bd=(c[3]/MM)*.75+6;
 const face=(fx,fy,nx,ny)=>{const d=(p.x-fx)*nx+(p.y-fy)*ny;if(d>0&&d<bd){bd=d;best={x:p.x-nx*d,y:p.y-ny*d,r:Math.round(Math.atan2(-nx,ny)*180/Math.PI)}}};
 M.walls.forEach(w=>{const G=wgeo(w),[s]=loc(p.x,p.y,G.cx,G.cy,G.a);if(Math.abs(s)>G.len/2)return;const nx=-G.uy,ny=G.ux;[1,-1].forEach(k=>face(G.cx+s*G.ux+nx*k*w.t/2,G.cy+s*G.uy+ny*k*w.t/2,nx*k,ny*k))});
 fixedPolys(M).forEach(pg=>pg.forEach((a,i)=>{const b=pg[(i+1)%pg.length],dx=b[0]-a[0],dy=b[1]-a[1],L=Math.hypot(dx,dy);if(L<8)return;const t=((p.x-a[0])*dx+(p.y-a[1])*dy)/L/L;if(t<0||t>1)return;
  let nx=-dy/L,ny=dx/L;if(inFixed(M,a[0]+dx*t+nx,a[1]+dy*t+ny)){nx=-nx;ny=-ny}face(a[0]+dx*t,a[1]+dy*t,nx,ny)}));
 return best?{c:ED.ft,x:q2(best.x),y:q2(best.y),r:best.r,m:0}:{c:ED.ft,x:q2(p.x),y:q2(p.y),r:ED.frot,m:0}}
/* ---- мышь ---- */
let DR=null,PAN=null,_raf=0;const reDraw=()=>{if(_raf)return;_raf=requestAnimationFrame(()=>{_raf=0;draw()})};
function evP(e){const sv=$('#plan svg[data-m]');if(!sv)return null;const m=sv.getScreenCTM();if(!m)return null;ED.s=1/m.a;return new DOMPoint(e.clientX,e.clientY).matrixTransform(m.inverse())}
$('#plan').addEventListener('pointerdown',e=>{if(e.button==1){const st=$('#stage');PAN={x:e.clientX,y:e.clientY,l:st.scrollLeft,t:st.scrollTop};e.preventDefault();return}
 if(e.button!==0)return;const M=curM(),p=evP(e);if(!M||!p)return;
 if(!ED.on){const h=hit(M,p);if(!h)return;if(h.t=='room'){if(sel)pickRoom(h.i);return}edStart();ED.sel=h;draw();renderProps();return}
 const t=ED.tool;e.preventDefault();
 if(t=='select'){const s0=ED.sel&&ED.sel.t=='wall'&&M.walls.find(w=>w.id==ED.sel.id);
  if(s0)for(const k of [1,2])if(Math.hypot(p.x-s0['x'+k],p.y-s0['y'+k])<7*ED.s){DR={k:'end',end:k,id:s0.id,p0:p,st:snap(M),o:cl(s0),mv:0};return}
  const h=hit(M,p);ED.sel=h;if(h&&h.t=='fixed')toast('Наружный контур из модели на замке — двигать нельзя, проёмы ставятся');
  if(h&&h.t!='fixed'&&h.t!='room'||h&&h.t=='room')DR={k:h.t,id:h.id,i:h.i,p0:p,st:snap(M),mv:0,o:cl(h.t=='wall'?M.walls.find(w=>w.id==h.id):h.t=='op'?M.ops.find(o=>o.id==h.id):h.t=='furn'?M.furn.find(f=>f.id==h.id):h.t=='riser'?M.risers.find(r=>r.id==h.id):null)};
  if(DR&&DR.k=='wall'){const w=DR.o,G=wgeo(w);DR.con=[];M.walls.forEach(v=>{if(v.id==w.id)return;const H=wgeo(v);if(Math.abs(H.ux*G.ux+H.uy*G.uy)>.5)return;[1,2].forEach(k=>{const [s,q]=loc(v['x'+k],v['y'+k],G.cx,G.cy,G.a);if(Math.abs(q)<=w.t/2+v.t/2+1.5&&Math.abs(s)<=G.len/2+v.t)DR.con.push({id:v.id,k,x:v['x'+k],y:v['y'+k]})})});
   DR.ops=M.ops.filter(o=>o.wall==w.id).map(o=>({id:o.id,x:o.x,y:o.y}))}
  if(DR&&DR.k=='room'){const K=calcRooms(M),R=K.regs[h.i];DR.lab=R?R.main:null;DR.o=DR.lab!=null?cl(M.rooms[DR.lab]):null}
  draw();renderProps();return}
 if(t=='wall'){const q=snapPt(M,p,ED.chain);if(!ED.chain){ED.chain=q;hint('Клик — следующий угол · Esc или двойной клик — закончить');reDraw();return}
  const w={x1:q2(ED.chain.x),y1:q2(ED.chain.y),x2:q2(q.x),y2:q2(q.y)};if(Math.hypot(w.x2-w.x1,w.y2-w.y1)<2){ED.chain=null;reDraw();return}
  mut(M=>{M.walls.push({id:nid(M,'w'),...w,t:ED.wth/MM,type:ED.wt,cap:1,fixed:ED.wt!='part'?1:0})},1);ED.chain=q;return}
 if(t=='door'||t=='window'){const o=placeOp(M,p,t);if(!o)return toast('Наведите на стену');mut(M=>{o.id=nid(M,'o');M.ops.push(o)},1);ED.sel={t:'op',id:o.id};renderProps();return}
 if(t=='riser'){mut(M=>{const r={id:nid(M,'r'),x:q2(p.x),y:q2(p.y),d:110,type:ED.rt,fixed:1};M.risers.push(r);ED.sel={t:'riser',id:r.id}},0);return}
 if(t=='room'){const r=regAt(M,p.x,p.y);if(r<0)return toast('Кликните внутри замкнутого контура стен');const K=calcRooms(M);if(K.regs[r]&&K.regs[r].labs.length){ED.sel={t:'room',i:r};draw();renderProps();return}
  mut(M=>M.rooms.push({n:'Помещение',x:q2(p.x),y:q2(p.y)}),1);ED.sel={t:'room',i:calcRooms(M).lab2[M.rooms.length-1]};draw();renderProps();return}
 if(t=='furn'){const f=placeFurn(M,p);mut(M=>{f.id=nid(M,'f');M.furn.push(f);M.furnOn=true},0);ED.sel={t:'furn',id:f.id};renderProps();return}});
$('#plan').addEventListener('dblclick',()=>{if(ED.on&&ED.tool=='wall'){ED.chain=null;hint('Клик — начало стены · привязка к углам и осям стен');reDraw()}});
window.addEventListener('pointermove',e=>{if(PAN){const st=$('#stage');st.scrollLeft=PAN.l-(e.clientX-PAN.x);st.scrollTop=PAN.t-(e.clientY-PAN.y);return}
 const M=curM();if(!M||!$('#s-ws').classList.contains('on'))return;const p=evP(e);if(!p)return;
 if(!ED.on){if(e.target.closest&&e.target.closest('#plan')){const h=hit(M,p);$('#plan').style.cursor=h?'pointer':''}return}
 if(DR){const dx=p.x-DR.p0.x,dy=p.y-DR.p0.y;if(!DR.mv&&Math.hypot(dx,dy)<2*ED.s)return;if(!DR.mv){ED.hist.push(DR.st);ED.fut=[];DR.mv=1}
  if(DR.k=='furn'||DR.k=='riser'){const a=(DR.k=='furn'?M.furn:M.risers).find(x=>x.id==DR.id);a.x=q2(DR.o.x+dx);a.y=q2(DR.o.y+dy)}
  else if(DR.k=='room'&&DR.o){const l=M.rooms[DR.lab];l.x=q2(DR.o.x+dx);l.y=q2(DR.o.y+dy)}
  else if(DR.k=='wall'){const w=M.walls.find(x=>x.id==DR.id),G=wgeo(DR.o),nx=-G.uy,ny=G.ux,d=q2(dx*nx+dy*ny);w.x1=DR.o.x1+nx*d;w.y1=DR.o.y1+ny*d;w.x2=DR.o.x2+nx*d;w.y2=DR.o.y2+ny*d;
   DR.con.forEach(c=>{const v=M.walls.find(x=>x.id==c.id);if(v){v['x'+c.k]=c.x+nx*d;v['y'+c.k]=c.y+ny*d}});DR.ops.forEach(c=>{const o=M.ops.find(x=>x.id==c.id);if(o){o.x=c.x+nx*d;o.y=c.y+ny*d}})}
  else if(DR.k=='end'){const w=M.walls.find(x=>x.id==DR.id),k=DR.end,o2=k==1?2:1,q=snapPt(M,{x:DR.o['x'+k]+dx,y:DR.o['y'+k]+dy},{x:DR.o['x'+o2],y:DR.o['y'+o2]});w['x'+k]=q2(q.x);w['y'+k]=q2(q.y)}
  else if(DR.k=='op'){const o=M.ops.find(x=>x.id==DR.id),w=o.wall&&M.walls.find(x=>x.id==o.wall);
   if(w){const G=wgeo(w),[s]=loc(p.x,p.y,G.cx,G.cy,G.a),c=Math.max(-G.len/2+o.w/2,Math.min(G.len/2-o.w/2,q2(s)));o.x=G.cx+G.ux*c;o.y=G.cy+G.uy*c}
   else{const [ux,uy]=ang(DR.o.a),s=q2(dx*ux+dy*uy);o.x=DR.o.x+ux*s;o.y=DR.o.y+uy*s}}
  reDraw();return}
 ED.pt=ED.tool=='wall'?snapPt(M,p,ED.chain):p;
 if(ED.tool=='door'||ED.tool=='window')ED.prev=placeOp(M,p,ED.tool);
 if(ED.tool=='furn')ED.fg=placeFurn(M,p);
 if(ED.tool=='select'){const h=e.target.closest&&e.target.closest('#plan')?hit(M,p):null,k=h?h.t+(h.id||h.i):'',k0=ED.hover?ED.hover.t+(ED.hover.id||ED.hover.i):'';$('#plan').style.cursor=h&&h.t!='fixed'&&h.t!='room'?'move':h?'pointer':'';if(k==k0)return;ED.hover=h&&h.t!='room'?h:null}
 else $('#plan').style.cursor='crosshair';
 reDraw()});
window.addEventListener('pointerup',()=>{PAN=null;if(!DR)return;const d=DR;DR=null;if(d.mv)changed(d.k!='furn'&&d.k!='riser'?1:0)});
/* ---- клавиши (перехват до общего обработчика) ---- */
window.addEventListener('keydown',e=>{if(!$('#s-ws').classList.contains('on')||/TEXTAREA|INPUT|SELECT/.test(e.target.tagName))return;const k=e.key.toLowerCase(),M=curM();
 if((e.ctrlKey||e.metaKey)&&(k=='z'||k=='я')){if(ED.on){e.shiftKey?redo():undo();e.preventDefault()}return}
 if((e.ctrlKey||e.metaKey)&&(k=='y'||k=='н')){if(ED.on){redo();e.preventDefault()}return}
 if(!ED.on)return;
 if(e.key=='Escape'){e.stopImmediatePropagation();if(ED.chain){ED.chain=null;reDraw();return}if(ED.tool!='select'){_pick('select');ED.tool='select';ED.prev=ED.fg=null;renderProps();reDraw();return}if(ED.sel){ED.sel=null;draw();renderProps();return}edDone();return}
 if(e.key=='Enter'&&ED.chain){ED.chain=null;reDraw();return}
 if(e.key=='Tab'&&ED.tool=='door'){e.preventDefault();ED.hg=ED.hg=='e'?'s':'e';if(ED.prev)ED.prev.h=ED.hg;reDraw();return}
 if((e.key=='Delete'||e.key=='Backspace')&&ED.sel){e.preventDefault();delSel();return}
 if(k=='r'||k=='к'){e.stopImmediatePropagation();if(ED.tool=='furn'){ED.frot=(ED.frot+90)%360;if(ED.fg&&ED.pt){ED.fg=placeFurn(M,ED.pt);ED.fg.r=ED.frot}reDraw();return}if(ED.sel&&ED.sel.t=='furn'){turnF(e.shiftKey?-90:90);return}pickTool('room');return}});
function delSel(){const M=curM(),s=ED.sel;if(!s)return;if(s.t=='fixed')return toast('Наружный контур из модели на замке');
 if(s.t=='room'){const R=calcRooms(M).regs[s.i];if(!R)return;mut(M=>{M.rooms=M.rooms.filter((l,i)=>!R.labs.includes(i))},1);ED.sel=null;renderProps();return}
 mut(M=>{if(s.t=='wall'){M.walls=M.walls.filter(w=>w.id!=s.id);M.ops=M.ops.filter(o=>o.wall!=s.id)}
  if(s.t=='op'){const o=M.ops.find(x=>x.id==s.id);if(!o.wall&&o.k!='blank'&&o.k!='pass'){o.was=o.k;o.k='blank'}else M.ops=M.ops.filter(x=>x.id!=s.id)}
  if(s.t=='furn')M.furn=M.furn.filter(f=>f.id!=s.id);if(s.t=='riser')M.risers=M.risers.filter(r=>r.id!=s.id)},s.t!='furn'&&s.t!='riser');ED.sel=null;renderProps()}
function turnF(d){const M=curM(),f=M.furn.find(x=>x.id==ED.sel.id);if(!f)return;mut(()=>{f.r=((f.r+d)%360+360)%360},0)}
/* ---- панель «Свойства» справа ---- */
const fld=(lab,val,on,unit='мм',dis)=>`<label class="fld"><span>${lab}</span><input inputmode="numeric" value="${val}" ${dis?'disabled':''} onchange="${on}"><span>${unit}</span></label>`;
const pchip=(t,on,js,dis)=>`<button class="chip ${on?'on':''}" ${dis?'disabled':''} onclick="${js}">${t}</button>`;
const SW=[['s',-1,'Петли слева · вверх','M5 12 L5 3 A9 9 0 0 1 14 12'],['e',-1,'Петли справа · вверх','M19 12 L19 3 A9 9 0 0 0 10 12'],['s',1,'Петли слева · вниз','M5 12 L5 21 A9 9 0 0 0 14 12'],['e',1,'Петли справа · вниз','M19 12 L19 21 A9 9 0 0 1 10 12']];
const sec=(ic,t,b)=>`<div class="blk"><p class="lbl"><span class="i" style="font-size:16px">${ic}</span>${t}</p>${b}</div>`;
function opOff(M,o){const w=M.walls.find(x=>x.id==o.wall);if(!w)return null;const G=wgeo(w),[s]=loc(o.x,o.y,G.cx,G.cy,G.a);return mmv(s+G.len/2-o.w/2)}
function opsList(M,w){const os=M.ops.filter(o=>o.wall==w.id);if(!os.length)return '';return `<p class="lbl" style="margin:14px 0 6px">Проёмы</p>`+os.map(o=>`<button class="orow" onclick="ED.sel={t:'op',id:'${o.id}'};draw();renderProps()"><span class="i">${o.k=='door'?'door_front':o.k=='win'?'window':'crop_free'}</span>${o.k=='door'?'Дверь':o.k=='win'?'Окно':'Проход'}<span class="sp"></span><span class="lead">${mmv(o.w)} мм</span></button>`).join('')}
function renderProps(){if(!ED.on)return;const M=curM(),s=ED.sel,b=$('#props');if(!M)return;$('#undo').disabled=!ED.hist.length;$('#redo').disabled=!ED.fut.length;let h='';
 const tl={wall:'Стена',door:'Дверь',window:'Окно',riser:'Стояк',room:'Помещение',furn:'Мебель',ruler:'Масштаб'}[ED.tool];
 if(tl&&!(s&&(ED.tool=='door'||ED.tool=='window'||ED.tool=='furn'||ED.tool=='riser'))){
  if(ED.tool=='wall')h+=sec('draw','Новая стена',`<div class="seg" style="margin-bottom:6px">${Object.entries(WT).map(([k,[n,t]])=>`<button class="${ED.wt==k?'on':''}" onclick="ED.wt='${k}';ED.wth=${t};renderProps()">${n}</button>`).join('')}</div>${fld('Толщина',ED.wth,"ED.wth=+this.value||ED.wth")}<p class="hintp">Клик — начало, клик — следующий угол. Привязка к углам и осям стен, ортогонально от начала. Esc или двойной клик — закончить.</p>`);
  if(ED.tool=='door')h+=sec('door_front','Новая дверь',`${fld('Ширина',ED.dw,"ED.dw=+this.value||ED.dw")}<p class="hintp">Наведите на стену и кликните. Сторона открывания — по курсору, Tab — петли.</p>`);
  if(ED.tool=='window')h+=sec('window','Новое окно',`${fld('Ширина',ED.ww,"ED.ww=+this.value||ED.ww")}<p class="hintp">Наведите на наружную стену и кликните.</p>`);
  if(ED.tool=='riser')h+=sec('water_drop','Новый стояк',`<div class="rooms">${RT.map(t=>pchip(t,ED.rt==t,`ED.rt='${t}';renderProps()`)).join('')}</div><p class="hintp">${ED.rt} · ${RTL[ED.rt]}. Клик — поставить. Стояки фиксируются при генерации.</p>`);
  if(ED.tool=='room')h+=sec('dashboard','Помещение',`<p class="hintp">Клик внутри замкнутого контура стен — помещение с площадью по внутренним граням.</p>`);
  if(ED.tool=='ruler')h+=sec('straighten','Масштаб',`<p class="hintp">Два клика по отрезку известной длины на подложке, затем длина в мм. План из Rhino уже в масштабе.</p>`)}
 if(ED.tool=='furn')h+=sec('chair','Каталог IND',`<div class="cat">${FCAT.map(([c,n,w,d])=>`<button class="${ED.ft==c?'on':''}" onclick="ED.ft='${c}';ED.frot=0;renderProps()" title="${n}"><svg viewBox="${-w/2-60} -60 ${w+120} ${d+120}" width="44" height="34"><path d="${fup(c)}" fill="#fff" stroke="${EC.furn}" stroke-width="${Math.max(w,d)/40}"/></svg><span>${n}</span><small>${w}×${d}</small></button>`).join('')}</div><p class="hintp">Клик — поставить. У стены встаёт спинкой к стене. R — поворот 90°.</p>`);
 if(s){
  if(s.t=='wall'){const w=M.walls.find(x=>x.id==s.id);if(w){const G=wgeo(w);h+=sec('view_agenda','Стена',`<div class="seg" style="margin-bottom:6px">${Object.entries(WT).map(([k,[n,t]])=>`<button class="${w.type==k?'on':''}" onclick="mut(M=>{const w=M.walls.find(x=>x.id=='${w.id}');w.type='${k}';w.t=${t}/MM;w.fixed=${k!='part'?1:0};M.ops.forEach(o=>{if(o.wall==w.id)o.t=w.t})},1)">${n}</button>`).join('')}</div>
   ${fld('Толщина',mmv(w.t),`setW('${w.id}','t',this.value)`)}${fld('Длина',mmv(G.len),`setW('${w.id}','len',this.value)`)}
   <div class="chk ${w.fixed?'on':''}" onclick="mut(M=>{const w=M.walls.find(x=>x.id=='${w.id}');w.fixed=w.fixed?0:1},0)"><span class="bx"><span class="i">check</span></span>Зафиксирована при генерации</div>${opsList(M,w)}
   <div class="pacts"><button class="btn sm" onclick="delSel()"><span class="i">delete</span>Удалить стену</button></div>`)}}
  if(s.t=='fixed')h+=sec('lock','Наружные стены',`<p class="hintp" style="margin-top:0">Контур квартиры из модели Rhino — на замке, как основа из Revit. Двигать нельзя; двери и окна в нём ставятся инструментами «Дверь» и «Окно», лишний проём можно заложить.</p><div class="row"><span class="lead">Толщина</span><span>по модели</span></div>`);
  if(s.t=='op'){const o=M.ops.find(x=>x.id==s.id);if(o){const off=opOff(M,o),nm={door:'Дверь',win:'Окно',pass:'Проход без полотна',blank:'Заложенный проём'}[o.k],up=`mut(M=>{const o=M.ops.find(x=>x.id=='${o.id}');`;
   h+=sec(o.k=='door'?'door_front':o.k=='win'?'window':'crop_free',nm+(o.wall?'':' · в наружной стене'),
   (o.k=='door'?`<p class="lbl" style="margin:0 0 6px">Открывание</p><div class="swg">${SW.map(([hg,sd,t,d])=>`<button title="${t}" class="${o.h==hg&&o.side==sd?'on':''}" onclick="${up}o.h='${hg}';o.side=${sd}},0)"><svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.5"><line x1="2" y1="12" x2="22" y2="12" stroke-width="3" stroke-opacity=".35"/><path d="${d}"/></svg></button>`).join('')}</div>
    <div class="pacts" style="margin-top:8px"><button class="btn sm" onclick="${up}o.h=o.h=='s'?'e':'s'},0)"><span class="i">swap_horiz</span>Петли</button><button class="btn sm" onclick="${up}o.side=-o.side},0)"><span class="i">swap_vert</span>Внутрь / наружу</button></div>`:'')+
   (o.k!='blank'?fld('Ширина',mmv(o.w),`setOp('${o.id}','w',this.value)`)+(off!=null?fld('От угла',off,`setOp('${o.id}','off',this.value)`):''):'')+
   `<div class="pacts">${o.k=='pass'?`<button class="btn sm" onclick="${up}o.k='door';o.side=1;o.h='s'},1)"><span class="i">door_front</span>Поставить дверь</button>`:''}${o.k=='blank'?`<button class="btn sm" onclick="${up}o.k=o.was||'win'},1)"><span class="i">undo</span>Вернуть ${o.was=='door'?'дверь':'окно'}</button>`:`<button class="btn sm" onclick="delSel()"><span class="i">${o.wall?'delete':'select'}</span>${o.wall?'Удалить проём':'Заложить проём'}</button>`}</div>`)}}
  if(s.t=='furn'){const f=M.furn.find(x=>x.id==s.id);if(f){const c=f.c&&FC[f.c];h+=sec('chair',c?c[1]:(f.cat=='PLB'?'Сантехника из модели':'Мебель из модели'),
   (c?`<select class="sel" onchange="mut(M=>{const f=M.furn.find(x=>x.id=='${f.id}');f.c=this.value},0)">${FCAT.map(([k,n,w,d])=>`<option value="${k}" ${k==f.c?'selected':''}>${n} · ${w}×${d}</option>`).join('')}</select>`:'')+
   `<div class="row"><span class="lead">Габарит</span><span>${c?c[2]+' × '+c[3]:f.w+' × '+f.d} мм</span></div><div class="row"><span class="lead">Поворот</span><span>${f.r}°${f.m?' · зеркально':''}</span></div>
   <div class="pacts"><button class="btn sm" onclick="turnF(90)"><span class="i">rotate_right</span>90°</button><button class="btn sm" onclick="turnF(-90)"><span class="i">rotate_left</span>90°</button><button class="btn sm ${f.m?'onb':''}" onclick="mut(M=>{const f=M.furn.find(x=>x.id=='${f.id}');f.m=f.m?0:1},0)"><span class="i">flip</span>Зеркало</button></div>
   <div class="pacts"><button class="btn sm" onclick="delSel()"><span class="i">delete</span>Удалить</button></div>`)}}
  if(s.t=='riser'){const r=M.risers.find(x=>x.id==s.id);if(r)h+=sec('water_drop','Стояк',`<div class="rooms">${RT.map(t=>pchip(t,r.type==t,`mut(M=>{M.risers.find(x=>x.id=='${r.id}').type='${t}'},0)`)).join('')}</div><p class="hintp">${r.type} · ${RTL[r.type]}</p>${fld('Диаметр',r.d,`mut(M=>{M.risers.find(x=>x.id=='${r.id}').d=+this.value||110},0)`)}
   <div class="chk ${r.fixed?'on':''}" onclick="mut(M=>{const r=M.risers.find(x=>x.id=='${r.id}');r.fixed=r.fixed?0:1},0)"><span class="bx"><span class="i">check</span></span>Зафиксирован при генерации</div><div class="pacts"><button class="btn sm" onclick="delSel()"><span class="i">delete</span>Удалить</button></div>`)}
  if(s.t=='room'){const K=calcRooms(M),R=K.regs[s.i];if(R){const L=M.rooms[R.main];h+=sec('dashboard','Помещение',`<label class="fld" style="grid-template-columns:96px 1fr"><span>Название</span><input value="${L.n}" onchange="renameRoom(this.value)"></label>
   <div class="rooms" style="margin:8px 0 10px">${RNAMES.map(n=>pchip(n,L.n==n,`renameRoom('${n}')`)).join('')}</div>
   <div class="row"><span class="lead">Площадь</span><b>${R.a.toFixed(1)} м²</b></div><p class="hintp">По внутренним граням стен, пересчитывается при каждой правке.${R.labs.length>1?' Открытая зона: '+R.n+'.':''}</p>
   <div class="pacts"><button class="btn sm" onclick="delSel()"><span class="i">delete</span>Убрать помещение</button></div>`)}}}
 if(!s&&(!tl||ED.tool=='ruler')&&ED.tool!='furn'){const K=calcRooms(M),tot=K.regs.reduce((a,r)=>a+r.a,0);
  h+=sec('dashboard','Помещения',K.regs.length?K.regs.map((R,i)=>`<button class="orow" onclick="ED.sel={t:'room',i:${i}};draw();renderProps()"><i class="sw" style="background:${RCOL(R.n)}"></i>${R.n}<span class="sp"></span><span class="lead">${R.a.toFixed(1)} м²</span></button>`).join('')+`<div class="row" style="margin-top:10px"><span class="lead">Итого по внутренним граням</span><b>${tot.toFixed(1)} м²</b></div>`:'<p class="hintp" style="margin-top:0">Пока нет помещений. Инструмент «Помещение» (R) — клик внутри контура стен.</p>');
  h+=sec('layers','Слои',`<div class="chk ${M.furnOn!==false?'on':''}" onclick="mut(M=>{M.furnOn=M.furnOn===false},0)"><span class="bx"><span class="i">check</span></span>Мебель<small>${M.furn.length}</small></div><div class="chk ${ED.lbl?'on':''}" onclick="ED.lbl=ED.lbl?0:1;draw();renderProps()"><span class="bx"><span class="i">check</span></span>Подписи и площади</div>
   <div class="row"><span class="lead">Стен</span><span>${M.walls.length}${M.fixed?' + наружный контур':''}</span></div><div class="row"><span class="lead">Дверей · окон</span><span>${M.ops.filter(o=>o.k=='door').length} · ${M.ops.filter(o=>o.k=='win').length}</span></div>`);
  h+=sec('keyboard','Клавиши',`<div class="keys">${[['V','Выбор'],['W','Стена'],['D','Дверь'],['O','Окно'],['S','Стояк'],['R','Помещение · поворот'],['F','Мебель'],['Del','Удалить'],['Ctrl Z','Отменить'],['Esc','Снять выбор']].map(([k,t])=>`<span><kbd>${k}</kbd>${t}</span>`).join('')}</div><p class="hintp">Колесо мыши — средняя кнопка двигает поле, Ctrl + колесо — масштаб.</p>`)}
 b.innerHTML=h}
function setW(id,k,v){const n=+v;if(!(n>0))return renderProps();mut(M=>{const w=M.walls.find(x=>x.id==id);if(k=='t'){w.t=n/MM;M.ops.forEach(o=>{if(o.wall==id)o.t=w.t})}else{const G=wgeo(w),L=n/MM;w.x2=w.x1+G.ux*L;w.y2=w.y1+G.uy*L}},1)}
function setOp(id,k,v){const n=+v;if(!(n>=0))return renderProps();mut(M=>{const o=M.ops.find(x=>x.id==id),w=o.wall&&M.walls.find(x=>x.id==o.wall);
 if(k=='w'&&n>0){const keep=w?opOff(M,o):null;o.w=n/MM;if(w&&keep!=null){const G=wgeo(w),c=keep/MM-G.len/2+o.w/2;o.x=G.cx+G.ux*c;o.y=G.cy+G.uy*c}}
 if(k=='off'&&w){const G=wgeo(w),c=Math.max(-G.len/2+o.w/2,Math.min(G.len/2-o.w/2,n/MM-G.len/2+o.w/2));o.x=G.cx+G.ux*c;o.y=G.cy+G.uy*c}},1)}
function renameRoom(n){const M=curM(),R=calcRooms(M).regs[ED.sel.i];if(!R||!n.trim())return;mut(M=>{M.rooms[R.main].n=n.trim()},1)}
/* ---- связка с экранами MVP ---- */
const _pick=pickTool;pickTool=function(t){const E=['wall','door','window','riser','room','furn','ruler'];
 if(E.includes(t)){if(!contour)drawContour();if(refOn){toast('Эталон бюро не редактируется — выберите вариант');return}edStart()}
 _pick(t);ED.tool=t;ED.chain=null;ED.prev=null;ED.fg=null;ED.pt=null;if(t!='select'&&ED.sel&&!(t=='furn'&&ED.sel.t=='furn'))ED.sel=null;if(ED.on){renderProps();reDraw()}};
const _svgE=svg;svg=(R,o={})=>R&&R.M?msvg(R.M,o):R&&!R.length&&!R.L&&!R.rh&&contour?msvg(curM()||CM||(CM=mkModel('contour')),o):_svgE(R,o);
addVar=function(r,q,base,fix){const id=V.length+1;let M;if(base)M=cl(base.M);else{const k=V.filter(v=>!v.from).length;M=mkModel(COMBO[k%COMBO.length][0])}
 M.furnOn=$('#furnchk').classList.contains('on');M.gv=1;M.seq=M.seq||500;const v={id,run:r,q,seed:0,M,type:curType,err:base?0:Math.random()<.2?1:0,warn:base?(fix?0:Math.random()<.25?1:0):Math.floor(Math.random()*3),vote:0,ver:1,from:base?base.id:0};syncR(v);V.push(v)};
setRoom=function(n){const R=calcRooms(sel.M).regs[rSel];if(!R)return;sel.M.rooms[R.main].n=n;sel.M.gv++;syncR(sel);bump('Назначение изменено')};
const _showVar=showVar;showVar=function(id){_showVar(id);if(ED.on){ED.sel=null;ED.hist=[];ED.fut=[];ED.dirty=0;edStart()}};
function showVinfo(){const v=sel;if(!v)return;$('#vinfo').innerHTML=`<b>Вариант ${v.id}${v.ver>1?' · v'+v.ver:''}</b><span class="m"><span>${v.type}</span><span>жилая ${v.live} м²</span><span>${v.R.length} помещ.</span></span>${st(v)}<button class="ib" onclick="edStart()" title="Править план · стены, двери, окна, мебель"><span class="i">edit</span></button><button class="ib" onclick="showContour()" title="Показать исходный контур"><span class="i">layers</span></button>`}
const _showVar2=showVar;showVar=function(id){_showVar2(id);showVinfo()};
const _showRef=showRef;showRef=function(){if(ED.on)edDone();_showRef()};
const _showC=showContour;showContour=function(){_showC();if(ED.on){ED.sel=null;ED.hist=[];ED.fut=[];ED.dirty=0;edStart()}};
const _gen=gen;gen=function(){if(ED.on)edDone();_gen()};
const _reset=reset;reset=function(){if(ED.on){ED.on=0;$('.right').classList.remove('ed')}CM=null;ED.sel=null;ZM=1;zoom(0);_reset()};
/* масштаб поля */
let ZM=1;function zoom(d){ZM=Math.max(.5,Math.min(4,d?ZM*d:1));const sh=$('.sheet');sh.style.width=ZM==1?'':Math.round(760*ZM)+'px';$('.zoom .zv').textContent=Math.round(ZM*100)+'%'}
$$('.zoom .ib')[0].onclick=()=>zoom(1/1.25);$$('.zoom .ib')[1].onclick=()=>zoom(1.25);$('.zoom .zv').onclick=()=>zoom(0);$('.zoom .zv').style.cursor='pointer';$('.zoom .zv').title='Сбросить масштаб';
$('#cv').addEventListener('wheel',e=>{if(!e.ctrlKey)return;e.preventDefault();zoom(e.deltaY<0?1.12:1/1.12)},{passive:false});
