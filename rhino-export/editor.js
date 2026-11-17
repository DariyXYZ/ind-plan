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
/* биде: без бачка — узкая планка у стены, чаша, смеситель и слив; так его не спутать с унитазом */
FU.bidet=()=>rr(-170,0,170,90,25)+el(0,330,170,240)+el(0,345,110,170)+ci(0,215,20)+pl(0,90,0,195)+ci(0,420,14);
const FCAT=[['bed','Кровать двуспальная',1600,2000],['sbed','Кровать односпальная',900,2000],['sofa','Диван трёхместный',2200,950],['dining','Стол обеденный, 4 стула',1200,1700],['desk','Рабочий стол со стулом',1200,1100],['coffee','Столик журнальный',900,500],['wardrobe','Шкаф',1800,600],['base','Кухонный модуль',600,600],['hob','Варочная панель',600,600],['sink','Мойка кухонная',600,600],['fridge','Холодильник',600,650],['washer','Стиральная машина',600,600],['wc','Унитаз',380,650],['bidet','Биде',360,560],['basin','Раковина',500,450],['bath','Ванна',1700,700],['shower','Душевой поддон',900,900]];
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
const inFixed=(M,x,y)=>!!M.fixed&&HC.isPointInPath(fixedPath(M),x,y,'nonzero');
function mkModel(lay){const M=cl(RHM[lay]);M.lay=lay;M.gv=1;M.seq=500;heal(M);bidets(M);return M}
/* ---- унитаз и биде из модели: в Rhino оба нарисованы одним символом с бачком ---- */
/* по размеру раковина в Rhino не отличается от унитаза; у раковины есть линия смесителя (открытая кривая), у унитаза — только замкнутые бачок и чаша */
const WCS={},wcShape=src=>WCS[src]??(WCS[src]=(()=>{const e=document.getElementById(src),d=e&&e.getAttribute('d')||'',s=d.split('M').filter(Boolean);return s.length>=2&&s.length<=3&&s.every(x=>x.includes('Z'))})());
const wcLike=f=>f.src&&f.cat=='PLB'&&Math.min(f.w,f.d)>=300&&Math.min(f.w,f.d)<=450&&Math.max(f.w,f.d)>=540&&Math.max(f.w,f.d)<=720&&wcShape(f.src);
/* предмет каталога на месте предмета модели: спинкой к ближайшей стене по длинной оси */
function asCat(M,f,c){const b=fbox(f),[ux,uy]=ang(b.a),L=b.l>=b.t,ax=L?[ux,uy]:[-uy,ux],half=(L?b.l:b.t)/2,wallAt=k=>{for(let s=1;s<=10;s+=1){const x=b.cx+ax[0]*k*(half+s),y=b.cy+ax[1]*k*(half+s);if(inFixed(M,x,y)||regAt(M,x,y)==-1)return s}return 99};
 const k=wallAt(1)<=wallAt(-1)?1:-1,fw=[-ax[0]*k,-ax[1]*k],dep=FC[c][3]/MM,back=[b.cx-fw[0]*half,b.cy-fw[1]*half];
 return {id:f.id,c,x:q2(back[0]),y:q2(back[1]),r:Math.round(Math.atan2(-fw[0],fw[1])*180/Math.PI),m:0,was:f.src?{src:f.src,x:f.x,y:f.y,r:f.r,m:f.m,w:f.w,d:f.d,cat:f.cat}:f.was}}
/* в санузле с двумя «унитазами» меньший — биде (по размерам в модели); ошибётся — в панели «Это унитаз» */
function bidets(M){const K=calcRooms(M),by={};M.furn.forEach((f,i)=>{if(!wcLike(f))return;const r=regAt(M,f.x,f.y);if(r<0)return;(by[r]=by[r]||[]).push(i)});
 Object.values(by).forEach(ix=>{if(ix.length<2)return;const i=ix.reduce((a,b)=>M.furn[b].w*M.furn[b].d<M.furn[a].w*M.furn[a].d?b:a);M.furn[i]=asCat(M,M.furn[i],'bidet')})}
function swapWc(id){mut(M=>{const i=M.furn.findIndex(x=>x.id==id),f=M.furn[i];if(f.c=='bidet'&&f.was)M.furn[i]={id:f.id,...f.was};else if(f.c=='bidet'||f.c=='wc'){f.c=f.c=='wc'?'bidet':'wc'}else M.furn[i]=asCat(M,f,'bidet')},0)}
/* ---- проёмы в наружном контуре ---- */
const pa=(P,d,k)=>[P[0]+d[0]*k,P[1]+d[1]*k],lerp=(A,B,f)=>[A[0]+(B[0]-A[0])*f,A[1]+(B[1]-A[1])*f],pin=(M,P)=>inFixed(M,P[0],P[1]);
function xLine(P,d,Q,e){const den=d[0]*e[1]-d[1]*e[0];if(Math.abs(den)<1e-6)return null;return pa(P,d,((Q[0]-P[0])*e[1]-(Q[1]-P[1])*e[0])/den)}
const parea=pg=>pg.reduce((s,a,i)=>{const b=pg[(i+1)%pg.length];return s+a[0]*b[1]-b[0]*a[1]},0);
function boxPts(o){const [ux,uy]=ang(o.a),h=o.w/2,k=o.t/2;return [[-h,-k],[h,-k],[h,k],[-h,k]].map(([s,q])=>[o.x+ux*s-uy*q,o.y+uy*s+ux*q])}
/* разрывы контура под окна и двери модели заделываем, сами проёмы ставим на всю толщину стены — как новые: тогда их можно возить по стенам */
function heal(M){if(!M.fixed||M.hd)return;M.hd=1;const add=[],sg=Math.sign(fixedPolys(M).reduce((s,pg)=>s+Math.sign(parea(pg)),0))||-1;
 M.ops.forEach(o=>{if(o.wall||o.cw)return;const [ux,uy]=ang(o.a),n=[-uy,ux];let lo=1e9,hi=-1e9;
  [-1,1].forEach(e=>{for(const g of [1.5,3,6]){const P=[o.x+ux*e*(o.w/2+g),o.y+uy*e*(o.w/2+g)];let a=null,best=null;
   for(let q=-40;q<=40.01;q+=.25){const s=pin(M,pa(P,n,q));if(s&&a==null)a=q;if((!s||q>=40)&&a!=null){const b=s?q:q-.25,d=a>0?a:b<0?-b:0;if(!best||d<best.d)best={a,b,d};a=null}}
   if(best&&best.d<6){lo=Math.min(lo,best.a);hi=Math.max(hi,best.b);break}}});
  if(hi-lo<3)return;const m=(lo+hi)/2;o.x+=n[0]*m;o.y+=n[1]*m;o.t=hi-lo+.25;let pg=boxPts({...o,w:o.w+1});if(Math.sign(parea(pg))!=sg)pg.reverse();add.push('M'+pg.map(f2).join(' ')+'Z')});
 M.fixed+=add.join('');delete M._fx;delete M._fp}
function inner(M,a,b){const dx=b[0]-a[0],dy=b[1]-a[1],L=Math.hypot(dx,dy),mx=(a[0]+b[0])/2,my=(a[1]+b[1])/2,nx=-dy/L*.75,ny=dx/L*.75;return inFixed(M,mx+nx,my+ny)&&inFixed(M,mx-nx,my-ny)}
function edgeAt(M,p,lim,skip){let fe=null,bd=lim;fixedPolys(M).forEach(pg=>pg.forEach((a,i)=>{const b=pg[(i+1)%pg.length],dx=b[0]-a[0],dy=b[1]-a[1],L2=dx*dx+dy*dy;if(L2<4)return;const L=Math.sqrt(L2),ux=dx/L,uy=dy/L;
  if(skip&&skip(ux,uy))return;let t=((p.x-a[0])*dx+(p.y-a[1])*dy)/L2;t=Math.max(0,Math.min(1,t));const fx=a[0]+dx*t,fy=a[1]+dy*t,d=Math.hypot(p.x-fx,p.y-fy);if(d>=bd||inner(M,a,b))return;bd=d;fe={fx,fy,ux,uy}}));return fe}
