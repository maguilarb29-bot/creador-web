"""
actualizar_sheets_estructura.py

1. Fusiona medidas en descripcionES de INVENTARIO_MAESTRO
2. Elimina columna refSothebys — conserva solo tieneSothebys (TRUE/FALSE)
3. Agrega columnas: estadoComercial, reservadoPara, visibleWeb
4. Actualiza HEADERS finales
5. Elimina hojas MEDICIONES y SOTHEBYS
"""
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Any
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[2]
ENV_PATH     = PROJECT_ROOT / "pignatelli-app" / ".env.local"
JSON_PATH    = PROJECT_ROOT / "Api_PG" / "data" / "solaris_catalogo.json"

SHEET_NAME   = "INVENTARIO_MAESTRO"
SCOPES       = ["https://www.googleapis.com/auth/spreadsheets"]

# Headers finales — refSothebys eliminado, medidas integrado en descripcionES
# Se agregan estadoComercial, reservadoPara, visibleWeb
HEADERS = [
    "codigoItem",       # A
    "nombreES",         # B
    "descripcionES",    # C  ← incluye medidas si las tiene
    "categoria",        # D
    "catCodigo",        # E
    "ubicacion",        # F
    "precioUSD",        # G
    "tieneSothebys",    # H  ← TRUE/FALSE, única columna Sotheby's
    "cantidad",         # I
    "materiales",       # J
    "estilo",           # K
    "estado",           # L
    "estadoComercial",  # M  ← disponible / reservado / vendido
    "reservadoPara",    # N
    "visibleWeb",       # O  ← TRUE/FALSE
    "foto1",            # P
    "foto2",            # Q
    "foto3",            # R
    "notas",            # S
]

CAT_ORDER = {"C":0,"D":1,"E":2,"F":3,"G":4,"J":5,"M":6,"P":7,"S":8,"U":9}


