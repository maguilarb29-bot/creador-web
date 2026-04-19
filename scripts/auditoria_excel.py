"""
Auditoría completa de coherencia de datos antes de entregar el Excel.
Cruza: fotos_estructura, catálogo, reservas (JSON+CSV), Sotheby's
"""
import json, csv, re
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).resolve().parent.parent

# ── Cargar datos ──────────────────────────────────────────────────────────────
with open(BASE / "Api_PG/data/solaris_fotos_estructura.json", encoding="utf-8-sig") as f:
    fotos_estructura = json.load(f)

with open(BASE / "Api_PG/data/solaris_catalogo.json", encoding="utf-8-sig") as f:
    catalogo = json.load(f)

with open(BASE / "Api_PG/data/reservas_herederos_actual_2026-04-13.json", encoding="utf-8-sig") as f:
    reservas_json = json.load(f)

def leer_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows

reservas_csv = leer_csv(BASE / "docs/reservas_herederos_maestro_2026-04-13.csv")
sothebys_csv = leer_csv(BASE / "docs/sothebys_maestro_2026-04-13.csv")

def extraer_base(raw):
    first = raw.split(";")[0].strip()
    return re.sub(r"-\d+$", "", first).strip()

SEP = "=" * 70

print(SEP)
print("AUDITORIA GENERAL --- PROYECTO PIGNATELLI / CONDOMINIO SOLARIS")
print(SEP)

# ── 1. Fotos estructura ───────────────────────────────────────────────────────
total_fotos = sum(len(item.get("fotos", [])) for item in fotos_estructura.values())
print(f"\n[1] FOTOS_ESTRUCTURA")
print(f"    Articulos registrados : {len(fotos_estructura)}")
print(f"    Fotos registradas     : {total_fotos}")

# ── 2. Catalogo ───────────────────────────────────────────────────────────────
print(f"\n[2] CATALOGO (solaris_catalogo.json)")
print(f"    Articulos en catalogo : {len(catalogo)}")
cat_por_cat = defaultdict(int)
sin_nombre = []
sin_codigo = []
codigos_catalogo = set()
for art in catalogo:
    cod  = art.get("codigoItem", "").strip()
    nom  = (art.get("nombreES") or art.get("nombre") or "").strip()
    cat_por_cat[art.get("categoria", "SIN_CAT")] += 1
    if not nom or nom == "-":
        sin_nombre.append(cod)
    if not cod:
        sin_codigo.append(art)
    codigos_catalogo.add(cod)

print(f"    Sin nombre            : {len(sin_nombre)}")
if sin_nombre[:8]:
    print(f"      Ej: {sin_nombre[:8]}")
print(f"    Sin codigo            : {len(sin_codigo)}")
print(f"    Por categoria:")
for cat, n in sorted(cat_por_cat.items()):
    print(f"      {cat:<22} {n}")

# ── 3. Reservas interna ───────────────────────────────────────────────────────
print(f"\n[3] RESERVAS CSV")
print(f"    Total items reservados: {len(reservas_csv)}")
heredero_count = defaultdict(int)
codigos_reservados = set()
duplicados = []
seen = set()
for r in reservas_csv:
    cod = r["codigo"].strip()
    heredero_count[r["heredero"]] += 1
    if cod in seen:
        duplicados.append(cod)
    seen.add(cod)
    codigos_reservados.add(cod)

print(f"    Duplicados de codigo  : {len(duplicados)}")
if duplicados:
    print(f"      -> {duplicados}")
print(f"    Por heredero:")
for h, n in heredero_count.items():
    print(f"      {h:<28} {n}")

# ── 4. Reservas vs Catalogo ───────────────────────────────────────────────────
print(f"\n[4] CRUCE Reservas vs Catalogo")
no_en_cat = [(r["codigo"], r["nombre"], r["heredero"])
             for r in reservas_csv if r["codigo"].strip() not in codigos_catalogo]
print(f"    En catalogo           : {len(reservas_csv) - len(no_en_cat)}")
print(f"    SIN codigo en catalogo: {len(no_en_cat)}")
for cod, nom, her in no_en_cat:
    print(f"      FALTA: {cod} ({nom}) -> {her}")

# ── 5. Reservas vs Fotos ──────────────────────────────────────────────────────
fotos_por_cod = {cod: item.get("fotos",[])
                 for cod, item in fotos_estructura.items()}
print(f"\n[5] CRUCE Reservas vs Fotos_Estructura")
sin_fotos = []
con_fotos = []
for r in reservas_csv:
    cod = r["codigo"].strip()
    if fotos_por_cod.get(cod):
        con_fotos.append(cod)
    else:
        sin_fotos.append((cod, r["nombre"], r["cantidad_fotos"]))
print(f"    Con fotos en estructura: {len(con_fotos)}")
print(f"    SIN fotos en estructura: {len(sin_fotos)}")
for cod, nom, nf in sin_fotos:
    print(f"      SIN FOTOS: {cod} ({nom}, esperadas:{nf})")

# ── 6. Sothebys vs Catalogo ───────────────────────────────────────────────────
print(f"\n[6] CRUCE Sothebys vs Catalogo")
print(f"    Total refs Sothebys   : {len(sothebys_csv)}")
soth_no_cat = []
soth_codigos = set()
for s in sothebys_csv:
    for parte in s.get("codigo_actual","").split(";"):
        base = extraer_base(parte)
        if not base:
            continue
        soth_codigos.add(base)
        if base not in codigos_catalogo:
            soth_no_cat.append((base, s.get("descripcion_sothebys","")[:55]))