function thick(M,F,n){let t=0;for(let s=.25;s<40;s+=.25){if(pin(M,pa(F,n,s)))t=s;else if(t)break}return t+.25}
/* свободный участок внутренней грани: B — точка грани, u — вдоль, r — в комнату; другие проёмы ограничивают участок */
function faceSpan(M,B,u,r,t,s,ex){const ok=v=>{const X=pa(B,u,v);return !pin(M,pa(X,r,1))&&pin(M,pa(X,r,-1))};
 if(!ok(s)){let f=null;for(let d=.5;d<=4&&f==null;d+=.5){if(ok(s+d))f=s+d;else if(ok(s-d))f=s-d}if(f==null)return null;s=f}
 let s0=s,s1=s;while(s1-s<1500&&ok(s1+.5))s1+=.5;while(s-s0<1500&&ok(s0-.5))s0-=.5;
 M.ops.forEach(o=>{if(o.id==ex||o.wall)return;let lo=1e9,hi=-1e9,n=0;
  opPts(o).forEach(P=>{const l=(P[0]-B[0])*r[0]+(P[1]-B[1])*r[1];if(l>-t-1.5&&l<1.5){const v=(P[0]-B[0])*u[0]+(P[1]-B[1])*u[1];lo=Math.min(lo,v);hi=Math.max(hi,v);n++}});
  if(n<2||hi<=s0||lo>=s1)return;if((lo+hi)/2<=s)s0=Math.max(s0,hi);else s1=Math.min(s1,lo)});
 return s1-s0>1?[s0,s1]:null}
/* угловое окно: внутренний угол I, наружный O, стороны L1/L2 по внутренним граням от угла */
function cwPts(c){const A=pa(c.I,c.d1,c.L1),D=pa(c.I,c.d2,c.L2);return {A,B:pa(A,c.o1,c.t1),C:pa(D,c.o2,c.t2),D}}
const opPts=o=>{if(!o.cw)return boxPts(o);const c=o.cw,{A,B,C,D}=cwPts(c);return [c.I,A,B,c.O,C,D]};
const opPath=(o,pw=0,pt=0)=>o.cw?'M'+opPts(o).map(f2).join('L')+'Z':obox(o.x,o.y,o.a,o.w+pw,o.t+pt);
function corner(M,B,u,r,t,se,dir,ex){const I0=pa(B,u,se);
 if(!pin(M,pa(pa(I0,u,dir*1.5),r,2)))return null;
 const X=pa(pa(I0,u,dir*(t+3)),r,-(t+3));if(pin(M,X)||regAt(M,X[0],X[1])>=0)return null;
 const Q=pa(pa(I0,r,12),u,dir);const fe=edgeAt(M,{x:Q[0],y:Q[1]},16,(x,y)=>Math.abs(x*u[0]+y*u[1])>.7);if(!fe)return null;
 let d2=[fe.ux,fe.uy];if(d2[0]*r[0]+d2[1]*r[1]<0)d2=[-d2[0],-d2[1]];let o2=[-d2[1],d2[0]];const F=[fe.fx,fe.fy];if(!pin(M,pa(F,o2,1)))o2=[-o2[0],-o2[1]];
 const t2=thick(M,F,o2);if(t2<3)return null;const I=xLine(B,u,F,d2);if(!I)return null;const o1=[-r[0],-r[1]],O=xLine(pa(I,o1,t),u,pa(I,o2,t2),d2);if(!O)return null;
 const S2=faceSpan(M,I,d2,[-o2[0],-o2[1]],t2,3,ex);if(!S2)return null;
 return {I,O,d1:[-u[0]*dir,-u[1]*dir],d2,o1,o2,t1:t,t2,m2:S2[1]}}
function placeFixed(M,p,k,w0,ex,lim){const fe=edgeAt(M,p,inFixed(M,p.x,p.y)?60:lim||10*ED.s);if(!fe)return null;
 const u=[fe.ux,fe.uy],F=[fe.fx,fe.fy];let n=[-u[1],u[0]];if(!pin(M,pa(F,n,1)))n=[-n[0],-n[1]];
 // в самом углу толщина меряется насквозь через обе стены — тогда берём точку грани чуть в стороне от угла
 for(const k0 of [0,4,-4,8,-8,12,-12,16,-16,24,-24,32,-32]){const S=pa(F,u,k0);if(!pin(M,pa(S,n,.5)))continue;const t0=thick(M,S,n);if(t0<3||t0>=39)continue;
  let r=[-n[0],-n[1]],B=F;if(regAt(M,...pa(S,n,-2))<0){if(regAt(M,...pa(S,n,t0+2))<0)continue;r=n;B=pa(F,n,t0)}
  const o=onFace(M,p,k,w0,ex,B,u,r,t0,k0);if(o)return o}
 return null}
/* линия стены, по которой едет проём при перетаскивании: внутренняя грань B, направление u, комната r, толщина t */
function opFrame(M,O){if(O.wall)return null;if(O.cw){const c=O.cw;return {B:c.I,u:c.d1,r:[-c.o1[0],-c.o1[1]],t:c.t1,s:c.L1/2}}
 const [ux,uy]=ang(O.a),m=[-uy,ux],h=O.t/2+3,r=regAt(M,O.x+m[0]*h,O.y+m[1]*h)>=0?m:regAt(M,O.x-m[0]*h,O.y-m[1]*h)>=0?[-m[0],-m[1]]:null;
 return r?{B:pa([O.x,O.y],r,O.t/2),u:[ux,uy],r,t:O.t,s:0}:null}
function onFace(M,p,k,w0,ex,B,u,r,t0,s){
 const sp=(p.x-B[0])*u[0]+(p.y-B[1])*u[1],S=faceSpan(M,B,u,r,t0,s,ex);if(!S)return null;const [s0,s1]=S;
 let t=thick(M,pa(B,u,(s0+s1)/2),[-r[0],-r[1]]);if(t<3||t>t0+2)t=t0; // толщину меряем в середине участка, не у угла
 if(k=='win'){const tryC=dir=>{const se=dir>0?s1:s0,ov=dir>0?sp+w0/2-s1:s0-(sp-w0/2);if(ov<12)return null;const c=corner(M,B,u,r,t,se,dir,ex);if(!c)return null;
   c.L2=Math.min(ov,c.m2,w0-10);c.L1=Math.min(w0-c.L2,s1-s0);delete c.m2;return c.L1>=10&&c.L2>=10?c:null};
  const c=tryC(1)||tryC(-1);if(c)return {k,cw:c,x:c.I[0],y:c.I[1],a:Math.atan2(c.d1[1],c.d1[0])*180/Math.PI,w:c.L1+c.L2,t}}
 const w=Math.min(w0,s1-s0);if(w<10)return null;const P=pa(pa(B,r,-t/2),u,Math.max(s0+w/2,Math.min(s1-w/2,sp)));
 let a=Math.atan2(u[1],u[0])*180/Math.PI;if(a>90)a-=180;if(a<=-90)a+=180;const [ax,ay]=ang(a);
 return {k,x:P[0],y:P[1],a,w,t,side:-ay*r[0]+ax*r[1]>0?1:-1,h:ED.hg||'s'}}
/* ---- помещения: растр 1 px = 20 мм, двери и окна закрыты, заливка от подписей ---- */
function dil(A,W,H,r){const B=new Uint8Array(W*H),C=new Uint8Array(W*H);
 for(let y=0;y<H;y++){let c=0;const o=y*W;for(let x=-r;x<W;x++){const a=x+r;if(a<W&&A[o+a])c++;const m=x-r-1;if(m>=0&&A[o+m])c--;if(x>=0)B[o+x]=c>0?1:0}}
 for(let x=0;x<W;x++){let c=0;for(let y=-r;y<H;y++){const a=y+r;if(a<H&&B[a*W+x])c++;const m=y-r-1;if(m>=0&&B[m*W+x])c--;if(y>=0)C[y*W+x]=c>0?1:0}}return C}
function mclose(A,W,H,r){const D=dil(A,W,H,r);for(let i=0;i<D.length;i++)D[i]^=1;const E=dil(D,W,H,r);for(let i=0;i<E.length;i++)E[i]^=1;return E}
function flood(L,W,H,s,v){const st=[s];let n=0;L[s]=v;while(st.length){const i=st.pop();n++;const x=i%W;
 if(x>0&&L[i-1]===0){L[i-1]=v;st.push(i-1)}if(x<W-1&&L[i+1]===0){L[i+1]=v;st.push(i+1)}if(i>=W&&L[i-W]===0){L[i-W]=v;st.push(i-W)}if(i+W<L.length&&L[i+W]===0){L[i+W]=v;st.push(i+W)}}return n}
