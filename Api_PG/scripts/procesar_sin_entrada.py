"""
procesar_sin_entrada.py
- Analiza con Gemini las 18 fotos sin entrada en catalogo
- Las renombra con nombre comercial en español
- Las agrega al catalogo
"""
import json, base64, os, re, time, unicodedata, io, sys
import urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE      = 'c:/Users/Alejandro/Documents/Proyecto Pignatelli/Api_PG'
FOTOS_DIR = f'{BASE}/images/fotos-Solaris-inventory'
CAT_PATH  = f'{BASE}/data/solaris_catalogo.json'
API_KEY   = 'AIzaSyC8nEevXGRFyOFqmplqcMO_YkMdzwL-kK4'
URL       = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}'

# Fotos sin entrada + su contexto conocido
# (foto_actual, codigo_destino, categoria, es_ref, contexto)
ITEMS = [
    ('D18-1 Italian giltwood and engraved mid-18th Century \ufffd $4,200-7,000 - Sotheby\ufffd s #65 p. 40.HEIC',
     'D18', 'Decorative', False, 'Espejo o marco italiano dorado tallado siglo XVIII, Sothebys #65 valorado $4200-7000'),
    ('D180-1 Louis XVI giltwood barometer, circa 1790 - $1,680-2,520 \ufffd Sotheby\ufffd s #96 p. 50.HEIC',
     'D180', 'Decorative', False, 'Barometro dorado estilo Luis XVI circa 1790, Sothebys #96 valorado $1680-2520'),
    ('D27-1 sculpture with stone flowers.HEIC',
     'D27', 'Decorative', False, 'Escultura con flores de piedra'),
    ('D30-1 Louis XV gilt-bronze cartel clock attributed to Jean-Joseph de Saint-German, circa 1748 - $11,200-16,800 \ufffd Sotheby\ufffd s #97 p. 50.HEIC',
     'D30', 'Decorative', False, 'Reloj cartel Luis XV bronce dorado atribuido a Saint-German circa 1748, Sothebys #97 valorado $11200-16800'),
    ('F15-Green top console table.HEIC',
     'F15', 'Furniture', False, 'Mesa consola con tapa verde'),
    ('F184.jpg',
     'F184', 'Furniture', False, ''),
    ('F23-1 Louis XV style beech, mahogany, rosewood with metal structure - assume $2000.HEIC',
     'F23', 'Furniture', False, 'Mueble estilo Luis XV en haya, caoba y palisandro con estructura metalica'),
    ('F29a -  tufted corner mini sofas with 2 pillows petrol blue.jpeg',
     'F29a', 'Furniture', False, 'Segunda foto del sofa esquinero capitone azul petroleo de F29'),
    ('F41-1 rug mostly blue with beige patterns and border.HEIC',
     'F41', 'Furniture', False, 'Alfombra azul con patrones y borde beige'),
    ('S183-Austrian silver ewer and basin stamped STN, Vienna 1836$2,100-2,800 \ufffd Sotheby\ufffd s #107 p. 59.HEIC',
     'S183', 'Silver', False, 'Aguamanil y jofaina de plata austriaca sellado STN Viena 1836, Sothebys #107 valorado $2100-2800'),
    ('c150f-Misc glass carafes, bowls, plates, gobblets.jpg',
     'C150f', 'China', False, 'Miscelanea: carafes, cuencos, platos y copas de vidrio'),
    ('g192.jpg',
     'G192', 'Glasses', False, ''),
    ('p1.jpg',
     'P1', 'Paintings', False, ''),
    ('p2.jpg',
     'P2', 'Paintings', False, ''),
    ('p185.jpg',
     'P185', 'Paintings', False, ''),
    ('p186.jpg',
     'P186', 'Paintings', False, ''),
    ('p187.jpg',
     'P187', 'Paintings', False, ''),
    ('p188.jpg',
     'P188', 'Paintings', False, ''),
]

CAT_NOMBRES = {
    'C':'China','D':'Decorative','F':'Furniture','G':'Glasses',
    'J':'Jewelry','S':'Silver','U':'Utensils','E':'Electronics',
    'M':'Misc','P':'Paintings'
}

# Sothebys conocidos
SOTHEBYS = {
    'D18':  ('D18',  True, 'Sothebys #65 p.40 - Italian giltwood mirror mid-18th Century $4200-7000'),
    'D180': ('D180', True, 'Sothebys #96 p.50 - Louis XVI giltwood barometer circa 1790 $1680-2520'),
    'D30':  ('D30',  True, 'Sothebys #97 p.50 - Louis XV gilt-bronze cartel clock Saint-German circa 1748 $11200-16800'),
    'S183': ('S183', True, 'Sothebys #107 p.59 - Austrian silver ewer and basin STN Vienna 1836 $2100-2800'),
}

def slugify(texto, max_len=42):
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    texto = texto.lower()
    texto = re.sub(r'[^a-z0-9]+', '-', texto)
    texto = texto.strip('-')
    if len(texto) > max_len:
        t = texto[:max_len]
        pos = t.rfind('-')
        texto = t[:pos] if pos > max_len * 0.55 else t
    return texto.strip('-')