print(f"    En catalogo           : {len(soth_codigos) - len(soth_no_cat)}")
print(f"    SIN codigo en catalogo: {len(soth_no_cat)}")
for cod, desc in soth_no_cat:
    print(f"      FALTA: {cod!r:<12} {desc}")

# ── 7. Sothebys vs Reservas ───────────────────────────────────────────────────
print(f"\n[7] CRUCE Sothebys vs Reservas")
con_tasacion = codigos_reservados & soth_codigos
sin_tasacion = codigos_reservados - soth_codigos
print(f"    Reservados CON tasacion: {len(con_tasacion)}")
print(f"    Reservados SIN tasacion: {len(sin_tasacion)}")
for cod in sorted(sin_tasacion):
    nom = next((r["nombre"] for r in reservas_csv if r["codigo"] == cod), "?")
    her = next((r["heredero"] for r in reservas_csv if r["codigo"] == cod), "?")
    cat = next((r["categoria"] for r in reservas_csv if r["codigo"] == cod), "?")
    print(f"      {cod:<12} {cat:<18} {nom:<38} ({her})")

# ── 8. JSON vs CSV coherencia ─────────────────────────────────────────────────
print(f"\n[8] COHERENCIA JSON vs CSV de reservas")
codigos_json = set()
for heir in reservas_json.get("heirs", []):
    for item in heir.get("items", []):
        codigos_json.add(item["codigo"])
solo_json = codigos_json - codigos_reservados
solo_csv  = codigos_reservados - codigos_json
print(f"    Solo en JSON (no en CSV): {len(solo_json)}")
if solo_json:
    print(f"      -> {sorted(solo_json)}")
print(f"    Solo en CSV (no en JSON): {len(solo_csv)}")
if solo_csv:
    print(f"      -> {sorted(solo_csv)}")

# ── 9. Nombres catalogo vs reservas ──────────────────────────────────────────
print(f"\n[9] NOMBRES: Catalogo vs Reservas (items en comun)")
nom_cat = {art.get("codigoItem","").strip(): (art.get("nombreES") or art.get("nombre") or "").strip() for art in catalogo}
disc = []
for r in reservas_csv:
    cod = r["codigo"].strip()
    nr  = r["nombre"].strip()
    nc  = nom_cat.get(cod, "")
    if nc and nr and nc.lower() != nr.lower():
        disc.append((cod, nr, nc))
print(f"    Discrepancias de nombre: {len(disc)}")
for cod, nr, nc in disc:
    print(f"      {cod}: reserva='{nr}'")
    print(f"           catalogo='{nc}'")

# ── 10. Categorias reservadas: consistencia letra-codigo ─────────────────────
print(f"\n[10] CATEGORIAS: letra del codigo vs categoria declarada")
CAT_LETRA = {"G": "Cristaleria", "P": "Arte en papel", "S": "Plateria",
             "U": "Utensilios", "D": "Decorativos", "J": "Joyas", "F": "Muebles",
             "C": "Ceramica", "M": "Misc", "E": "Electronics"}
cat_errors = []
for r in reservas_csv:
    cod = r["codigo"].strip()
    cat_declarada = r["categoria"].strip()
    letra = re.sub(r"\d.*", "", cod)  # primera parte no numerica
    cat_esperada = CAT_LETRA.get(letra.upper())
    if cat_esperada and cat_esperada.lower() != cat_declarada.lower():
        cat_errors.append((cod, cat_declarada, cat_esperada))
print(f"    Inconsistencias cat/letra: {len(cat_errors)}")
for cod, cd, ce in cat_errors:
    print(f"      {cod}: declarada='{cd}' esperada='{ce}'")

# ── RESUMEN FINAL ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("RESUMEN EJECUTIVO")
print(SEP)
issues = []
if duplicados:
    issues.append(f"  PROBLEMA: {len(duplicados)} codigo(s) duplicado(s) en reservas: {duplicados}")
if no_en_cat:
    issues.append(f"  PROBLEMA: {len(no_en_cat)} reserva(s) con codigo inexistente en catalogo")
if sin_fotos:
    issues.append(f"  PROBLEMA: {len(sin_fotos)} reserva(s) sin fotos en estructura")
if soth_no_cat:
    issues.append(f"  ATENCION: {len(soth_no_cat)} ref(s) Sothebys con codigo fuera del catalogo actual")
if solo_json or solo_csv:
    issues.append(f"  ATENCION: desincronia JSON/CSV: solo_JSON={sorted(solo_json)}, solo_CSV={sorted(solo_csv)}")
if disc:
    issues.append(f"  ATENCION: {len(disc)} nombre(s) diferente entre reservas y catalogo")
if cat_errors:
    issues.append(f"  ATENCION: {len(cat_errors)} categoria(s) inconsistente con letra del codigo")

if not issues:
    print("  TODO ALINEADO -- sin inconsistencias criticas detectadas")
else:
    for i in issues:
        print(i)

print(f"\nResumen numerico:")
print(f"  Fotos en estructura : {total_fotos} (artículos: {len(fotos_estructura)})")
print(f"  Articulos catalogo  : {len(catalogo)}")
print(f"  Items reservados    : {len(reservas_csv)} ({len(codigos_reservados)} unicos)")
print(f"  Refs Sothebys       : {len(sothebys_csv)} ({len(soth_codigos)} codigos base)")
print(f"  Tasados reservados  : {len(con_tasacion)} / {len(codigos_reservados)}")
