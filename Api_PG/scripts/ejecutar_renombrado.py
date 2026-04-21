"""
ejecutar_renombrado.py
Lee rename_plan.json y renombra físicamente las fotos en disco.
También actualiza las referencias en solaris_catalogo.json.
"""
import json, os, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE       = "C:/Users/Alejandro/Documents/Proyecto Pignatelli/Api_PG"
FOTOS_DIR  = f"{BASE}/images/fotos-Solaris-inventory"
PLAN_PATH  = f"{BASE}/data/rename_plan.json"
CATALOGO   = f"{BASE}/data/solaris_catalogo.json"

plan    = json.load(open(PLAN_PATH, encoding='utf-8'))
catalogo = json.load(open(CATALOGO, encoding='utf-8'))

renombres = plan['renombres']
ok = 0
err = 0
ya_existia = 0
log = []

print("=" * 60)
print(f"EJECUTAR RENOMBRADO — {len(renombres)} archivos")
print("=" * 60)

# Construir mapa origen→destino para actualizar catálogo después
mapa = {}

for item in renombres:
    origen  = item['origen']
    destino = item['destino']

    ruta_origen  = os.path.join(FOTOS_DIR, origen)
    ruta_destino = os.path.join(FOTOS_DIR, destino)

    # Ya tiene el nombre correcto
    if origen == destino:
        ya_existia += 1
        mapa[origen] = destino
        continue

    # Origen no existe en disco
    if not os.path.isfile(ruta_origen):
        print(f"  [NO ENCONTRADO] {origen}")
        err += 1
        log.append({"status": "error", "motivo": "archivo no encontrado", "origen": origen, "destino": destino})
        continue

    # Destino ya existe (colisión inesperada)
    if os.path.isfile(ruta_destino) and origen != destino:
        print(f"  [COLISION] {destino} ya existe — omitido")
        err += 1
        log.append({"status": "error", "motivo": "destino ya existe", "origen": origen, "destino": destino})
        continue

    try:
        os.rename(ruta_origen, ruta_destino)
        mapa[origen] = destino
        ok += 1
        if ok <= 30 or ok % 50 == 0:
            print(f"  [{item['foto_codigo']}] {origen}")
            print(f"    -> {destino}")
    except Exception as e:
        print(f"  [ERROR] {origen}: {e}")
        err += 1
        log.append({"status": "error", "motivo": str(e), "origen": origen, "destino": destino})

# ── Actualizar solaris_catalogo.json con los nuevos nombres ──────────────────
print()
print("Actualizando catálogo JSON...")
cambios_cat = 0
for codigo, item in catalogo.items():
    fotos_nuevas = []
    for foto in item.get('fotos', []):
        nuevo = mapa.get(foto, foto)
        fotos_nuevas.append(nuevo)
        if nuevo != foto:
            cambios_cat += 1
    item['fotos'] = fotos_nuevas

json.dump(catalogo, open(CATALOGO, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"  Referencias actualizadas en catálogo: {cambios_cat}")

# ── Guardar log ───────────────────────────────────────────────────────────────
log_path = f"{BASE}/data/rename_log.json"
json.dump({"ok": ok, "errores": err, "log": log}, open(log_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

print()
print("=" * 60)
print(f"COMPLETADO")
print(f"  Renombrados:  {ok}")
print(f"  Errores:      {err}")
print(f"  Ya correctos: {ya_existia}")
print(f"  Log:          {log_path}")
print("=" * 60)
