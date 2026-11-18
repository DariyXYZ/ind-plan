/* ===== Финальный интерфейс IND PLAN (всё, кроме самой генерации).
   Слой поверх MVP и редактора: контур с нуля (стены по оси → вход → окна → стояк) с проверкой на каждом шаге,
   прямоугольник по размерам, импорт Revit .json (ind-plan / ind-plan-base), AutoCAD .dxf, подложка PDF/картинка
   с калибровкой масштаба, перетаскивание файла на поле, сохранение файлов в браузере, список файлов, переименование,
   состояния запуска (очередь, прогресс, остановка, ошибка, нехватка токенов, нет сети), настоящий экспорт JSON/SVG/PNG/PDF.
   Генерация — заглушка: варианты есть только для примера кв. 28, для своего контура запуск честно говорит, что генератор не подключён. ===== */
const IP={pid:null,ro:0,busy:0,res:0,cv:1,runs:{},fresh:new Set(),saveT:0,saveSt:'',wasClosed:0,r1:null,menu:null};
const LSK='indplan:v1',LSU='indplan:user';
const nf=(v,d=1)=>(+v).toFixed(d).replace('.',',');
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const ipLS={get(){try{return JSON.parse(localStorage.getItem(LSK)||'{"projects":[]}')}catch{return {projects:[]}}},
 set(d){localStorage.setItem(LSK,JSON.stringify(d))}};
/* ---------- стили ---------- */
document.head.insertAdjacentHTML('beforeend',`<style>
@keyframes ipIn{from{opacity:0;transform:translateY(6px)}}@keyframes ipPop{from{opacity:0;transform:scale(.96)}}@keyframes ipFade{from{opacity:0}}
@keyframes ipSpin{to{transform:rotate(360deg)}}@keyframes ipCheck{0%{transform:scale(.6)}60%{transform:scale(1.15)}}@keyframes ipPulse{50%{border-color:var(--acc)}}
.screen.on{animation:ipFade .2s}.scrim.on{animation:ipFade .15s}.scrim.on .modal{animation:ipPop .18s cubic-bezier(.2,.8,.3,1)}
.gi.new{animation:ipIn .35s both}.spin{animation:ipSpin .9s linear infinite}
.ipempty{display:flex;flex-direction:column;align-items:center;gap:14px;width:min(640px,86%)}
.ghost-rect{width:100%}.ipopts{display:flex;flex-wrap:wrap;gap:8px;justify-content:center}
.ipfoot{font-size:12px;color:var(--faint);text-align:center;line-height:1.5}.ipfoot a,.lnk{color:var(--acc-text);cursor:pointer;text-decoration:underline;text-underline-offset:2px;background:none;border:0;padding:0;font:inherit}
.ipalert{display:flex;gap:10px;align-items:flex-start;width:100%;padding:12px 14px;border-radius:12px;font-size:13px;line-height:1.45;background:var(--err-soft);color:var(--text);animation:ipIn .25s}
.ipalert.w{background:var(--warn-soft)}.ipalert .i{color:var(--err);font-size:20px}.ipalert.w .i{color:var(--warn)}.ipalert b{display:block}.ipalert .sp{flex:1}
.ipdrop{position:absolute;inset:10px;border:2px dashed var(--line2);border-radius:16px;background:color-mix(in srgb,var(--acc-soft) 85%,transparent);display:none;align-items:center;justify-content:center;flex-direction:column;gap:6px;z-index:20;color:var(--acc-text);font-weight:600;animation:ipPulse 1.2s infinite}
.ipdrop.on{display:flex}.ipdrop .i{font-size:40px}.ipdrop small{font-weight:400;color:var(--muted)}
.ipload{position:absolute;inset:0;display:none;align-items:center;justify-content:center;z-index:21;background:color-mix(in srgb,var(--bg) 70%,transparent)}
.ipload.on{display:flex;animation:ipFade .15s}.ipload>div{display:flex;align-items:center;gap:10px;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 16px;box-shadow:var(--sh);font-size:13px}
.ipsteps{position:absolute;left:50%;top:14px;transform:translateX(-50%);display:none;align-items:center;gap:2px;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:4px;box-shadow:var(--sh);z-index:4;white-space:nowrap}
.ipsteps.on{display:flex;animation:ipIn .2s}.ipsteps button{display:flex;align-items:center;gap:5px;height:32px;padding:0 10px;border:0;background:transparent;border-radius:8px;cursor:pointer;font-size:13px;color:var(--muted)}
.ipsteps button:hover{background:var(--sub);color:var(--text)}.ipsteps button.cur{background:var(--acc-soft);color:var(--acc-text)}.ipsteps .i{font-size:17px}
.ipsteps .ok{color:var(--text)}.ipsteps .ok .i{color:var(--ok);animation:ipCheck .3s}.ipsteps .opt .i{color:var(--faint)}.ipsteps small{color:var(--faint);font-size:12px}
.ipsteps .sep{width:1px;height:20px;background:var(--line);margin:0 4px}
.iprun{margin:4px 0 6px}.iprun .runh{padding-right:4px}.iprun .runh .sp{flex:1}.iprun .runh button{height:24px;padding:0 8px;border-radius:6px;border:1px solid var(--line2);background:var(--panel);font-size:12px;cursor:pointer;color:var(--text)}
.iprun .runh button:hover{background:var(--sub)}.ipst{font-size:12px;color:var(--muted);display:flex;align-items:center;gap:4px;padding:0 8px 6px}.ipst .i{font-size:15px}
.ipbar{height:3px;margin:0 8px 8px;border-radius:2px;background:var(--line);overflow:hidden}.ipbar i{display:block;height:100%;background:var(--acc);transition:width .5s ease}
.ipfail{margin:4px 8px 8px;padding:12px;border-radius:10px;background:var(--sub);font-size:12px;line-height:1.45;color:var(--muted);animation:ipIn .25s}.ipfail b{display:flex;gap:6px;align-items:center;color:var(--text);font-size:13px;margin-bottom:4px}
.ipfail .i{font-size:17px}.ipfail .acts{display:flex;gap:6px;margin-top:10px;flex-wrap:wrap}
.tok small{color:var(--warn);font-weight:500}
.fname b{cursor:text;border-radius:6px;padding:2px 4px;margin:-2px -4px}.fname b:hover{background:var(--sub)}.fname input{font:inherit;font-weight:600;color:var(--text);border:1px solid var(--acc);border-radius:6px;padding:2px 6px;width:260px;background:var(--panel);outline:none}
.fname .crumb{cursor:pointer}.fname .crumb:hover{color:var(--text)}
#save.err{background:var(--err-soft);color:var(--err);cursor:pointer}#save.ro{background:var(--warn-soft);color:var(--warn)}
.ferr{font-size:12px;color:var(--err);min-height:16px;margin-top:4px}.inp.bad{border-color:var(--err)}
.sec-h{display:flex;align-items:baseline;gap:10px;margin:36px 0 0}.sec-h h2{font-size:17px}.sec-h span{color:var(--muted);font-size:13px}
.pcard{position:relative}.pcard .more{position:absolute;right:8px;top:8px;background:var(--panel);box-shadow:0 1px 3px #0002;opacity:0;transition:.12s}.pcard:hover .more,.pcard .more:focus{opacity:1}
.pcard .ph{color:var(--faint);display:flex;flex-direction:column;align-items:center;gap:6px;font-size:12px}.pcard .ph .i{font-size:30px}
.ipmenu{position:fixed;z-index:70;min-width:200px;background:var(--panel);border:1px solid var(--line);border-radius:12px;box-shadow:0 12px 32px #0002;padding:6px;animation:ipPop .12s}
.ipmenu button{display:flex;align-items:center;gap:10px;width:100%;height:34px;padding:0 10px;border:0;background:transparent;border-radius:8px;cursor:pointer;font-size:13px;color:var(--text);text-align:left}
.ipmenu button:hover{background:var(--sub)}.ipmenu button.dng{color:var(--err)}.ipmenu .i{font-size:18px;color:var(--muted)}.ipmenu button.dng .i{color:var(--err)}.ipmenu .who{padding:8px 10px 10px;font-size:12px;color:var(--muted);border-bottom:1px solid var(--line);margin-bottom:4px}
.toast{top:auto!important;bottom:118px;transform:translateX(-50%) translateY(12px)!important}.toast.on{transform:translateX(-50%) translateY(0)!important}#s-projects.on~.toast,.toast.k-top{bottom:32px}.toast.k-err .i{color:#ff8a80}.toast.k-warn .i{color:#ffcc80}.toast .tact{margin-left:8px;background:#ffffff26;border:0;color:#fff;border-radius:6px;height:26px;padding:0 10px;cursor:pointer;font:inherit;font-weight:600}
.opt3{display:grid;gap:8px}.opt3 button{display:flex;gap:12px;align-items:center;text-align:left;padding:12px 14px;border:1px solid var(--line2);border-radius:12px;background:var(--panel);cursor:pointer;color:var(--text);font:inherit}
.opt3 button:hover{border-color:var(--acc);background:var(--acc-soft)}.opt3 .i{font-size:22px;color:var(--acc-text)}.opt3 small{display:block;color:var(--muted);font-size:12px}
.pgs{display:flex;flex-wrap:wrap;gap:6px}.pgs button{width:42px;height:36px;border:1px solid var(--line2);border-radius:8px;background:var(--panel);cursor:pointer;font:inherit;color:var(--text)}.pgs button:hover{border-color:var(--acc);background:var(--acc-soft)}
.ipsmall{display:none}.pcard .th svg{width:100%;height:118px}.stage{padding-top:84px}.ipempty .ghost-rect{aspect-ratio:2/1}
@media (max-width:1000px){.ipsmall{display:flex;position:absolute;inset:52px 0 0;z-index:30;background:var(--bg);flex-direction:column;align-items:center;justify-content:center;gap:8px;text-align:center;padding:24px;color:var(--muted)}.ipsmall .i{font-size:40px;color:var(--faint)}.ipsmall b{color:var(--text)}}
@media (prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;transition:none!important}}
</style>`);
/* сетка листа 1 м и пустой контейнер для общих defs */
document.body.insertAdjacentHTML('beforeend',`<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs><pattern id="ipg" width="50" height="50" patternUnits="userSpaceOnUse"><path d="M50 0H0V50" fill="none" stroke="#0000000f" stroke-width="1"/></pattern></defs></svg><input type="file" id="ipfile" hidden>`);

/* ---------- тосты: тип и действие ---------- */
toast=function(t,o={}){const el=$('#toast');el.className='toast k-'+(o.k||'ok');el.querySelector('.i').textContent=o.k=='err'?'error':o.k=='warn'?'warning':o.icon||'check_circle';
 $('#tt').innerHTML=esc(t)+(o.act?`<button class="tact">${esc(o.act)}</button>`:'');if(o.act)el.querySelector('.tact').onclick=()=>{el.classList.remove('on');o.fn()};
 el.style.pointerEvents=o.act?'auto':'none';el.classList.add('on');clearTimeout(toast.t);toast.t=setTimeout(()=>el.classList.remove('on'),o.ms||(o.act?6000:o.k=='err'?4500:2600))};

/* ---------- модалки ---------- */
function ipModal(h,o={}){$('#expbox').innerHTML=h;$('#exp').classList.add('on');IP.modal=o;setTimeout(()=>{const f=$('#expbox [autofocus]')||$('#expbox .btn.pri');f&&f.focus()},30)}
function ipClose(){$('#exp').classList.remove('on');const c=IP.modal&&IP.modal.onClose;IP.modal=null;c&&c()}
$('#exp').addEventListener('pointerdown',e=>{if(e.target.id=='exp')ipClose()});
const mHead=t=>`<div class="mh"><h2>${t}</h2><span class="sp"></span><button class="ib" onclick="ipClose()" title="Закрыть · Esc"><span class="i">close</span></button></div>`;
function ipConfirm(t,body,ok,fn,o={}){ipModal(`${mHead(t)}<div class="mb"><p class="lead">${body}</p></div><div class="mf"><button class="btn" onclick="ipClose()">${o.cancel||'Отмена'}</button><button class="btn pri" ${o.danger?'style="background:var(--err);border-color:var(--err)"':''} id="ipok">${ok}</button></div>`);$('#ipok').onclick=()=>{ipClose();fn()}}

/* ---------- клавиши: модалка и меню перехватывают раньше редактора ---------- */
document.addEventListener('keydown',e=>{if(IP.menu&&e.key=='Escape'){ipMenuClose();e.stopImmediatePropagation();return}
 if(!$('#exp').classList.contains('on'))return;if(e.key=='Escape'){ipClose();e.preventDefault();e.stopImmediatePropagation();return}
 if(e.key=='Enter'&&e.target.tagName=='INPUT'){const b=$('#expbox .btn.pri');if(b&&!b.disabled){e.preventDefault();b.click()}}
 e.stopImmediatePropagation()},true);

/* ---------- модель: чистый лист 20 × 14 м, 1 ед. = 20 мм ---------- */
const ipBlank=(w=1000,h=700)=>({lay:'contour',user:1,vb:`0 0 ${w} ${h}`,W:w,H:h,fixed:'',walls:[],ops:[],furn:[],risers:[],rooms:[],cut:[],gv:1,seq:500,furnOn:true,off:[0,0]});
const ipHas=M=>!!M&&!!(M.fixed||M.walls.length||M.ul||M.risers.length);
const isExt=(M,id)=>{const w=M.walls.find(x=>x.id==id);return !!w&&w.type!='part'};
function ipCheck(M){if(!M)return null;const ext=M.walls.filter(w=>w.type!='part');let closed,area;
 if(M.fixed){closed=1;area=106.21}else{const Kr=calcRooms(M);let n=0;for(let i=0;i<Kr.L.length;i++)if(Kr.L[i]>=0)n++;area=n*MM*MM/1e6;closed=ext.length>=3&&area>=2}
 const entr=M.ops.some(o=>o.k=='door'&&(!o.wall||isExt(M,o.wall))),wins=M.fixed?1:M.ops.filter(o=>o.k=='win'&&(!o.wall||isExt(M,o.wall))).length;
 const Kr=calcRooms(M),rOut=M.risers.filter(r=>{const x=Math.round(r.x),y=Math.round(r.y);return x<0||y<0||x>=Kr.W||y>=Kr.H||Kr.L[y*Kr.W+x]==-2}).length;
 const E=[],W=[];
 if(!closed)E.push({t:ext.length?'Контур не замкнут — доведите стену до первой точки':'Нарисуйте наружные стены квартиры',tool:'wall'});
 else if(area<12)E.push({t:`Площадь ${nf(area)} м² — слишком мало для квартиры. Проверьте масштаб`,tool:'wall'});
 if(!entr)E.push({t:'Поставьте входную дверь в наружную стену',tool:'door'});
 if(!wins)E.push({t:'Добавьте хотя бы одно окно в наружную стену',tool:'window'});
 if(M.ul&&!M.ul.cal)W.push({t:'Масштаб подложки не задан — стены могут не совпасть с чертежом',tool:'ruler'});
 if(closed&&area>600)W.push({t:`Площадь ${nf(area,0)} м² — больше обычной квартиры. Проверьте масштаб`,tool:'wall'});
 if(!M.risers.length)W.push({t:'Стояк не задан — санузлы встанут, где удобнее генератору',tool:'riser'});
 if(rOut)W.push({t:'Стояк стоит за пределами квартиры',tool:'riser'});
 return {closed,area,entr,wins,risers:M.risers.length,ext:ext.length,ok:!E.length,err:E[0],warn:W[0],E,W}}
