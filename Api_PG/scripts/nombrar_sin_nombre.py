"""
nombrar_sin_nombre.py
Analiza con Gemini las 28 fotos sin nombreES y les asigna nombre comercial en español.
Actualiza solaris_catalogo.json. NO renombra archivos.
"""

import json
import base64
import re
import time
import os
import urllib.request
import urllib.error

# ── Configuración ────────────────────────────────────────────────────────────
BASE       = "C:/Users/Alejandro/Documents/Proyecto Pignatelli/Api_PG"
FOTOS_DIR  = f"{BASE}/images/fotos-Solaris-inventory"
CATALOGO   = f"{BASE}/data/solaris_catalogo.json"
API_KEY    = "AIzaSyC8nEevXGRFyOFqmplqcMO_YkMdzwL-kK4"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"

# ── Los 28 items a procesar ──────────────────────────────────────────────────
# (codigo, foto, categoria, contexto_extra)
ITEMS = [
    # Código       Foto              Categoría     Contexto
    ("C343",    "C343.jpg",          "Ceramica",   ""),
    ("D32ab",   "D32ab.jpg",         "Decorativo", "Parte de set: 8 objetos decorativos chinos azul con dorado (abanico, portapapeles, tazas)"),
    ("D76a",    "D76a.jpg",          "Decorativo", "Parte de set: 9 piezas de porcelana china (jarrones, cuencos, jarrón grande)"),
    ("D76b",    "D76b.jpg",          "Decorativo", "Parte de set: 9 piezas de porcelana china (jarrones, cuencos, jarrón grande)"),
    ("D76c",    "D76c.jpg",          "Decorativo", "Parte de set: 9 piezas de porcelana china (jarrones, cuencos, jarrón grande)"),
    ("D76d",    "D76d.jpg",          "Decorativo", "Parte de set: 9 piezas de porcelana china (jarrones, cuencos, jarrón grande)"),
    ("D76e",    "D76e.jpg",          "Decorativo", "Parte de set: 9 piezas de porcelana china (jarrones, cuencos, jarrón grande)"),
    ("D76f",    "D76f.jpg",          "Decorativo", "Parte de set: 9 piezas de porcelana china (jarrones, cuencos, jarrón grande)"),
    ("D76g",    "D76g.jpg",          "Decorativo", "Parte de set: 9 piezas de porcelana china (jarrones, cuencos, jarrón grande)"),
    ("G50",     "G50-.jpg",          "Cristaleria","Copas con borde dorado"),
    ("G158ac",  "G158ac.jpg",        "Cristaleria","Parte de set: cuencos, copas y platos dorados"),
    ("G229",    "G229.jpg",          "Cristaleria",""),
    ("G251",    "G251.jpg",          "Cristaleria",""),
    ("G257",    "G257.jpg",          "Cristaleria",""),
    ("G360",    "G360.jpg",          "Cristaleria",""),
    ("J265",    "J265.jpg",          "Joyeria",    ""),
    ("J267",    "J267.jpg",          "Joyeria",    ""),
    ("J273",    "J273.jpg",          "Joyeria",    ""),
    ("J281",    "J281.jpg",          "Joyeria",    ""),
    ("J282",    "J282.jpg",          "Joyeria",    ""),
    ("J288",    "J288.jpg",          "Joyeria",    ""),
    ("J296",    "J296.jpg",          "Joyeria",    ""),
    ("S54a",    "S54a.jpg",          "Plateria",   "Parte de set: 4 bandejas de plata de distintos tamaños"),
    ("U361",    "U361.jpg",          "Utensilio",  ""),
    ("U400",    "U400.jpg",          "Utensilio",  ""),
    ("U401",    "U401.jpg",          "Utensilio",  ""),
    ("U405",    "U405.jpg",          "Utensilio",  ""),
    ("U407",    "U407.jpg",          "Utensilio",  ""),
]

# ── Helpers ──────────────────────────────────────────────────────────────────

