"""
generar_rename_plan.py
Genera rename_plan.json — tabla completa de mapeo origen→destino para fotos.
NO renombra archivos. NO modifica el catálogo. Solo prepara el plan para revisión.

Reglas aplicadas:
- El código del artículo es INTOCABLE (letra+numero+sufijo)
- Si hay -Ref en la descripción inglesa, se traslada al código como -Ref
- La parte descriptiva nueva viene del nombreES del catálogo
- Sin nombreES → flagear como dudoso
- Sin conflictos forzados
"""

import json
import re
import unicodedata
import os

# ── Rutas ───────────────────────────────────────────────────────────────────
BASE = "C:/Users/Alejandro/Documents/Proyecto Pignatelli/Api_PG"
CATALOGO_PATH = f"{BASE}/data/solaris_catalogo.json"
FOTOS_DIR = f"{BASE}/images/fotos-Solaris-inventory"
OUTPUT_PATH = f"{BASE}/data/rename_plan.json"

# ── Helpers ─────────────────────────────────────────────────────────────────

# Regex para extraer el código del artículo del nombre de archivo
# Formato: [LetraMayúscula][número][0-2 letras minúsculas]
CODIGO_REGEX = re.compile(r'^([A-Z]\d+[a-z]{0,2})')

def extraer_codigo(filename):
    """Extrae el código del artículo del nombre de archivo. Retorna None si no parsea."""
    m = CODIGO_REGEX.match(filename)
    return m.group(1) if m else None

def es_ref_foto(filename):
    """
    Detecta si esta foto es de tipo Ref.
    Un foto Ref tiene 'Ref' (con mayúscula) en la parte descriptiva (después del código).
    Ejemplos válidos:
      G48-3 glass decanters + 2 glass bowls. Ref.JPG  → True
      C136a-Misc set ... - Ref.JPG                    → True
      F1-Sideboard cherry wood.JPG                    → False
      C136ca.jpg                                      → False
    """
    codigo = extraer_codigo(filename)
    if not codigo:
        return False
    # La parte descriptiva es todo lo que queda después del código
    resto = filename[len(codigo):]
    return bool(re.search(r'\bRef\b', resto))

def normalizar_slug(nombre, max_len=42):
    """
    Convierte un nombre en español a slug para nombre de archivo.
    - Sin tildes ni caracteres especiales
    - Minúsculas
    - Espacios y símbolos → guiones
    - Máximo max_len caracteres, cortado en límite de palabra
    """
    if not nombre:
        return ""
    # Quitar tildes/diacríticos
    nombre = unicodedata.normalize('NFKD', nombre)
    nombre = ''.join(c for c in nombre if not unicodedata.combining(c))
    # Minúsculas
    nombre = nombre.lower()
    # Reemplazar todo lo que no sea alfanumérico con guión
    nombre = re.sub(r'[^a-z0-9]+', '-', nombre)
    # Quitar guiones al inicio/final
    nombre = nombre.strip('-')
    # Truncar respetando límite de palabra
    if len(nombre) > max_len:
        truncado = nombre[:max_len]
        ultimo_guion = truncado.rfind('-')
        if ultimo_guion > int(max_len * 0.55):
            nombre = truncado[:ultimo_guion]
        else:
            nombre = truncado
    nombre = nombre.strip('-')
    return nombre

def normalizar_ext(filename):
    """Normaliza extensión a minúsculas. .jpeg → .jpg"""
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    if ext == '.jpeg':
        ext = '.jpg'
    return ext

def construir_destino(codigo, es_ref, slug, ext):
    """
    Construye el nombre de destino según las reglas oficiales.
    [codigo]-Ref-[slug].ext  o  [codigo]-[slug].ext
    """
    if not slug:
        return None
    if es_ref:
        return f"{codigo}-Ref-{slug}{ext}"
    else:
        return f"{codigo}-{slug}{ext}"

# ── Carga datos ─────────────────────────────────────────────────────────────

with open(CATALOGO_PATH, encoding='utf-8') as f:
    catalogo = json.load(f)