function ipDims(M){if(M.fixed)return '16,6 × 8,8 м';const ex=M.walls.filter(w=>w.type!='part');if(!ex.length)return '';let a=1e9,b=1e9,c=-1e9,d=-1e9;
 ex.forEach(w=>{const h=w.t/2;a=Math.min(a,w.x1-h,w.x2-h);b=Math.min(b,w.y1-h,w.y2-h);c=Math.max(c,w.x1+h,w.x2+h);d=Math.max(d,w.y1+h,w.y2+h)});return `${nf((c-a)*MM/1000)} × ${nf((d-b)*MM/1000)} м`}
/* сдвиг всей модели и подгонка листа под содержимое; off помнит сдвиг — экспорт вернёт исходные координаты */
function ipShift(M,dx,dy){const P=o=>{o.x+=dx;o.y+=dy};M.walls.forEach(w=>{w.x1+=dx;w.x2+=dx;w.y1+=dy;w.y2+=dy});M.ops.forEach(P);M.risers.forEach(P);M.rooms.forEach(P);M.furn.forEach(P);if(M.ul)P(M.ul);
 M.cut=(M.cut||[]).map(([a,b,c,d])=>[a+dx,b+dy,c+dx,d+dy]);M.off=[(M.off||[0,0])[0]+dx,(M.off||[0,0])[1]+dy]}
function ipFit(M){if(M.fixed)return true;let a=1e9,b=1e9,c=-1e9,d=-1e9;const add=(x,y,r=0)=>{a=Math.min(a,x-r);b=Math.min(b,y-r);c=Math.max(c,x+r);d=Math.max(d,y+r)};
 M.walls.forEach(w=>{add(w.x1,w.y1,w.t);add(w.x2,w.y2,w.t)});M.risers.forEach(r=>add(r.x,r.y,8));M.rooms.forEach(r=>add(r.x,r.y,10));if(M.ul){add(M.ul.x,M.ul.y);add(M.ul.x+M.ul.w,M.ul.y+M.ul.h)}
 if(a>c)return true;const w=c-a,h=d-b;if(w>2500||h>2500)return false;const m=60;ipShift(M,m-a,m-b);
 M.W=Math.max(800,Math.ceil(w+2*m));M.H=Math.max(520,Math.ceil(h+2*m));M.vb=`0 0 ${M.W} ${M.H}`;M.gv++;return true}

/* ---------- отрисовка: сетка листа, подложка, линейка ---------- */
const _ipMsvg=msvg;msvg=function(M,o={}){let s=_ipMsvg(M,o);if(!M.user)return s;let pre='';
 if(!o.exp)pre+=`<rect x="0" y="0" width="${M.W}" height="${M.H}" fill="url(#ipg)"/>`;
 if(M.ul&&!o.exp&&!o.thumb)pre+=`<image href="${M.ul.url}" x="${M.ul.x}" y="${M.ul.y}" width="${M.ul.w}" height="${M.ul.h}" opacity="${M.ul.op}" preserveAspectRatio="none" style="pointer-events:none"/>`;
 s=s.replace('data-m="1">','data-m="1">'+pre);
 if(o.ed&&ED.on&&ED.tool=='ruler'&&IP.r1){const P=ED.pt||IP.r1,z=ED.s||1,L=Math.hypot(P.x-IP.r1.x,P.y-IP.r1.y);
  s=s.replace(/<\/svg>$/,`<path d="M${IP.r1.x} ${IP.r1.y}L${P.x} ${P.y}" stroke="#E5484D" stroke-width="2" vector-effect="non-scaling-stroke"/><circle cx="${IP.r1.x}" cy="${IP.r1.y}" r="${4*z}" fill="#E5484D"/><text x="${(IP.r1.x+P.x)/2}" y="${(IP.r1.y+P.y)/2-8*z}" font-size="${12*z}" text-anchor="middle" font-family="Inter,sans-serif" fill="#E5484D" font-weight="600" paint-order="stroke" stroke="#fff" stroke-width="${3*z}">${M.ul&&M.ul.cal?Math.round(L*MM).toLocaleString('ru-RU')+' мм':'кликните во вторую точку'}</text></svg>`)}
 return s};

/* ---------- пустой экран: три способа начать ---------- */
$('#empty').innerHTML=`<div class="ipempty">
 <div class="ghost-rect" onclick="pickTool('wall')" role="button" tabindex="0"><div style="text-align:center;padding:12px"><span class="i" style="font-size:32px">draw</span><div style="font-weight:600;margin-top:6px">Нарисуйте контур квартиры</div><div style="font-size:12px;margin-top:2px">Наружные стены по оси: клик — угол, клик в первую точку — замкнуть · <kbd>W</kbd></div></div></div>
 <div class="ipopts"><button class="btn sm" onclick="ipRect()"><span class="i">crop_square</span>Прямоугольник по размерам</button><button class="btn sm" onclick="ipPick('json')"><span class="i">upload_file</span>Revit · .json</button><button class="btn sm" onclick="ipPick('dxf')"><span class="i">upload_file</span>AutoCAD · .dxf</button><button class="btn sm" onclick="ipPick('under')"><span class="i">image</span>PDF или картинка — подложка</button></div>
 <div id="ipalert" style="display:none;width:100%"></div>
 <p class="ipfoot">Или перетащите файл на поле — .json, .dxf, .pdf, .png, .jpg до 25 МБ<br>Нет своего плана? <button class="lnk" onclick="ipExample()">Откройте пример — кв. 28, 106 м²</button></p></div>`;
$('#empty .ghost-rect').addEventListener('keydown',e=>{if(e.key=='Enter'||e.key==' '){e.preventDefault();pickTool('wall')}});
$('#cv').insertAdjacentHTML('beforeend',`<div class="ipsteps" id="ipsteps"></div><div class="ipdrop" id="ipdrop"><span class="i">upload_file</span>Отпустите файл<small>.json из Revit · .dxf · PDF · PNG · JPG</small></div><div class="ipload" id="ipload"><div><span class="i spin">progress_activity</span><span id="iplt">Читаем файл…</span></div></div>`);
$('#s-ws').insertAdjacentHTML('beforeend',`<div class="ipsmall"><span class="i">desktop_windows</span><b>Редактор работает на экране от 1000 px</b>Откройте IND PLAN на компьютере — файлы сохранятся в этом браузере</div>`);
function ipAlert(t,body,o={}){const a=$('#ipalert');if(!a||$('#empty').style.display=='none')return toast(t+'. '+body.replace(/<[^>]+>/g,''),{k:o.w?'warn':'err',ms:7000});a.style.display='block';a.innerHTML=`<div class="ipalert ${o.w?'w':''}"><span class="i f">${o.w?'warning':'error'}</span><div><b>${esc(t)}</b>${body}</div><span class="sp"></span><button class="ib" style="width:26px;height:26px;margin:-4px -6px 0 0" onclick="$('#ipalert').style.display='none'" title="Скрыть"><span class="i" style="font-size:17px;color:var(--muted)">close</span></button></div>`}
const ipBusyOn=t=>{$('#iplt').textContent=t;$('#ipload').classList.add('on')},ipBusyOff=()=>$('#ipload').classList.remove('on');

/* ---------- старт контура ---------- */
function ipShowStage(){$('#empty').style.display='none';$('#stage').style.display='flex';$('#ipalert')&&($('#ipalert').style.display='none');
 if(ED.on)draw();else $('#plan').innerHTML=msvg(CM,{});ipTag();ipGate();$('#expbtn').style.display='';$('#expbtn').disabled=false}
function ipStartWith(M,msg){IP.hadEntr=ipCheck(M).entr;if(sel||refOn){sel=null;refOn=0;$('#vinfo').style.display='none';$('#insp').style.display='none';renderList()}CM=M;contour=true;IP.cv++;IP.wasClosed=ipCheck(M).closed;if(IP.wasClosed&&!M.fixed&&$('#fn').textContent=='Без названия'&&!IP.ro)$('#fn').textContent=`Квартира · ${nf(ipCheck(M).area,0)} м²`;ipShowStage();if(msg)toast(msg);saved()}
function ipStartBlank(){ipStartWith(ipBlank());edStart();ED.wt='ext';ED.wth=300;hint(WH1)}
function ipReplace(fn,what){if(!(contour&&ipHas(CM)))return fn();const n=V.length;
 ipConfirm('Заменить контур?',`Сейчас на поле есть контур${n?` и ${n} ${n%10==1&&n%100!=11?'вариант':'вариантов'} по нему. Варианты останутся в списке с пометкой «старый контур»`:''}. ${what}`,'Заменить',fn)}
function ipExample(){ipReplace(()=>{if(ED.on){ED.on=0;$('.right').classList.remove('ed')}ED.hist=[];ED.fut=[];const M=mkModel('contour');ipStartWith(M,'Пример: квартира 28, 106,21 м². Можно сразу создавать варианты');tool='select';renderTb();hint('')},'Пример кв. 28 откроется вместо него.')}
/* прямоугольник по размерам */
function ipRect(){ipReplace(()=>ipModal(`${mHead('Контур по размерам')}<div class="mb"><p class="lead" style="margin-bottom:14px">Прямоугольная квартира по осям наружных стен. Углы, вход и окна потом поправите на поле.</p>
 ${fld('Ширина','10000','',)}${fld('Глубина','7000','')}${fld('Толщина стен','300','')}<div class="ferr" id="rerr"></div></div>
 <div class="mf"><button class="btn" onclick="ipClose()">Отмена</button><button class="btn pri" onclick="ipRectGo()">Построить</button></div>`),'Новый прямоугольник заменит его.');
 setTimeout(()=>{const i=$('#expbox input');i&&(i.setAttribute('autofocus',''),i.focus(),i.select())},40)}
function ipRectGo(){const [w,h,t]=[...$$('#expbox input')].map(i=>+String(i.value).replace(/\s/g,'').replace(',','.'));const bad=(v,a,b)=>!(v>=a&&v<=b);
 $$('#expbox input').forEach(i=>i.classList.remove('bad'));
 if(bad(w,2000,60000)||bad(h,2000,60000)){$('#rerr').textContent='Ширина и глубина — от 2 000 до 60 000 мм';$$('#expbox input').forEach((i,k)=>k<2&&bad(+i.value,2000,60000)&&i.classList.add('bad'));return}
 if(bad(t,100,800)){$('#rerr').textContent='Толщина — от 100 до 800 мм';$$('#expbox input')[2].classList.add('bad');return}
 ipClose();const M=ipBlank(),a=w/MM,b=h/MM,x0=60,y0=60,P=[[x0,y0],[x0+a,y0],[x0+a,y0+b],[x0,y0+b]];
 P.forEach((p,i)=>{const q=P[(i+1)%4];M.walls.push({id:nid(M,'w'),x1:p[0],y1:p[1],x2:q[0],y2:q[1],t:t/MM,type:'ext',fixed:1})});ipFit(M);
 if(ED.on){ED.on=0;$('.right').classList.remove('ed')}ipStartWith(M,`Контур ${nf(w/1000)} × ${nf(h/1000)} м готов. Теперь вход — дверь в наружную стену`);edStart();pickTool('door')}

/* ---------- пикер инструментов: без контура рисовать можно только стены ---------- */
const _ipPick=pickTool;pickTool=function(t){if(t=='underlay')return ipPick('under');if(t=='import')return ipImportMenu();
 const E=['wall','door','window','riser','room','furn','ruler','part'];
 if(E.includes(t)&&!contour&&!refOn){if(t!='wall'){toast('Сначала нарисуйте наружные стены — W',{k:'warn'});return}ipStartBlank()}
 if(t=='ruler'&&!(curM()&&curM().ul)){toast('Масштаб задаётся по подложке — сначала загрузите PDF или картинку',{k:'warn'});return}
 _ipPick(t);IP.r1=null;
 if(t=='wall'&&!sel&&CM&&CM.user&&!ipCheck(CM).closed){ED.wt='ext';ED.wth=300;renderProps()}
 if(t=='ruler')hint('Кликните в начало отрезка известной длины на подложке, например размерной линии');ipSteps()};

/* ---------- линейка: два клика по подложке → длина в мм → масштаб ---------- */
$('#plan').addEventListener('pointerdown',e=>{if(!ED.on||ED.tool!='ruler'||e.button!==0)return;const M=curM(),p=evP(e);if(!M||!M.ul||!p)return;
 if(!IP.r1){IP.r1={x:p.x,y:p.y};hint('Теперь кликните в конец отрезка');reDraw();return}
 const r1=IP.r1,L=Math.hypot(p.x-r1.x,p.y-r1.y);if(L<3)return toast('Точки слишком близко — выберите отрезок длиннее',{k:'warn'});IP.r2={x:p.x,y:p.y};
 ipModal(`${mHead('Длина отрезка')}<div class="mb"><p class="lead" style="margin-bottom:12px">Сколько это в натуре? Чем длиннее отрезок, тем точнее масштаб — лучше брать размер всей стены.</p>${fld('Длина',M.ul.cal?Math.round(L*MM):'','')}<div class="ferr" id="lerr"></div></div>
  <div class="mf"><button class="btn" onclick="ipClose()">Отмена</button><button class="btn pri" onclick="ipCalib()">Задать масштаб</button></div>`,{onClose:()=>{IP.r1=null;reDraw()}});
 setTimeout(()=>{const i=$('#expbox input');i.placeholder='например, 6000';i.focus()},40)});
function ipCalib(){const v=+String($('#expbox input').value).replace(/\s/g,'').replace(',','.');if(!(v>=100&&v<=200000)){$('#lerr').textContent='Введите длину от 100 до 200 000 мм';$('#expbox input').classList.add('bad');return}
 const M=curM(),r1=IP.r1,r2=IP.r2,f=v/MM/Math.hypot(r2.x-r1.x,r2.y-r1.y);if(f>60||f<1/60){$('#lerr').textContent='Масштаб меняется больше чем в 60 раз — проверьте точки и длину';return}
 mut(M=>{const u=M.ul;u.x=r1.x+(u.x-r1.x)*f;u.y=r1.y+(u.y-r1.y)*f;u.w*=f;u.h*=f;u.cal=1;if(!ipFit(M))toast('Подложка вышла больше 50 м — проверьте длину',{k:'warn'})},1);
 IP.r1=null;ipClose();pickTool('wall');toast('Масштаб задан. Обведите наружные стены по подложке')}

/* ---------- проверка, шаги и кнопка «Создать» ---------- */
function ipTag(){if(!contour||sel||refOn||!CM)return;const c=ipCheck(CM);
 $('#sheettag').innerHTML=ED.on?`<span class="i" style="font-size:15px">edit</span><b>Контур</b>· клик — выбрать, тянуть — сдвинуть · Esc — выйти из правки`:
  `<span class="i" style="font-size:15px">draft</span>Контур квартиры${c.closed?` · ${ipDims(CM)} · ${nf(c.area,CM.fixed?2:1)} м²`:' · не замкнут'}${IP.ro?' · пример':''}`}
