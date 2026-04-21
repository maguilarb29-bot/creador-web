import json, io, sys
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
root=Path(r'c:\Users\Alejandro\Documents\Proyecto Pignatelli')
ref=json.loads((root/'docs'/'referencia_sothebys_pignatelli.json').read_text(encoding='utf-8'))
refs=ref.get('sothebys_references',[])
man=ref.get('manual_values',[])
print('referencia_sothebys_pignatelli.json')
print('  sothebys_references:', len(refs))
print('  manual_values:', len(man))
print('  total entradas:', len(refs)+len(man))

# unique codigos split by /,
import re
codes=[]
for r in refs+man:
    raw=str(r.get('codigo_pignatelli','')).strip()
    for c in [x.strip() for x in raw.replace('/',',').split(',') if x.strip()]:
        codes.append(c)
print('  codigos tokenizados:', len(codes))
print('  codigos unicos tokenizados:', len(set(codes)))