const hex=c=>[1,3,5].map(i=>parseInt(c.slice(i,i+2),16));
function rasterWalls(M,W,H){const c=document.createElement('canvas');c.width=W;c.height=H;const g=c.getContext('2d');g.fillStyle=g.strokeStyle='#000';
 if(M.fixed)g.fill(fixedPath(M),'nonzero');wallPolys(M).forEach(({pts})=>g.fill(new Path2D(polyD(pts))));
 M.ops.forEach(o=>g.fill(new Path2D(o.cw?opPath(o):obox(o.x,o.y,o.a,o.w+1,Math.max(o.t,3)))));g.lineWidth=2;(M.cut||[]).forEach(([a,b,c2,d])=>{g.beginPath();g.moveTo(a,b);g.lineTo(c2,d);g.stroke()});return [c,g]}
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
function opG(o){if(o.cw){const c=o.cw,{A,D}=cwPts(c),gl=f=>`M${f2(pa(A,c.o1,c.t1*f))}L${f2(lerp(c.I,c.O,f))}L${f2(pa(D,c.o2,c.t2*f))}`;
  return `<path d="${opPath(o)}" fill="#fff" stroke="${EC.win}" stroke-width=".6" stroke-linejoin="round"/><path d="${gl(1/3)}${gl(2/3)}" fill="none" stroke="${EC.win}" stroke-width=".6" stroke-linejoin="round"/>`}
 if(o.k=='blank')return `<path d="${obox(o.x,o.y,o.a,o.w,o.t)}" fill="${EC.ext}"/>`;
 if(o.k=='win'){const [ux,uy]=ang(o.a),nx=-uy,ny=ux,h=o.w/2,q=o.t*.17,ln=k=>`M${(o.x-ux*h+nx*k).toFixed(2)} ${(o.y-uy*h+ny*k).toFixed(2)}L${(o.x+ux*h+nx*k).toFixed(2)} ${(o.y+uy*h+ny*k).toFixed(2)}`;
  return `<path d="${obox(o.x,o.y,o.a,o.w,o.t)}${ln(q)}${ln(-q)}" fill="#fff" stroke="${EC.win}" stroke-width=".6" stroke-linejoin="round"/>`}
 let s=`<path d="${obox(o.x,o.y,o.a,o.w,o.t+.6)}" fill="${EC.floor}"/>`;if(o.k=='door')s+=`<path d="${doorP(o)}" fill="none" stroke="${EC.door}" stroke-width=".75" stroke-linecap="round"/>`;return s}
function furG(f){if(f.src)return `<use href="#${f.src}" transform="translate(${f.x} ${f.y}) rotate(${f.r})${f.m?' scale(-1 1)':''}" fill="none" stroke="${EC.furn}" stroke-width=".7" stroke-linejoin="round" stroke-linecap="round"/>`;
 return `<path d="${fup(f.c)}" transform="translate(${f.x} ${f.y}) rotate(${f.r}) scale(${f.m?-.05:.05} .05)" fill="#fff" stroke="${EC.furn}" stroke-width="14" stroke-linejoin="round" stroke-linecap="round"/>`}
function riserG(r){const R=Math.max(r.d/MM/2,4),d=R*.7;return `<circle cx="${r.x}" cy="${r.y}" r="${R}" fill="${EC.riserFill}" stroke="${EC.riser}" stroke-width=".7"/><path d="M${r.x-d} ${r.y-d}L${r.x+d} ${r.y+d}M${r.x-d} ${r.y+d}L${r.x+d} ${r.y-d}" stroke="${EC.riser}" stroke-width=".7"/><text x="${r.x+R+2}" y="${r.y+3}" font-size="9" font-family="Inter,sans-serif" fill="${EC.riser}" font-weight="600">${r.type}</text>`}
const outl=(d,dash)=>`<path d="${d}" fill="var(--acc)" fill-opacity="${dash?0:.1}" stroke="var(--acc)" stroke-width="${dash?1.2:2}" ${dash?'stroke-dasharray="4 3"':''} vector-effect="non-scaling-stroke" style="pointer-events:none"/>`;
function elOutline(M,h,dash){if(!h)return '';const s=ED.s||1;
 if(h.t=='wall'){const w=M.walls.find(x=>x.id==h.id);if(!w)return '';const wp=wallPolys(M).find(x=>x.w===w&&x.pts.length==4);return outl(wp?polyD(wp.pts):'',dash)+(dash?'':[[w.x1,w.y1],[w.x2,w.y2]].map(([x,y])=>`<circle cx="${x}" cy="${y}" r="${4*s}" fill="#fff" stroke="var(--acc)" stroke-width="1.5" vector-effect="non-scaling-stroke"/>`).join(''))}
 if(h.t=='op'){const o=M.ops.find(x=>x.id==h.id);return o?outl(opPath(o,0,1),dash):''}
 if(h.t=='furn'){const f=M.furn.find(x=>x.id==h.id);if(!f)return '';const b=fbox(f);return outl(obox(b.cx,b.cy,b.a,b.l+1,b.t+1),dash)}
 if(h.t=='riser'){const r=M.risers.find(x=>x.id==h.id);return r?`<circle cx="${r.x}" cy="${r.y}" r="${Math.max(r.d/MM/2,4)+2}" fill="none" stroke="var(--acc)" stroke-width="2" ${dash?'stroke-dasharray="4 3"':''} vector-effect="non-scaling-stroke"/>`:''}
 if(h.t=='fixed')return `<path d="${M.fixed}" fill="var(--acc)" fill-opacity=".12" stroke="var(--acc)" stroke-width="${dash?1.2:2}" ${dash?'stroke-dasharray="4 3"':''} fill-rule="nonzero" vector-effect="non-scaling-stroke" style="pointer-events:none"/>`;
 return ''}
function msvg(M,o={}){const K=calcRooms(M),fs=13,ed=o.ed&&ED.on;let s='';
 if(M.lay!='contour')s+=`<use href="#rh-${M.floorOf||M.lay}-f"/>`;
 s+=`<image href="${K.url}" x="0" y="0" width="${K.W}" height="${K.H}" preserveAspectRatio="none"/>`;
 const rs=ed?(ED.sel&&ED.sel.t=='room'?ED.sel.i:null):o.sel;if(rs!=null&&K.regs[rs])s+=`<image href="${selURL(M,rs)}" x="0" y="0" width="${K.W}" height="${K.H}" preserveAspectRatio="none"/>`;
 s+=(M.cut||[]).map(c=>`<path d="M${c[0]} ${c[1]}L${c[2]} ${c[3]}" stroke="#6B7280" stroke-width="1.2" stroke-dasharray="5 4"/>`).join('');
 if(M.furnOn!==false)s+=M.furn.map(furG).join('');
 if(M.fixed)s+=`<path d="${M.fixed}" fill="${EC.ext}" fill-rule="nonzero"/>`;
 s+=wallPolys(M).map(({w,pts})=>{const c=EC[w.type]||EC.part;return `<path d="${polyD(pts)}" fill="${c}" stroke="${c}" stroke-width=".25" stroke-linejoin="round"/>`}).join('');
 s+=M.ops.map(opG).join('')+M.risers.map(riserG).join('');
 if(o.label!==false&&(!ed||ED.lbl))M.rooms.forEach((l,i)=>{const r=K.regs[K.lab2[i]],on=r&&K.lab2[i]===rs,bg=on?'#E3E8FD':r?RCOL(r.n):'#fff';
  s+=`<g style="pointer-events:none" font-family="Inter,sans-serif" text-anchor="middle" paint-order="stroke" stroke="${bg}" stroke-width="4" stroke-linejoin="round"><text x="${l.x}" y="${l.y+fs*.35}" font-size="${fs}" font-weight="600" fill="${on?'var(--acc-text)':r?'#1F2328':'#9CA3AF'}">${l.n}</text>${(o.area||ed)&&r&&r.main===i?`<text x="${l.x}" y="${l.y+fs*1.5}" font-size="${fs*.85}" fill="#1F2328">${r.a.toFixed(1)} м²</text>`:''}</g>`});
 if(ed){s+=elOutline(M,ED.hover&&!(ED.sel&&ED.hover.t==ED.sel.t&&ED.hover.id==ED.sel.id)?ED.hover:null,1)+elOutline(M,ED.sel);s+=previewG(M)}
 return `<svg viewBox="${M.vb}" width="100%" style="display:block;overflow:visible" data-m="1">${s}</svg>`}