function ipSteps(){const el=$('#ipsteps');if(!el)return;if(!contour||sel||refOn||!CM){el.classList.remove('on');return}const c=ipCheck(CM),cur=ED.on?ED.tool:'';
 const S=[];if(CM.ul)S.push(['ruler','Масштаб',CM.ul.cal,'']);S.push(['wall','Стены',c.closed,c.closed?nf(c.area)+' м²':''],['door','Вход',c.entr,''],['window','Окна',c.wins>0,c.wins&&!CM.fixed?String(c.wins):''],['riser','Стояк',c.risers>0,'',1]);
 el.innerHTML=S.map(([t,n,ok,m,opt],i)=>`${i?'<span class="sep"></span>':''}<button class="${ok?'ok':opt?'opt':''} ${cur==t?'cur':''}" onclick="pickTool('${t}')" title="${ok?'Готово — можно поправить':opt?'Необязательно, но лучше задать':'Нужно для запуска'}"><span class="i ${ok?'f':''}">${ok?'check_circle':'radio_button_unchecked'}</span>${n}${m?` <small>${m}</small>`:''}</button>`).join('');el.classList.add('on')}
function ipGate(){const g=$('#genbtn');if(!g)return;const c=contour&&CM?ipCheck(CM):null,n=+$('#nseg .on').textContent,cost=n*COST,av=TOK-IP.res;let m,ic='info',col='';
 if(!c)m='Нарисуйте контур квартиры или загрузите файл';
 else if(IP.busy){m='Идёт запуск — дождитесь или остановите его';ic='progress_activity'}
 else if(c.err){m=c.err.t;ic='error';col='var(--err)'}
 else if(cost>av){m=`Не хватает токенов: запуск стоит ${cost}, доступно ${av}`;ic='toll';col='var(--warn)'}
 else if(c.warn){m=c.warn.t;ic='warning';col='var(--warn)'}
 else{m=`Контур готов · ${nf(c.area,CM.fixed?2:1)} м²`;ic='check_circle';col='var(--ok)'}
 g.disabled=!c||!c.ok||!!IP.busy;$('#ctast').innerHTML=`<span class="i ${ic=='progress_activity'?'spin':''} ${ic=='check_circle'||ic=='error'||ic=='warning'?'f':''}" ${col?`style="color:${col}"`:''}>${ic}</span>${esc(m)}`;
 const sb=$('#simbtn');if(sb)sb.disabled=!!IP.busy;ipTok()}
function ipTok(){$('#tok').innerHTML=(TOK-IP.res).toLocaleString('ru-RU')+(IP.res?` <small>· ${IP.res} в резерве</small>`:'')}
$$('#nseg button').forEach(b=>b.addEventListener('click',()=>setTimeout(ipGate)));

/* ---------- обёртки над MVP и редактором ---------- */
const _ipChanged=changed;changed=function(geo){if(geo&&!sel&&contour)IP.cv++;_ipChanged(geo);ipAfter()};
function ipAfter(){if(!contour||!CM)return;ipTag();ipSteps();ipGate();if(sel)return;const cl0=ipCheck(CM).closed;
 if(cl0&&!IP.wasClosed&&CM.user){const c=ipCheck(CM);toast(`Контур замкнут · ${nf(c.area)} м². Теперь вход — дверь в наружную стену`);setTimeout(()=>{if(ED.on&&ED.tool=='wall'){ED.chain=null;pickTool(c.entr?c.wins?'riser':'window':'door')}},0)}
 else if(ED.on&&ED.tool=='door'&&CM.user&&!IP.hadEntr&&ipCheck(CM).entr){setTimeout(()=>{if(ED.on&&ED.tool=='door'){pickTool(ipCheck(CM).wins?'riser':'window');toast(ipCheck(CM).wins?'Вход есть. Осталось отметить стояк':'Вход есть. Теперь окна — кликайте по наружным стенам')}},0)}
 else if(!cl0&&IP.wasClosed&&CM.user)toast('Контур разомкнулся — генератору нужен замкнутый контур',{k:'warn'});IP.wasClosed=cl0;IP.hadEntr=ipCheck(CM).entr;if(cl0&&$('#fn').textContent=='Без названия'&&!IP.ro)$('#fn').textContent=`Квартира · ${nf(ipCheck(CM).area,0)} м²`}
/* за краем листа рисовать можно — лист сам растёт (ipGrow); держим только предел 50 м */
const _ipAddPt=addWallPt;addWallPt=function(M,q){if(q&&M.user){let a=q.x,b=q.y,c=q.x,d=q.y;const add=(x,y)=>{a=Math.min(a,x);b=Math.min(b,y);c=Math.max(c,x);d=Math.max(d,y)};M.walls.forEach(w=>{add(w.x1,w.y1);add(w.x2,w.y2)});if(ED.chain)add(ED.chain.x,ED.chain.y);
 if(c-a>2500||d-b>2500){toast('Квартира выходит больше 50 м — проверьте длину стены',{k:'warn'});return}}
 IP.q=q&&{x:q.x,y:q.y,kind:q.kind,guides:[]};try{_ipAddPt(M,IP.q)}finally{IP.q=null}}; // копия точки: если лист вырастет, ipGrow сдвинет и её
const _ipEdStart=edStart;edStart=function(){_ipEdStart();ipTag();ipSteps()};
const _ipEdDone=edDone;edDone=function(){_ipEdDone();IP.r1=null;ipTag();ipSteps();ipGate()};
const _ipShowC=showContour;showContour=function(){_ipShowC();ipTag();ipSteps()};
const _ipShowVar=showVar;showVar=function(id){_ipShowVar(id);ipSteps()};
const _ipShowRef=showRef;showRef=function(){_ipShowRef();ipSteps()};
const _ipDraw=drawContour;drawContour=function(s){if(!CM)CM=mkModel('contour');_ipDraw(s);ipTag();ipSteps();ipGate();$('#expbtn').style.display=''};
const _ipReset=reset;reset=function(){_ipReset();clearTimeout(IP.noteT);Object.values(IP.runs).forEach(R=>(R.tm||[]).forEach(clearTimeout));IP.runs={};IP.busy=0;IP.res=0;IP.cv=1;IP.r1=null;IP.wasClosed=0;IP.fresh.clear();
 $('#ctast').innerHTML='<span class="i">info</span>Нарисуйте контур квартиры или загрузите файл';$('#expbtn').style.display='none';ipSteps();ipTok();$('#ipalert')&&($('#ipalert').style.display='none')};
const _ipAddVar=addVar;addVar=function(r,q,b,f){_ipAddVar(r,q,b,f);const v=V[V.length-1];v.cv=IP.cv;IP.fresh.add(v.id)};
const _ipRenderProps=renderProps;renderProps=function(){_ipRenderProps();if(!ED.on||sel||!CM||ED.sel)return;const c=ipCheck(CM);let h='';
 if(!(ED.tool!='select'&&ED.tool!='ruler')){const L=[...c.E.map(x=>['error','var(--err)',x]),...c.W.map(x=>['warning','var(--warn)',x])];
  h+=sec('fact_check','Контур',(L.length?L.map(([i,cl2,x])=>`<button class="orow" onclick="pickTool('${x.tool}')"><span class="i f" style="color:${cl2}">${i}</span><span style="white-space:normal">${esc(x.t)}</span></button>`).join(''):`<div class="row" style="margin:0"><span><span class="i f" style="color:var(--ok);font-size:17px">check_circle</span> Всё на месте</span><b>${nf(c.area,CM.fixed?2:1)} м²</b></div>`)+'<p class="hintp">Наружные стены, вход и окна генератор не двигает. Перегородки можно не рисовать.</p>')}
 if(CM.ul)h+=sec('image','Подложка',`<label class="fld" style="grid-template-columns:96px 1fr 36px"><span>Прозрачность</span><input type="range" min="10" max="90" value="${Math.round(CM.ul.op*100)}" oninput="CM.ul.op=this.value/100;this.nextElementSibling.textContent=this.value+'%';reDraw()" onchange="saved()"><span>${Math.round(CM.ul.op*100)}%</span></label>
  <div class="row"><span class="lead">Масштаб</span><span>${CM.ul.cal?'задан':'<span style="color:var(--warn)">не задан</span>'}</span></div><div class="pacts"><button class="btn sm" onclick="pickTool('ruler')"><span class="i">straighten</span>${CM.ul.cal?'Задать заново':'Задать масштаб'}</button><button class="btn sm" onclick="ipPick('under')"><span class="i">swap_horiz</span>Заменить</button><button class="btn sm" onclick="mut(M=>{delete M.ul},0);toast('Подложка убрана')"><span class="i">delete</span>Убрать</button></div>`);
 if(h)$('#props').insertAdjacentHTML('afterbegin',h)};
const _ipVote=vote;vote=function(x,id){_ipVote(x,id);saved()};

/* ---------- запуск: очередь → прогресс → готово / остановлено / ошибка ---------- */
gen=function(){if(ED.on)edDone();const c=CM&&ipCheck(CM);if(!c||!c.ok){toast(c&&c.err?c.err.t:'Сначала нарисуйте контур',{k:'err'});return}
 const n=+$('#nseg .on').textContent;run++;ipRun({r:run,n,q:$('#tz').value.trim(),type:curType,cost:n*COST})};
genSim=function(){const base=sel,tz=$('#simtz').value.trim(),n=simN,fix=$('#expbox .chk').classList.contains('on');ipClose();run++;
 ipRun({r:run,n,q:`изменения варианта ${base.id}`+(tz?' · '+tz:''),type:base.type,cost:n*COST,base,fix})};
const _ipOpenSim=openSim;openSim=function(){if(IP.busy)return toast('Дождитесь текущего запуска или остановите его',{k:'warn'});_ipOpenSim()};
function ipRun(R){if(IP.busy){run--;return toast('Дождитесь текущего запуска или остановите его',{k:'warn'})}
 if(R.cost>TOK-IP.res){run--;return ipNoTok(R)}
 if(!navigator.onLine){run--;return toast('Нет сети — запуск не отправлен. Проверьте подключение',{k:'err'})}
 R.nm=R.nm||$('#fn').textContent.trim();Object.assign(R,{st:'queue',got:0,tm:[]});IP.runs[R.r]=R;IP.busy=R.r;IP.res+=R.cost;
 $('#gempty').style.display='none';$('#glist').style.display='block';setGen('progress_activity','Создаём…',0);ipGate();renderList();$('#glist').scrollTop=0;hint('');
 const T=(f,ms)=>R.tm.push(setTimeout(f,ms)),demo=!!(CM&&CM.fixed);
 T(()=>{R.st='run';renderList()},900);
 if(!demo){T(()=>ipFail(R,'nogen'),2600);return}
 for(let i=0;i<R.n;i++)T(()=>{addVar(R.r,R.q,R.base,R.fix);R.got++;if(R.got==1)showVar(V[V.length-1].id);renderList();if(R.got==R.n)ipDone(R)},1500+i*700)}
function ipEnd(R){IP.busy=0;IP.res-=R.cost;setGen('auto_awesome',V.length?'Создать ещё':'Создать планировку');ipGate();renderList();saved()}
function ipDone(R){R.st='done';spend(R.cost);ipEnd(R);toast(`Готово: ${R.n} ${plur(R.n)}${R.base?'':' планировки'} · списано ${R.cost} токенов`)}
function ipStop(r){const R=IP.runs[r];if(!R||R.st=='done')return;R.tm.forEach(clearTimeout);R.st='cancel';const c=R.got*COST;if(c)spend(c);R.paid=c;ipEnd(R);
 toast(R.got?`Остановлено: готово ${R.got} из ${R.n}, списано ${c} токенов`:'Запуск отменён — токены не списаны',{icon:'block'})}
function ipFail(R,why){R.tm.forEach(clearTimeout);R.st='fail';R.why=why;const c=R.got*COST;if(c)spend(c);R.paid=c;ipEnd(R);if(why!='nogen')toast('Запуск прервался',{k:'err'})}
function ipRetry(r){const R=IP.runs[r];if(!R)return;run++;ipRun({r:run,n:R.n-R.got||R.n,q:R.q,type:R.type,cost:(R.n-R.got||R.n)*COST,base:R.base,fix:R.fix})}
function ipNoTok(R){const av=TOK-IP.res,k=Math.floor(av/COST);ipModal(`${mHead('Не хватает токенов')}<div class="mb"><p class="lead">Запуск на ${R.n} ${plur(R.n)} стоит ${R.cost} токенов, а доступно ${av}. Пополнить баланс может администратор бюро.</p></div>
 <div class="mf"><button class="btn" onclick="ipClose()">Понятно</button>${k>=1?`<button class="btn pri" id="ipk">Создать ${k} ${plur(k)} · ${k*COST}</button>`:''}</div>`);
 if(k>=1)$('#ipk').onclick=()=>{ipClose();run++;ipRun({...R,r:run,n:k,cost:k*COST})}}