# Construir mapa inverso: nombre_foto → codigoItem_padre
# Necesario para fotos sin entrada propia (C136ca.jpg → C136)
foto_a_padre = {}
for codigo_item, item in catalogo.items():
    for foto in item.get('fotos', []):
        foto_a_padre[foto] = codigo_item

# ── Procesamiento ────────────────────────────────────────────────────────────

renombres = []     # casos limpios con propuesta confirmada
dudosos = []       # casos que requieren revisión manual

for codigo_item, item in catalogo.items():
    nombre_es_padre = item.get('nombreES', '').strip()
    fotos = item.get('fotos', [])

    for foto in fotos:
        codigo_foto = extraer_codigo(foto)
        es_ref = es_ref_foto(foto)
        ext = normalizar_ext(foto)

        # ── 1. Determinar el código a usar ──────────────────────────────
        if not codigo_foto:
            dudosos.append({
                "codigoItem": codigo_item,
                "foto_codigo": None,
                "es_ref": False,
                "origen": foto,
                "destino": None,
                "nombre_es_usado": None,
                "motivo_revision": "No se pudo extraer código del nombre de archivo"
            })
            continue

        # ── 2. Obtener el mejor nombreES disponible ─────────────────────
        # Prioridad 1: entrada propia con nombreES
        # Prioridad 2: padre con nombreES
        # Prioridad 3: descripcionOriginal inglés de entrada propia (fallback)
        # Prioridad 4: descripcionOriginal inglés del padre (fallback)
        nombre_es = None
        fuente_nombre = None

        if codigo_foto in catalogo:
            nombre_foto_entry = catalogo[codigo_foto].get('nombreES', '').strip()
            if nombre_foto_entry:
                nombre_es = nombre_foto_entry
                fuente_nombre = f"entrada_propia:{codigo_foto}"

        # Si no, usar el nombreES del artículo padre
        if not nombre_es and nombre_es_padre:
            nombre_es = nombre_es_padre
            fuente_nombre = f"padre:{codigo_item}"

        # Fallback: descripcionOriginal en inglés (para generar slug)
        if not nombre_es:
            desc_orig = ''
            if codigo_foto in catalogo:
                desc_orig = catalogo[codigo_foto].get('descripcionOriginal', '').strip()
            if not desc_orig:
                desc_orig = item.get('descripcionOriginal', '').strip()
            if desc_orig:
                nombre_es = desc_orig
                fuente_nombre = f"desc_original:{codigo_foto}"

        # ── 3. Sin ningún nombre → dudoso ───────────────────────────────
        if not nombre_es:
            dudosos.append({
                "codigoItem": codigo_item,
                "foto_codigo": codigo_foto,
                "es_ref": es_ref,
                "origen": foto,
                "destino": None,
                "nombre_es_usado": None,
                "motivo_revision": f"Sin nombreES en catálogo (ni en {codigo_foto} ni en {codigo_item})"
            })
            continue

        # ── 4. Construir slug y destino ─────────────────────────────────
        slug = normalizar_slug(nombre_es, max_len=42)

        if not slug:
            dudosos.append({
                "codigoItem": codigo_item,
                "foto_codigo": codigo_foto,
                "es_ref": es_ref,
                "origen": foto,
                "destino": None,
                "nombre_es_usado": nombre_es,
                "motivo_revision": "Slug vacío tras normalización"
            })
            continue

        destino = construir_destino(codigo_foto, es_ref, slug, ext)

        # ── 5. Verificar que el origen ≠ destino (ya renombrado o igual) ─
        if foto == destino:
            dudosos.append({
                "codigoItem": codigo_item,
                "foto_codigo": codigo_foto,
                "es_ref": es_ref,
                "origen": foto,
                "destino": destino,
                "nombre_es_usado": nombre_es,
                "fuente_nombre": fuente_nombre,
                "motivo_revision": "El origen ya es igual al destino propuesto (posible foto ya renombrada)"
            })
            continue

        renombres.append({
            "codigoItem": codigo_item,
            "foto_codigo": codigo_foto,
            "es_ref": es_ref,
            "origen": foto,
            "destino": destino,
            "nombre_es_usado": nombre_es,
            "fuente_nombre": fuente_nombre
        })

