# Вставляет редактор в ind-plan-mvp.html (идемпотентно: старая вставка между маркерами заменяется).
import os,re,sys
D=os.path.dirname(os.path.abspath(__file__));H=os.path.join(D,'..','ind-plan-mvp.html')
s=open(H,encoding='utf-8').read()
def put(s,tag,payload,anchor,before=True):
    a,b=f'<!--{tag}-->',f'<!--/{tag}-->' if not tag.startswith('js:') else None
    if tag.startswith('js:'):a,b=f'/*{tag}*/',f'/*/{tag}*/'
    blk=a+payload+b
    if a in s: return re.sub(re.escape(a)+'.*?'+re.escape(b),lambda m:blk,s,flags=re.S)
    i=s.index(anchor) if before else s.index(anchor)+len(anchor)
    return s[:i]+blk+s[i:]
CSS='''<style>
.right.ed>:not(#pedit){display:none!important}#pedit{display:none;flex:1;min-height:0;flex-direction:column}.right.ed #pedit{display:flex}
#props{flex:1;overflow:auto;padding:0 16px 8px}#props .blk:first-child{padding-top:4px}
.fld{display:grid;grid-template-columns:96px 1fr 26px;align-items:center;gap:8px;margin:8px 0;font-size:13px}.fld>span:first-child{color:var(--muted)}.fld>span:last-child{color:var(--faint);font-size:12px}
.fld input{height:32px;min-width:0;border:1px solid var(--line2);border-radius:8px;padding:0 10px;font:inherit;font-size:13px;background:var(--panel);color:var(--text);font-variant-numeric:tabular-nums}.fld input:focus{outline:2px solid var(--acc);outline-offset:-1px}
.sel{width:100%;height:34px;border:1px solid var(--line2);border-radius:8px;padding:0 8px;font:inherit;font-size:13px;background:var(--panel);color:var(--text);margin-bottom:6px}
.hintp{font-size:12px;color:var(--muted);margin:8px 0 0;line-height:1.45}
.pacts{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}.pacts .btn.onb{border-color:var(--acc);background:var(--acc-soft);color:var(--acc-text)}
.orow{display:flex;align-items:center;gap:8px;width:100%;border:0;background:transparent;padding:6px 8px;margin:0 -8px;width:calc(100% + 16px);border-radius:8px;cursor:pointer;font-size:13px;text-align:left;color:var(--text)}.orow:hover{background:var(--sub)}.orow .i{font-size:17px;color:var(--muted)}.orow .lead{font-size:12px;white-space:nowrap}
.sw{width:10px;height:10px;border-radius:3px;border:1px solid #0002;flex:none}
.swg{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}.swg button{height:40px;border:1px solid var(--line2);border-radius:8px;background:var(--panel);cursor:pointer;display:grid;place-items:center;color:var(--text)}.swg button:hover{background:var(--sub)}.swg button.on{border-color:var(--acc);background:var(--acc-soft);color:var(--acc-text)}
.cat{display:grid;grid-template-columns:1fr 1fr;gap:6px}.cat button{border:1px solid var(--line2);border-radius:10px;background:var(--panel);padding:8px 6px;cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:3px;font-size:12px;line-height:1.25;text-align:center;color:var(--text)}.cat button:hover{background:var(--sub)}.cat button.on{border-color:var(--acc);background:var(--acc-soft);color:var(--acc-text)}.cat small{color:var(--faint);font-size:11px}
.keys{display:grid;grid-template-columns:1fr 1fr;gap:6px 10px;font-size:12px;color:var(--muted)}.keys kbd{display:inline-block;min-width:22px;padding:1px 5px;margin-right:6px;border:1px solid var(--line2);border-bottom-width:2px;border-radius:5px;font:600 11px Inter,sans-serif;color:var(--text);text-align:center;background:var(--panel)}
.stage{overflow:auto}.stage>.sheet{margin:auto;flex:none}
</style>'''
PANEL='''<div id="pedit"><div class="rh"><button class="ib" title="К генерациям" onclick="edDone()"><span class="i">arrow_back</span></button><h2 id="ptitle">Свойства</h2><span class="sp"></span><button class="ib" id="undo" title="Отменить · Ctrl+Z" onclick="undo()"><span class="i">undo</span></button><button class="ib" id="redo" title="Повторить · Ctrl+Shift+Z" onclick="redo()"><span class="i">redo</span></button></div><div class="rsub">Свойства</div><div id="props"></div><div class="cta"><button class="btn pri lg w" onclick="edDone()"><span class="i">check</span>Готово</button></div></div>'''
msym=open(D+'/rh/msym.html',encoding='utf-8').read()
model=open(D+'/rh/model.js',encoding='utf-8').read();ed=open(D+'/editor.js',encoding='utf-8').read()
# v4 — вариант, спроектированный вручную (v4.js); идёт после editor.js: дополняет каталог мебели и COMBO
ed+=chr(10)+open(D+'/v4.js',encoding='utf-8').read()
# финальный интерфейс (контур с нуля, импорт, сохранение, состояния запуска, экспорт) — после v4.js
ed+=chr(10)+open(D+'/app.js',encoding='utf-8').read()
# стили — во второй <head> (первый — обёртка артефакта)
anc='@media (max-width:1000px)';i=s.index(anc);j=s.index('</style>',i)+len('</style>')
if '<!--ed-css-->' in s: s=put(s,'ed-css',CSS,'')
else: s=s[:j]+'<!--ed-css-->'+CSS+'<!--/ed-css-->'+s[j:]
s=put(s,'ed-sym',msym,'<!-- LOGIN -->')
s=put(s,'ed-panel',PANEL,'''  </aside>
 </div>
</section>''')
last=s.rindex('</script></body></html>')
if '/*js:editor*/' in s: s=put(s,'js:editor','\n'+model+'\n'+ed+'\n','')
else: s=s[:last]+'/*js:editor*/\n'+model+'\n'+ed+'\n/*/js:editor*/'+s[last:]
s=s.replace("onclick=\"pickTool('part')\"><span class=\"i\">open_with</span>Сдвинуть перегородку","onclick=\"edStart()\"><span class=\"i\">edit</span>Править стены и мебель")
open(H,'w',encoding='utf-8').write(s);print('ok',len(s))