window.addEventListener('offline',()=>{const R=IP.runs[IP.busy];if(R)ipFail(R,'net');else toast('Нет сети. Рисовать можно — файл сохраняется в этом браузере',{k:'warn'})});
window.addEventListener('online',()=>toast('Сеть снова есть'));
/* список вариантов с карточками запусков */
const ipItem=v=>`<div class="gi ${sel&&sel.id==v.id?'on':''} ${IP.fresh.has(v.id)?'new':''}" onclick="showVar(${v.id})"><div class="th">${svg(v.R,{label:false})}</div><div class="tt"><b>Вариант ${v.id}${v.ver>1?` <span class="badge b-n">v${v.ver}</span>`:''}</b><small>${v.type} · жилая ${nf(v.live)} м²</small><div style="margin-top:4px;display:flex;gap:4px;flex-wrap:wrap">${st(v)}${v.cv&&v.cv!=IP.cv?'<span class="badge b-n" title="Контур изменился после этого запуска">старый контур</span>':''}</div></div><div class="vb"><button class="ib ${v.vote>0?'up':''}" title="Нравится" onclick="event.stopPropagation();vote(1,${v.id})"><span class="i ${v.vote>0?'f':''}">thumb_up</span></button><button class="ib ${v.vote<0?'dn':''}" title="Мимо — учтём в следующих запусках" onclick="event.stopPropagation();vote(-1,${v.id})"><span class="i ${v.vote<0?'f':''}">thumb_down</span></button></div></div>`;
renderList=function(){renderFlt();let h='';const fl=FL.beds||FL.like||FL.ok;
 for(let r=run;r>=1;r--){const R=IP.runs[r],vs=V.filter(v=>v.run==r&&pass(v)),q=R?R.q:(V.find(v=>v.run==r)||{}).q,ty=R?R.type:(V.find(v=>v.run==r)||{}).type;
  if(!R||R.st=='done'){if(vs.length)h+=`<div class="runh"><span class="i">auto_awesome</span>${R&&R.nm?esc(R.nm)+' · з':'З'}апуск ${r} · ${ty}${q?' · '+esc(q):''}</div>`+vs.map(ipItem).join('');continue}
  if(fl&&!vs.length&&R.st!='run'&&R.st!='queue')continue;
  const pct=R.st=='queue'?6:Math.max(12,R.got/R.n*100),stl=R.st=='queue'?'<span class="i spin">progress_activity</span>В очереди…':R.st=='run'?`<span class="i spin">progress_activity</span>${R.got?`Готово ${R.got} из ${R.n}`:'Собираем зоны и стены…'}`:
   R.st=='cancel'?`<span class="i">block</span>${R.got?`Остановлено · готово ${R.got} из ${R.n} · списано ${R.paid}`:'Отменено · токены не списаны'}`:'';
  h+=`<div class="iprun"><div class="runh"><span class="i">auto_awesome</span>${R&&R.nm?esc(R.nm)+' · з':'З'}апуск ${r} · ${ty}${q?' · '+esc(q):''}<span class="sp"></span>${R.st=='queue'||R.st=='run'?`<button onclick="ipStop(${r})">${R.got?'Остановить':'Отменить'}</button>`:''}</div>`+
   (stl?`<div class="ipst">${stl}</div>`:'')+(R.st=='queue'||R.st=='run'?`<div class="ipbar"><i style="width:${pct}%"></i></div>`:'')+vs.map(ipItem).join('')+
   (R.st=='queue'||R.st=='run'?'<div class="sk"></div>'.repeat(R.n-R.got):'')+
   (R.st=='fail'?(R.why=='nogen'?`<div class="ipfail"><b><span class="i" style="color:var(--acc)">hourglass_top</span>Генератор пока не подключён</b>Контур сохранён — варианты для него появятся здесь, когда генератор заработает. Токены не списаны. Как выглядят варианты, можно посмотреть на примере кв. 28.<div class="acts"><button class="btn sm" onclick="ipOpenEx()"><span class="i">apartment</span>Открыть пример</button></div></div>`:
    `<div class="ipfail"><b><span class="i f" style="color:var(--err)">wifi_off</span>Запуск прервался — пропала сеть</b>${R.got?`Готовые ${R.got} из ${R.n} сохранены, списано ${R.paid}. За остальные токены не списаны.`:'Токены не списаны.'}<div class="acts"><button class="btn sm" onclick="ipRetry(${r})"><span class="i">refresh</span>Повторить${R.got?' остальные':''}</button></div></div>`):'')+'</div>'}
 const ref=V.length&&CM&&CM.fixed?`<div class="runh"><span class="i">apartment</span>Эталон бюро</div><div class="gi ${refOn?'on':''}" onclick="showRef()"><div class="th">${isvg()}</div><div class="tt"><b>Проект IND · кв. 28</b><small>Рабочая планировка · 106,21 м²</small><div style="margin-top:4px"><span class="badge b-n">IND</span></div></div></div>`:'';
 $('#glist').innerHTML=(h||(V.length?'<div class="fempty">Нет вариантов под фильтр · <button class="lnk" onclick="FL={beds:0,like:0,ok:0};renderList()">сбросить</button></div>':''))+ref;
 const any=V.length||Object.keys(IP.runs).length;$('#glist').style.display=any?'block':'none';$('#gempty').style.display=any?'none':'flex';$('#flt').style.display=V.length?'':'none';
 setTimeout(()=>IP.fresh.clear(),400)};
function ipOpenEx(){go('projects');setTimeout(()=>openWs(false,'Пример · кв. 28'),50)}

/* ---------- файлы: выбор, перетаскивание, разбор ---------- */
function ipImportMenu(){ipModal(`${mHead('Импорт')}<div class="mb"><div class="opt3">
 <button onclick="ipClose();ipPick('json')"><span class="i">upload_file</span><div><b>Revit · .json</b><small>Выгрузка графа «IND PLAN - транзит Revit» или экспорт IND PLAN. Стены, окна и двери встанут на места</small></div></button>
 <button onclick="ipClose();ipPick('dxf')"><span class="i">upload_file</span><div><b>AutoCAD · .dxf</b><small>Внешняя замкнутая полилиния станет наружными стенами, остальное — подложкой</small></div></button>
 <button onclick="ipClose();ipPick('under')"><span class="i">image</span><div><b>PDF или картинка</b><small>Ляжет подложкой: задайте масштаб и обведите стены</small></div></button></div></div>`)}
