"""
generar_descripciones.py
Genera descripcionES para artículos que tienen nombreES pero no descripcionES.
Resume automáticamente desde donde quedó usando desc_progress.json.
"""
import json, base64, os, time, io, sys, re
import urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE      = 'c:/Users/Alejandro/Documents/Proyecto Pignatelli/Api_PG'
FOTOS_DIR = f'{BASE}/images/fotos-Solaris-inventory'
CAT_PATH  = f'{BASE}/data/solaris_catalogo.json'
PROG_PATH = f'{BASE}/data/desc_progress.json'
API_KEY   = 'AIzaSyC8nEevXGRFyOFqmplqcMO_YkMdzwL-kK4'
URL       = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}'

PROMPT = (
    'Eres un experto en subastas de arte y antiguedades de alto nivel. '
    'Analiza esta foto del articulo: "{nombre}". '
    'Escribe una descripcion profesional en espanol de 60 a 100 palabras. '
    'Incluye: materiales, colores, estilo o periodo, cantidad de piezas si es un conjunto, '
    'y cualquier detalle notable de calidad o decoracion. '
    'Tono elegante, como catalogo de subasta. Sin titulos, solo el parrafo de descripcion.'
)

def gemini(ruta, prompt):
    _, ext = os.path.splitext(ruta)
    mime = 'image/jpeg' if ext.lower() in ('.jpg','.jpeg','.heic') else 'image/png'
    with open(ruta,'rb') as f: data = base64.b64encode(f.read()).decode()
    payload = json.dumps({
        'contents':[{'parts':[{'text':prompt},{'inline_data':{'mime_type':mime,'data':data}}]}],
        'generationConfig':{'maxOutputTokens':400,'temperature':0.4}
    }).encode()
    req = urllib.request.Request(URL, data=payload, headers={'Content-Type':'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=40) as r:
        res = json.loads(r.read().decode())
        parts = res['candidates'][0]['content']['parts']
        return parts[0]['text'].strip()

# Cargar catalogo y progreso
cat = json.load(open(CAT_PATH, encoding='utf-8'))
progress = json.load(open(PROG_PATH, encoding='utf-8')) if os.path.isfile(PROG_PATH) else {}

# Identificar artículos sin descripción (no Ref)
pendientes = []
for k, v in cat.items():
    if v.get('descripcionES','').strip(): continue
    if not v.get('nombreES','').strip(): continue
    fotos = v.get('fotos',[])
    if not fotos: continue
    es_ref = (len(fotos)==1 and '-Ref-' in fotos[0]) or 'Ref del set' in v.get('notas','')
    if es_ref: continue
    if k in progress: continue  # ya procesado
    pendientes.append(k)

print('='*60)
print(f'GENERAR DESCRIPCIONES — {len(pendientes)} pendientes')
print('='*60)

ok, err = 0, 0
for i, codigo in enumerate(pendientes):
    item = cat[codigo]
    nombre = item.get('nombreES','')
    fotos = item.get('fotos',[])

    # Buscar foto en disco
    foto_nombre = fotos[0] if fotos else ''
    ruta = os.path.join(FOTOS_DIR, foto_nombre)
    if not os.path.isfile(ruta):
        # Buscar por prefijo
        disco = os.listdir(FOTOS_DIR)
        prefix = codigo.lower()
        candidatos = [f for f in disco if f.lower().startswith(prefix+'-') or f.lower().startswith(prefix+' ') or f.lower() == prefix+'.jpg']
        if candidatos:
            ruta = os.path.join(FOTOS_DIR, candidatos[0])
        else:
            print(f'  [{codigo}] FOTO NO ENCONTRADA — omitido')
            err += 1
            continue

    prompt = PROMPT.replace('{nombre}', nombre[:80])
    print(f'  [{i+1}/{len(pendientes)}] [{codigo}] {nombre[:50]}...', end=' ', flush=True)

    try:
        desc = gemini(ruta, prompt)
        # Validar longitud mínima
        palabras = desc.split()
        if len(palabras) < 20:
            print(f'MUY CORTA ({len(palabras)} palabras) — reintentando')
            time.sleep(1)
            desc = gemini(ruta, prompt)

        cat[codigo]['descripcionES'] = desc
        progress[codigo] = desc
        ok += 1
        print(f'OK ({len(desc.split())} palabras)')
    except Exception as e:
        print(f'ERROR: {e}')
        err += 1
        time.sleep(2)

    # Guardar cada 10
    if (i+1) % 10 == 0:
        json.dump(cat, open(CAT_PATH,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
        json.dump(progress, open(PROG_PATH,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
        print(f'  [CHECKPOINT] {i+1} procesados, catalogo guardado')

    time.sleep(0.6)

# Guardar final
json.dump(cat, open(CAT_PATH,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
json.dump(progress, open(PROG_PATH,'w',encoding='utf-8'), ensure_ascii=False, indent=2)

print()
print('='*60)
print(f'COMPLETADO: {ok} OK | {err} errores')
print(f'Catalogo guardado: {CAT_PATH}')
print('='*60)
