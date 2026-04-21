"""
reconstruir_catalogo.py

Reconstruye solaris_catalogo.json desde cero con la nueva lógica.

FUENTES DE VERDAD (en orden de prioridad):
  1. Todas las Fotos/       → código, fotos, nombre del slug
  2. Carpetas categoría     → categoria de cada ítem
  3. Con valoracion Sothebys/ → tieneSothebys
  4. Reservas Herederos/    → estado Reservado + reservadoPara
  5. reservas_herederos_actual_2026-04-13.json → nombres de reservas
  6. Catálogo viejo         → precios (único dato rescatado)

LÓGICA DE CÓDIGO:
  136DC-1-slug.HEIC → codigoItem = 136DC
  136DC-2-slug.HEIC → misma entrada, segunda foto
  136DC → codigoPadre = 136D
  136D  → codigoPadre = 136
  136   → codigoPadre = None

TIPO ESTRUCTURAL:
  SET      → tiene hijos en el disco
  ARTICULO → hoja (sin hijos)
"""
import sys, io, json, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path

# ── Rutas ──────────────────────────────────────────────────────────
PROJECT  = Path("C:/Users/Alejandro/Documents/Proyecto Pignatelli")
FOTOS    = PROJECT / "Api_PG/images/fotos-Solaris-inventory"
TODAS    = FOTOS / "Todas las Fotos"
OUT      = PROJECT / "Api_PG/data/solaris_catalogo.json"
BACKUP   = PROJECT / "Api_PG/data/solaris_catalogo_backup_pre_rebuild.json"

OLD_CAT  = PROJECT / "Api_PG/data/solaris_catalogo_nuevo.json"   # temp del paso anterior
RESERVAS_JSON = PROJECT / "Api_PG/data/reservas_herederos_actual_2026-04-13.json"

VENDIDOS = {"63A", "70A", "80A", "135A"}   # vendidos a Pablo Brenes

CAT_FOLDERS = {
    "Arte en papel":     "Arte en papel",
    "Ceramica":          "Ceramica",
    "Cristaleria":       "Cristaleria",
    "Decorativos":       "Decorativos",
    "Electrodomesticos": "Electrodomesticos",
    "Insumos Medicos":   "Insumos Medicos",
    "Joyas":             "Joyas",
    "Muebles":           "Muebles",
    "Plateria":          "Plateria",
    "Utensilios":        "Utensilios",
}

EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic'}

def slug_to_nombre(slug):
    if not slug:
        return ""
    # replace hyphens, capitalize first letter only (not title case – avoids wrong caps)
    nombre = slug.replace("-", " ").strip()
    return nombre[0].upper() + nombre[1:] if nombre else ""

def derive_parent(code):
    """
    136DC  → 136D
    136D   → 136
    136    → None
    44AAA  → 44AA
    44AA   → 44A
    44A    → 44
    44     → None
    """
    m = re.match(r'^(\d+)([A-Z]*)$', code)
    if not m:
        return None
    num   = m.group(1)
    letters = m.group(2)
    if not letters:
        return None           # root number, no parent
    parent_letters = letters[:-1]
    return num + parent_letters if parent_letters else num

def sort_key(code):
    m = re.match(r'^(\d+)([A-Z]*)$', code)
    if m:
        return (int(m.group(1)), m.group(2))
    return (999999, code)

# ══════════════════════════════════════════════════════════════════
# PASO 1 — Leer todas las fotos → agrupar por código
# ══════════════════════════════════════════════════════════════════
print("PASO 1: Leyendo Todas las Fotos...")

items = {}   # code → {fotos, nombre, numItem}

