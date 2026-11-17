# ind-plan-mvp.html (с обёрткой артефакта) → index.html для GitHub Pages: чистый документ без внешней обёртки
import os
D=os.path.dirname(os.path.abspath(__file__));R=os.path.join(D,'..')
s=open(os.path.join(R,'ind-plan-mvp.html'),encoding='utf-8').read()
i=s.find('<!doctype html>',10)
if i>0: s=s[i:]
s=s.rstrip()
if s.endswith('</html>\n\n</body></html>') or s.count('</html>')>1: s=s[:s.rfind('</body></html>')].rstrip()
open(os.path.join(R,'index.html'),'w',encoding='utf-8').write(s+'\n');print('index',len(s))