function previewG(M){const t=ED.tool,P=ED.pt;if(!P)return '';let s='';const g='fill="var(--acc)" fill-opacity=".35" stroke="var(--acc)" stroke-width="1.2" vector-effect="non-scaling-stroke"';
 if(t=='wall'){const th=ED.wth/MM,E=liveEnd()||P,z=ED.s,gc='#E5484D';
  // направляющие от углов, с которыми точка на одной линии (как smart guides в Figma)
  (E.guides||[]).forEach(q=>{s+=`<path d="M${f2(q.a)}L${E.x.toFixed(2)} ${E.y.toFixed(2)}" stroke="${gc}" stroke-width="1" stroke-dasharray="4 3" fill="none" vector-effect="non-scaling-stroke"/><circle cx="${q.a[0]}" cy="${q.a[1]}" r="${2.5*z}" fill="${gc}"/>`});
  if(ED.chain){const w={x1:ED.chain.x,y1:ED.chain.y,x2:E.x,y2:E.y,t:th},G=wgeo(w);if(G.len>.5){const up=G.a>90||G.a<-90?G.a-180:G.a,lx=G.cx-G.uy*(th/2+9*z),ly=G.cy+G.ux*(th/2+9*z);
   s+=`<path d="${obox(G.cx,G.cy,G.a,G.len,th)}" ${g}/><text x="${lx}" y="${ly}" transform="rotate(${up} ${lx} ${ly})" dominant-baseline="middle" font-size="${11*z}" text-anchor="middle" font-family="Inter,sans-serif" fill="var(--acc-text)" font-weight="600" paint-order="stroke" stroke="#fff" stroke-width="${3*z}">${ED.typed?ED.typed+' мм':mmv(G.len).toLocaleString('ru-RU')}</text>`}
   s+=`<circle cx="${ED.start.x}" cy="${ED.start.y}" r="${3.5*z}" fill="#fff" stroke="var(--acc)" stroke-width="1.5" vector-effect="non-scaling-stroke"/>`}
  const k=E.kind,m=4.5*z;s+=k=='vertex'?`<rect x="${E.x-m}" y="${E.y-m}" width="${2*m}" height="${2*m}" fill="#fff" stroke="var(--acc)" stroke-width="1.5" vector-effect="non-scaling-stroke"/>`:
   k=='mid'?`<path d="M${E.x} ${E.y-m*1.2}L${E.x+m*1.1} ${E.y+m*.8}L${E.x-m*1.1} ${E.y+m*.8}Z" fill="#fff" stroke="var(--acc)" stroke-width="1.5" vector-effect="non-scaling-stroke"/>`:
   k=='cross'||k=='axis'?`<path d="M${E.x-m} ${E.y-m}L${E.x+m} ${E.y+m}M${E.x-m} ${E.y+m}L${E.x+m} ${E.y-m}" stroke="var(--acc)" stroke-width="2" vector-effect="non-scaling-stroke"/>`:
   `<circle cx="${E.x}" cy="${E.y}" r="${3.5*z}" fill="var(--acc)"/>`}
 if((t=='door'||t=='window')&&ED.prev){const o=ED.prev;s+=`<g opacity=".85">${opG(o)}</g>`+outl(opPath(o,0,1))}
 if(t=='furn'&&ED.fg)s+=`<g opacity=".7">${furG(ED.fg)}</g>`;
 if(t=='riser')s+=`<g opacity=".6">${riserG({x:P.x,y:P.y,d:110,type:ED.rt})}</g>`;
 return s}
/* ---- состояние правки ---- */
let ED={on:0,tool:'select',sel:null,hover:null,hist:[],fut:[],chain:null,pt:null,prev:null,fg:null,s:1,lbl:1,ft:'bed',frot:0,wt:'part',wth:100,dw:800,ww:1400,rt:'К1',dirty:0};
let CM=null;const curM=()=>refOn?null:sel?sel.M:contour?(CM||(CM=mkModel('contour'))):null;
const snap=M=>cl({walls:M.walls,ops:M.ops,furn:M.furn,risers:M.risers,rooms:M.rooms,furnOn:M.furnOn});
function syncR(v){const K=calcRooms(v.M);v.R=K.regs.map(R=>({n:R.n,a:R.a,p:''}));v.R.rh={lay:v.M.lay,furn:v.M.furnOn!==false};v.R.M=v.M;
 v.live=v.R.filter(m=>/спальн|гостин|детск|кабинет/i.test(m.n)).reduce((s,m)=>s+m.a,0).toFixed(1)}
let _rl=0;function changed(geo){const M=curM();if(geo)M.gv++;if(sel){if(!ED.dirty){sel.ver++;ED.dirty=1}syncR(sel);clearTimeout(_rl);_rl=setTimeout(()=>{renderList();if(sel)$('#vinfo .m')&&showVinfo()},250)}saved();draw();renderProps()}
function mut(fn,geo){const M=curM();ED.hist.push(snap(M));if(ED.hist.length>80)ED.hist.shift();ED.fut=[];fn(M);changed(geo)}
function restore(st){const M=curM();Object.assign(M,cl(st));M.gv++;M.seq+=50}
function undo(){if(!ED.hist.length)return toast('Нечего отменять');const M=curM();ED.fut.push(snap(M));restore(ED.hist.pop());ED.sel=null;changed(0)}
function redo(){if(!ED.fut.length)return;const M=curM();ED.hist.push(snap(M));restore(ED.fut.pop());ED.sel=null;changed(0)}
const nid=(M,p)=>p+(++M.seq);
function draw(){const M=curM();if(!M)return;if(ED.on){$('#plan').innerHTML=msvg(M,{ed:1,area:1});return}if(sel)drawSel();else $('#plan').innerHTML=msvg(M,{})}
function edStart(){const M=curM();if(!M){if(refOn)toast('Эталон бюро не редактируется — выберите вариант');return}
 if(!ED.on){ED.on=1;ED.hist=[];ED.fut=[];ED.dirty=0;ED.sel=null}$('.right').classList.add('ed');$('#insp').style.display='none';rSel=null;
 $('#ptitle').textContent='Свойства';$('#pedit .rsub').textContent=sel?`Вариант ${sel.id}`:'Контур квартиры';$('#sheettag').innerHTML=`<span class="i" style="font-size:15px">edit</span><b>Правка</b>· ${sel?'Вариант '+sel.id:'контур квартиры'} · клик — выбрать, тянуть — сдвинуть`;draw();renderProps()}
function edDone(){if(!ED.on)return;const was=ED.dirty;ED.on=0;ED.sel=null;ED.chain=null;ED.prev=null;ED.fg=null;tool='select';renderTb();hint('');$('.right').classList.remove('ed');
 if(sel){showVar(sel.id);if(was)toast(`Правки сохранены · вариант ${sel.id} v${sel.ver}`)}else if(contour){$('#sheettag').innerHTML=CT;draw();if(was)toast('Контур сохранён')}ED.dirty=0}
/* ---- поиск под курсором ---- */
function hit(M,p){const e=5*ED.s;
 for(const r of M.risers)if(Math.hypot(p.x-r.x,p.y-r.y)<=Math.max(r.d/MM/2,4)+e)return {t:'riser',id:r.id};
 for(const o of M.ops)if(o.cw?HC.isPointInPath(new Path2D(opPath(o)),p.x,p.y):inBox(p.x,p.y,o.x,o.y,o.a,o.w,o.t,e*.6))return {t:'op',id:o.id};
 for(const w of M.walls){const G=wgeo(w);if(inBox(p.x,p.y,G.cx,G.cy,G.a,G.L,w.t,e*.6))return {t:'wall',id:w.id}}
 if(inFixed(M,p.x,p.y))return {t:'fixed'};
 if(M.furnOn!==false)for(let i=M.furn.length-1;i>=0;i--){const f=M.furn[i],b=fbox(f);if(inBox(p.x,p.y,b.cx,b.cy,b.a,b.l,b.t,0))return {t:'furn',id:f.id}}
 const r=regAt(M,p.x,p.y);if(r>=0)return {t:'room',i:r};return null}
/* ---- стены как сеть (из IND PLAN editor, geometry.ts → wallCorners): концы в одной точке — узел;
   обходя узел, левая грань каждой стены встречает правую грань следующей — там их общий угол, без щелей у L, T и креста ---- */
function wallPolys(M){const W=M.walls,nodes=[],C={},out=[];
 W.forEach(w=>[1,2].forEach(k=>{const x=w['x'+k],y=w['y'+k];let n=nodes.find(n=>Math.hypot(n.x-x,n.y-y)<1);if(!n)nodes.push(n={x,y,legs:[]});n.legs.push({w,k})}));
 nodes.forEach(n=>{if(n.legs.length<2)return;const at=[n.x,n.y];
  const legs=n.legs.map(l=>{const w=l.w,L=Math.hypot(w.x2-w.x1,w.y2-w.y1)||1,s=l.k==1?1:-1,u=[(w.x2-w.x1)/L*s,(w.y2-w.y1)/L*s];return {...l,u,h:w.t/2,an:Math.atan2(u[1],u[0])}}).sort((a,b)=>a.an-b.an);
  const ring=[],put=(g,f,P)=>{(C[g.w.id+':'+g.k]=C[g.w.id+':'+g.k]||{})[f]=P};
  legs.forEach((g,i)=>{const nx=legs[(i+1)%legs.length],own=pa(at,[-g.u[1],g.u[0]],g.h),th=pa(at,[-nx.u[1],nx.u[0]],-nx.h);let P=xLine(own,g.u,th,nx.u);
   if(P&&Math.hypot(P[0]-at[0],P[1]-at[1])>Math.max(g.h,nx.h)*6)P=null; // слишком острый угол — торцы встык
   put(g,'l',P||own);put(nx,'r',P||th);if(P)ring.push(P);else ring.push(own,th)});
  if(legs.length>=3)out.push({w:legs[0].w,pts:ring})}); // три стены и больше: середину узла заливает «хаб»
 W.forEach(w=>{const L=Math.hypot(w.x2-w.x1,w.y2-w.y1)||1,u=[(w.x2-w.x1)/L,(w.y2-w.y1)/L],n=[-u[1],u[0]],h=w.t/2,c1=C[w.id+':1'],c2=C[w.id+':2'];
  const A=pa([w.x1,w.y1],u,c1||!w.cap?0:-h),B=pa([w.x2,w.y2],u,c2||!w.cap?0:h);
  out.push({w,pts:[c1?c1.l:pa(A,n,h),c2?c2.r:pa(B,n,h),c2?c2.l:pa(B,n,-h),c1?c1.r:pa(A,n,-h)]})});
 return out}