for f in sorted(TODAS.iterdir()):
    if not f.is_file():
        continue
    if f.suffix.lower() not in EXTENSIONS:
        continue

    # Pattern: CODE-PHOTONUM[-slug].ext
    m = re.match(r'^([A-Z0-9]+)-(\d+)(?:-(.+?))?(?:\.[^.]+)$', f.name, re.IGNORECASE)
    if not m:
        print(f"  [SKIP] no parseable: {f.name}")
        continue

    code     = m.group(1).upper()
    slug     = m.group(3) or ""
    nombre   = slug_to_nombre(slug)
    num_m    = re.match(r'^(\d+)', code)
    num_item = int(num_m.group(1)) if num_m else 0

    if code not in items:
        items[code] = {
            "codigoItem":  code,
            "numItem":     num_item,
            "nombre":      nombre,
            "fotos":       [],
        }
    items[code]["fotos"].append(f.name)
    # Use the first photo's slug as name if current name is empty
    if nombre and not items[code]["nombre"]:
        items[code]["nombre"] = nombre

print(f"  Códigos únicos: {len(items)}")

# ══════════════════════════════════════════════════════════════════
# PASO 2 — Categorías desde carpetas
# ══════════════════════════════════════════════════════════════════
print("PASO 2: Leyendo categorías...")

code_to_cat = {}
for folder_name, cat_name in CAT_FOLDERS.items():
    folder = FOTOS / folder_name
    if not folder.exists():
        continue
    for f in folder.iterdir():
        if not f.is_file():
            continue
        m = re.match(r'^([A-Z0-9]+)-\d+', f.name, re.IGNORECASE)
        if m:
            code_to_cat[m.group(1).upper()] = cat_name

print(f"  Códigos con categoría: {len(code_to_cat)}")
sin_cat = [c for c in items if c not in code_to_cat]
if sin_cat:
    print(f"  Sin categoría ({len(sin_cat)}): {sin_cat[:10]}")

# ══════════════════════════════════════════════════════════════════
# PASO 3 — Sotheby's flag desde carpeta
# ══════════════════════════════════════════════════════════════════
print("PASO 3: Leyendo Con valoracion Sothebys...")

sothebys_codes = set()
sothebys_folder = FOTOS / "Con valoracion Sothebys"
if sothebys_folder.exists():
    for f in sothebys_folder.iterdir():
        if not f.is_file():
            continue
        m = re.match(r'^([A-Z0-9]+)-\d+', f.name, re.IGNORECASE)
        if m:
            sothebys_codes.add(m.group(1).upper())

print(f"  Códigos con Sotheby's: {len(sothebys_codes)}")

# ══════════════════════════════════════════════════════════════════
# PASO 4 — Reservas desde carpetas de herederos
# ══════════════════════════════════════════════════════════════════
print("PASO 4: Leyendo Reservas Herederos...")

reservas = {}   # code → heir_name
herederos_folder = FOTOS / "Reservas Herederos"
heir_map = {
    "Adriano PG":    "Adriano Pignatelli",
    "Diego PG":      "Diego Pignatelli",
    "Fabrizia PG":   "Fabrizia Pignatelli",
    "Margherita PG": "Margherita Pignatelli",
    "Maria Cristina":"Maria Cristina Pignatelli",
}

if herederos_folder.exists():
    for heir_folder in herederos_folder.iterdir():
        if not heir_folder.is_dir():
            continue
        heir_name = heir_map.get(heir_folder.name, heir_folder.name)
        for f in heir_folder.iterdir():
            if not f.is_file():
                continue
            mm = re.match(r'^([A-Z0-9]+)-\d+', f.name, re.IGNORECASE)
            if mm:
                code = mm.group(1).upper()
                reservas[code] = heir_name

print(f"  Ítems reservados: {len(reservas)}")
for heir in heir_map.values():
    n = sum(1 for v in reservas.values() if v == heir)
    if n:
        print(f"    {heir}: {n}")

# ══════════════════════════════════════════════════════════════════
# PASO 5 — Precios del catálogo viejo (único dato rescatado)
# ══════════════════════════════════════════════════════════════════
print("PASO 5: Rescatando precios del catálogo anterior...")

old_prices = {}   # code → precioUSD
if OLD_CAT.exists():
    old_raw = json.loads(OLD_CAT.read_text(encoding="utf-8-sig"))
    old_items = old_raw if isinstance(old_raw, list) else list(old_raw.values())
    for it in old_items:
        cod = it.get("codigoItem", "")
        precio = it.get("precioUSD")
        if precio and precio not in (None, 0, "", "0"):
            old_prices[cod] = precio