def leer_foto_b64(ruta):
    with open(ruta, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def llamar_gemini(ruta_foto, prompt):
    datos = leer_foto_b64(ruta_foto)
    _, ext = os.path.splitext(ruta_foto)
    mime = "image/jpeg" if ext.lower() in (".jpg", ".jpeg") else "image/png"

    payload = json.dumps({
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": mime, "data": datos}}
            ]
        }],
        "generationConfig": {"maxOutputTokens": 80, "temperature": 0.2}
    }).encode("utf-8")

    req = urllib.request.Request(
        GEMINI_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            cands = result.get("candidates", [])
            if not cands:
                return None
            parts = cands[0].get("content", {}).get("parts", [])
            return parts[0].get("text", "").strip() if parts else None
    except Exception as e:
        print(f"    [ERROR Gemini] {e}")
        return None

PROMPT_TEMPLATE = (
    "Eres un experto en subastas de arte y antigüedades. "
    "Mira la foto con atención.{contexto} "
    "Dame SOLO el nombre comercial del objeto en español, máximo 8 palabras, "
    "específico y profesional (ej: 'Copa de cristal tallado con borde dorado'). "
    "Sin explicaciones, sin puntos al final."
)

def limpiar_nombre(texto):
    """Quita comillas, puntos finales y exceso de espacios."""
    texto = texto.strip().strip('"\'').strip('.')
    # Si Gemini devuelve algo muy largo, cortar en 10 palabras
    palabras = texto.split()
    if len(palabras) > 10:
        texto = ' '.join(palabras[:10])
    return texto

# ── Proceso principal ────────────────────────────────────────────────────────

with open(CATALOGO, encoding="utf-8") as f:
    catalogo = json.load(f)

resultados = []
errores = []

print("=" * 60)
print("NOMBRAR FOTOS SIN NOMBRE — Gemini Vision")
print("=" * 60)

for codigo, foto_nombre, categoria, contexto in ITEMS:
    ruta = os.path.join(FOTOS_DIR, foto_nombre)

    if not os.path.isfile(ruta):
        print(f"  [{codigo}] FOTO NO ENCONTRADA: {foto_nombre}")
        errores.append({"codigo": codigo, "foto": foto_nombre, "error": "Foto no encontrada en disco"})
        continue

    ctx_str = f" Contexto adicional: {contexto}." if contexto else ""
    prompt = PROMPT_TEMPLATE.replace("{contexto}", ctx_str)

    print(f"  [{codigo}] Analizando {foto_nombre}...")
    nombre_raw = llamar_gemini(ruta, prompt)

    if not nombre_raw:
        print(f"    >> Sin respuesta de Gemini")
        errores.append({"codigo": codigo, "foto": foto_nombre, "error": "Sin respuesta de Gemini"})
        time.sleep(1)
        continue

    nombre_limpio = limpiar_nombre(nombre_raw)
    print(f"    >> {nombre_limpio}")
    resultados.append({"codigo": codigo, "foto": foto_nombre, "nombreES": nombre_limpio})

    # Actualizar catalogo
    if codigo in catalogo:
        catalogo[codigo]["nombreES"] = nombre_limpio
    else:
        # El item no existe en el catálogo — crearlo mínimamente
        cat_codigo = codigo[0]  # Primera letra
        num_str = re.sub(r'[^0-9]', '', codigo)
        num_item = int(num_str) if num_str else 0
        cat_nombres = {
            "C": "China", "D": "Decorative", "G": "Glasses", "F": "Furniture",
            "J": "Jewelry", "S": "Silver", "U": "Utensils", "E": "Electronics",
            "M": "Misc", "P": "Paintings"
        }
        catalogo[codigo] = {
            "fotos": [foto_nombre],
            "refs": [],
            "categoria": cat_nombres.get(cat_codigo, "Unknown"),
            "numItem": num_item,
            "catCodigo": cat_codigo,
            "codigoItem": codigo,
            "descripcionOriginal": "",
            "ubicacion": "",
            "precioUSD": None,
            "tieneSothebys": False,
            "refSothebys": "",
            "notas": "",
            "nombreES": nombre_limpio,
            "descripcionES": "",
            "cantidad": 1,
            "materiales": "",
            "estilo": "",
            "estado": ""
        }
        print(f"    >> Entrada nueva creada en catálogo")

    time.sleep(0.5)

# ── Guardar catálogo actualizado ─────────────────────────────────────────────
with open(CATALOGO, "w", encoding="utf-8") as f:
    json.dump(catalogo, f, ensure_ascii=False, indent=2)

# ── Resumen ──────────────────────────────────────────────────────────────────
print()
print("=" * 60)
print(f"COMPLETADO: {len(resultados)}/{len(ITEMS)} nombres asignados")
if errores:
    print(f"  Errores ({len(errores)}):")
    for e in errores:
        print(f"    [{e['codigo']}] {e['error']}")
print()
print("Nombres asignados:")
for r in resultados:
    print(f"  [{r['codigo']}] {r['nombreES']}")
print()
print(f"Catálogo guardado: {CATALOGO}")