const ACC={json:'.json,application/json',dxf:'.dxf',under:'.pdf,.png,.jpg,.jpeg,.webp,application/pdf,image/*',any:''};
function ipPick(k){const i=$('#ipfile');i.value='';i.accept=ACC[k];i.onchange=()=>i.files[0]&&ipFile(i.files[0]);i.click()}
let ipDrag=0;const cvEl=$('#cv');
cvEl.addEventListener('dragenter',e=>{if(!e.dataTransfer||![...e.dataTransfer.types].includes('Files'))return;e.preventDefault();ipDrag++;$('#ipdrop').classList.add('on')});
cvEl.addEventListener('dragover',e=>{if([...(e.dataTransfer||{}).types||[]].includes('Files'))e.preventDefault()});
cvEl.addEventListener('dragleave',()=>{if(--ipDrag<=0){ipDrag=0;$('#ipdrop').classList.remove('on')}});
cvEl.addEventListener('drop',e=>{e.preventDefault();ipDrag=0;$('#ipdrop').classList.remove('on');const f=e.dataTransfer.files;if(!f.length)return;if(f.length>1)toast('Беру первый файл — по одному за раз',{k:'warn'});ipFile(f[0])});
window.addEventListener('dragover',e=>e.preventDefault());window.addEventListener('drop',e=>e.preventDefault());
function ipFile(f){const ext=(f.name.split('.').pop()||'').toLowerCase(),nm=`«${f.name}»`;
 if(!$('#s-ws').classList.contains('on'))return;
 if(!f.size)return ipAlert(`Файл ${nm} пустой`,'Сохраните его заново и попробуйте ещё раз.');
 if(f.size>25*1024*1024)return ipAlert(`Файл ${nm} больше 25 МБ`,'Выгрузите только нужный этаж или уменьшите картинку.');
 if(ext=='dwg')return ipAlert('DWG не читаем','В AutoCAD: «Сохранить как» → DXF (версия 2013 или новее), затем загрузите .dxf.');
 if(ext=='rvt'||ext=='rfa')return ipAlert('Файл Revit напрямую не читаем','Выгрузите план графом Dynamo «IND PLAN - транзит Revit» — получится .json.');
 if(ext=='ifc')return ipAlert('IFC пока не поддерживается','Выгрузите из Revit .json или сохраните план как DXF.');
 if(ext=='heic'||ext=='heif')return ipAlert('HEIC не поддерживается','Сохраните фото как JPG или PNG.');
 if(ext=='json')return ipReplace(()=>ipJson(f),'Контур из файла встанет вместо него.');
 if(ext=='dxf')return ipReplace(()=>ipDxf(f),'Контур из чертежа встанет вместо него.');
 if(ext=='pdf'||/^(png|jpe?g|webp|gif|bmp)$/.test(ext)||/^image\//.test(f.type))return ipUnder(f,ext=='pdf');
 ipAlert(`Формат .${esc(ext)} не поддерживается`,'Подходят: .json из Revit, .dxf, .pdf, .png, .jpg.')}
const ipDone2=(M,msg)=>{if(ED.on){ED.on=0;$('.right').classList.remove('ed')}ED.hist=[];ED.fut=[];ED.sel=null;ipStartWith(M,msg);tool='select';renderTb();hint('');const c=ipCheck(M);if(c.err){edStart();pickTool(c.err.tool)}};
/* Revit / IND PLAN json (мм, Y вверх) */
async function ipJson(f){ipBusyOn('Читаем выгрузку…');let raw;try{raw=JSON.parse(await f.text())}catch{ipBusyOff();return ipAlert(`Не получилось прочитать «${esc(f.name)}»`,'Файл повреждён или это не JSON. Выгрузите план заново.')}
 ipBusyOff();const fmt=raw&&raw.format;
 if(fmt=='ind-plan-base'){const L=(raw.levels||[]).filter(l=>(raw.walls||[]).some(w=>(w.levels||[]).includes(l.uid)));if(!L.length)return ipAlert('В выгрузке нет стен','Проверьте, что в Revit выбраны уровни со стенами.');
  if(L.length==1)return ipBuild(ipFromBase(raw,L[0]),f.name);
  return ipModal(`${mHead('Какой этаж взять?')}<div class="mb"><p class="lead" style="margin-bottom:12px">В выгрузке ${L.length} уровней. Один файл — одна квартира, поэтому выберите этаж.</p><div class="opt3">${L.map((l,i)=>`<button data-i="${i}"><span class="i">layers</span><div><b>${esc(l.name)}</b><small>${levelMk(l.elevation)} · стен ${(raw.walls||[]).filter(w=>(w.levels||[]).includes(l.uid)).length}</small></div></button>`).join('')}</div></div>`),
   $$('#expbox .opt3 button').forEach(b=>b.onclick=()=>{ipClose();ipBuild(ipFromBase(raw,L[+b.dataset.i]),f.name)})}
 if(fmt=='ind-plan'){const pages=Array.isArray(raw.levels)&&raw.levels.some(l=>l&&l.walls)?raw.levels:null;
  if(pages&&pages.length>1)return ipModal(`${mHead('Какой этаж взять?')}<div class="mb"><div class="opt3">${pages.map((p,i)=>`<button data-i="${i}"><span class="i">layers</span><div><b>${esc(p.level&&p.level.name||p.name||'Этаж '+(i+1))}</b><small>стен ${(p.walls||[]).length}</small></div></button>`).join('')}</div></div>`),
   $$('#expbox .opt3 button').forEach(b=>b.onclick=()=>{ipClose();ipBuild(ipFromPlan(pages[+b.dataset.i]),f.name)});
  return ipBuild(ipFromPlan(pages?pages[0]:raw),f.name)}
 ipAlert('Это не выгрузка IND PLAN',`Нужен .json из графа «IND PLAN - транзит Revit» или экспорт IND PLAN${fmt?` — в файле формат «${esc(fmt)}»`:''}.`)}
const levelMk=e=>(e>0?'+':e<0?'−':'±')+nf(Math.abs(e)/1000,3);
const WTM={exterior:'ext',bearing:'bear',partition:'part'},RNM={bedroom:'Спальня',living:'Гостиная',kitchen:'Кухня',hall:'Прихожая',corridor:'Коридор',bath:'Ванная',wc:'Санузел',wardrobe:'Гардероб',storage:'Кладовая',laundry:'Постирочная',office:'Кабинет',kids:'Детская',other:'Помещение'};
function ipWallsFrom(M,list,opsOf){let nOps=0,skip=0;list.forEach(w=>{const ax=w.axis||[];if(ax.length<2)return;const segs=[];for(let i=0;i<ax.length-1;i++)segs.push([ax[i],ax[i+1]]);if(w.closed&&ax.length>2)segs.push([ax[ax.length-1],ax[0]]);
 const ids=segs.map(([a,b])=>{const id=nid(M,'w');M.walls.push({id,x1:a[0]/MM,y1:-a[1]/MM,x2:b[0]/MM,y2:-b[1]/MM,t:Math.max(40,w.thickness||100)/MM,type:w._t,fixed:w._t!='part'?1:0});return id});
 opsOf(w).forEach(o=>{const wid=ids[o.seg||0],ww=M.walls.find(x=>x.id==wid);if(!ww){skip++;return}const G=wgeo(ww),wd=(o.width||(o.kind=='door'?900:1200))/MM,s=Math.max(wd/2,Math.min(G.len-wd/2,(o.at||0)/MM));
  M.ops.push({id:nid(M,'o'),k:o.kind=='door'?'door':'win',x:ww.x1+G.ux*s,y:ww.y1+G.uy*s,a:G.a,w:Math.min(wd,G.len),t:ww.t,side:o.side==-1?-1:1,h:o.hinge=='end'?'e':'s',wall:wid});nOps++})});return {nOps,skip}}
function ipFromPlan(d){const M=ipBlank();const W=(d.walls||[]).map(w=>({...w,_t:WTM[w.type]||'part'}));const r=ipWallsFrom(M,W,w=>(w.openings||[]).filter(o=>o.kind=='door'||o.kind=='window'));
 (d.risers||[]).forEach(x=>x.at&&M.risers.push({id:nid(M,'r'),x:x.at[0]/MM,y:-x.at[1]/MM,d:x.d||110,type:RT.includes(x.type)?x.type:'К1',fixed:1}));
 (d.rooms||[]).forEach(x=>x.seed&&M.rooms.push({n:x.name||RNM[x.type]||'Помещение',x:x.seed[0]/MM,y:-x.seed[1]/MM}));
 return {M,src:d.source=='revit'?'Revit':'IND PLAN',nf:(d.furniture||[]).length,...r}}
function ipFromBase(d,lv){const M=ipBlank();const W=(d.walls||[]).filter(w=>(w.levels||[]).includes(lv.uid)).map(w=>{const os=(w.openings||[]).filter(o=>o.level==lv.uid);
  return {...w,_t:w.curtain||os.some(o=>o.kind=='window')||/наруж|ext/i.test(w.type||'')?'ext':(w.thickness>=180?'bear':'part'),_os:os}});
 const r=ipWallsFrom(M,W,w=>w._os.map(o=>{const a=w.axis[o.seg]||w.axis[0],b=w.axis[o.seg+1]||w.axis[1],L=Math.hypot(b[0]-a[0],b[1]-a[1])||1,n=[-(b[1]-a[1])/L,(b[0]-a[0])/L],f=o.facing||[0,0];
  return {...o,width:o.width||(o.kind=='door'?900:1200),side:(f[0]*n[0]+f[1]*n[1])>0?-1:1}}));return {M,src:'Revit',lv:lv.name,nf:0,...r}}
function ipBuild(R,name){const M=R.M;if(!M.walls.length)return ipAlert(`В «${esc(name)}» нет стен`,'Проверьте выгрузку: нужен уровень с наружными стенами квартиры.');
 if(!ipFit(M))return ipAlert('План больше 50 метров','Похоже, единицы не те. Нужна выгрузка в миллиметрах.');
 const ex=M.walls.filter(w=>w.type=='ext').length,dr=M.ops.filter(o=>o.k=='door').length,wn=M.ops.filter(o=>o.k=='win').length;
 ipDone2(M,`${R.src}${R.lv?' · '+R.lv:''}: стен ${M.walls.length} (наружных ${ex}), дверей ${dr}, окон ${wn}`);
 const notes=[];if(!ex)notes.push('Наружные стены не распознаны — выделите стену и выберите тип «Наружная».');if(R.nf)notes.push(`Мебель из файла (${R.nf}) не перенесена — её расставит генератор.`);if(R.skip)notes.push(`Проёмов без стены: ${R.skip} — пропущены.`);
 if(notes.length)IP.noteT=setTimeout(()=>toast(notes.join(' '),{k:'warn',ms:7000}),2700)}
/* DXF: ASCII, LINE / LWPOLYLINE / POLYLINE. Самая большая замкнутая полилиния — наружная грань: стены 300 мм внутрь. Всё остальное — подложкой */
async function ipDxf(f){ipBusyOn('Разбираем чертёж…');await new Promise(r=>setTimeout(r,30));let txt;try{txt=await f.text()}catch{ipBusyOff();return ipAlert('Файл не читается','Сохраните DXF заново.')}
 if(txt.startsWith('AutoCAD Binary DXF')){ipBusyOff();return ipAlert('Двоичный DXF не читаем','Сохраните чертёж как ASCII DXF (в AutoCAD: Сохранить как → DXF, формат ASCII).')}
 const ln=txt.split(/\r?\n/);let units=0,i=0,sec='',ent=null;const E=[],nIns={n:0};
 const flush=()=>{if(ent&&(ent.t=='LINE'||ent.t=='LWPOLYLINE'||ent.t=='POLYLINE')&&ent.p.length>=2)E.push(ent);ent=null};let poly=null;
 for(;i<ln.length-1;i+=2){const c=ln[i].trim(),v=ln[i+1].trim();
  if(c=='0'){if(v=='SECTION'){sec='';continue}if(v=='VERTEX'&&poly){if(ent&&ent.t=='V'&&ent.p.length)poly.p.push(ent.p[0]);ent={t:'V',p:[]};continue}if(v=='SEQEND'){if(ent&&ent.t=='V'&&ent.p.length)poly.p.push(ent.p[0]);ent=poly;poly=null;flush();continue}
   if(ent&&ent.t=='V'&&poly){if(ent.p.length)poly.p.push(ent.p[0]);ent=null}flush();if(sec!='ENTITIES')continue;if(v=='INSERT')nIns.n++;ent={t:v,p:[],cl:0,cur:[]};if(v=='POLYLINE'){poly=ent;ent=poly;}continue}
  if(c=='2'&&!sec&&ln[i-2]&&ln[i-1].trim()=='SECTION'){sec=v;continue}
  if(sec=='HEADER'&&c=='9'&&v=='$INSUNITS'){units=+ln[i+3].trim();continue}
  if(!ent)continue;const n=parseFloat(v);
  if(ent.t=='LINE'){if(c=='10')ent.p[0]=[n,0];else if(c=='20'&&ent.p[0])ent.p[0][1]=n;else if(c=='11')ent.p[1]=[n,0];else if(c=='21'&&ent.p[1])ent.p[1][1]=n}
  else if(ent.t=='LWPOLYLINE'||ent.t=='V'||ent.t=='POLYLINE'){if(c=='70'&&ent.t!='V')ent.cl=n&1;else if(c=='10'&&!(ent.t=='POLYLINE'))ent.p.push([n,0]);else if(c=='20'&&ent.t!='POLYLINE'&&ent.p.length)ent.p[ent.p.length-1][1]=n}}
 flush();ipBusyOff();
 if(!E.length)return ipAlert('В чертеже нет линий',nIns.n?'План собран из блоков — расчлените их (EXPLODE) и сохраните DXF заново.':'Проверьте, что план начерчен в пространстве модели, а не на листе.');
 let a=1e18,b=1e18,c=-1e18,d=-1e18;E.forEach(e=>e.p.forEach(([x,y])=>{a=Math.min(a,x);b=Math.min(b,y);c=Math.max(c,x);d=Math.max(d,y)}));
 const ext=Math.max(c-a,d-b),U={1:25.4,2:304.8,4:1,5:10,6:1000}[units]||(ext<200?1000:ext<3000?10:1),k=U;
 if(ext*k>120000)return ipAlert('Чертёж больше 120 метров','Оставьте в DXF только план одной квартиры или этажа.');
 if(ext*k<1500)return ipAlert('Чертёж слишком маленький',`Получилось ${nf(ext*k/1000)} м. Проверьте единицы чертежа ($INSUNITS) — нужны миллиметры.`);
 const pa2=pg=>pg.reduce((s,p,i)=>{const q=pg[(i+1)%pg.length];return s+p[0]*q[1]-q[0]*p[1]},0)/2;
 let best=null;E.forEach(e=>{if(e.t=='LINE'||e.p.length<3)return;const pg=e.p.slice();const cl0=e.cl||Math.hypot(pg[0][0]-pg[pg.length-1][0],pg[0][1]-pg[pg.length-1][1])<1e-6;if(!cl0)return;if(Math.hypot(pg[0][0]-pg[pg.length-1][0],pg[0][1]-pg[pg.length-1][1])<1e-6)pg.pop();
  const A=Math.abs(pa2(pg))*k*k/1e6;if(A>=10&&A<=3000&&(!best||A>best.A))best={pg,A}});
 /* подложка: все линии, в тех же координатах */
 const sc=1/MM*k,W0=(c-a)*sc,H0=(d-b)*sc,px=4,cw=Math.min(4000,Math.max(800,W0*px)),f2s=cw/W0;
 const cv=document.createElement('canvas');cv.width=Math.ceil(W0*f2s);cv.height=Math.ceil(H0*f2s);const g=cv.getContext('2d');g.strokeStyle='#1d4ed8';g.lineWidth=1.2;g.beginPath();
 E.forEach(e=>{e.p.forEach(([x,y],j)=>{const X2=(x-a)*sc*f2s,Y2=(d-y)*sc*f2s;j?g.lineTo(X2,Y2):g.moveTo(X2,Y2)});if(e.cl&&e.p.length>2)g.closePath()});g.stroke();
 const M=ipBlank();M.ul={url:cv.toDataURL('image/png'),x:a*sc,y:-d*sc,w:W0,h:H0,op:.45,cal:1};
 if(best){let pg=best.pg.map(([x,y])=>[x*k,y*k]);if(pa2(pg)<0)pg.reverse();pg=pg.filter((p,i)=>{const q=pg[(i+1)%pg.length];return Math.hypot(q[0]-p[0],q[1]-p[1])>20});
  const t=300,h=t/2,L=pg.map((p,i)=>{const q=pg[(i+1)%pg.length],l=Math.hypot(q[0]-p[0],q[1]-p[1]),u=[(q[0]-p[0])/l,(q[1]-p[1])/l],n=[-u[1],u[0]];return {p:[p[0]+n[0]*h,p[1]+n[1]*h],u}});
  const V2=L.map((l,i)=>{const m=L[(i+L.length-1)%L.length],P=xLine(m.p,m.u,l.p,l.u);return P||l.p});
  V2.forEach((p,i)=>{const q=V2[(i+1)%V2.length];M.walls.push({id:nid(M,'w'),x1:p[0]/MM,y1:-p[1]/MM,x2:q[0]/MM,y2:-q[1]/MM,t:t/MM,type:'ext',fixed:1})})}
 if(!ipFit(M))return ipAlert('Чертёж больше 50 метров','Оставьте в DXF только план квартиры.');
 if(best){ipDone2(M,`Контур из DXF: ${nf(best.A)} м² по внешней линии, стены 300 мм внутрь. Сверьте с подложкой`)}
 else{ipDone2(M,'');edStart();pickTool('wall');ED.wt='ext';ED.wth=300;renderProps();toast('Замкнутый контур не нашёлся — чертёж лёг подложкой. Обведите наружные стены',{k:'warn',ms:6000})}}
/* PDF или картинка → подложка 50 %, затем масштаб */
let pdfLib=null;function ipPdfLib(){if(pdfLib)return pdfLib;pdfLib=new Promise((ok,no)=>{const s=document.createElement('script');s.src='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
 s.onload=()=>{window.pdfjsLib.GlobalWorkerOptions.workerSrc='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';ok(window.pdfjsLib)};s.onerror=()=>{pdfLib=null;no(new Error('lib'))};document.head.appendChild(s)});return pdfLib}
async function ipUnder(f,isPdf){if(CM&&CM.ul&&contour)return ipConfirm('Заменить подложку?','Новая картинка встанет вместо текущей. Масштаб нужно будет задать заново.','Заменить',()=>ipUnder2(f,isPdf));ipUnder2(f,isPdf)}
async function ipUnder2(f,isPdf){let url,iw,ih;try{
 if(isPdf){ipBusyOn('Загружаем модуль PDF…');const lib=await ipPdfLib();ipBusyOn('Открываем PDF…');let doc;
  try{doc=await lib.getDocument({data:new Uint8Array(await f.arrayBuffer())}).promise}catch(e){ipBusyOff();return e&&e.name=='PasswordException'?ipAlert('PDF защищён паролем','Снимите пароль или экспортируйте лист в PNG.'):ipAlert('PDF не открывается','Файл повреждён. Сохраните лист заново или как PNG.')}
  let pn=1;if(doc.numPages>1){ipBusyOff();pn=await new Promise(res=>{ipModal(`${mHead('Какую страницу взять?')}<div class="mb"><p class="lead" style="margin-bottom:12px">В PDF ${doc.numPages} стр. Подложкой ляжет одна.</p><div class="pgs">${Array.from({length:Math.min(doc.numPages,40)},(_,i)=>`<button data-p="${i+1}">${i+1}</button>`).join('')}</div></div>`,{onClose:()=>res(0)});$$('#expbox .pgs button').forEach(b=>b.onclick=()=>{const p=+b.dataset.p;IP.modal=null;$('#exp').classList.remove('on');res(p)})});if(!pn)return}
  ipBusyOn('Рисуем страницу…');const pg=await doc.getPage(pn),v0=pg.getViewport({scale:1}),s=Math.min(4,2600/Math.max(v0.width,v0.height)),vp=pg.getViewport({scale:s}),cv=document.createElement('canvas');cv.width=vp.width;cv.height=vp.height;
  const g=cv.getContext('2d');g.fillStyle='#fff';g.fillRect(0,0,cv.width,cv.height);await pg.render({canvasContext:g,viewport:vp}).promise;url=cv.toDataURL('image/jpeg',.82);iw=cv.width;ih=cv.height}
 else{ipBusyOn('Открываем картинку…');const bm=await createImageBitmap(f).catch(()=>null);if(!bm){ipBusyOff();return ipAlert('Картинка не открывается','Сохраните её как PNG или JPG.')}
  const s=Math.min(1,2600/Math.max(bm.width,bm.height)),cv=document.createElement('canvas');cv.width=Math.round(bm.width*s);cv.height=Math.round(bm.height*s);const g=cv.getContext('2d');g.fillStyle='#fff';g.fillRect(0,0,cv.width,cv.height);g.drawImage(bm,0,0,cv.width,cv.height);
  url=cv.toDataURL('image/jpeg',.85);iw=cv.width;ih=cv.height;if(Math.max(bm.width,bm.height)<600)setTimeout(()=>toast('Картинка мелкая — линии будут размыты, лучше взять PDF или скан крупнее',{k:'warn'}),2800)}}
 catch(e){ipBusyOff();return ipAlert(e&&e.message=='lib'?'Модуль PDF не загрузился':'Не получилось открыть файл',e&&e.message=='lib'?'Нужен интернет для чтения PDF. Можно сохранить лист как PNG и загрузить картинку.':'Попробуйте другой файл или формат.')}
 ipBusyOff();const fresh=!contour||!CM;const M=fresh?ipBlank():CM;const w=M.W*.8,h=w*ih/iw,k=Math.min(1,M.H*.8/h);
 const ul={url,x:(M.W-w*k)/2,y:(M.H-h*k)/2,w:w*k,h:h*k,op:.5,cal:0,name:f.name};
 if(fresh){M.ul=ul;ipDone2(M,'');edStart()}else{if(sel||refOn)showContour();mut(M=>{M.ul=ul},0)}pickTool('ruler');
 toast('Подложка на месте. Задайте масштаб: два клика по отрезку известной длины',{ms:6000})}

/* ---------- сохранение в браузере ---------- */
function ipSaveSt(s,t){const b=$('#save');IP.saveSt=s;b.className='badge '+(s=='err'?'err':s=='ro'?'ro':'b-n');b.style.display='';
 b.innerHTML=s=='ing'?'<span class="i spin">progress_activity</span>Сохранение…':s=='ok'?'<span class="i">cloud_done</span>Сохранено в браузере':s=='ro'?'<span class="i">visibility</span>Пример · не сохраняется':s=='err'?`<span class="i">error</span>${t||'Не сохранено'}`:'';
 b.title=s=='ok'?'Файл хранится в этом браузере на этом компьютере':s=='err'?'Нажмите, чтобы попробовать ещё раз':'';b.onclick=s=='err'?ipSaveNow:s=='ro'?ipSaveCopy:null;if(s=='ro')b.innerHTML+=' · <u>сохранить копию</u>';b.style.cursor=s=='err'||s=='ro'?'pointer':''}
saved=function(){if(!$('#s-ws').classList.contains('on'))return;if(IP.ro){ipSaveSt('ro');return}if(!IP.pid&&!ipHas(CM))return;ipSaveSt('ing');clearTimeout(IP.saveT);IP.saveT=setTimeout(ipSaveNow,500)};
function ipRec(){return {id:IP.pid,name:$('#fn').textContent.trim()||'Без названия',upd:Date.now(),M:cl(CM),run,cv:IP.cv,tz:$('#tz').value,type:curType,
 V:V.map(v=>({id:v.id,run:v.run,q:v.q,seed:v.seed,type:v.type,err:v.err,warn:v.warn,vote:v.vote,ver:v.ver,from:v.from,cv:v.cv,M:cl(v.M)}))}}
function ipSaveNow(){clearTimeout(IP.saveT);IP.saveT=0;if(IP.ro||!CM)return;if(!IP.pid)IP.pid='p'+Date.now().toString(36);const d=ipLS.get(),r=ipRec();
 const put=rec=>{const i=d.projects.findIndex(p=>p.id==rec.id);if(i>=0)d.projects[i]=rec;else d.projects.unshift(rec);ipLS.set(d)};
 try{put(r);ipSaveSt('ok')}catch(e){if(r.M.ul){try{const r2={...r,M:{...r.M,ul:{...r.M.ul,url:''}}};put(r2);ipSaveSt('ok');toast('Подложка слишком большая для браузера — сохранён только контур',{k:'warn',ms:6000});return}catch{}}
  ipSaveSt('err','Не сохранено: мало места');toast('В браузере кончилось место. Удалите старые файлы в «Мои планировки»',{k:'err',act:'Открыть',fn:()=>go('projects')})}}
function ipSaveCopy(){IP.ro=0;IP.pid=null;$('#fn').textContent=$('#fn').textContent.replace(/^Пример · /,'')+' · копия';ipSaveNow();toast('Копия сохранена — это ваш файл, правьте свободно')}
window.addEventListener('beforeunload',e=>{if(IP.saveT){ipSaveNow()}if(IP.busy){e.preventDefault();e.returnValue=''}});
function ipOpen(id){const p=ipLS.get().projects.find(x=>x.id==id);if(!p)return toast('Файл не найден — возможно, его удалили в другой вкладке',{k:'err'});
 openWs(true);IP.pid=id;IP.ro=0;$('#fn').textContent=p.name;$('#tz').value=p.tz||'';if(p.type){curType=p.type;$$('#typeseg button').forEach(b=>b.classList.toggle('on',b.getAttribute('onclick').includes(`'${p.type}'`)))}
 const M=p.M;M.gv=1;M.seq=M.seq||900;if(M.ul&&!M.ul.url){delete M.ul;setTimeout(()=>toast('Подложка не сохранилась — загрузите её снова',{k:'warn'}),600)}
 CM=M;contour=ipHas(M);run=p.run||0;IP.cv=p.cv||1;V=(p.V||[]).map(v=>{v.M.gv=1;syncR(v);return v});
 if(contour){IP.wasClosed=ipCheck(M).closed;ipShowStage()}
 if(V.length){setGen('auto_awesome','Создать ещё');renderList();showVar(V[0].id)}else renderList();ipGate();ipSaveSt('ok')}

/* ---------- экраны: вход, список файлов, шапка ---------- */
const _ipGo=go;go=function(id){if(id!='ws'&&$('#s-ws').classList.contains('on')){if(IP.busy){const r=IP.busy;return ipConfirm('Остановить запуск?','Пока идёт генерация, файл лучше не закрывать. Если выйти, запуск остановится, а за неготовые варианты токены не спишутся.','Остановить и выйти',()=>{ipStop(r);go(id)},{cancel:'Остаться'})}
  if(IP.saveT)ipSaveNow();if(ED.on)edDone()}ipMenuClose();_ipGo(id);if(id=='projects')ipGrid()};
const ago=t=>{const s=(Date.now()-t)/1000;return s<60?'только что':s<3600?Math.floor(s/60)+' мин назад':s<86400?Math.floor(s/3600)+' ч назад':s<172800?'вчера':new Date(t).toLocaleDateString('ru-RU',{day:'numeric',month:'short'})};
const EXM=[['Пример · кв. 28','3к · 106,21 м² · 4 варианта','v3']];
function ipGrid(){const P=ipLS.get().projects.sort((a,b)=>b.upd-a.upd),w=$('#s-projects .wrap');
 w.innerHTML=`<div style="display:flex;align-items:flex-end;gap:16px;flex-wrap:wrap"><div style="flex:1;min-width:240px"><h1>Мои планировки</h1><p class="lead">Один файл — одна квартира и все варианты её планировки. Файлы хранятся в этом браузере</p></div><button class="btn pri lg" onclick="openWs(true)"><span class="i">add</span>Новый файл</button></div>
 <div class="grid" id="pgrid"><button class="card pnew" onclick="openWs(true)"><span class="i">add_circle</span>Новый файл<span style="font-size:12px;font-weight:400">Нарисовать контур или загрузить план</span></button>${P.map(p=>{let th='';try{th=ipHas(p.M)?(p.V&&p.V[0]?msvg(Object.assign(p.V[0].M,{gv:1}),{label:false,thumb:1}):ipThumb(p.M)):''}catch{th=''}
  return `<div class="card pcard" onclick="ipOpen('${p.id}')"><div class="th">${th||'<div class="ph"><span class="i">draft</span>Контур не начат</div>'}</div><div class="bd"><b>${esc(p.name)}</b><div class="meta"><span>${(p.V||[]).length?(p.V.length+' '+(p.V.length%10==1&&p.V.length%100!=11?'вариант':p.V.length%10>=2&&p.V.length%10<=4&&(p.V.length%100<10||p.V.length%100>=20)?'варианта':'вариантов')):'без вариантов'}</span><span>${ago(p.upd)}</span></div></div><button class="ib more" title="Ещё" onclick="event.stopPropagation();ipCardMenu(event,'${p.id}')"><span class="i">more_horiz</span></button></div>`}).join('')}</div>
 ${P.length?'':'<p class="lead" style="margin-top:14px;font-size:13px">Своих файлов пока нет. Начните с нового или посмотрите пример ниже.</p>'}
 <div class="sec-h"><h2>Примеры бюро</h2><span>Открываются только для просмотра — изменения не сохраняются</span></div>
 <div class="grid" style="margin-top:16px">${EXM.map(([n,m,l])=>`<div class="card pcard" onclick="openWs(false,'${n}')"><div class="th">${svg(rhPlan(l),{label:false})}</div><div class="bd"><b>${n}</b><div class="meta"><span>${m}</span><span>пример</span></div></div></div>`).join('')}</div>`}
function ipThumb(M){M.gv=1;let s=msvg(M,{label:false,thumb:1,exp:1});if(!M.walls.length)return s;let a=1e9,b=1e9,c=-1e9,d=-1e9;M.walls.forEach(w=>{a=Math.min(a,w.x1,w.x2);b=Math.min(b,w.y1,w.y2);c=Math.max(c,w.x1,w.x2);d=Math.max(d,w.y1,w.y2)});const m=30;
 return s.replace(/viewBox="[^"]*"/,`viewBox="${a-m} ${b-m} ${c-a+2*m} ${d-b+2*m}"`)}
function ipMenuClose(){if(IP.menu){IP.menu.remove();IP.menu=null}}
function ipMenu(e,items){ipMenuClose();const m=document.createElement('div');m.className='ipmenu';m.innerHTML=items.map((it,i)=>it.who?`<div class="who">${it.who}</div>`:`<button data-i="${i}" class="${it.dng?'dng':''}"><span class="i">${it.ic}</span>${it.t}</button>`).join('');
 document.body.appendChild(m);const r=e.currentTarget.getBoundingClientRect();m.style.top=Math.min(innerHeight-m.offsetHeight-8,r.bottom+6)+'px';m.style.left=Math.max(8,Math.min(innerWidth-m.offsetWidth-8,r.right-m.offsetWidth))+'px';
 m.querySelectorAll('button').forEach(b=>b.onclick=()=>{ipMenuClose();items[+b.dataset.i].fn()});IP.menu=m}
document.addEventListener('pointerdown',e=>{if(IP.menu&&!IP.menu.contains(e.target)&&!e.target.closest('.more,.avatar'))ipMenuClose()});
function ipCardMenu(e,id){ipMenu(e,[{ic:'edit',t:'Переименовать',fn:()=>ipRename(id)},{ic:'content_copy',t:'Сделать копию',fn:()=>{const d=ipLS.get(),p=d.projects.find(x=>x.id==id);if(!p)return;
 try{d.projects.unshift({...JSON.parse(JSON.stringify(p)),id:'p'+Date.now().toString(36),name:p.name+' · копия',upd:Date.now()});ipLS.set(d);ipGrid();toast('Копия готова')}catch{toast('Не хватает места в браузере для копии',{k:'err'})}}},
 {ic:'delete',t:'Удалить',dng:1,fn:()=>{const d=ipLS.get(),i=d.projects.findIndex(x=>x.id==id);if(i<0)return;const [p]=d.projects.splice(i,1);ipLS.set(d);ipGrid();
  toast(`«${p.name}» удалён`,{icon:'delete',act:'Вернуть',fn:()=>{const d2=ipLS.get();d2.projects.splice(i,0,p);ipLS.set(d2);ipGrid()}})}}])}
function ipRename(id){const d=ipLS.get(),p=d.projects.find(x=>x.id==id);if(!p)return;
 ipModal(`${mHead('Название файла')}<div class="mb"><input class="inp" id="rnm" maxlength="80" value="${esc(p.name)}" autofocus><div class="ferr" id="rnerr"></div></div><div class="mf"><button class="btn" onclick="ipClose()">Отмена</button><button class="btn pri" id="rnok">Сохранить</button></div>`);
 setTimeout(()=>$('#rnm').select(),40);$('#rnok').onclick=()=>{const v=$('#rnm').value.trim();if(!v){$('#rnerr').textContent='Название не может быть пустым';$('#rnm').classList.add('bad');return}p.name=v;p.upd=Date.now();ipLS.set(d);ipClose();ipGrid()}}
/* шапка рабочего поля: имя файла правится по клику, крошка ведёт в список */
$('.fname').innerHTML=`<span class="crumb" onclick="go('projects')">Мои планировки</span><span class="i" style="font-size:16px">chevron_right</span><b id="fn" title="Переименовать">Без названия</b>`;
$('#fn').addEventListener('click',()=>{if(IP.ro)return toast('Пример не переименовать — сохраните копию',{k:'warn',act:'Сохранить копию',fn:ipSaveCopy});const b=$('#fn'),old=b.textContent,i=document.createElement('input');i.value=old;i.maxLength=80;b.replaceWith(i);i.focus();i.select();
 const done=ok=>{if(!i.isConnected)return;const v=i.value.trim();b.textContent=ok&&v?v:old;i.replaceWith(b);if(ok&&!v)toast('Название не может быть пустым — оставили прежнее',{k:'warn'});if(ok&&v&&v!=old){if(!IP.pid&&!ipHas(CM))toast('Название сохранится вместе с контуром');saved()}};
 i.addEventListener('keydown',e=>{if(e.key=='Enter')done(1);if(e.key=='Escape'){e.stopPropagation();done(0)}});i.addEventListener('blur',()=>done(1))});
const _ipOpenWs=openWs;openWs=function(fresh,name){_ipOpenWs(fresh,name);IP.pid=null;IP.ro=fresh?0:1;$('#save').style.display='none';if(!fresh){IP.cv=1;V.forEach(v=>v.cv=1);ipSaveSt('ro');renderList()}ipTag();ipSteps();ipGate();$('#tz').value=fresh?'':$('#tz').value};
/* вход */
(()=>{const L=$('.login-box'),inps=L.querySelectorAll('.inp');inps[0].id='lem';inps[1].id='lpw';inps[1].value='';inps[1].placeholder='Пароль от рабочей почты';
 inps.forEach(i=>i.insertAdjacentHTML('afterend','<div class="ferr"></div>'));L.querySelector('.btn.pri').setAttribute('onclick','ipLogin()');L.querySelector('.btn.pri').id='lbtn';
 L.querySelector('.btn.pri').insertAdjacentHTML('afterend','<p class="lead" style="font-size:12px;margin-top:14px">Нет доступа? Напишите администратору IND PLAN в бюро.</p>');
 L.addEventListener('keydown',e=>{if(e.key=='Enter')ipLogin()});inps.forEach(i=>i.addEventListener('input',()=>{i.classList.remove('bad');i.nextElementSibling.textContent=''}))})();
function ipLogin(){const em=$('#lem'),pw=$('#lpw'),b=$('#lbtn');let ok=1;const bad=(i,t)=>{i.classList.add('bad');i.nextElementSibling.textContent=t;ok=0};
 if(!em.value.trim())bad(em,'Введите почту');else if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em.value.trim()))bad(em,'Похоже, в почте опечатка');
 if(!pw.value)bad(pw,'Введите пароль');else if(pw.value.length<4)bad(pw,'Неверная почта или пароль');if(!ok)return;
 if(!navigator.onLine)return bad(pw,'Нет сети — проверьте подключение');
 b.disabled=1;b.innerHTML='<span class="i spin">progress_activity</span>Входим…';setTimeout(()=>{b.disabled=0;b.innerHTML='Войти<span class="i">arrow_forward</span>';try{localStorage.setItem(LSU,em.value.trim())}catch{}ipAva();go('projects')},700)}
