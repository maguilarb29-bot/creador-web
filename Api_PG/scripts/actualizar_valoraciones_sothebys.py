"""
actualizar_valoraciones_sothebys.py

Actualiza la columna "Sotheby's" en INVENTARIO_MAESTRO con las valoraciones
reales del catálogo de Sotheby's (enero 2016), usando el archivo de referencia
docs/referencia_sothebys_pignatelli.json como fuente de verdad.

Reglas:
- Columna "Sotheby's" (J) muestra el rango de valoración del catálogo.
- La columna "Precio USD" (D) NO se toca si ya tiene valor (precio del propietario).
- Items sin referencia Sotheby's quedan como "No".
"""
from __future__ import annotations
import io, sys, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCRIPT_PATH  = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[2]
ENV_PATH     = PROJECT_ROOT / "pignatelli-app" / ".env.local"
REF_PATH     = PROJECT_ROOT / "docs" / "referencia_sothebys_pignatelli.json"
SCOPES       = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_NAME   = "INVENTARIO_MAESTRO"

# Correcciones de código: código en referencia → código en catálogo
ALIAS = {
    "S1786a": "S178a",   # Goldsmiths bowl → S178a
    "D69":    "D60",     # Loros porcelana → D60
    "S309a":  "S309",    # Portamenús (ya capturado como S309)
    "S309b":  "S309",    # ídem
}

def load_env(path):
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, v = line.split("=", 1)
        v = v.strip()
        if v.startswith('"') and v.endswith('"'): v = v[1:-1]
        env[k.strip()] = v
    return env

def get_service():
    env = load_env(ENV_PATH)
    sheet_id = env["GOOGLE_SHEETS_ID"].strip()
    private_key = env["GOOGLE_PRIVATE_KEY"].replace("\\n", "\n").strip()
    info = {
        "type": "service_account", "project_id": "inventario-pignatelli",
        "private_key_id": "", "private_key": private_key,
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

def build_sothebys_map():
    """Construye mapa codigo_catalogo → texto_valoracion desde el JSON de referencia."""
    ref = json.loads(REF_PATH.read_text(encoding="utf-8"))
    all_refs = ref.get("sothebys_references", []) + ref.get("manual_values", [])

    smap = {}  # codigo → valoracion string
    omitidos = []

    for r in all_refs:
        cod_raw = r.get("codigo_pignatelli", "").strip()
        val = (r.get("valoracion_usd") or "").strip()
        lot = r.get("referencia_sothebys", "")
        fuente = r.get("fuente", "Sotheby's").strip() or "Sotheby's"

        if not val or val == "manual":
            val_txt = r.get("notas", "").strip() or ""
        else:
            val_txt = val

        if fuente.lower() == "manual usuario" or r.get("referencia_sothebys") == "manual":
            label = f"Manual — {val_txt}"
        else:
            label = f"Lote #{lot} — {val_txt}"

        # Puede ser "A / B" — separar por / o ,
        codigos = [c.strip() for c in cod_raw.replace("/", ",").split(",") if c.strip()]
        for cod in codigos:
            real = ALIAS.get(cod, cod)
            smap[real] = label

    return smap

def main():
    print("Cargando mapa de valoraciones...")
    smap = build_sothebys_map()
    print(f"  Referencias cargadas: {len(smap)}")
    for k, v in sorted(smap.items()):
        print(f"    {k:12} → {v}")
    print()

    svc, sheet_id = get_service()

    resp = svc.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"{SHEET_NAME}!A1:O",
        valueRenderOption="UNFORMATTED_VALUE"
    ).execute()
    filas = resp.get("values", [])
    if not filas:
        print("ERROR: Hoja vacía")
        return

    headers = filas[0]
    try:
        col_codigo   = headers.index("Artículo")
    except ValueError:
        col_codigo = 0
    try:
        col_sothebys = headers.index("Sotheby's")
    except ValueError:
        print("ERROR: columna Sotheby's no encontrada:", headers)
        return
    try:
        col_precio = headers.index("Precio USD")
    except ValueError:
        col_precio = 3

    print(f"Columna código:    {chr(65+col_codigo)} (idx {col_codigo})")
    print(f"Columna Sotheby's: {chr(65+col_sothebys)} (idx {col_sothebys})")
    print(f"Columna Precio:    {chr(65+col_precio)} (idx {col_precio})")
    print()

    updates = []
    actualizados = 0
    precio_conservado = 0
    no_encontrado = []

    for i, fila in enumerate(filas[1:], start=2):
        codigo = fila[col_codigo] if col_codigo < len(fila) else ""
        if not codigo:
            continue
        if codigo in smap:
            precio_actual = fila[col_precio] if col_precio < len(fila) else ""
            val = smap[codigo]
            updates.append({
                "range": f"{SHEET_NAME}!{chr(65+col_sothebys)}{i}",
                "values": [[val]]
            })
            actualizados += 1
            if precio_actual:
                precio_conservado += 1
                tag = f"  [precio propietario: {precio_actual}]"
            else:
                tag = ""
            print(f"  {codigo}: {val}{tag}")

    # Reportar los que están en referencia pero no en hoja
    codigos_en_hoja = {(fila[col_codigo] if col_codigo < len(fila) else "") for fila in filas[1:]}
    for cod in smap:
        if cod not in codigos_en_hoja:
            no_encontrado.append(cod)

    print()
    if no_encontrado:
        print(f"En referencia pero no en hoja ({len(no_encontrado)}): {no_encontrado}")
        print()

    if not updates:
        print("No hay nada que actualizar.")
        return

    print(f"Enviando {actualizados} actualizaciones a Sheets...")
    svc.spreadsheets().values().batchUpdate(
        spreadsheetId=sheet_id,
        body={"valueInputOption": "USER_ENTERED", "data": updates}
    ).execute()

    print()
    print("=" * 60)
    print(f"VALORACIONES SOTHEBY'S ACTUALIZADAS")
    print("=" * 60)
    print(f"  Artículos actualizados:          {actualizados}")
    print(f"  Precios propietarios conservados: {precio_conservado}")
    print(f"  En referencia sin match en hoja:  {len(no_encontrado)}")

if __name__ == "__main__":
    main()
