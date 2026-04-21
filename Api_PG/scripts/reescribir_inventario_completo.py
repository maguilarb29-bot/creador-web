"""
reescribir_inventario_completo.py

Reescribe INVENTARIO_MAESTRO desde cero con:
- 510 items: 484 reales + 26 Refs
- Sin columna Condición
- Refs incluidas y marcadas con [REF] en nombre
- Precios solo donde los dueños los pusieron
- Formato completo: encabezado oscuro, filas alternas, filtros, freeze, dropdown Estado
"""
from __future__ import annotations
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCRIPT_PATH  = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[2]
ENV_PATH     = PROJECT_ROOT / "pignatelli-app" / ".env.local"
JSON_PATH    = PROJECT_ROOT / "Api_PG" / "data" / "solaris_catalogo.json"
SCOPES       = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_NAME   = "INVENTARIO_MAESTRO"

CAT_LABEL = {
    "C": "Porcelana y Cerámica", "D": "Decorativos y Arte",
    "E": "Electrodomésticos",    "F": "Muebles",
    "G": "Cristalería",          "J": "Joyería",
    "M": "Miscelánea",           "P": "Cuadros y Grabados",
    "S": "Platería",             "U": "Utensilios",
}
CAT_ORDER = {"C":0,"D":1,"E":2,"F":3,"G":4,"J":5,"M":6,"P":7,"S":8,"U":9}

# Columnas finales (sin Condición)
HEADERS = [
    "Artículo",         # A
    "Nombre",           # B
    "Categoría",        # C
    "Precio USD",       # D
    "Estado",           # E  dropdown
    "Cliente",          # F
    "Monto pagado",     # G
    "Ubicación",        # H
    "Sotheby's",        # I
    "Piezas",           # J
    "Descripción",      # K
    "Foto principal",   # L
    "Fotos adicionales",# M
    "Notas",            # N
]

def load_env(path):
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, v = line.split("=", 1); v = v.strip()
        if v.startswith('"') and v.endswith('"'): v = v[1:-1]
        env[k.strip()] = v
    return env

def get_service():
    env = load_env(ENV_PATH)
    sheet_id = env["GOOGLE_SHEETS_ID"].strip()
    pk = env["GOOGLE_PRIVATE_KEY"].replace("\\n", "\n").strip()
    info = {
        "type": "service_account", "project_id": "inventario-pignatelli",
        "private_key_id": "", "private_key": pk,
        "client_email": env["GOOGLE_SERVICE_ACCOUNT_EMAIL"].strip(),
        "client_id": "",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "",
    }
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds, cache_discovery=False), sheet_id

def c(v):
    if v is None: return ""
    s = str(v).strip()
    return "" if s.lower() in {"none","null","0.0","0"} else s

def es_ref(item):
    fotos = [str(f).strip() for f in item.get("fotos",[]) if str(f).strip()]
    if "Ref del set" in str(item.get("notas","")): return True
    return len(fotos)==1 and "-Ref-" in fotos[0]

def sort_key(item):
    cat = str(item.get("catCodigo","")).strip()
    try: num = int(item.get("numItem",0) or 0)
    except: num = 10**9
    return (CAT_ORDER.get(cat,999), num, str(item.get("codigoItem","")))

def build_row(item, ref=False):
    fotos = [str(f).strip() for f in item.get("fotos",[]) if str(f).strip()]
    foto1 = fotos[0] if fotos else ""
    fotos_extra = " | ".join(fotos[1:]) if len(fotos) > 1 else ""

    precio = item.get("precioUSD")
    if precio in (None, 0, 0.0, "0", "0.0", ""): precio = ""

    nombre = c(item.get("nombreES")) or c(item.get("descripcionOriginal"))
    if ref:
        nombre = f"[REF] {nombre}" if nombre else "[REF]"

    cat_label = CAT_LABEL.get(str(item.get("catCodigo","")), c(item.get("categoria","")))
    piezas = item.get("cantidad") or ""
    sothebys = c(item.get("refSothebysValor","")) or ("Sí" if item.get("tieneSothebys") else "No")
    notas = c(item.get("notas"))

    return [
        c(item.get("codigoItem")),  # A Artículo
        nombre,                      # B Nombre
        cat_label,                   # C Categoría
        precio,                      # D Precio USD
        "Disponible",                # E Estado
        "",                          # F Cliente
        "",                          # G Monto pagado
        c(item.get("ubicacion")),    # H Ubicación
        sothebys,                    # I Sotheby's
        piezas,                      # J Piezas
        c(item.get("descripcionES")),# K Descripción
        foto1,                       # L Foto principal
        fotos_extra,                 # M Fotos adicionales
        notas,                       # N Notas
    ]