function ipAva(){let u='';try{u=localStorage.getItem(LSU)||''}catch{}const ini=(u.split('@')[0].split(/[._-]/).map(s=>s[0]||'').join('').slice(0,2)||'ИН').toUpperCase();
 $$('.avatar').forEach(a=>{a.textContent=ini;a.style.cursor='pointer';a.title=u;a.onclick=e=>ipMenu(e,[{who:esc(u||'Гость')},{ic:'help',t:'Как это работает',fn:ipHelp},{ic:'logout',t:'Выйти',fn:()=>{try{localStorage.removeItem(LSU)}catch{}go('login')}}])})}
function ipHelp(){ipModal(`${mHead('Как это работает')}<div class="mb"><div class="opt3" style="pointer-events:none">
 <button><span class="i">draw</span><div><b>1. Контур</b><small>Нарисуйте наружные стены, поставьте вход, окна и стояк — или загрузите план из Revit, DXF, PDF</small></div></button>
 <button><span class="i">tune</span><div><b>2. Параметры</b><small>Слева — класс, тип квартиры, помещения и ТЗ своими словами</small></div></button>
 <button><span class="i">auto_awesome</span><div><b>3. Варианты</b><small>Генератор предложит планировки. Нравится, мимо, внести изменения — всё учитывается</small></div></button>
 <button><span class="i">ios_share</span><div><b>4. Правка и экспорт</b><small>Доведите вариант в редакторе и выгрузите в Revit (.json), SVG, PNG или PDF</small></div></button></div>
 <p class="lbl" style="margin:16px 0 8px">Клавиши</p><div class="keys"><span><kbd>W</kbd>стена</span><span><kbd>D</kbd>дверь</span><span><kbd>O</kbd>окно</span><span><kbd>S</kbd>стояк</span><span><kbd>F</kbd>мебель</span><span><kbd>R</kbd>помещение</span><span><kbd>Esc</kbd>закончить</span><span><kbd>Ctrl Z</kbd>отменить</span></div></div><div class="mf"><button class="btn pri" onclick="ipClose()">Понятно</button></div>`)}
$('#s-projects .top .ib').onclick=ipHelp;

/* ---------- экспорт: JSON для Revit, SVG, PNG, PDF через печать ---------- */
function ipToJson(M){const o0=M.off||[0,0],X2=x=>Math.round((x-o0[0])*MM),Y2=y=>-Math.round((y-o0[1])*MM);
 const walls=M.walls.map(w=>{const G=wgeo(w);return {id:w.id,type:{ext:'exterior',bear:'bearing',part:'partition'}[w.type]||'partition',thickness:Math.round(w.t*MM),axis:[[X2(w.x1),Y2(w.y1)],[X2(w.x2),Y2(w.y2)]],closed:false,
  openings:M.ops.filter(o=>(o.wall==w.id||o.cw&&o.cw.w2==w.id)&&(o.k=='door'||o.k=='win')).map(o=>{const at=P=>Math.round(((P[0]-w.x1)*G.ux+(P[1]-w.y1)*G.uy)*MM);
   if(o.cw){const c=o.cw,on1=o.wall==w.id,L=on1?c.L1:c.L2;return {id:o.id+(on1?'':'-2'),kind:'window',corner:o.id,seg:0,at:at(pa(c.I,on1?c.d1:c.d2,L/2)),width:Math.round(L*MM)}} // угловое окно — две части, по одной на каждой стене
   return {id:o.id,kind:o.k=='door'?'door':'window',seg:0,at:at([o.x,o.y]),width:Math.round(o.w*MM),...(o.k=='door'?{hinge:o.h=='e'?'end':'start',side:o.side}:{})}})}});
 const K2=calcRooms(M);return {format:'ind-plan',version:2,units:'mm',source:'ind-plan-mvp',walls,risers:M.risers.map(r=>({type:r.type,d:r.d,at:[X2(r.x),Y2(r.y)]})),
  rooms:K2.regs.map(R=>{const l=M.rooms[R.main];return {name:l.n,seed:[X2(l.x),Y2(l.y)],area:R.a}}),...(M.fixed?{note:'Наружный контур — из модели Rhino, в JSON не входит'}:{})}}
function ipSvgDoc(M){let s=msvg(M,{area:1,exp:1,label:true});const css=getComputedStyle(document.documentElement);s=s.replace(/var\((--[\w-]+)\)/g,(m,n)=>css.getPropertyValue(n).trim()||'#000');
 const ids=new Set(),q=[...s.matchAll(/href="#([^"]+)"/g)].map(m=>m[1]);let defs='';while(q.length){const id=q.pop();if(ids.has(id))continue;ids.add(id);const el=document.getElementById(id);if(!el)continue;const h=el.outerHTML;defs+=h;[...h.matchAll(/href="#([^"]+)"/g)].forEach(m=>q.push(m[1]))}
 const [,,w,h]=M.vb.split(' ').map(Number);s=s.replace(' width="100%"','');return s.replace(/^<svg /,`<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${Math.round(w*2)}" height="${Math.round(h*2)}" `).replace('data-m="1">',`data-m="1"><defs>${defs}</defs><rect x="-20" y="-20" width="${w+40}" height="${h+40}" fill="#fff"/>`)}
