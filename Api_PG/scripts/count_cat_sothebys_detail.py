import json, re, io, sys
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
root=Path(r'c:\Users\Alejandro\Documents\Proyecto Pignatelli')
cat=json.loads((root/'Api_PG'/'data'/'solaris_catalogo.json').read_text(encoding='utf-8'))

def es_ref(v):
    fotos=[str(f).strip() for f in v.get('fotos',[]) if str(f).strip()]
    if 'Ref del set' in str(v.get('notas','')): return True
    return len(fotos)==1 and '-Ref-' in fotos[0]

def es_root(code):
    return bool(re.match(r'^[A-Z]+\d+$', code))

all_items={k:v for k,v in cat.items() if isinstance(v,dict)}
con_s={k:v for k,v in all_items.items() if v.get('tieneSothebys')}
con_s_root={k:v for k,v in con_s.items() if es_root(k)}
con_s_sub={k:v for k,v in con_s.items() if not es_root(k) and not es_ref(v)}
con_s_ref={k:v for k,v in con_s.items() if es_ref(v)}
print('solaris_catalogo.json')
print('  con tieneSothebys=True (total):', len(con_s))
print('  de esos, raiz:', len(con_s_root))
print('  de esos, subitems:', len(con_s_sub))
print('  de esos, refs:', len(con_s_ref))
print('  codigos:', ', '.join(sorted(con_s.keys())))