const polyD=pts=>'M'+pts.map(f2).join('L')+'Z';
/* ---- умная привязка (из IND PLAN editor, snap.ts): углы, середины стен, луч 45° от прошлой точки (Shift — 15°),
   упор луча в ось стены или грань контура, направляющие по углам поперёк и вдоль, сетка 50 мм; Alt — держат только углы ---- */
function snapCtx(M,o){const V=[],A=[];M.walls.forEach(w=>{[1,2].forEach(k=>{if(!(o.skipV&&o.skipV.has(w.id+':'+k)))V.push([w['x'+k],w['y'+k]])});if(!(o.skipA&&o.skipA.has(w.id)))A.push({a:[w.x1,w.y1],b:[w.x2,w.y2],mid:1})});
 fixedPolys(M).forEach(pg=>pg.forEach((a,i)=>{const b=pg[(i+1)%pg.length];if(Math.hypot(b[0]-a[0],b[1]-a[1])<2||inner(M,a,b))return;V.push(a);A.push({a,b})}));
 if(o.extra)V.push(...o.extra);return {V,A}}
const r1=v=>Math.round(v*10)/10,d2=(p,q)=>Math.hypot(p[0]-q[0],p[1]-q[1]);
function nearSeg(p,a,b){const dx=b[0]-a[0],dy=b[1]-a[1],L2=dx*dx+dy*dy;if(!L2)return a;const t=Math.max(0,Math.min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/L2));return [a[0]+dx*t,a[1]+dy*t]}
function rayHit(p,d,a,b){const ex=b[0]-a[0],ey=b[1]-a[1],den=d[0]*ey-d[1]*ex;if(Math.abs(den)<1e-6)return null;const wx=a[0]-p[0],wy=a[1]-p[1],t=(wx*ey-wy*ex)/den,u=(wx*d[1]-wy*d[0])/den;
 return t<-1e-6||u<-1e-6||u>1+1e-6?null:[p[0]+d[0]*t,p[1]+d[1]*t]}
function smartSnap(M,raw,from,o={}){const reach=10*ED.s,{V,A}=snapCtx(M,o),r=[raw.x,raw.y],F=from&&[from.x,from.y];
 const aligned=p=>{const G=[];[0,1].forEach(ax=>{let b=null;V.forEach(v=>{if(Math.abs(v[ax]-p[ax])>.05||d2(v,p)<.05)return;if(!b||d2(v,p)<d2(b,p))b=v});if(b)G.push({a:b,b:p})});return G};
 const fin=(p,kind)=>({x:p[0],y:p[1],kind,guides:kind=='free'?[]:aligned(p)});
 let best=null,bd=reach;V.forEach(v=>{const d=d2(v,r);if(d<bd){bd=d;best=v}});if(best)return fin(best,'vertex');if(o.free)return fin(r,'free');
 A.forEach(s=>{if(!s.mid)return;const m=lerp(s.a,s.b,.5),d=d2(m,r);if(d<bd){bd=d;best=m}});if(best)return fin(best,'mid');
 let line=null,lk='angle';
 if(F){const st=(o.step||45)*Math.PI/180,an=Math.round(Math.atan2(r[1]-F[1],r[0]-F[0])/st)*st;line={p:F,d:[Math.cos(an),Math.sin(an)],min:0,max:1e9}}
 else for(const s of A){const L=d2(s.a,s.b);if(L<1e-6||d2(nearSeg(r,s.a,s.b),r)>=reach)continue;line={p:s.a,d:[(s.b[0]-s.a[0])/L,(s.b[1]-s.a[1])/L],min:0,max:L};lk='axis';break}
 if(line){const at=t=>pa(line.p,line.d,t),t0=Math.min(line.max,Math.max(line.min,(r[0]-line.p[0])*line.d[0]+(r[1]-line.p[1])*line.d[1])),base=at(t0),found=[];
  const offer=(q,k)=>{const d=d2(q,base);if(d<reach)found.push({q,k,d})};
  if(F)A.forEach(s=>{const q=rayHit(line.p,line.d,s.a,s.b);if(q&&d2(q,F)>1e-6)offer(q,'cross')}); // стена, нарисованная до другой, кончается на её оси
  if(!found.length)V.forEach(v=>[0,1].forEach(ax=>{const dd=line.d[ax];if(Math.abs(dd)<1e-6)return;const t=(v[ax]-line.p[ax])/dd;if(t<line.min-1e-6||t>line.max+1e-6)return;const q=at(t);if(d2(q,v)>1e-6&&(!F||d2(q,F)>1e-6))offer(q,'guide')}));
  found.sort((a,b)=>a.d-b.d);if(found[0])return fin(found[0].q.map(r1),found[0].k);
  return fin(at(lk=='angle'?Math.round(t0*2)/2:t0).map(r1),lk)} // по лучу — длина кратна 10 мм
 let gx=null,gy=null,dx=reach,dy=reach;V.forEach(v=>{const ex=Math.abs(v[0]-r[0]),ey=Math.abs(v[1]-r[1]);if(ex<dx){dx=ex;gx=v[0]}if(ey<dy){dy=ey;gy=v[1]}});
 const sg=v=>Math.round(v/2.5)*2.5;return fin([gx??sg(r[0]),gy??sg(r[1])],gx!=null||gy!=null?'guide':'grid')}
/* ---- рисование стены цепочкой ---- */
const WH1='Клик — начало стены · привязка к углам, серединам и осям стен',WH2='Клик — следующий угол · цифры — длина, Enter · Shift — шаг 15° · Alt — без привязки · Esc — закончить';
const wsnap=(M,p,e)=>smartSnap(M,p,ED.chain,{free:e&&e.altKey,step:e&&e.shiftKey?15:45,extra:ED.start?[[ED.start.x,ED.start.y]]:[]});
function liveEnd(){const P=ED.pt,c=ED.chain,mm=parseFloat(ED.typed);if(!P||!c||!ED.typed||!(mm>0))return P;const d=Math.hypot(P.x-c.x,P.y-c.y);if(d<1e-6)return P;
 return {x:r1(c.x+(P.x-c.x)/d*mm/MM),y:r1(c.y+(P.y-c.y)/d*mm/MM),kind:'typed',guides:[]}}
function endChain(){ED.chain=ED.start=null;ED.typed='';hint(WH1);reDraw()}
function addWallPt(M,q){if(!q)return;if(!ED.chain){ED.chain=ED.start={x:q.x,y:q.y};ED.nseg=0;hint(WH2);reDraw();return}
 if(Math.hypot(q.x-ED.chain.x,q.y-ED.chain.y)<.5)return endChain(); // второй клик в ту же точку — конец, как двойной
 const w={x1:ED.chain.x,y1:ED.chain.y,x2:q.x,y2:q.y};mut(M=>{M.walls.push({id:nid(M,'w'),...w,t:ED.wth/MM,type:ED.wt,fixed:ED.wt!='part'?1:0})},1);ED.nseg++;ED.typed='';
 if(ED.nseg>=2&&Math.hypot(q.x-ED.start.x,q.y-ED.start.y)<.5)return endChain(); // замкнули на первую точку
 ED.chain={x:q.x,y:q.y};reDraw()}