def get_mime(fname):
    ext = os.path.splitext(fname)[1].lower()
    return {'heic':'image/heic','jpg':'image/jpeg','jpeg':'image/jpeg','png':'image/png'}.get(ext.lstrip('.'), 'image/jpeg')

def gemini(ruta, prompt):
    with open(ruta, 'rb') as f:
        data = base64.b64encode(f.read()).decode()
    mime = get_mime(ruta)
    payload = json.dumps({
        'contents': [{'parts': [{'text': prompt}, {'inline_data': {'mime_type': mime, 'data': data}}]}],
        'generationConfig': {'maxOutputTokens': 300, 'temperature': 0.2}
    }).encode()
    req = urllib.request.Request(URL, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=40) as r:
        res = json.loads(r.read().decode())
        parts = res['candidates'][0]['content']['parts']
        return parts[0]['text'].strip()

cat = json.load(open(CAT_PATH, encoding='utf-8'))

print('=' * 60)
print('PROCESAR 18 FOTOS SIN ENTRADA')
print('=' * 60)

ok, err = 0, 0

for foto_actual, codigo, categoria, es_ref, contexto in ITEMS:
    ruta = os.path.join(FOTOS_DIR, foto_actual)

    # Buscar en disco (puede diferir por encoding)
    if not os.path.isfile(ruta):
        disco = os.listdir(FOTOS_DIR)
        prefix = codigo.lower()
        candidatos = [f for f in disco if f.lower().startswith(prefix.lower() + '-') or f.lower().startswith(prefix.lower() + ' ') or f.lower() == prefix.lower() + '.jpg' or f.lower() == prefix.lower() + '.heic' or f.lower() == prefix.lower() + '.jpeg' or f.lower() == prefix.lower() + '.png']
        if not candidatos:
            # Buscar por nombre similar
            candidatos = [f for f in disco if f.lower().replace('\ufffd','').startswith(codigo.lower())]
        if candidatos:
            foto_actual = candidatos[0]
            ruta = os.path.join(FOTOS_DIR, foto_actual)
        else:
            print(f'  [{codigo}] NO ENCONTRADO EN DISCO')
            err += 1
            continue

    ext = os.path.splitext(foto_actual)[1].lower()
    if ext == '.heic': ext = '.jpg'  # convertir extensión destino
    if ext == '.jpeg': ext = '.jpg'

    ctx_str = f' Contexto: {contexto}.' if contexto else ''
    prompt = (f'Eres experto en subastas de arte y antiguedades. Mira la foto.{ctx_str} '
              f'Dame SOLO el nombre comercial en espanol, maximo 8 palabras, especifico y profesional. '
              f'Sin comillas, sin punto final.')

    print(f'  [{codigo}] {foto_actual} ...', end=' ', flush=True)
    try:
        nombre_raw = gemini(ruta, prompt)
        nombre = nombre_raw.strip().strip('"\'').strip('.')
        nombre = ' '.join(nombre.split()[:10])
        print(nombre)
    except Exception as e:
        print(f'ERROR: {e}')
        nombre = contexto.split(',')[0][:50] if contexto else codigo
        err += 1

    # Construir nombre de archivo destino
    slug = slugify(nombre)
    if es_ref:
        destino = f'{codigo}-Ref-{slug}{ext}'
    else:
        destino = f'{codigo}-{slug}{ext}'

    # Renombrar en disco
    ruta_dest = os.path.join(FOTOS_DIR, destino)
    if not os.path.isfile(ruta_dest):
        try:
            os.rename(ruta, ruta_dest)
            print(f'    -> {destino}')
        except Exception as e:
            print(f'    [ERROR RENAME] {e}')
            destino = foto_actual  # mantener nombre original si falla
    else:
        print(f'    -> {destino} (ya existe)')

    # Agregar/actualizar entrada en catalogo
    s_info = SOTHEBYS.get(codigo, (None, False, ''))
    tiene_s = s_info[1]
    ref_s   = s_info[2]

    num_str = re.sub(r'[^0-9]', '', codigo)
    num_item = int(num_str) if num_str else 0

    if codigo in cat:
        # Ya existe (ej. F29a), solo agregar foto si no está
        if destino not in cat[codigo]['fotos']:
            cat[codigo]['fotos'].append(destino)
        if not cat[codigo].get('nombreES'):
            cat[codigo]['nombreES'] = nombre
        print(f'    Entrada existente actualizada')
    else:
        cat[codigo] = {
            'fotos': [destino], 'refs': [],
            'categoria': CAT_NOMBRES.get(codigo[0], 'Unknown'),
            'numItem': num_item, 'catCodigo': codigo[0], 'codigoItem': codigo,
            'descripcionOriginal': contexto, 'ubicacion': '', 'precioUSD': None,
            'tieneSothebys': tiene_s, 'refSothebys': ref_s, 'notas': '',
            'nombreES': nombre, 'descripcionES': '',
            'cantidad': 1, 'materiales': '', 'estilo': '', 'estado': ''
        }
        print(f'    Entrada nueva creada en catalogo')
    ok += 1
    time.sleep(0.6)

json.dump(cat, open(CAT_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

print()
print('=' * 60)
print(f'COMPLETADO: {ok} OK | {err} errores')
print('=' * 60)
