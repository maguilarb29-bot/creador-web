"""
migrar_catalogo_nuevo_formato.py

Migra solaris_catalogo.json al nuevo formato de códigos:
  - Elimina todos los códigos OLD (F77, C136a, D7b...)
  - Convierte al nuevo formato basado en disco (77A, 136A, 7B...)
  - Agrega los 277 ítems que están en disco pero no en catálogo
  - Fuente de verdad: Todas las Fotos/ + carpetas de categoría
"""
import sys, io, json, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path

PROJECT = Path("C:/Users/Alejandro/Documents/Proyecto Pignatelli")
FOTOS   = PROJECT / "Api_PG/images/fotos-Solaris-inventory"
TODAS   = FOTOS / "Todas las Fotos"
CATALOGO = PROJECT / "Api_PG/data/solaris_catalogo.json"
CATALOGO_OUT = PROJECT / "Api_PG/data/solaris_catalogo_nuevo.json"

CAT_FOLDERS = {
    "Arte en papel":    "Arte en papel",
    "Ceramica":         "Ceramica",
    "Cristaleria":      "Cristaleria",
    "Decorativos":      "Decorativos",
    "Electrodomesticos":"Electrodomesticos",
    "Insumos Medicos":  "Insumos Medicos",
    "Joyas":            "Joyas",
    "Muebles":          "Muebles",
    "Plateria":         "Plateria",
    "Utensilios":       "Utensilios",
}

# ─── 1. BUILD DISK MAP ──────────────────────────────────────────────
print("=== PASO 1: Leyendo disco ===")
disk = {}   # code -> {fotos: [], nombre: str, categoria: str}

# Category from folders
code_to_cat = {}
for folder_name, cat_name in CAT_FOLDERS.items():
    folder = FOTOS / folder_name
    if not folder.exists(): continue
    for f in folder.iterdir():
        if not f.is_file(): continue
        m = re.match(r'^([A-Z0-9]+)-\d+', f.name, re.IGNORECASE)
        if m:
            code_to_cat[m.group(1).upper()] = cat_name

# Files from Todas las Fotos
for f in sorted(TODAS.iterdir()):
    if not f.is_file(): continue
    ext = f.suffix.lower()
    if ext not in ('.jpg','.jpeg','.png','.heic'): continue
    m = re.match(r'^([A-Z0-9]+)-(\d+)(?:-(.+?))?(?:\.[^.]+)$', f.name, re.IGNORECASE)
    if not m: continue
    code = m.group(1).upper()
    slug = m.group(3) or ""
    nombre = slug.replace("-", " ").title() if slug else ""
    if code not in disk:
        disk[code] = {"fotos": [], "nombre": nombre, "categoria": code_to_cat.get(code, "Sin clasificar")}
    disk[code]["fotos"].append(f.name)

print(f"  Codigos en disco: {len(disk)}")

# ─── 2. OLD→NEW CODE CONVERSION ─────────────────────────────────────
def old_to_new(old_code):
    """
    F77   → 77A    (letra categ + numero sin sub → numero + A)
    C136a → 136A   (letra categ + numero + subletra → numero + MAYUS)
    C136ca→ 136CA  (letra categ + numero + 2subletras → numero + MAYUS2)
    D7a   → 7A
    """
    m = re.match(r'^([A-Z])(\d+)([a-z]*)$', old_code)
    if not m: return old_code  # ya es nuevo o desconocido
    num   = m.group(2)
    sub   = m.group(3).upper()
    if not sub:
        sub = "A"  # single item gets A
    return num + sub

# ─── 3. LOAD EXISTING CATALOG ───────────────────────────────────────
print("\n=== PASO 2: Cargando catálogo actual ===")
raw = json.loads(CATALOGO.read_text(encoding="utf-8-sig"))
old_items = list(raw.values()) if isinstance(raw, dict) else raw
print(f"  Items actuales: {len(old_items)}")

# Build new catalog dict keyed by new code
new_catalog = {}

old_count = new_count = skip_count = 0