/* проём под курсором: перегородка (по оси) или наружная стена из модели (по ближайшей грани) */
function placeOp(M,p,k,w0,ex,fr){if(k=='window')k='win';w0=w0||(k=='door'?ED.dw:ED.ww)/MM;let best=null,bd=1e9;
 if(fr){const l=(p.x-fr.B[0])*fr.r[0]+(p.y-fr.B[1])*fr.r[1];if(l>-fr.t-30&&l<30){const o=onFace(M,p,k,w0,ex,fr.B,fr.u,fr.r,fr.t,fr.s);if(o)return o}}
 M.walls.forEach(w=>{const G=wgeo(w),[s,q]=loc(p.x,p.y,G.cx,G.cy,G.a);if(Math.abs(s)>G.len/2+2||Math.abs(q)>w.t/2+8*ED.s)return;if(Math.abs(q)<bd){bd=Math.abs(q);const ww=Math.min(w0,G.len-1),c=Math.max(-G.len/2+ww/2,Math.min(G.len/2-ww/2,s));
  best={k,x:G.cx+G.ux*c,y:G.cy+G.uy*c,a:G.a,w:ww,t:w.t,side:q<0?-1:1,h:ED.hg||'s',wall:w.id}}});
 if(best)return best;if(!M.fixed)return null;return placeFixed(M,p,k,w0,ex,fr?40:0)}
/* перетаскивание проёма: едет по стене, переходит на соседние, окно у наружного угла заворачивает за угол */
function dragOp(M,o,O,p,dx,dy){if(DR.fr===undefined)DR.fr=opFrame(M,O);const n=placeOp(M,O.cw?p:{x:O.x+dx,y:O.y+dy},O.k,O.w,O.id,DR.fr);if(!n)return;
 let side=n.side,h=O.h;if(!n.cw&&!O.cw&&n.wall==O.wall){const d=(n.a-O.a)*Math.PI/180;if(Math.abs(Math.sin(d))<.02){const fl=Math.cos(d)<0;side=fl?-O.side:O.side;h=fl?(O.h=='s'?'e':'s'):O.h}}
 for(const k in o)if(k!='id')delete o[k];Object.assign(o,n,{k:O.k,h,side});if(!n.wall)delete o.wall}
function setCw(id,k,v){const n=+v;if(!(n>0))return renderProps();mut(M=>{const o=M.ops.find(x=>x.id==id),c=o.cw,L=Math.max(10,n/MM);
 const S=k=='L1'?faceSpan(M,c.I,c.d1,c.o1.map(x=>-x),c.t1,3,id):faceSpan(M,c.I,c.d2,c.o2.map(x=>-x),c.t2,3,id);c[k]=S?Math.min(L,S[1]):L;o.w=c.L1+c.L2},1)}
function cwStraight(id){mut(M=>{const o=M.ops.find(x=>x.id==id),c=o.cw,P=pa(pa(c.I,c.d1,c.L1/2),c.o1,c.t1/2);let a=Math.atan2(c.d1[1],c.d1[0])*180/Math.PI;if(a>90)a-=180;if(a<=-90)a+=180;
 delete o.cw;Object.assign(o,{x:P[0],y:P[1],a,w:c.L1,t:c.t1,side:1,h:'s'})},1)}
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
  if(s0)for(const k of [1,2])if(Math.hypot(p.x-s0['x'+k],p.y-s0['y'+k])<7*ED.s){DR={k:'end',end:k,id:s0.id,p0:p,st:snap(M),o:cl(s0),mv:0,co:[]};
   // узел: концы других стен в этой точке едут вместе с ним
   M.walls.forEach(v=>{if(v.id!=s0.id)[1,2].forEach(j=>{if(Math.hypot(v['x'+j]-s0['x'+k],v['y'+j]-s0['y'+k])<1)DR.co.push({id:v.id,k:j})})});
   DR.skipV=new Set([s0.id+':'+k,...DR.co.map(c=>c.id+':'+c.k)]);DR.skipA=new Set([s0.id,...DR.co.map(c=>c.id)]);
   // проёмы на этих стенах держат расстояние от начала стены (как fitOpenings в старом редакторе)
   DR.ops=M.ops.filter(o=>DR.skipA.has(o.wall)).map(o=>{const v=M.walls.find(x=>x.id==o.wall);return {id:o.id,s:(o.x-v.x1)*(v.x2-v.x1)/Math.hypot(v.x2-v.x1,v.y2-v.y1)+(o.y-v.y1)*(v.y2-v.y1)/Math.hypot(v.x2-v.x1,v.y2-v.y1)}});return}
  const h=hit(M,p);ED.sel=h;if(h&&h.t=='fixed')toast('Наружный контур из модели на замке — двигать нельзя, проёмы ставятся');
  if(h&&h.t!='fixed'&&h.t!='room'||h&&h.t=='room')DR={k:h.t,id:h.id,i:h.i,p0:p,st:snap(M),mv:0,o:cl(h.t=='wall'?M.walls.find(w=>w.id==h.id):h.t=='op'?M.ops.find(o=>o.id==h.id):h.t=='furn'?M.furn.find(f=>f.id==h.id):h.t=='riser'?M.risers.find(r=>r.id==h.id):null)};
  if(DR&&DR.k=='wall'){const w=DR.o,G=wgeo(w);DR.con=[];
   // все стены, что касаются двигаемой (общий конец или примыкание к ней), остаются на ней: их конец скользит вдоль своей линии
   M.walls.forEach(v=>{if(v.id==w.id)return;[1,2].forEach(k=>{const P=[v['x'+k],v['y'+k]],o=k==1?2:1,j=[1,2].find(j=>Math.hypot(P[0]-w['x'+j],P[1]-w['y'+j])<1),[s,q]=loc(P[0],P[1],G.cx,G.cy,G.a);
    if(j||Math.abs(q)<=w.t/2+v.t/2+1.5&&Math.abs(s)<=G.len/2+v.t/2+1)DR.con.push({id:v.id,k,j,x:P[0],y:P[1],ox:v['x'+o],oy:v['y'+o]})})});
   DR.ops=M.ops.filter(o=>o.wall==w.id).map(o=>({id:o.id,x:o.x,y:o.y}));
   const cs=new Set([w.id,...DR.con.map(c=>c.id)]);DR.mag=[];M.walls.forEach(v=>{if(!cs.has(v.id))DR.mag.push([v.x1,v.y1],[v.x2,v.y2])});fixedPolys(M).forEach(pg=>pg.forEach(a=>DR.mag.push(a)))}
  if(DR&&DR.k=='furn'&&e.altKey){const c=cl(DR.o);c.id=nid(M,'f');M.furn.push(c);DR.id=c.id;DR.clone=DR.o.id;ED.sel={t:'furn',id:c.id}} // Alt — тянем копию, оригинал остаётся
  if(DR&&DR.k=='room'){const K=calcRooms(M),R=K.regs[h.i];DR.lab=R?R.main:null;DR.o=DR.lab!=null?cl(M.rooms[DR.lab]):null}
  draw();renderProps();return}
 if(t=='wall'){ED.pt=ED.typed?ED.pt:wsnap(M,p,e);addWallPt(M,liveEnd());return}
 if(t=='door'||t=='window'){const o=placeOp(M,p,t);if(!o)return toast('Наведите на стену');mut(M=>{o.id=nid(M,'o');M.ops.push(o)},1);ED.sel={t:'op',id:o.id};renderProps();return}
 if(t=='riser'){mut(M=>{const r={id:nid(M,'r'),x:q2(p.x),y:q2(p.y),d:110,type:ED.rt,fixed:1};M.risers.push(r);ED.sel={t:'riser',id:r.id}},0);return}
 if(t=='room'){const r=regAt(M,p.x,p.y);if(r<0)return toast('Кликните внутри замкнутого контура стен');const K=calcRooms(M);if(K.regs[r]&&K.regs[r].labs.length){ED.sel={t:'room',i:r};draw();renderProps();return}
  mut(M=>M.rooms.push({n:'Помещение',x:q2(p.x),y:q2(p.y)}),1);ED.sel={t:'room',i:calcRooms(M).lab2[M.rooms.length-1]};draw();renderProps();return}
 if(t=='furn'){const f=placeFurn(M,p);mut(M=>{f.id=nid(M,'f');M.furn.push(f);M.furnOn=true},0);ED.sel={t:'furn',id:f.id};renderProps();return}});