const ipDl=(name,blob)=>{const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;document.body.appendChild(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove()},1500)};
openExp=function(){if(ED.on)edDone();const v=sel,M=v?v.M:(contour&&ipHas(CM)?CM:null);if(!M)return toast('Экспортировать пока нечего — нарисуйте контур',{k:'warn'});
 const t=v?`Вариант ${v.id}${v.ver>1?' · v'+v.ver:''}`:'Контур квартиры';IP.exM=M;IP.exT=t;
 ipModal(`${mHead('Экспорт · '+t)}<div class="mb"><div class="card" style="padding:14px 24px;margin-bottom:16px;background:var(--sub)">${msvg(M,{area:1,label:true,exp:1})}</div>
 <div class="fmt"><label><input type="checkbox" data-f="json" checked><div><b>JSON</b><small>Для Revit · граф «IND PLAN - транзит»</small></div></label><label><input type="checkbox" data-f="svg" checked><div><b>SVG</b><small>Для Illustrator · векторный план</small></div></label>
 <label><input type="checkbox" data-f="png"><div><b>PNG</b><small>Картинка в 2×, белый фон</small></div></label><label><input type="checkbox" data-f="pdf"><div><b>PDF</b><small>Откроется окно печати → «Сохранить как PDF»</small></div></label></div>
 ${M.fixed?'<p class="hintp" style="margin-top:10px">Наружный контур этого примера взят из Rhino — в JSON попадут только перегородки, проёмы и помещения.</p>':''}<div class="ferr" id="experr"></div></div>
 <div class="mf"><button class="btn" onclick="ipClose()">Отмена</button><button class="btn pri" id="expgo"><span class="i">download</span>Скачать</button></div>`);
 $$('#expbox .fmt input').forEach(i=>i.onchange=()=>{const n=$$('#expbox .fmt input:checked').length;$('#expgo').disabled=!n;$('#experr').textContent=n?'':'Выберите хотя бы один формат'});$('#expgo').onclick=ipExport};
