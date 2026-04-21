"""
pulir_inventario_maestro.py
Reorganiza INVENTARIO_MAESTRO para uso real por la familia:
- Reordena columnas: principales primero, técnicas al final
- Renombra columnas al español natural
- Agrega columnas cliente y monto (vacías)
- Dropdown en estado: Disponible / Reservado / Vendido
- Congela fila 1
- Activa filtros
- NO toca datos
"""
from __future__ import annotations
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCRIPT_PATH  = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[2]
ENV_PATH     = PROJECT_ROOT / "pignatelli-app" / ".env.local"
SCOPES       = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_NAME   = "INVENTARIO_MAESTRO"

# Orden final de columnas — reordenado lógicamente
# PRINCIPALES (lo que la familia necesita ver primero)
# TÉCNICAS (al final)
NUEVO_ORDEN = [
    # Col  Nombre visible          # origen actual
    ("Artículo",       "Código"),           # A
    ("Nombre",         "Nombre"),           # B
    ("Categoría",      "Categoría"),        # C
    ("Precio USD",     "Precio USD"),       # D
    ("Estado",         "Disponibilidad"),   # E  ← dropdown
    ("Cliente",        None),               # F  ← nueva columna vacía
    ("Monto pagado",   None),               # G  ← nueva columna vacía
    ("Condición",      "Condición"),        # H
    ("Ubicación",      "Ubicación"),        # I
    ("Sotheby's",      "Sotheby's"),        # J
    ("Piezas",         "Piezas"),           # K
    ("Descripción",    "Descripción"),      # L
    ("Foto principal", "Foto principal"),   # M
    ("Fotos adicionales","Fotos adicionales"), # N
    ("Notas",          "Notas"),            # O
]

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

def col_letter(n):
    """0-based index → letra de columna"""
    return chr(65 + n)