$('#plan').addEventListener('dblclick',()=>{if(ED.on&&ED.tool=='wall')endChain()});
window.addEventListener('pointermove',e=>{if(PAN){const st=$('#stage');st.scrollLeft=PAN.l-(e.clientX-PAN.x);st.scrollTop=PAN.t-(e.clientY-PAN.y);return}
 const M=curM();if(!M||!$('#s-ws').classList.contains('on'))return;const p=evP(e);if(!p)return;
 if(!ED.on){if(e.target.closest&&e.target.closest('#plan')){const h=hit(M,p);$('#plan').style.cursor=h?'pointer':''}return}
 if(DR){const dx=p.x-DR.p0.x,dy=p.y-DR.p0.y;if(!DR.mv&&Math.hypot(dx,dy)<2*ED.s)return;if(!DR.mv){ED.hist.push(DR.st);ED.fut=[];DR.mv=1}
  if(DR.k=='furn'||DR.k=='riser'){const a=(DR.k=='furn'?M.furn:M.risers).find(x=>x.id==DR.id);a.x=q2(DR.o.x+dx);a.y=q2(DR.o.y+dy)}
  else if(DR.k=='room'&&DR.o){const l=M.rooms[DR.lab];l.x=q2(DR.o.x+dx);l.y=q2(DR.o.y+dy)}
  else if(DR.k=='wall'){const w=M.walls.find(x=>x.id==DR.id),O=DR.o,G=wgeo(O),u=[G.ux,G.uy],n=[-G.uy,G.ux];let d=q2(dx*n[0]+dy*n[1]);
   // магнит: ось стены прилипает к углам других стен и контура
   if(!e.altKey){let bd=8*ED.s,bv=null;DR.mag.forEach(V=>{const v=(V[0]-O.x1)*n[0]+(V[1]-O.y1)*n[1];if(Math.abs(v-d)<bd){bd=Math.abs(v-d);bv=v}});if(bv!=null)d=r1(bv)}
   const A=pa([O.x1,O.y1],n,d);w.x1=A[0];w.y1=A[1];const B2=pa([O.x2,O.y2],n,d);w.x2=B2[0];w.y2=B2[1];
   DR.con.forEach(c=>{const v=M.walls.find(x=>x.id==c.id);if(!v)return;const L=Math.hypot(c.x-c.ox,c.y-c.oy)||1,ev=[(c.x-c.ox)/L,(c.y-c.oy)/L];
    const P=Math.abs(ev[0]*u[1]-ev[1]*u[0])>.1?xLine([c.ox,c.oy],ev,A,u):pa([c.x,c.y],n,d);if(!P)return;v['x'+c.k]=r1(P[0]);v['y'+c.k]=r1(P[1]);
    if(c.j){w['x'+c.j]=v['x'+c.k];w['y'+c.j]=v['y'+c.k]}}); // общий угол остаётся общим
   DR.ops.forEach(c=>{const o=M.ops.find(x=>x.id==c.id);if(o){o.x=c.x+n[0]*d;o.y=c.y+n[1]*d}})}
  else if(DR.k=='end'){const w=M.walls.find(x=>x.id==DR.id),k=DR.end,o2=k==1?2:1,q=smartSnap(M,{x:DR.o['x'+k]+dx,y:DR.o['y'+k]+dy},DR.co.length?null:{x:DR.o['x'+o2],y:DR.o['y'+o2]},{skipV:DR.skipV,skipA:DR.skipA,free:e.altKey,step:e.shiftKey?15:45});
   w['x'+k]=q.x;w['y'+k]=q.y;DR.co.forEach(c=>{const v=M.walls.find(x=>x.id==c.id);if(v){v['x'+c.k]=q.x;v['y'+c.k]=q.y}});ED.pt=q;
   DR.ops.forEach(c=>{const o=M.ops.find(x=>x.id==c.id),v=o&&M.walls.find(x=>x.id==o.wall);if(!v)return;const G=wgeo(v),s=Math.max(o.w/2,Math.min(G.len-o.w/2,c.s));o.x=v.x1+G.ux*s;o.y=v.y1+G.uy*s;o.a=G.a})}
  else if(DR.k=='op'){const o=M.ops.find(x=>x.id==DR.id);if(o)dragOp(M,o,DR.o,p,dx,dy)}
  reDraw();return}
 ED.cur=p;ED.pt=ED.tool=='wall'?wsnap(M,p,e):p;
 if(ED.tool=='door'||ED.tool=='window')ED.prev=placeOp(M,p,ED.tool);
 if(ED.tool=='furn')ED.fg=placeFurn(M,p);
 if(ED.tool=='select'){const h=e.target.closest&&e.target.closest('#plan')?hit(M,p):null,k=h?h.t+(h.id||h.i):'',k0=ED.hover?ED.hover.t+(ED.hover.id||ED.hover.i):'';$('#plan').style.cursor=h&&h.t=='furn'&&e.altKey?'copy':h&&h.t!='fixed'&&h.t!='room'?'move':h?'pointer':'';if(k==k0)return;ED.hover=h&&h.t!='room'?h:null}
 else $('#plan').style.cursor='crosshair';
 reDraw()});
window.addEventListener('pointerup',()=>{PAN=null;if(!DR)return;const d=DR;DR=null;
 if(d.clone&&!d.mv){const M=curM();M.furn=M.furn.filter(f=>f.id!=d.id);ED.sel={t:'furn',id:d.clone};draw();renderProps();return} // Alt-клик без сдвига — копии нет
 if(d.mv)changed(d.k!='furn'&&d.k!='riser'?1:0)});
/* ---- клавиши (перехват до общего обработчика) ---- */
window.addEventListener('keydown',e=>{if(!$('#s-ws').classList.contains('on')||/TEXTAREA|INPUT|SELECT/.test(e.target.tagName))return;const k=e.key.toLowerCase(),M=curM();
 if((e.ctrlKey||e.metaKey)&&(k=='z'||k=='я')){if(ED.on){e.shiftKey?redo():undo();e.preventDefault()}return}
 if((e.ctrlKey||e.metaKey)&&(k=='y'||k=='н')){if(ED.on){redo();e.preventDefault()}return}
 if(!ED.on)return;
 if((e.ctrlKey||e.metaKey)&&e.code=='KeyC'&&ED.sel&&ED.sel.t=='furn'){const f=M.furn.find(x=>x.id==ED.sel.id);if(f){ED.clip=cl(f);ED.pn=0;toast('Скопировано · Ctrl+V — вставить');e.preventDefault();e.stopImmediatePropagation()}return}
 if((e.ctrlKey||e.metaKey)&&e.code=='KeyV'&&ED.clip){e.preventDefault();e.stopImmediatePropagation();pasteFurn();return}
 if(ED.tool=='wall'&&ED.chain&&!e.ctrlKey&&!e.metaKey&&(/^[0-9]$/.test(e.key)||e.key=='Backspace'&&ED.typed)){e.stopImmediatePropagation();e.preventDefault();ED.typed=e.key=='Backspace'?ED.typed.slice(0,-1):ED.typed+e.key;reDraw();return}
 if(e.key=='Enter'&&ED.tool=='wall'&&ED.chain){e.stopImmediatePropagation();if(ED.typed)addWallPt(M,liveEnd());else endChain();return}
 if(e.key=='Escape'){e.stopImmediatePropagation();if(ED.chain){endChain();return}if(ED.tool!='select'){_pick('select');ED.tool='select';ED.prev=ED.fg=null;renderProps();reDraw();return}if(ED.sel){ED.sel=null;draw();renderProps();return}edDone();return}
 if(e.key=='Tab'&&ED.tool=='door'){e.preventDefault();ED.hg=ED.hg=='e'?'s':'e';if(ED.prev)ED.prev.h=ED.hg;reDraw();return}
 if((e.key=='Delete'||e.key=='Backspace')&&ED.sel){e.preventDefault();delSel();return}
 if(k=='r'||k=='к'){e.stopImmediatePropagation();if(ED.tool=='furn'){ED.frot=(ED.frot+90)%360;if(ED.fg&&ED.pt){ED.fg=placeFurn(M,ED.pt);ED.fg.r=ED.frot}reDraw();return}if(ED.sel&&ED.sel.t=='furn'){turnF(e.shiftKey?-90:90);return}pickTool('room');return}});
function delSel(){const M=curM(),s=ED.sel;if(!s)return;if(s.t=='fixed')return toast('Наружный контур из модели на замке');
 if(s.t=='room'){const R=calcRooms(M).regs[s.i];if(!R)return;mut(M=>{M.rooms=M.rooms.filter((l,i)=>!R.labs.includes(i))},1);ED.sel=null;renderProps();return}
 mut(M=>{if(s.t=='wall'){M.walls=M.walls.filter(w=>w.id!=s.id);M.ops=M.ops.filter(o=>o.wall!=s.id)}
  if(s.t=='op')M.ops=M.ops.filter(x=>x.id!=s.id);
  if(s.t=='furn')M.furn=M.furn.filter(f=>f.id!=s.id);if(s.t=='riser')M.risers=M.risers.filter(r=>r.id!=s.id)},s.t!='furn'&&s.t!='riser');ED.sel=null;renderProps()}
/* вставка мебели: под курсор, если он над планом, иначе со сдвигом 200 мм от оригинала */
function pasteFurn(){let id;mut(M=>{const c=cl(ED.clip);c.id=nid(M,'f');const b=fbox(c),P=ED.cur&&ED.cur.x>=0&&ED.cur.y>=0&&ED.cur.x<=M.W&&ED.cur.y<=M.H?ED.cur:null;ED.pn=(ED.pn||0)+1;
 const dx=P?P.x-b.cx:10*ED.pn,dy=P?P.y-b.cy:10*ED.pn;c.x=q2(c.x+dx);c.y=q2(c.y+dy);M.furn.push(c);M.furnOn=true;id=c.id},0);ED.sel={t:'furn',id};draw();renderProps()}