# ── Detectar conflictos de destino (dos fotos distintas → mismo nombre) ────
destino_count = {}
for r in renombres:
    d = r['destino']
    destino_count[d] = destino_count.get(d, 0) + 1

conflictos = []
renombres_limpios = []
for r in renombres:
    if destino_count.get(r['destino'], 0) > 1:
        r['motivo_revision'] = f"Conflicto: destino '{r['destino']}' compartido por {destino_count[r['destino']]} fotos"
        conflictos.append(r)
    else:
        renombres_limpios.append(r)

# ── Verificar fotos físicas que no están en catálogo ───────────────────────
fotos_fisicas = set()
if os.path.isdir(FOTOS_DIR):
    fotos_fisicas = set(os.listdir(FOTOS_DIR))

fotos_en_plan = set(r['origen'] for r in renombres_limpios + conflictos) | set(d['origen'] for d in dudosos)
fotos_sin_entrada_catalogo = sorted(fotos_fisicas - fotos_en_plan - {'.DS_Store'})

# ── Construir el plan final ──────────────────────────────────────────────────
plan = {
    "resumen": {
        "total_fotos_en_catalogo": sum(len(v.get('fotos', [])) for v in catalogo.values()),
        "total_fotos_fisicas_en_carpeta": len([f for f in fotos_fisicas if f != '.DS_Store']),
        "total_renombres_propuestos": len(renombres_limpios),
        "total_casos_limpios": len(renombres_limpios),
        "total_conflictos_destino": len(conflictos),
        "total_dudosos": len(dudosos) + len(conflictos),
        "total_fotos_fisicas_no_en_catalogo": len(fotos_sin_entrada_catalogo)
    },
    "renombres": renombres_limpios,
    "dudosos": dudosos,
    "conflictos_destino": conflictos,
    "fotos_fisicas_no_en_catalogo": fotos_sin_entrada_catalogo
}

# ── Escribir el plan ─────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(plan, f, ensure_ascii=False, indent=2)

# ── Resumen en consola ───────────────────────────────────────────────────────
print("=" * 60)
print("RENAME PLAN — RESUMEN")
print("=" * 60)
r = plan["resumen"]
print(f"  Fotos en catálogo:           {r['total_fotos_en_catalogo']}")
print(f"  Fotos físicas en carpeta:    {r['total_fotos_fisicas_en_carpeta']}")
print(f"  Renombres limpios propuestos:{r['total_renombres_propuestos']}")
print(f"  Casos dudosos (sin nombre):  {r['total_dudosos']}")
print(f"  Conflictos de destino:       {r['total_conflictos_destino']}")
print(f"  Fotos físicas sin entrada:   {r['total_fotos_fisicas_no_en_catalogo']}")
print()
print(f"  Archivo generado: {OUTPUT_PATH}")
print()

# Muestra 20 ejemplos limpios
print("── 20 EJEMPLOS LIMPIOS ────────────────────────────────")
for item in renombres_limpios[:20]:
    print(f"  [{item['foto_codigo']}{'(Ref)' if item['es_ref'] else '     '}]")
    print(f"    origen:  {item['origen']}")
    print(f"    destino: {item['destino']}")
    print()

# Lista de casos dudosos
print("── CASOS QUE REQUIEREN REVISIÓN MANUAL ───────────────")
for item in dudosos:
    print(f"  [{item.get('foto_codigo') or item['codigoItem']}] {item['origen']}")
    print(f"    motivo: {item['motivo_revision']}")
    print()

if conflictos:
    print("── CONFLICTOS DE DESTINO ──────────────────────────────")
    for item in conflictos:
        print(f"  [{item['foto_codigo']}] {item['origen']} → {item['destino']}")
        print(f"    motivo: {item['motivo_revision']}")
        print()