async function ipExport(){const F=[...$$('#expbox .fmt input:checked')].map(i=>i.dataset.f),M=IP.exM,b=$('#expgo'),base=($('#fn').textContent.trim()+' · '+IP.exT).replace(/[\\/:*?"<>|]+/g,' ').slice(0,90);
 b.disabled=1;b.innerHTML='<span class="i spin">progress_activity</span>Собираем…';const got=[],bad=[];
 for(const f of F){try{if(f=='json')ipDl(base+'.json',new Blob([JSON.stringify(ipToJson(M),null,1)],{type:'application/json'}));
  if(f=='svg')ipDl(base+'.svg',new Blob([ipSvgDoc(M)],{type:'image/svg+xml'}));
  if(f=='png'){const u=URL.createObjectURL(new Blob([ipSvgDoc(M)],{type:'image/svg+xml'})),im=new Image();await new Promise((ok,no)=>{im.onload=ok;im.onerror=no;im.src=u});
   const c=document.createElement('canvas');c.width=im.width*2;c.height=im.height*2;const g=c.getContext('2d');g.fillStyle='#fff';g.fillRect(0,0,c.width,c.height);g.drawImage(im,0,0,c.width,c.height);URL.revokeObjectURL(u);
   await new Promise(ok=>c.toBlob(bl=>{ipDl(base+'.png',bl);ok()},'image/png'))}
  if(f=='pdf'){const w=window.open('','_blank');if(!w)throw new Error('popup');w.document.write(`<!doctype html><title>${esc(base)}</title><style>@page{size:A3 landscape;margin:12mm}body{margin:0;font:12px Inter,sans-serif}h1{font-size:14px;margin:0 0 8mm}svg{width:100%;height:auto;max-height:240mm}</style><h1>${esc(base)}</h1>${ipSvgDoc(M)}<script>onload=()=>setTimeout(()=>print(),200)<\/script>`);w.document.close()}
  got.push(f.toUpperCase());await new Promise(r=>setTimeout(r,250))}catch(e){bad.push(f=='pdf'&&e.message=='popup'?'PDF — браузер заблокировал окно печати, разрешите всплывающие окна':f.toUpperCase())}}
 if(!got.length){b.disabled=0;b.innerHTML='<span class="i">download</span>Скачать';$('#experr').textContent='Не получилось: '+bad.join(', ');return}
 ipModal(`<div class="mb" style="text-align:center;padding:32px 24px 8px"><div class="done-ic"><span class="i">check</span></div><h2 style="font-size:20px">Готово</h2><p class="lead" style="margin-top:6px">${esc(base)} · ${got.join(', ')}</p>${bad.length?`<p class="ferr" style="margin-top:10px">Не вышло: ${esc(bad.join(', '))}</p>`:''}<p class="lead" style="font-size:12px;margin-top:10px">Файлы — в папке загрузок браузера</p></div><div class="mf" style="justify-content:center"><button class="btn pri" onclick="ipClose()">Вернуться к работе</button></div>`)}
$('#expbtn').setAttribute('onclick','openExp()');

/* ---------- старт ---------- */
$('#gempty').innerHTML='<span class="i">dashboard_customize</span><b style="color:var(--text)">Здесь появятся варианты</b>Нарисуйте контур квартиры и нажмите «Создать планировку». Один запуск — до 8 вариантов';
document.title='IND PLAN';ipAva();ipTok();
try{if(localStorage.getItem(LSU))go('projects')}catch{}

/* ---------- 2026-11-18: выделение стены заливкой, имя проекта над листом, угловые окна на стенах, лист растёт под стены ---------- */
document.head.insertAdjacentHTML('beforeend',`<style>
.sheet .tag{white-space:nowrap;top:-30px}
.ipname{display:inline-flex;align-items:center;gap:4px;border:0;background:none;padding:3px 6px;margin:-3px -2px -3px -6px;border-radius:6px;font:inherit;font-size:13px;font-weight:600;color:var(--text);cursor:text;max-width:420px;transition:background .15s}
.ipname .t{overflow:hidden;text-overflow:ellipsis}.ipname .i{font-size:14px;color:var(--faint);opacity:0;transition:opacity .15s}
.ipname:hover,.ipname:focus-visible{background:var(--sub);outline:0}.ipname:hover .i,.ipname:focus-visible .i{opacity:1}
.ipname-in{font:inherit;font-size:13px;font-weight:600;color:var(--text);border:1px solid var(--acc);border-radius:6px;padding:2px 6px;margin:-3px -2px -3px -7px;outline:0;background:var(--panel);width:280px;box-shadow:0 0 0 3px var(--acc-soft)}
.stage.ipwall{cursor:crosshair}
</style>`);

/* имя проекта над листом: оно же в шапке, в заголовках запусков и в именах файлов экспорта */
ipTag=function(){if(!contour||sel||refOn||!CM)return;const c=ipCheck(CM),n=$('#fn').textContent.trim()||'Без названия';
 $('#sheettag').innerHTML=`<button class="ipname" onclick="ipNameEdit()" title="${IP.ro?'Пример — чтобы переименовать, сохраните копию':'Название проекта — им подписаны запуски и файлы экспорта'}"><span class="t">${esc(n)}</span><span class="i">edit</span></button><span>·</span><span>${c.closed?`${ipDims(CM)} · ${nf(c.area,CM.fixed?2:1)} м²`:ipHas(CM)?'контур не замкнут':'контур не нарисован'}${IP.ro?' · пример':''}</span>`};
function ipNameEdit(){if(IP.ro)return toast('Пример не переименовать — сохраните копию',{k:'warn',act:'Сохранить копию',fn:ipSaveCopy});const b=$('#sheettag .ipname');if(!b)return;
 const old=$('#fn').textContent.trim(),i=document.createElement('input');i.className='ipname-in';i.value=old=='Без названия'?'':old;i.placeholder='Например, ЖК Сад · кв. 14';i.maxLength=80;b.replaceWith(i);i.focus();i.select();
 let fin=0;const done=ok=>{if(fin||!i.isConnected)return;fin=1;const v=i.value.trim();i.remove();if(ok&&v&&v!=old){$('#fn').textContent=v;saved();toast('Проект переименован',{icon:'check'})}ipTag()};
 i.addEventListener('keydown',e=>{e.stopPropagation();if(e.key=='Enter')done(1);if(e.key=='Escape')done(0)});i.addEventListener('blur',()=>done(1))}
new MutationObserver(()=>ipTag()).observe($('#fn'),{childList:true,characterData:true,subtree:true});

/* выделение: стена целиком синяя, без обводки (обводка с non-scaling-stroke кривила углы); проём — перекрашен в акцент */
const ipOpSel=(o,f)=>`<g style="pointer-events:none"${f<1?` opacity="${f}"`:''}>${opG(o).split(EC.win).join('var(--acc)').split(EC.door).join('var(--acc)').replace(/fill="#fff"/g,'fill="var(--acc-soft)"').split(`fill="${EC.floor}"`).join('fill="var(--acc-soft)"')}</g>`;
const _ipOutl=elOutline;elOutline=function(M,h,dash){if(!h)return '';
 if(h.t=='wall'){const w=M.walls.find(x=>x.id==h.id);if(!w)return '';const wp=wallPolys(M).filter(x=>x.w===w).pop();if(!wp)return '';const s=ED.s||1;
  return `<path d="${polyD(wp.pts)}" fill="var(--acc)" ${dash?'fill-opacity=".45"':'stroke="var(--acc)" stroke-width=".25" stroke-linejoin="round"'} style="pointer-events:none"/>`+
   M.ops.filter(o=>o.wall==w.id||o.cw&&o.cw.w2==w.id).map(o=>`<g style="pointer-events:none">${opG(o)}</g>`).join('')+
   (dash?'':[[w.x1,w.y1],[w.x2,w.y2]].map(([x,y])=>`<circle cx="${x}" cy="${y}" r="${4*s}" fill="#fff" stroke="var(--acc)" stroke-width="1.5" vector-effect="non-scaling-stroke"/>`).join(''))}
 if(h.t=='op'){const o=M.ops.find(x=>x.id==h.id);return o?ipOpSel(o,dash?.6:1):''}
 return _ipOutl(M,h,dash)};

/* ---- проёмы в нарисованных стенах: только в свободной части грани (не заезжают в угол), окно у угла заворачивает на соседнюю стену ---- */
function ipWG(M,w){const G=wgeo(w),u=[G.ux,G.uy],n=[-u[1],u[0]],wp=wallPolys(M).filter(x=>x.w===w).pop(),P=wp&&wp.pts.length==4?wp.pts:null;
 if(!P)return {G,u,n,P:null,a:0,b:G.len};const s=Q=>(Q[0]-w.x1)*u[0]+(Q[1]-w.y1)*u[1];return {G,u,n,P,a:Math.max(s(P[0]),s(P[3])),b:Math.min(s(P[1]),s(P[2]))}}
/* сколько свободно вдоль стены x от точки I в сторону d: до ближайшего другого проёма */
function ipFree(M,x,I,d,ex){let m=1e9;M.ops.forEach(o=>{if(o.id==ex||!(o.wall==x.id||o.cw&&o.cw.w2==x.id))return;let t=1e9;opPts(o).forEach(P=>{t=Math.min(t,(P[0]-I[0])*d[0]+(P[1]-I[1])*d[1])});m=Math.min(m,Math.max(0,t))});return m}
/* угол на конце end стены w: ровно одна соседняя наружная стена, комната внутри угла */
function ipCorner(M,w,end,ex){if(w.type=='part')return null;const N=end==1?[w.x1,w.y1]:[w.x2,w.y2],vs=M.walls.filter(v=>v!==w&&[1,2].some(j=>Math.hypot(v['x'+j]-N[0],v['y'+j]-N[1])<1));
 if(vs.length!=1||vs[0].type=='part')return null;const v=vs[0],j=Math.hypot(v.x1-N[0],v.y1-N[1])<1?1:2,F=j==1?[v.x2,v.y2]:[v.x1,v.y1],Lv=Math.hypot(F[0]-N[0],F[1]-N[1]);if(Lv<1)return null;
 const d2=[(F[0]-N[0])/Lv,(F[1]-N[1])/Lv],A=ipWG(M,w),B=ipWG(M,v);if(!A.P||!B.P)return null;
 const cr=d2[0]*A.n[0]+d2[1]*A.n[1];if(Math.abs(cr)<.2)return null;const si=cr>0?1:-1; // внутренняя сторона угла — куда уходит соседняя стена
 const mid=[(w.x1+w.x2)/2,(w.y1+w.y2)/2],h=w.t/2+2;if(regAt(M,...pa(mid,A.n,-si*h))>=0&&regAt(M,...pa(mid,A.n,si*h))<0)return null; // комната снаружи угла — окно не завернуть
 const P=A.P,I=si>0?P[end==1?0:1]:P[end==1?3:2],O=si>0?P[end==1?3:2]:P[end==1?0:1],far1=si>0?P[end==1?1:0]:P[end==1?2:3],d1=end==1?A.u:[-A.u[0],-A.u[1]],o1=[-si*A.n[0],-si*A.n[1]];
 const sv=(I[0]-N[0])*B.n[0]+(I[1]-N[1])*B.n[1]>0?1:-1,o2=[-sv*B.n[0],-sv*B.n[1]],k2=j==1?2:1,far2=sv>0?B.P[k2==1?0:1]:B.P[k2==1?3:2];
 const m1=Math.min((far1[0]-I[0])*d1[0]+(far1[1]-I[1])*d1[1],ipFree(M,w,I,d1,ex)),m2=Math.min((far2[0]-I[0])*d2[0]+(far2[1]-I[1])*d2[1],ipFree(M,v,I,d2,ex));
 return {I,O,d1,d2,o1,o2,t1:w.t,t2:v.t,end,w2:v.id,m1,m2}}
const ipCw=(c,L1,L2,w,k)=>({k,cw:{I:c.I,O:c.O,d1:c.d1,d2:c.d2,o1:c.o1,o2:c.o2,t1:c.t1,t2:c.t2,L1,L2,end:c.end,w2:c.w2},x:c.I[0],y:c.I[1],a:Math.atan2(c.d1[1],c.d1[0])*180/Math.PI,w:L1+L2,t:c.t1,wall:w.id});
function ipPlaceWallOp(M,p,k,w0,ex){let best=null,bd=1e9;
 M.walls.forEach(w=>{const G=wgeo(w),[s0,q]=loc(p.x,p.y,G.cx,G.cy,G.a);if(Math.abs(s0)>G.len/2+2||Math.abs(q)>w.t/2+8*ED.s||Math.abs(q)>=bd)return;
  const A=ipWG(M,w),s=s0+G.len/2;if(A.b-A.a<10)return;bd=Math.abs(q);
  if(k=='win')for(const end of [2,1]){const ov=end==2?s+w0/2-A.b:A.a-(s-w0/2);if(ov<12)continue;const c=ipCorner(M,w,end,ex);if(!c)continue;
   const L2=Math.min(ov,c.m2,w0-10),L1=Math.min(w0-L2,c.m1);if(L1<10||L2<10)continue;best=ipCw(c,L1,L2,w,k);return}
  const ww=Math.min(w0,A.b-A.a-1),c=Math.max(A.a+ww/2,Math.min(A.b-ww/2,s));
  best={k,x:w.x1+G.ux*c,y:w.y1+G.uy*c,a:G.a,w:ww,t:w.t,side:q<0?-1:1,h:ED.hg||'s',wall:w.id}});
 return best}
const _ipPlaceOp=placeOp;placeOp=function(M,p,k,w0,ex,fr){if(!M.user)return _ipPlaceOp(M,p,k,w0,ex,fr);if(k=='window')k='win';return ipPlaceWallOp(M,p,k,w0||(k=='door'?ED.dw:ED.ww)/MM,ex)};
/* после правки стен проёмы догоняют геометрию: угловое пересобирается, прямое не выходит за свободную часть */
function ipRefit(M){if(!M||!M.user)return;M.ops.forEach(o=>{const w=M.walls.find(x=>x.id==o.wall);if(!w)return;const G=wgeo(w),A=ipWG(M,w);
 if(o.cw){const c=ipCorner(M,w,o.cw.end,o.id);if(c&&c.w2==o.cw.w2){const L1=Math.min(o.cw.L1,c.m1),L2=Math.min(o.cw.L2,c.m2);if(L1>=10&&L2>=10){Object.assign(o,ipCw(c,L1,L2,w,o.k));return}}
  const ww=Math.max(10,Math.min(o.w,A.b-A.a-1)),s=o.cw.end==2?A.b-ww/2:A.a+ww/2;delete o.cw;Object.assign(o,{x:w.x1+G.ux*s,y:w.y1+G.uy*s,a:G.a,w:ww,t:w.t,side:1,h:'s'});return} // угла больше нет — окно прямое
 if(A.b-A.a<10)return;const s=(o.x-w.x1)*G.ux+(o.y-w.y1)*G.uy,ww=Math.min(o.w,A.b-A.a-1),c=Math.max(A.a+ww/2,Math.min(A.b-ww/2,s));
 if(Math.abs(c-s)>.05||ww<o.w-.05){o.x=w.x1+G.ux*c;o.y=w.y1+G.uy*c;o.w=ww}})}

/* ---- лист растёт: ось любой стены не ближе IPPAD к краю; влево/вверх — сдвигом всей модели (off помнит сдвиг для экспорта) ---- */
const IPPAD=50,IPK=.712;
const _ipShift=ipShift;ipShift=function(M,dx,dy){_ipShift(M,dx,dy);M.ops.forEach(o=>{if(o.cw){o.cw.I=[o.cw.I[0]+dx,o.cw.I[1]+dy];o.cw.O=[o.cw.O[0]+dx,o.cw.O[1]+dy]}})};
function ipShiftSnap(st,dx,dy){const P=o=>{o.x+=dx;o.y+=dy;if(o.cw){o.cw.I=[o.cw.I[0]+dx,o.cw.I[1]+dy];o.cw.O=[o.cw.O[0]+dx,o.cw.O[1]+dy]}};
 (st.walls||[]).forEach(w=>{w.x1+=dx;w.x2+=dx;w.y1+=dy;w.y2+=dy});['ops','furn','risers','rooms'].forEach(k=>(st[k]||[]).forEach(P))}
function ipGrow(M){if(!M||!M.user||M.fixed)return null;let a=1e9,b=1e9,c=-1e9,d=-1e9;const add=(x,y)=>{a=Math.min(a,x);b=Math.min(b,y);c=Math.max(c,x);d=Math.max(d,y)};
 M.walls.forEach(w=>{add(w.x1,w.y1);add(w.x2,w.y2)});M.risers.forEach(r=>add(r.x,r.y));if(a>c)return null;
 const dx=a<IPPAD?Math.ceil(IPPAD-a):0,dy=b<IPPAD?Math.ceil(IPPAD-b):0,W=Math.max(M.W+dx,Math.ceil(c+dx+IPPAD)),H=Math.max(M.H+dy,Math.ceil(d+dy+IPPAD));
 if(!dx&&!dy&&W==M.W&&H==M.H)return null;
 if(dx||dy){ipShift(M,dx,dy);ED.hist.forEach(s=>ipShiftSnap(s,dx,dy));ED.fut.forEach(s=>ipShiftSnap(s,dx,dy));new Set([ED.chain,ED.start,ED.pt,ED.cur,IP.r1,IP.r2,IP.q].filter(Boolean)).forEach(p=>{p.x+=dx;p.y+=dy})}
 M.W=W;M.H=H;M.vb=`0 0 ${W} ${H}`;M.gv++;return {dx,dy}}
function ipSheetW(){const sh=$('.sheet');if(!sh)return;const M=curM(),w=M&&M.user?Math.round(M.W*IPK*ZM+48)+'px':ZM==1?'':Math.round(760*ZM)+'px';if(sh.style.width!=w)sh.style.width=w}
const _ipZoom=zoom;zoom=function(d){_ipZoom(d);ipSheetW()};
const _ipSS=ipShowStage;ipShowStage=function(){_ipSS();ipSheetW()};
const _ipDraw2=draw;draw=function(){const M=curM();if(DR&&DR.mv&&M&&M.user&&(DR.k=='wall'||DR.k=='end'))ipRefit(M);_ipDraw2();ipSheetW();$('#stage').classList.toggle('ipwall',!!(ED.on&&ED.tool=='wall'))};
/* экранная точка модели — чтобы после роста листа план не прыгал */
const ipScr=P=>{const sv=$('#plan svg[data-m]'),m=sv&&sv.getScreenCTM();return m?new DOMPoint(P[0],P[1]).matrixTransform(m):null};
const _ipCh2=changed;changed=function(geo){const M=curM();let g=null,R=null,S0=null;
 if(geo&&M&&M.user){ipRefit(M);const w=M.walls[0];if(w){R=[w.x1,w.y1];S0=ipScr(R)}g=ipGrow(M)}
 _ipCh2(geo);
 if(g&&S0){const S1=ipScr([R[0]+g.dx,R[1]+g.dy]),st=$('#stage');if(S1){st.scrollLeft+=S1.x-S0.x;st.scrollTop+=S1.y-S0.y}}};
/* стены можно рисовать и по серому полю вокруг листа */
$('#stage').addEventListener('pointerdown',e=>{if(e.button!==0||!ED.on||ED.tool!='wall'||e.target.closest('#plan,button,input,a,.tag,.ipsteps,.zoom'))return;const M=curM(),p=evP(e);if(!M||!p)return;
 e.preventDefault();ED.pt=ED.typed?ED.pt:wsnap(M,p,e);addWallPt(M,liveEnd())});
$('#stage').addEventListener('dblclick',e=>{if(!e.target.closest('#plan')&&ED.on&&ED.tool=='wall')endChain()});

/* ---------- список файлов: примеры в общей сетке, карточка «Новый файл» принимает план перетаскиванием ---------- */
document.head.insertAdjacentHTML('beforeend',`<style>
.pnew{position:relative;text-align:center;padding:20px 16px;gap:6px}
.pnew>.i{font-size:32px;color:var(--acc)}.pnew b{font-size:15px;color:var(--text);font-weight:600}
.pnew .pn-sub{font-size:13px;font-weight:400;line-height:1.45}
.pnew .pn-fmt{display:flex;flex-wrap:wrap;justify-content:center;gap:4px;margin:4px 0 6px}
.pnew .pn-fmt span{font-size:11px;font-weight:500;padding:2px 7px;border-radius:99px;background:var(--sub);color:var(--muted)}
.pnew .btn .i{font-size:18px;color:inherit}
.pnew .pn-drop{position:absolute;inset:-1.5px;border:2px dashed var(--acc);border-radius:inherit;background:var(--acc-soft);color:var(--acc-text);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;padding:16px;font-weight:600;opacity:0;pointer-events:none;transition:opacity .15s}
.pnew .pn-drop .i{font-size:36px;color:var(--acc);animation:ipBob 1s ease-in-out infinite alternate}.pnew .pn-drop small{font-weight:400;font-size:12px;color:var(--muted);max-width:240px}
.pnew.drag .pn-drop{opacity:1}.pnew.drag{transform:scale(1.02)}
@keyframes ipBob{to{transform:translateY(4px)}}
.pcard .ex{color:var(--acc-text)}
@media (prefers-reduced-motion:reduce){.pnew .pn-drop .i{animation:none}.pnew.drag{transform:none}}
</style>`);

/* примеры: 0 — простой прямоугольник, 1 — кв. 28 из Rhino с вариантами, 2 — Г-образная с угловыми окнами */
function ipDemoM(pts,ops,ris){const M=ipBlank();pts.forEach((p,i)=>{const q=pts[(i+1)%pts.length];M.walls.push({id:nid(M,'w'),x1:p[0]/MM,y1:p[1]/MM,x2:q[0]/MM,y2:q[1]/MM,t:300/MM,type:'ext',fixed:1})});
 ipFit(M);ipGrow(M);const o0=M.off,s0=ED.s;ED.s=1;
 ops.forEach(([k,x,y,w])=>{const o=placeOp(M,{x:x/MM+o0[0],y:y/MM+o0[1]},k,w/MM);if(o){o.id=nid(M,'o');if(k=='door'){o.h='s'}M.ops.push(o);M.gv++}});
 ris.forEach(([x,y,t])=>M.risers.push({id:nid(M,'r'),x:x/MM+o0[0],y:y/MM+o0[1],d:110,type:t,fixed:1}));ED.s=s0;M.gv++;return M}
const EXD=[
 {n:'Пример · прямоугольник',d:'9 × 6 м · вход и 3 окна',M:()=>ipDemoM([[0,0],[9000,0],[9000,6000],[0,6000]],
  [['door',1600,5900,900],['win',2600,0,1500],['win',6600,0,1500],['win',9000,3200,1500]],[[8300,5300,'К1']])},
 {n:'Пример · кв. 28',d:'3к · 106,21 м² · 4 варианта',rh:1},
 {n:'Пример · Г-образная',d:'79 м² · 2 угловых окна',M:()=>ipDemoM([[0,0],[11400,0],[11400,5400],[6600,5400],[6600,9000],[0,9000]],
  [['door',9200,5300,900],['win',400,0,1800],['win',8600,0,1800],['win',11400,2700,1500],['win',6600,8600,1800],['win',0,5600,1500]],[[6950,5000,'К1'],[7300,5000,'В1']])}];
function ipOpenDemo(k){const D=EXD[k];if(D.rh)return openWs(false,D.n);openWs(true);IP.ro=1;$('#fn').textContent=D.n;ipStartWith(D.M());ipSaveSt('ro');renderList();ipGate();
 toast('Пример открыт для просмотра. Чтобы править и сохранять — сделайте копию',{act:'Сделать копию',fn:ipSaveCopy,ms:6000})}
const ipDemoThumb=k=>{try{return EXD[k].rh?svg(rhPlan('v3'),{label:false}):ipThumb(EXD[k].M())}catch{return ''}};
const IPTH={};
ipGrid=function(){const P=ipLS.get().projects.sort((a,b)=>b.upd-a.upd),w=$('#s-projects .wrap');
 const card=p=>{let th='';try{th=ipHas(p.M)?(p.V&&p.V[0]?msvg(Object.assign(p.V[0].M,{gv:1}),{label:false,thumb:1}):ipThumb(p.M)):''}catch{th=''}
  const n=(p.V||[]).length;return `<div class="card pcard" onclick="ipOpen('${p.id}')"><div class="th">${th||'<div class="ph"><span class="i">draft</span>Контур не начат</div>'}</div><div class="bd"><b>${esc(p.name)}</b><div class="meta"><span>${n?(n+' '+(n%10==1&&n%100!=11?'вариант':n%10>=2&&n%10<=4&&(n%100<10||n%100>=20)?'варианта':'вариантов')):'без вариантов'}</span><span>${ago(p.upd)}</span></div></div><button class="ib more" title="Ещё" onclick="event.stopPropagation();ipCardMenu(event,'${p.id}')"><span class="i">more_horiz</span></button></div>`};
 const ex=(D,k)=>`<div class="card pcard" onclick="ipOpenDemo(${k})" title="Открывается только для просмотра"><div class="th">${IPTH[k]||(IPTH[k]=ipDemoThumb(k))}</div><div class="bd"><b>${esc(D.n)}</b><div class="meta"><span>${D.d}</span><span class="ex">пример</span></div></div></div>`;
 w.innerHTML=`<div style="display:flex;align-items:flex-end;gap:16px;flex-wrap:wrap"><div style="flex:1;min-width:240px"><h1>Мои планировки</h1><p class="lead">Один файл — одна квартира и все варианты её планировки. Файлы хранятся в этом браузере</p></div><button class="btn pri lg" onclick="openWs(true)"><span class="i">add</span>Новый файл</button></div>
 <div class="grid" id="pgrid"><div class="card pnew" id="pnew" role="button" tabindex="0" onclick="openWs(true)" onkeydown="if(event.key=='Enter'||event.key==' '){event.preventDefault();openWs(true)}">
  <span class="i">add_circle</span><b>Новый файл</b><span class="pn-sub">Нарисуйте контур с нуля<br>или перетащите сюда план</span>
  <span class="pn-fmt"><span>Revit .json</span><span>.dxf</span><span>PDF</span><span>PNG · JPG</span></span>
  <button class="btn sm" onclick="event.stopPropagation();ipPickNew()"><span class="i">upload_file</span>Выбрать файл</button>
  <div class="pn-drop"><span class="i">download</span>Отпустите — создадим файл<small>JSON и DXF станут стенами, PDF и картинка — подложкой</small></div></div>
  ${P.map(card).join('')}${EXD.map(ex).join('')}</div>`};
function ipNewFrom(f){openWs(true);setTimeout(()=>ipFile(f),60)}
function ipPickNew(){const i=$('#ipfile');i.value='';i.accept=[ACC.json,ACC.dxf,ACC.under].join(',');i.onchange=()=>i.files[0]&&ipNewFrom(i.files[0]);i.click()}
/* перетаскивание на экран списка: подсвечиваем карточку «Новый файл», бросить можно куда угодно */
{let n=0;const sp=$('#s-projects'),hasF=e=>e.dataTransfer&&[...e.dataTransfer.types].includes('Files'),pn=on=>{const c=$('#pnew');c&&c.classList.toggle('drag',on)};
 sp.addEventListener('dragenter',e=>{if(!hasF(e))return;e.preventDefault();n++;pn(true)});
 sp.addEventListener('dragover',e=>{if(hasF(e)){e.preventDefault();e.dataTransfer.dropEffect='copy'}});
 sp.addEventListener('dragleave',()=>{if(--n<=0){n=0;pn(false)}});
 sp.addEventListener('drop',e=>{e.preventDefault();n=0;pn(false);const f=e.dataTransfer.files;if(!f.length)return;if(f.length>1)toast('Беру первый файл — по одному за раз',{k:'warn'});ipNewFrom(f[0])})}
if($('#s-projects').classList.contains('on'))ipGrid();