def col_letter(n):
    return chr(65 + n)

def main():
    print("Cargando catálogo...")
    with JSON_PATH.open(encoding="utf-8") as f:
        raw = json.load(f)

    items = list(raw.values()) if isinstance(raw, dict) else raw
    items = [i for i in items if isinstance(i, dict)]
    items.sort(key=sort_key)

    rows = []
    n_refs = 0
    n_reales = 0
    for item in items:
        ref = es_ref(item)
        rows.append(build_row(item, ref=ref))
        if ref: n_refs += 1
        else: n_reales += 1

    print(f"  Items reales: {n_reales}")
    print(f"  Items Ref:    {n_refs}")
    print(f"  Total filas:  {len(rows)}")

    print("Conectando a Google Sheets...")
    svc, sheet_id = get_service()

    meta = svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheet_id_num = next(
        s["properties"]["sheetId"] for s in meta["sheets"]
        if s["properties"]["title"] == SHEET_NAME
    )

    n_cols  = len(HEADERS)
    n_filas = len(rows)

    # Limpiar y reescribir datos
    print("Limpiando hoja...")
    svc.spreadsheets().values().clear(
        spreadsheetId=sheet_id, range=f"{SHEET_NAME}!A1:Z", body={}
    ).execute()

    print("Escribiendo datos...")
    svc.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{SHEET_NAME}!A1:{col_letter(n_cols-1)}{n_filas+1}",
        valueInputOption="USER_ENTERED",
        body={"values": [HEADERS] + rows}
    ).execute()

    # Formato
    requests = []

    # Freeze fila 1
    requests.append({"updateSheetProperties": {
        "properties": {"sheetId": sheet_id_num,
                       "gridProperties": {"frozenRowCount": 1}},
        "fields": "gridProperties.frozenRowCount"
    }})

    # Filtros
    requests.append({"setBasicFilter": {"filter": {"range": {
        "sheetId": sheet_id_num, "startRowIndex": 0,
        "startColumnIndex": 0, "endColumnIndex": n_cols
    }}}})

    # Dropdown Estado (col E = índice 4)
    requests.append({"setDataValidation": {
        "range": {"sheetId": sheet_id_num, "startRowIndex": 1,
                  "endRowIndex": n_filas+1, "startColumnIndex": 4, "endColumnIndex": 5},
        "rule": {"condition": {"type": "ONE_OF_LIST", "values": [
            {"userEnteredValue": "Disponible"},
            {"userEnteredValue": "Reservado"},
            {"userEnteredValue": "Vendido"},
        ]}, "showCustomUi": True, "strict": False}
    }})

    # Encabezado: fondo oscuro, texto blanco, negrita
    requests.append({"repeatCell": {
        "range": {"sheetId": sheet_id_num, "startRowIndex": 0, "endRowIndex": 1,
                  "startColumnIndex": 0, "endColumnIndex": n_cols},
        "cell": {"userEnteredFormat": {
            "backgroundColor": {"red": 0.17, "green": 0.24, "blue": 0.31},
            "textFormat": {"foregroundColor": {"red":1,"green":1,"blue":1},
                           "bold": True, "fontSize": 11},
            "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"
        }},
        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
    }})

    # Altura encabezado
    requests.append({"updateDimensionProperties": {
        "range": {"sheetId": sheet_id_num, "dimension": "ROWS",
                  "startIndex": 0, "endIndex": 1},
        "properties": {"pixelSize": 36}, "fields": "pixelSize"
    }})

    # Anchos columnas
    anchos = [80, 220, 140, 90, 110, 160, 100, 130, 160, 60, 300, 200, 150, 200]
    for i, ancho in enumerate(anchos):
        requests.append({"updateDimensionProperties": {
            "range": {"sheetId": sheet_id_num, "dimension": "COLUMNS",
                      "startIndex": i, "endIndex": i+1},
            "properties": {"pixelSize": ancho}, "fields": "pixelSize"
        }})

    # Eliminar bandings existentes
    for s in meta["sheets"]:
        if s["properties"]["sheetId"] == sheet_id_num:
            for band in s.get("bandedRanges", []):
                requests.append({"deleteBanding": {"bandedRangeId": band["bandedRangeId"]}})

    # Filas alternas blanco / azul muy suave
    requests.append({"addBanding": {"bandedRange": {
        "bandedRangeId": 1,
        "range": {"sheetId": sheet_id_num, "startRowIndex": 1,
                  "startColumnIndex": 0, "endColumnIndex": n_cols},
        "rowProperties": {
            "headerColor":     {"red": 0.17, "green": 0.24, "blue": 0.31},
            "firstBandColor":  {"red": 1.0,  "green": 1.0,  "blue": 1.0},
            "secondBandColor": {"red": 0.95, "green": 0.97, "blue": 0.99}
        }
    }}})

    print("Aplicando formato...")
    svc.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id, body={"requests": requests}
    ).execute()

    # Ahora actualizar columna I (Sotheby's) con valoraciones reales del JSON de referencia
    REF_PATH = PROJECT_ROOT / "docs" / "referencia_sothebys_pignatelli.json"
    if REF_PATH.exists():
        ref_data = json.loads(REF_PATH.read_text(encoding="utf-8"))
        all_refs = ref_data.get("sothebys_references",[]) + ref_data.get("manual_values",[])
        ALIAS = {"S1786a":"S178a","D69":"D60","S309a":"S309","S309b":"S309"}
        smap = {}
        for r in all_refs:
            cod_raw = r.get("codigo_pignatelli","").strip()
            val = (r.get("valoracion_usd") or "").strip()
            lot = r.get("referencia_sothebys","")
            fuente = (r.get("fuente","") or "").strip()
            if fuente.lower() == "manual usuario" or lot == "manual":
                label = f"Manual — {val}"
            else:
                label = f"Lote #{lot} — {val}"
            for cod in [c.strip() for c in cod_raw.replace("/",",").split(",") if c.strip()]:
                smap[ALIAS.get(cod,cod)] = label

        # Leer códigos de la hoja recién escrita
        resp2 = svc.spreadsheets().values().get(
            spreadsheetId=sheet_id, range=f"{SHEET_NAME}!A2:A",
            valueRenderOption="UNFORMATTED_VALUE"
        ).execute()
        codigos_hoja = [r[0] if r else "" for r in resp2.get("values",[])]
        sothebys_updates = []
        for i, cod in enumerate(codigos_hoja, start=2):
            if cod in smap:
                sothebys_updates.append({
                    "range": f"{SHEET_NAME}!I{i}",
                    "values": [[smap[cod]]]
                })
        if sothebys_updates:
            svc.spreadsheets().values().batchUpdate(
                spreadsheetId=sheet_id,
                body={"valueInputOption":"USER_ENTERED","data":sothebys_updates}
            ).execute()
            print(f"  Valoraciones Sotheby's actualizadas: {len(sothebys_updates)} items")

    con_precio = sum(1 for r in rows if r[3] != "")
    sin_precio  = n_filas - con_precio

    print()
    print("=" * 55)
    print("INVENTARIO_MAESTRO — REESCRITO")
    print("=" * 55)
    print(f"  Total items:         {n_filas}")
    print(f"  Items reales:        {n_reales}")
    print(f"  Items Ref:           {n_refs}")
    print(f"  Con precio:          {con_precio}")
    print(f"  Sin precio:          {sin_precio}")
    print(f"  Columnas:            {n_cols} (A-{col_letter(n_cols-1)})")
    print()
    for i, h in enumerate(HEADERS):
        print(f"  {col_letter(i)}: {h}")

if __name__ == "__main__":
    main()