function turnF(d){const M=curM(),f=M.furn.find(x=>x.id==ED.sel.id);if(!f)return;mut(()=>{f.r=((f.r+d)%360+360)%360},0)}
/* ---- панель «Свойства» справа ---- */
const fld=(lab,val,on,unit='мм',dis)=>`<label class="fld"><span>${lab}</span><input inputmode="numeric" value="${val}" ${dis?'disabled':''} onchange="${on}"><span>${unit}</span></label>`;
const pchip=(t,on,js,dis)=>`<button class="chip ${on?'on':''}" ${dis?'disabled':''} onclick="${js}">${t}</button>`;
const SW=[['s',-1,'Петли слева · вверх',1,1],['e',-1,'Петли справа · вверх',-1,1],['s',1,'Петли слева · вниз',1,-1],['e',1,'Петли справа · вниз',-1,-1]];
/* значок открывания: стена с проёмом, полотно, дуга хода и лёгкая заливка зоны открывания */
const swIco=(sx,sy)=>`<svg viewBox="0 0 28 24" width="30" height="26" fill="none" stroke="currentColor" stroke-linecap="round"><g transform="translate(14 12) scale(${sx} ${sy}) translate(-14 -12)"><path d="M4.5 20V3.5A16.5 16.5 0 0 1 21 20Z" fill="currentColor" fill-opacity=".08" stroke="none"/><path d="M1 20h3.5M21 20h6" stroke-width="3" stroke-linecap="butt" stroke-opacity=".5"/><path d="M4.5 3.5A16.5 16.5 0 0 1 21 20" stroke-width="1" stroke-dasharray="2 2"/><path d="M4.5 20V3.5" stroke-width="2.2"/><circle cx="4.5" cy="20" r="1.6" fill="currentColor" stroke="none"/></g></svg>`;
const sec=(ic,t,b)=>`<div class="blk"><p class="lbl"><span class="i" style="font-size:16px">${ic}</span>${t}</p>${b}</div>`;
function opOff(M,o){const w=M.walls.find(x=>x.id==o.wall);if(!w)return null;const G=wgeo(w),[s]=loc(o.x,o.y,G.cx,G.cy,G.a);return mmv(s+G.len/2-o.w/2)}
function opsList(M,w){const os=M.ops.filter(o=>o.wall==w.id);if(!os.length)return '';return `<p class="lbl" style="margin:14px 0 6px">Проёмы</p>`+os.map(o=>`<button class="orow" onclick="ED.sel={t:'op',id:'${o.id}'};draw();renderProps()"><span class="i">${o.k=='door'?'door_front':o.k=='win'?'window':'crop_free'}</span>${o.k=='door'?'Дверь':o.k=='win'?'Окно':'Проход'}<span class="sp"></span><span class="lead">${mmv(o.w)} мм</span></button>`).join('')}
function renderProps(){if(!ED.on)return;const M=curM(),s=ED.sel,b=$('#props');if(!M)return;$('#undo').disabled=!ED.hist.length;$('#redo').disabled=!ED.fut.length;let h='';
 const tl={wall:'Стена',door:'Дверь',window:'Окно',riser:'Стояк',room:'Помещение',furn:'Мебель',ruler:'Масштаб'}[ED.tool];
 if(tl&&!(s&&(ED.tool=='door'||ED.tool=='window'||ED.tool=='furn'||ED.tool=='riser'))){
  if(ED.tool=='wall')h+=sec('draw','Новая стена',`<div class="seg" style="margin-bottom:6px">${Object.entries(WT).map(([k,[n,t]])=>`<button class="${ED.wt==k?'on':''}" onclick="ED.wt='${k}';ED.wth=${t};renderProps()">${n}</button>`).join('')}</div>${fld('Толщина',ED.wth,"ED.wth=+this.value||ED.wth")}<p class="hintp">Клик — начало, клик — следующий угол; клик в первую точку замыкает контур. Привязка к углам, серединам и осям стен, луч от прошлой точки — шаг 45° (Shift — 15°), Alt — без привязки. Цифры — длина в мм, Enter. Esc или двойной клик — закончить.</p>`);
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
  if(s.t=='op'){const o=M.ops.find(x=>x.id==s.id);if(o&&o.cw)h+=sec('window','Угловое окно',fld('Сторона 1',mmv(o.cw.L1),`setCw('${o.id}','L1',this.value)`)+fld('Сторона 2',mmv(o.cw.L2),`setCw('${o.id}','L2',this.value)`)+
    `<p class="hintp">Стороны — по внутренним граням от угла. Потяните окно вдоль стены — станет прямым, к углу — снова угловым.</p><div class="pacts"><button class="btn sm" onclick="cwStraight('${o.id}')"><span class="i">straighten</span>Сделать прямым</button><button class="btn sm" onclick="delSel()"><span class="i">delete</span>Удалить окно</button></div>`);
   else if(o){const off=opOff(M,o),nm={door:'Дверь',win:'Окно',pass:'Проход без полотна',blank:'Заложенный проём'}[o.k],up=`mut(M=>{const o=M.ops.find(x=>x.id=='${o.id}');`;
   h+=sec(o.k=='door'?'door_front':o.k=='win'?'window':'crop_free',nm+(o.wall?'':' · в наружной стене'),
   (o.k=='door'?`<p class="lbl" style="margin:0 0 6px">Открывание</p><div class="swg">${SW.map(([hg,sd,t,sx,sy])=>`<button title="${t}" class="${o.h==hg&&o.side==sd?'on':''}" onclick="${up}o.h='${hg}';o.side=${sd}},0)">${swIco(sx,sy)}</button>`).join('')}</div>
    <div class="pacts" style="margin-top:8px"><button class="btn sm" onclick="${up}o.h=o.h=='s'?'e':'s'},0)"><span class="i">swap_horiz</span>Петли</button><button class="btn sm" onclick="${up}o.side=-o.side},0)"><span class="i">swap_vert</span>Внутрь / наружу</button></div>`:'')+
   (o.k!='blank'?fld('Ширина',mmv(o.w),`setOp('${o.id}','w',this.value)`)+(off!=null?fld('От угла',off,`setOp('${o.id}','off',this.value)`):''):'')+
   `<div class="pacts">${o.k=='pass'?`<button class="btn sm" onclick="${up}o.k='door';o.side=1;o.h='s'},1)"><span class="i">door_front</span>Поставить дверь</button>`:''}${o.k=='blank'?`<button class="btn sm" onclick="${up}o.k=o.was||'win'},1)"><span class="i">undo</span>Вернуть ${o.was=='door'?'дверь':'окно'}</button>`:`<button class="btn sm" onclick="delSel()"><span class="i">${o.wall?'delete':'select'}</span>${o.wall?'Удалить проём':'Заложить проём'}</button>`}</div>`)}}
  if(s.t=='furn'){const f=M.furn.find(x=>x.id==s.id);if(f){const c=f.c&&FC[f.c];h+=sec('chair',c?c[1]:(f.cat=='PLB'?'Сантехника из модели':'Мебель из модели'),
   (c?`<select class="sel" onchange="mut(M=>{const f=M.furn.find(x=>x.id=='${f.id}');f.c=this.value},0)">${FCAT.map(([k,n,w,d])=>`<option value="${k}" ${k==f.c?'selected':''}>${n} · ${w}×${d}</option>`).join('')}</select>`:'')+
   `<div class="row"><span class="lead">Габарит</span><span>${c?c[2]+' × '+c[3]:f.w+' × '+f.d} мм</span></div><div class="row"><span class="lead">Поворот</span><span>${f.r}°${f.m?' · зеркально':''}</span></div>
   <div class="pacts"><button class="btn sm" onclick="turnF(90)"><span class="i">rotate_right</span>90°</button><button class="btn sm" onclick="turnF(-90)"><span class="i">rotate_left</span>90°</button><button class="btn sm ${f.m?'onb':''}" onclick="mut(M=>{const f=M.furn.find(x=>x.id=='${f.id}');f.m=f.m?0:1},0)"><span class="i">flip</span>Зеркало</button></div>
   <p class="hintp">Копия: Alt + тянуть или Ctrl+C, Ctrl+V.</p>
   ${wcLike(f)||f.c=='wc'||f.c=='bidet'?`<div class="pacts"><button class="btn sm" onclick="swapWc('${f.id}')"><span class="i">swap_horiz</span>${f.c=='bidet'?'Это унитаз':'Это биде'}</button></div>`:''}
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
  }
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
