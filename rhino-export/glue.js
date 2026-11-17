/* ===== Планировки из Rhino (Квартира 28, 106,21 м²). Мебель и сантехника — из модели; стены, окна, двери и цвета комнат — в стиле редактора IND PLAN. Площади — заливкой по внутренним граням ===== */
const COMBO=[['v3'],['v2'],['v1']];
const RCOL=n=>/Спальн|Детск|Кабинет/.test(n)?'#E4EEDD':/Гостин|Кухн|Столов/.test(n)?'#F7EDD8':/Ванн|С\/У|Санузел/.test(n)?'#DCEAF5':/Постир/.test(n)?'#E2EBF1':/Гардероб/.test(n)?'#EFE4EE':'#EEEDE8';
const scap=t=>t[0]+t.slice(1).toLowerCase();
function rhPlan(lay,pal,furn){const R=RH[lay].R.map(r=>({...r}));R.rh={lay,furn:furn!==false};return R}
function rsvg(R,o={}){const {lay,furn}=R.rh,M=RH[lay],fs=13;
 const fills=R.map((r,i)=>r.p?`<path d="${r.p}" fill="${o.sel===i?'var(--acc-soft)':RCOL(r.n)}" ${o.sel===i?'stroke="var(--acc)" stroke-width="2"':''} ${o.click?`onclick="pickRoom(${i})" style="cursor:pointer"`:''}/>`:'').join('');
 let t='';if(o.label!==false)M.L.forEach(l=>{const r=R[l.r],nm=r.cn&&l.f?r.n:scap(l.t),bg=o.sel===l.r?'var(--acc-soft)':RCOL(r.n);
  t+=`<g style="pointer-events:none" font-family="Inter,sans-serif" text-anchor="middle" paint-order="stroke" stroke="${bg}" stroke-width="4" stroke-linejoin="round"><text x="${l.x}" y="${l.y+fs*.35}" font-size="${fs}" font-weight="600" fill="${o.sel===l.r?'var(--acc-text)':'#1F2328'}">${nm}</text>${o.area&&l.f&&r.a?`<text x="${l.x}" y="${l.y+fs*1.5}" font-size="${fs*.85}" fill="#1F2328">${area(r)} м²</text>`:''}</g>`});
 return `<svg viewBox="${M.vb}" width="100%" style="display:block;--fd:${furn?'inline':'none'}"><use href="#rh-${lay}-f"/>${fills}${(M.cut||[]).map(c=>`<path d="M${c[0]} ${c[1]}L${c[2]} ${c[3]}" stroke="#6B7280" stroke-width="1.2" stroke-dasharray="5 4" style="pointer-events:none"/>`).join('')}<use href="#rh-${lay}" style="pointer-events:none"/>${t}</svg>`}
const csvg=()=>`<svg viewBox="${RH.contour.vb}" width="100%" style="display:block"><use href="#rh-ct"/></svg>`;
const isvg=()=>`<svg viewBox="${RH.ind.vb}" width="100%" style="display:block;background:#fff"><use href="#rh-ind"/></svg>`;
/* в объединённой зоне площадь подписываем у гостиной, а не у прихожей */
Object.values(RH).forEach(M=>{if(!M.L)return;M.R.forEach((r,i)=>{const ls=M.L.filter(l=>l.r==i),g=ls.find(l=>/ГОСТИН/.test(l.t));if(g&&ls.length>1)ls.forEach(l=>l.f=l===g?1:0)})});
const _svg=svg;svg=(R,o={})=>R&&R.rh?rsvg(R,o):R&&!R.length&&!R.L?csvg(o):_svg(R,o);