def load_env(path: Path) -> dict[str,str]:
    env: dict[str,str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k,v = line.split("=",1)
        v = v.strip()
        if v.startswith('"') and v.endswith('"'): v = v[1:-1]
        env[k.strip()] = v
    return env


def get_service():
    env = load_env(ENV_PATH)
    sheet_id = env["GOOGLE_SHEETS_ID"].strip()
    private_key = env["GOOGLE_PRIVATE_KEY"].replace("\\n", "\n").strip()
    info = {
        "type": "service_account",
        "project_id": "inventario-pignatelli",
        "private_key_id": "",
        "private_key": private_key,
        "client_email": env["GOOGLE_SERVICE_ACCOUNT_EMAIL"].strip(),
        "client_id": "",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "",
    }
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    svc = build("sheets", "v4", credentials=creds, cache_discovery=False)
    return svc, sheet_id


def is_ref_photo(name: str) -> bool:
    return bool(re.search(r"(^|[-_\s])ref([-. _]|$)", name, re.IGNORECASE))

def es_ref_item(item: dict) -> bool:
    fotos = [str(f).strip() for f in item.get("fotos",[]) if str(f).strip()]
    if "Ref del set" in str(item.get("notas","")):
        return True
    return len(fotos) == 1 and is_ref_photo(fotos[0])

def compact(v) -> str:
    if v is None: return ""
    s = str(v).strip()
    return "" if s.lower() in {"none","null"} else s

def sort_key(item: dict):
    cat = str(item.get("catCodigo","")).strip()
    try: num = int(item.get("numItem",0) or 0)
    except: num = 10**9
    return (CAT_ORDER.get(cat,999), num, str(item.get("codigoItem","")))

def build_descripcion(item: dict) -> str:
    """Fusiona descripcionES + medidas si existen."""
    desc = compact(item.get("descripcionES"))
    medidas = compact(item.get("medidas") or item.get("dimensiones") or item.get("tamano") or "")
    if medidas and medidas not in desc:
        return f"{desc} | Medidas: {medidas}".strip(" |")
    return desc

def split_photos(fotos: list) -> tuple:
    clean = [f.strip() for f in fotos if str(f).strip()]
    f1 = clean[0] if len(clean) > 0 else ""
    f2 = clean[1] if len(clean) > 1 else ""
    f3 = " | ".join(clean[2:]) if len(clean) > 2 else ""
    return f1, f2, f3

def build_row(item: dict) -> list:
    fotos = [str(f).strip() for f in item.get("fotos",[]) if str(f).strip()]
    f1,f2,f3 = split_photos(fotos)
    precio = item.get("precioUSD")
    if precio in (None, 0, 0.0, "0", "0.0"): precio = ""
    nombre = compact(item.get("nombreES")) or compact(item.get("descripcionOriginal"))
    notas = compact(item.get("notas"))
    if not compact(item.get("nombreES")) and compact(item.get("descripcionOriginal")):
        notas = (notas + " | PENDIENTE NOMBRE").strip(" |")

    return [
        compact(item.get("codigoItem")),   # A codigoItem
        nombre,                            # B nombreES
        build_descripcion(item),           # C descripcionES (+ medidas)
        compact(item.get("categoria")),    # D categoria
        compact(item.get("catCodigo")),    # E catCodigo
        compact(item.get("ubicacion")),    # F ubicacion
        precio,                            # G precioUSD
        "TRUE" if item.get("tieneSothebys") else "FALSE",  # H tieneSothebys
        item.get("cantidad") or 1,         # I cantidad
        compact(item.get("materiales")),   # J materiales
        compact(item.get("estilo")),       # K estilo
        compact(item.get("estado")),       # L estado
        "disponible",                      # M estadoComercial
        "",                                # N reservadoPara
        "FALSE",                           # O visibleWeb
        f1,                                # P foto1
        f2,                                # Q foto2
        f3,                                # R foto3
        notas,                             # S notas
    ]


def main():
    print("Cargando catalogo JSON...")
    with JSON_PATH.open(encoding="utf-8") as f:
        raw = json.load(f)
    items = list(raw.values()) if isinstance(raw, dict) else raw
    items = [i for i in items if isinstance(i, dict) and not es_ref_item(i)]
    items.sort(key=sort_key)
    rows = [build_row(i) for i in items]
    print(f"  Articulos a escribir: {len(rows)}")

    print("Conectando a Google Sheets...")
    svc, sheet_id = get_service()

    # Obtener metadatos de hojas
    meta = svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
    hojas = {s['properties']['title']: s['properties']['sheetId'] for s in meta['sheets']}
    print(f"  Hojas existentes: {list(hojas.keys())}")

    # Actualizar INVENTARIO_MAESTRO
    print("Actualizando INVENTARIO_MAESTRO...")
    svc.spreadsheets().values().clear(
        spreadsheetId=sheet_id,
        range=f"{SHEET_NAME}!A1:Z",
        body={}
    ).execute()

    svc.spreadsheets().values().batchUpdate(
        spreadsheetId=sheet_id,
        body={
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": f"{SHEET_NAME}!A1:S1", "values": [HEADERS]},
                {"range": f"{SHEET_NAME}!A2:S{len(rows)+1}", "values": rows},
            ]
        }
    ).execute()
    print(f"  Escrito: {len(rows)} filas con {len(HEADERS)} columnas")

    # Eliminar hojas MEDICIONES y SOTHEBYS si existen
    hojas_eliminar = ["MEDICIONES", "SOTHEBYS"]
    requests = []
    for nombre_hoja in hojas_eliminar:
        if nombre_hoja in hojas:
            requests.append({"deleteSheet": {"sheetId": hojas[nombre_hoja]}})
            print(f"  Eliminando hoja: {nombre_hoja}")
        else:
            print(f"  Hoja no encontrada (ya eliminada?): {nombre_hoja}")

    if requests:
        svc.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": requests}
        ).execute()

    # Resumen
    con_sothebys   = sum(1 for r in rows if r[7] == "TRUE")
    sin_precio     = sum(1 for r in rows if r[6] == "")
    sin_desc       = sum(1 for r in rows if not str(r[2]).strip())
    pendiente_nombre = sum(1 for r in rows if "PENDIENTE NOMBRE" in str(r[18]))

    print()
    print("=" * 50)
    print(f"Filas escritas:          {len(rows)}")
    print(f"Con referencia Sothebys: {con_sothebys}")
    print(f"Sin precio:              {sin_precio}")
    print(f"Sin descripcion:         {sin_desc}")
    print(f"Pendiente nombre:        {pendiente_nombre}")
    print(f"Columnas:                {len(HEADERS)} (A-S)")
    print("=" * 50)
    print()
    print("Headers finales:")
    for i, h in enumerate(HEADERS):
        print(f"  {chr(65+i)}: {h}")


if __name__ == "__main__":
    main()