def main():
    svc, sheet_id = get_service()

    # Obtener sheetId numérico
    meta = svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheet_id_num = None
    for s in meta['sheets']:
        if s['properties']['title'] == SHEET_NAME:
            sheet_id_num = s['properties']['sheetId']
            break
    print(f"sheetId numérico: {sheet_id_num}")

    # Leer datos actuales
    resp = svc.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"{SHEET_NAME}!A1:Z",
        valueRenderOption="UNFORMATTED_VALUE"
    ).execute()
    filas = resp.get("values", [])
    headers_actuales = filas[0] if filas else []
    datos = filas[1:] if len(filas) > 1 else []
    print(f"Headers actuales: {headers_actuales}")
    print(f"Filas de datos: {len(datos)}")

    # Construir mapa header_nombre → índice_columna_actual
    header_idx = {h: i for i, h in enumerate(headers_actuales)}

    # Construir nuevas filas reordenadas
    def get_val(fila, nombre_origen):
        if nombre_origen is None:
            return ""
        idx = header_idx.get(nombre_origen)
        if idx is None:
            return ""
        return fila[idx] if idx < len(fila) else ""

    nuevos_headers = [col[0] for col in NUEVO_ORDEN]
    nuevas_filas = []
    for fila in datos:
        nueva = [get_val(fila, col[1]) for col in NUEVO_ORDEN]
        nuevas_filas.append(nueva)

    n_cols = len(NUEVO_ORDEN)
    n_filas = len(nuevas_filas)
    # Limpiar y reescribir
    print("Limpiando hoja...")
    svc.spreadsheets().values().clear(
        spreadsheetId=sheet_id,
        range=f"{SHEET_NAME}!A1:Z",
        body={}
    ).execute()

    print("Escribiendo datos reordenados...")
    svc.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{SHEET_NAME}!A1:{col_letter(n_cols-1)}{n_filas+1}",
        valueInputOption="USER_ENTERED",
        body={"values": [nuevos_headers] + nuevas_filas}
    ).execute()

    # Ahora aplicar formato con batchUpdate
    requests = []

    # 1. Congelar fila 1
    requests.append({
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id_num,
                "gridProperties": {"frozenRowCount": 1}
            },
            "fields": "gridProperties.frozenRowCount"
        }
    })

    # 2. Activar filtros en toda la hoja
    requests.append({
        "setBasicFilter": {
            "filter": {
                "range": {
                    "sheetId": sheet_id_num,
                    "startRowIndex": 0,
                    "startColumnIndex": 0,
                    "endColumnIndex": n_cols
                }
            }
        }
    })

    # 3. Dropdown en columna E (Estado) — índice 4
    col_estado = 4  # columna E
    requests.append({
        "setDataValidation": {
            "range": {
                "sheetId": sheet_id_num,
                "startRowIndex": 1,
                "endRowIndex": n_filas + 1,
                "startColumnIndex": col_estado,
                "endColumnIndex": col_estado + 1
            },
            "rule": {
                "condition": {
                    "type": "ONE_OF_LIST",
                    "values": [
                        {"userEnteredValue": "Disponible"},
                        {"userEnteredValue": "Reservado"},
                        {"userEnteredValue": "Vendido"},
                    ]
                },
                "showCustomUi": True,
                "strict": False
            }
        }
    })

    # 4. Formato encabezado — fondo oscuro, texto blanco, negrita
    requests.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id_num,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 0,
                "endColumnIndex": n_cols
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": {"red": 0.17, "green": 0.24, "blue": 0.31},
                    "textFormat": {
                        "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                        "bold": True,
                        "fontSize": 11
                    },
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE"
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
        }
    })

    # 5. Altura de fila del encabezado
    requests.append({
        "updateDimensionProperties": {
            "range": {
                "sheetId": sheet_id_num,
                "dimension": "ROWS",
                "startIndex": 0,
                "endIndex": 1
            },
            "properties": {"pixelSize": 36},
            "fields": "pixelSize"
        }
    })

    # 6. Ancho columnas — principales más anchas
    anchos = [80, 220, 140, 90, 110, 180, 110, 100, 130, 70, 60, 300, 200, 150, 200]
    for i, ancho in enumerate(anchos):
        requests.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id_num,
                    "dimension": "COLUMNS",
                    "startIndex": i,
                    "endIndex": i + 1
                },
                "properties": {"pixelSize": ancho},
                "fields": "pixelSize"
            }
        })

    # 7. Eliminar bandings existentes antes de agregar
    sheet_meta = svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
    for s in sheet_meta['sheets']:
        if s['properties']['sheetId'] == sheet_id_num:
            for band in s.get('bandedRanges', []):
                requests.append({"deleteBanding": {"bandedRangeId": band['bandedRangeId']}})

    # Color de fondo alternado en filas de datos (blanco / gris muy suave)
    requests.append({
        "addBanding": {
            "bandedRange": {
                "bandedRangeId": 1,
                "range": {
                    "sheetId": sheet_id_num,
                    "startRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": n_cols
                },
                "rowProperties": {
                    "headerColor":     {"red": 0.17, "green": 0.24, "blue": 0.31},
                    "firstBandColor":  {"red": 1.0,  "green": 1.0,  "blue": 1.0},
                    "secondBandColor": {"red": 0.95, "green": 0.97, "blue": 0.99}
                }
            }
        }
    })

    print("Aplicando formato...")
    svc.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={"requests": requests}
    ).execute()

    print()
    print("=" * 55)
    print("INVENTARIO_MAESTRO — LISTO")
    print("=" * 55)
    print()
    print("A. Columnas organizadas:")
    for i, (nombre, origen) in enumerate(NUEVO_ORDEN):
        tag = "← principal" if i < 7 else "← técnica"
        print(f"   {col_letter(i)}: {nombre:22} {tag}")
    print()
    print("B. Columnas movidas:")
    print("   Descripción y Fotos → al final (técnicas)")
    print("   Artículo/Nombre/Categoría/Precio/Estado → al inicio")
    print()
    print("C. Estado configurado con dropdown:")
    print("   Disponible / Reservado / Vendido")
    print()
    print("D. Formato aplicado:")
    print("   ✓ Fila 1 congelada")
    print("   ✓ Filtros activos en todas las columnas")
    print("   ✓ Encabezado con fondo oscuro y texto blanco")
    print("   ✓ Filas con fondo alternado blanco/azul suave")
    print("   ✓ Anchos de columna ajustados")
    print("   ✓ Cliente y Monto pagado listos para ingresar")

if __name__ == "__main__":
    main()