print(f"  Precios rescatados: {len(old_prices)}")

# ══════════════════════════════════════════════════════════════════
# PASO 6 — Determinar jerarquía (padre / tipoEstructural)
# ══════════════════════════════════════════════════════════════════
print("PASO 6: Calculando jerarquía...")

all_codes = set(items.keys())

# A code is a SET if any other code has it as parent
parents_in_use = set()
for code in all_codes:
    p = derive_parent(code)
    if p:
        parents_in_use.add(p)

# ══════════════════════════════════════════════════════════════════
# PASO 7 — Construir catálogo final
# ══════════════════════════════════════════════════════════════════
print("PASO 7: Construyendo catálogo...")

catalog = []

for code in sorted(all_codes, key=sort_key):
    entry = items[code]
    fotos = entry["fotos"]
    nombre = entry["nombre"]
    num_item = entry["numItem"]

    parent_code = derive_parent(code)
    is_set      = code in parents_in_use
    tipo        = "SET" if is_set else "ARTICULO"

    # Estado
    if code in VENDIDOS:
        estado = "Vendido"
        reservado_para = "Pablo Brenes"
    elif code in reservas:
        estado = "Reservado"
        reservado_para = reservas[code]
    else:
        estado = "Disponible"
        reservado_para = ""

    item = {
        "codigoItem":        code,
        "codigoPadre":       parent_code or "",
        "numItem":           num_item,
        "tipoEstructural":   tipo,
        "categoria":         code_to_cat.get(code, "Sin clasificar"),
        "nombreES":          nombre,
        "descripcionES":     "",
        "fotos":             fotos,
        "tieneSothebys":     code in sothebys_codes,
        "refSothebys":       "",
        "paginaSothebys":    "",
        "estimacionSothebys":"",
        "descripcionSothebys":"",
        "estado":            estado,
        "reservadoPara":     reservado_para,
        "precioUSD":         old_prices.get(code),
        "cantidad":          len(fotos),
        "notas":             "",
    }
    catalog.append(item)

print(f"  Total ítems: {len(catalog)}")

# ══════════════════════════════════════════════════════════════════
# PASO 8 — Backup + guardar
# ══════════════════════════════════════════════════════════════════
print("PASO 8: Guardando...")

# Backup del catálogo anterior
old_original = PROJECT / "Api_PG/data/solaris_catalogo.json"
if old_original.exists():
    BACKUP.write_bytes(old_original.read_bytes())
    print(f"  Backup: {BACKUP.name}")

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(catalog, f, ensure_ascii=False, indent=2)

print(f"  Guardado: {OUT.name}")

# ══════════════════════════════════════════════════════════════════
# RESUMEN
# ══════════════════════════════════════════════════════════════════
sets_n       = sum(1 for it in catalog if it["tipoEstructural"] == "SET")
articulos_n  = sum(1 for it in catalog if it["tipoEstructural"] == "ARTICULO")
reservados_n = sum(1 for it in catalog if it["estado"] == "Reservado")
vendidos_n   = sum(1 for it in catalog if it["estado"] == "Vendido")
sothebys_n   = sum(1 for it in catalog if it["tieneSothebys"])
con_precio   = sum(1 for it in catalog if it["precioUSD"])

cats = {}
for it in catalog:
    c = it["categoria"]
    cats[c] = cats.get(c, 0) + 1

print()
print("=" * 55)
print("CATÁLOGO RECONSTRUIDO")
print("=" * 55)
print(f"  Total ítems:       {len(catalog)}")
print(f"  SETs (con hijos):  {sets_n}")
print(f"  ARTÍCULOs (hoja):  {articulos_n}")
print(f"  Disponibles:       {len(catalog) - reservados_n - vendidos_n}")
print(f"  Reservados:        {reservados_n}")
print(f"  Vendidos:          {vendidos_n}")
print(f"  Con Sotheby's:     {sothebys_n}")
print(f"  Con precio:        {con_precio}")
print()
print("  Por categoría:")
for cat, n in sorted(cats.items(), key=lambda x: -x[1]):
    print(f"    {n:4d}  {cat}")
