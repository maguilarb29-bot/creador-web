"""
corregir_nombres_truncados.py
Reprocesa los items con nombre truncado o vacío. max_tokens=300.
"""
import json, base64, re, time, os, sys
import urllib.request

BASE       = "C:/Users/Alejandro/Documents/Proyecto Pignatelli/Api_PG"
FOTOS_DIR  = f"{BASE}/images/fotos-Solaris-inventory"
CATALOGO   = f"{BASE}/data/solaris_catalogo.json"
API_KEY    = "AIzaSyC8nEevXGRFyOFqmplqcMO_YkMdzwL-kK4"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"

# Items que quedaron truncados o vacíos
ITEMS = [
    ("C343",   "C343.jpg",   "Cerámica",   ""),
    ("D76a",   "D76a.jpg",   "Decorativo", "Parte de set: 9 piezas de porcelana china"),
    ("D76c",   "D76c.jpg",   "Decorativo", "Parte de set: 9 piezas de porcelana china"),
    ("D76f",   "D76f.jpg",   "Decorativo", "Parte de set: 9 piezas de porcelana china"),
    ("D76g",   "D76g.jpg",   "Decorativo", "Parte de set: 9 piezas de porcelana china"),
    ("G50",    "G50-.jpg",   "Cristalería","Copas con borde dorado"),
    ("G158ac", "G158ac.jpg", "Cristalería","Parte de set: cuencos, copas y platos dorados"),
    ("G251",   "G251.jpg",   "Cristalería",""),
    ("G257",   "G257.jpg",   "Cristalería",""),
    ("J265",   "J265.jpg",   "Joyería",    ""),
    ("J267",   "J267.jpg",   "Joyería",    ""),
    ("J273",   "J273.jpg",   "Joyería",    ""),
    ("J281",   "J281.jpg",   "Joyería",    ""),
    ("J282",   "J282.jpg",   "Joyería",    ""),
    ("J288",   "J288.jpg",   "Joyería",    ""),
    ("S54a",   "S54a.jpg",   "Platería",   "Parte de set: 4 bandejas de plata de distintos tamaños"),
    ("U400",   "U400.jpg",   "Utensilio",  ""),
    ("U405",   "U405.jpg",   "Utensilio",  ""),
]

def leer_b64(ruta):
    with open(ruta, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def llamar_gemini(ruta, prompt):
    _, ext = os.path.splitext(ruta)
    mime = "image/jpeg" if ext.lower() in (".jpg", ".jpeg") else "image/png"
    payload = json.dumps({
        "contents": [{"parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": mime, "data": leer_b64(ruta)}}
        ]}],
        "generationConfig": {"maxOutputTokens": 300, "temperature": 0.2}
    }).encode("utf-8")
    req = urllib.request.Request(GEMINI_URL, data=payload,
                                  headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            r = json.loads(resp.read().decode("utf-8"))
            cands = r.get("candidates", [])
            if not cands: return None
            parts = cands[0].get("content", {}).get("parts", [])
            return parts[0].get("text", "").strip() if parts else None
    except Exception as e:
        print(f"    [ERROR] {e}")
        return None

PROMPT = (
    "Eres experto en subastas de arte y antigüedades. Mira la foto.{ctx} "
    "Dame SOLO el nombre comercial del objeto en español, máximo 8 palabras, "
    "específico y profesional. Ejemplo: 'Copa de cristal tallado con borde dorado'. "
    "Responde SOLO el nombre, sin comillas, sin puntos al final."
)

def limpiar(texto):
    texto = texto.strip().strip('"\'').strip('.')
    palabras = texto.split()
    return ' '.join(palabras[:10]) if len(palabras) > 10 else texto

with open(CATALOGO, encoding="utf-8") as f:
    catalogo = json.load(f)

print("=" * 60)
print("CORREGIR NOMBRES TRUNCADOS")
print("=" * 60)

ok, err = 0, 0
for codigo, foto_nombre, cat_label, contexto in ITEMS:
    ruta = os.path.join(FOTOS_DIR, foto_nombre)
    if not os.path.isfile(ruta):
        print(f"  [{codigo}] FOTO NO ENCONTRADA: {foto_nombre}")
        err += 1
        continue

    ctx_str = f" Contexto: {contexto}." if contexto else ""
    prompt = PROMPT.replace("{ctx}", ctx_str)

    print(f"  [{codigo}] {foto_nombre} ...", end=" ", flush=True)
    nombre_raw = llamar_gemini(ruta, prompt)

    if not nombre_raw:
        print("ERROR - sin respuesta")
        err += 1
        time.sleep(2)
        continue

    nombre = limpiar(nombre_raw)
    print(f">> {nombre}")
    ok += 1

    cat_codigos = {"C":"China","D":"Decorative","G":"Glasses","F":"Furniture",
                   "J":"Jewelry","S":"Silver","U":"Utensils","E":"Electronics","M":"Misc","P":"Paintings"}

    if codigo in catalogo:
        catalogo[codigo]["nombreES"] = nombre
    else:
        num_str = re.sub(r'[^0-9]', '', codigo)
        catalogo[codigo] = {
            "fotos": [foto_nombre], "refs": [],
            "categoria": cat_codigos.get(codigo[0], "Unknown"),
            "numItem": int(num_str) if num_str else 0,
            "catCodigo": codigo[0], "codigoItem": codigo,
            "descripcionOriginal": "", "ubicacion": "", "precioUSD": None,
            "tieneSothebys": False, "refSothebys": "", "notas": "",
            "nombreES": nombre, "descripcionES": "",
            "cantidad": 1, "materiales": "", "estilo": "", "estado": ""
        }
        print(f"    (entrada nueva creada)")

    time.sleep(0.6)

with open(CATALOGO, "w", encoding="utf-8") as f:
    json.dump(catalogo, f, ensure_ascii=False, indent=2)

print()
print(f"COMPLETADO: {ok}/{len(ITEMS)} OK | {err} errores")
print()
print("Verificación final:")
all_codes = [i[0] for i in ITEMS]
for c in all_codes:
    item = catalogo.get(c)
    n = item.get("nombreES","") if item else "NO EXISTE"
    flag = "OK" if n and len(n) > 4 and not n.endswith((" de", " b", " col")) else "REVISAR"
    print(f"  [{c}] {flag}: {n}")