for it in old_items:
    old_code = it.get("codigoItem", "")
    # Determine new code
    if re.match(r'^[A-Z]\d', old_code):
        new_code = old_to_new(old_code)
        old_count += 1
    else:
        new_code = old_code  # already new format or number-only
        new_count += 1

    # Get real fotos from disk
    disk_entry = disk.get(new_code, {})
    fotos_disk = disk_entry.get("fotos", [])

    # Update item
    it["codigoItem"] = new_code
    it["catCodigo"]  = ""   # no longer needed, category is in 'categoria'
    if fotos_disk:
        it["fotos"] = fotos_disk if len(fotos_disk) > 1 else fotos_disk[0]
        # Update nombre from disk slug if current nombre is empty or generic
        disk_nombre = disk_entry.get("nombre", "")
        if disk_nombre and (not it.get("nombreES") or it.get("nombreES") == it.get("descripcionOriginal","")):
            it["nombreES"] = disk_nombre

    # Update categoria from disk if available
    if disk_entry.get("categoria"):
        it["categoria"] = disk_entry["categoria"]

    if new_code in new_catalog:
        # Merge fotos if duplicate
        existing = new_catalog[new_code]
        ex_fotos = existing.get("fotos", [])
        if isinstance(ex_fotos, str): ex_fotos = [ex_fotos]
        if isinstance(fotos_disk, str): fotos_disk = [fotos_disk]
        merged = list(dict.fromkeys(ex_fotos + fotos_disk))
        existing["fotos"] = merged
        print(f"  MERGE: {old_code} → {new_code} (ya existía)")
    else:
        new_catalog[new_code] = it

print(f"  Convertidos OLD→NEW: {old_count}")
print(f"  Ya en nuevo formato: {new_count}")

# ─── 4. ADD MISSING DISK ITEMS ──────────────────────────────────────
print("\n=== PASO 3: Agregando ítems faltantes del disco ===")
added = 0
for code, entry in sorted(disk.items(), key=lambda x: (int(re.search(r'\d+',x[0]).group()), x[0])):
    if code in new_catalog:
        continue
    # New item from disk only
    nombre = entry["nombre"]
    fotos  = entry["fotos"]
    num_m  = re.search(r'\d+', code)
    num_item = int(num_m.group()) if num_m else 0

    new_item = {
        "codigoItem": code,
        "catCodigo": "",
        "categoria": entry["categoria"],
        "numItem": num_item,
        "nombreES": nombre,
        "descripcionES": "",
        "descripcionOriginal": "",
        "fotos": fotos if len(fotos) > 1 else fotos[0],
        "refs": [],
        "ubicacion": "",
        "precioUSD": None,
        "tieneSothebys": False,
        "refSothebys": "",
        "notas": "",
        "cantidad": 1,
        "materiales": "",
        "estilo": "",
        "estado": "",
        "paginaSothebys": "",
        "estimacionSothebys": "",
        "descripcionSothebys": "",
        "codigoPadre": "",
        "tipoEstructural": "",
    }
    new_catalog[code] = new_item
    added += 1

print(f"  Items nuevos agregados: {added}")

# ─── 5. SORT & SAVE ─────────────────────────────────────────────────
print("\n=== PASO 4: Ordenando y guardando ===")

def sort_key(code):
    m = re.match(r'^(\d+)([A-Z]*)$', code)
    if m:
        return (int(m.group(1)), m.group(2))
    return (999999, code)

sorted_items = sorted(new_catalog.values(), key=lambda x: sort_key(x.get("codigoItem","")))

with open(CATALOGO_OUT, "w", encoding="utf-8") as f:
    json.dump(sorted_items, f, ensure_ascii=False, indent=2)

print(f"  Guardado: {CATALOGO_OUT.name}")
print(f"  Total items: {len(sorted_items)}")

# ─── 6. RESUMEN ─────────────────────────────────────────────────────
print()
print("=" * 55)
print("MIGRACIÓN COMPLETA")
print("=" * 55)
print(f"  Catálogo anterior:   {len(old_items)} items")
print(f"  Catálogo nuevo:      {len(sorted_items)} items")
print(f"  Códigos OLD→NEW:     {old_count}")
print(f"  Items nuevos (disco):{added}")

