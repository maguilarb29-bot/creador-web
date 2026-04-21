"""
pulido_final.py
Aplica 3 cambios al INVENTARIO_MAESTRO real en Google Sheets:
  1. Descripcion corta (~120 chars) usando nombreES del catalogo JSON
  2. Sotheby's reformateado: Sotheby's #N (X,XXX USD)
  3. Elimina columna 'Foto principal'
No toca codigos, precios, estados, clientes, montos ni notas.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCRIPT_PATH  = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[2]
ENV_PATH     = PROJECT_ROOT / "pignatelli-app" / ".env.local"
CATALOGO     = PROJECT_ROOT / "Api_PG" / "data" / "solaris_catalogo.json"
SHEET_NAME   = "INVENTARIO_MAESTRO"
SCOPES       = ["https://www.googleapis.com/auth/spreadsheets"]


# ─── credenciales ────────────────────────────────────────────────────────────

def load_env(path: Path) -> dict:
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip()
        if v.startswith('"') and v.endswith('"'):
            v = v[1:-1]
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


# ─── helpers ─────────────────────────────────────────────────────────────────

def col_letter(n: int) -> str:
    return chr(65 + n)


def desc_corta(codigo: str, catalogo: dict) -> str:
    """Genera descripcion corta (~120 chars) desde el catalogo JSON."""
    item = catalogo.get(codigo)
    if not item:
        return ""
    nombre = (item.get("nombreES") or "").strip()
    if not nombre:
        return ""
    # Agregar material si cabe
    material = (item.get("materiales") or "").strip()
    if material and len(nombre) + len(material) + 2 <= 118:
        return f"{nombre}. {material}"
    return nombre[:120]


def sothebys_corto(texto: str) -> str:
    """
    Convierte texto largo de Sotheby's a formato corto.
    Entrada:  '2 Louis XV commodes $7000-9800 - Sotheby's #73 p. 42'
    Salida:   'Sotheby's #73 (7,000 USD)'
    Si no hay precio, devuelve: 'Sotheby's #73'
    """
    if not texto or not texto.strip():
        return ""

    # Extraer numero de referencia
    m_num = re.search(r"Sotheby[''s]*\s*#(\d+)", texto, re.IGNORECASE)
    if not m_num:
        return texto.strip()  # no reconocible, dejar intacto
    num = m_num.group(1)

    # Extraer precio minimo (primer valor de un rango $X o $X,XXX o $X.XXX)
    m_precio = re.search(r"\$\s*([\d,]+)", texto)
    if m_precio:
        raw = m_precio.group(1).replace(",", "")
        try:
            valor = int(raw)
            return f"Sotheby's #{num} ({valor:,} USD)"
        except ValueError:
            pass

    # Sin precio
    return f"Sotheby's #{num}"


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    print("Cargando catalogo JSON...")
    catalogo = json.loads(CATALOGO.read_text(encoding="utf-8"))
    print(f"  {len(catalogo)} articulos")

    svc, sheet_id = get_service()
    print("Conectando a Google Sheets...")

    # sheetId numerico
    meta = svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheet_id_num = None
    for s in meta["sheets"]:
        if s["properties"]["title"] == SHEET_NAME:
            sheet_id_num = s["properties"]["sheetId"]
            break
    print(f"  sheetId: {sheet_id_num}")

    # Leer hoja completa
    resp = svc.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"{SHEET_NAME}!A1:O",
        valueRenderOption="UNFORMATTED_VALUE",
    ).execute()
    filas = resp.get("values", [])
    headers = filas[0] if filas else []
    datos = filas[1:] if len(filas) > 1 else []
    print(f"  Headers: {headers}")
    print(f"  Filas de datos: {len(datos)}")

    # Indices por nombre de columna
    hidx = {h: i for i, h in enumerate(headers)}

    col_articulo   = hidx.get("Articulo") or hidx.get("Artículo") or 0
    col_desc       = hidx.get("Descripcion") or hidx.get("Descripción") or -1
    col_sothebys   = hidx.get("Sotheby's") or -1
    col_foto_princ = hidx.get("Foto principal") or -1

    print(f"  col Articulo:     {col_articulo} ({col_letter(col_articulo)})")
    print(f"  col Descripcion:  {col_desc} ({col_letter(col_desc) if col_desc >= 0 else 'no encontrada'})")
    print(f"  col Sothebys:     {col_sothebys} ({col_letter(col_sothebys) if col_sothebys >= 0 else 'no encontrada'})")
    print(f"  col Foto princ:   {col_foto_princ} ({col_letter(col_foto_princ) if col_foto_princ >= 0 else 'no encontrada'})")

    if col_desc < 0:
        print("ERROR: columna Descripcion no encontrada — abortando")
        return

    # ── 1 y 2: aplicar descripciones cortas y Sotheby's reformateado ──────────
    cambios_desc = 0
    cambios_soth = 0

    nuevas_filas = []
    for fila in datos:
        fila = list(fila)  # copia mutable
        # Asegurar largo suficiente
        while len(fila) <= max(col_desc, col_sothebys if col_sothebys >= 0 else 0):
            fila.append("")

        codigo = str(fila[col_articulo]).strip() if col_articulo < len(fila) else ""

        # 1. Descripcion corta
        nueva_desc = desc_corta(codigo, catalogo)
        if nueva_desc:
            fila[col_desc] = nueva_desc
            cambios_desc += 1

        # 2. Sotheby's
        if col_sothebys >= 0:
            texto_soth = str(fila[col_sothebys]).strip() if col_sothebys < len(fila) else ""
            if texto_soth:
                nuevo_soth = sothebys_corto(texto_soth)
                if nuevo_soth != texto_soth:
                    fila[col_sothebys] = nuevo_soth
                    cambios_soth += 1

        nuevas_filas.append(fila)

    print(f"\nDescripciones actualizadas: {cambios_desc}")
    print(f"Sotheby's reformateados:    {cambios_soth}")

    # ── 3: eliminar columna Foto principal ────────────────────────────────────
    if col_foto_princ >= 0:
        nuevos_headers = [h for i, h in enumerate(headers) if i != col_foto_princ]
        nuevas_filas_sin_foto = [
            [v for i, v in enumerate(fila) if i != col_foto_princ]
            for fila in nuevas_filas
        ]
        print(f"Columna 'Foto principal' ({col_letter(col_foto_princ)}) eliminada")
    else:
        nuevos_headers = headers
        nuevas_filas_sin_foto = nuevas_filas
        print("'Foto principal' no encontrada — ya eliminada anteriormente")

    n_cols  = len(nuevos_headers)
    n_filas = len(nuevas_filas_sin_foto)

    # ── escribir de vuelta ────────────────────────────────────────────────────
    print("\nLimpiando hoja...")
    svc.spreadsheets().values().clear(
        spreadsheetId=sheet_id,
        range=f"{SHEET_NAME}!A1:Z",
        body={},
    ).execute()

    print("Escribiendo datos actualizados...")
    svc.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{SHEET_NAME}!A1:{col_letter(n_cols - 1)}{n_filas + 1}",
        valueInputOption="USER_ENTERED",
        body={"values": [nuevos_headers] + nuevas_filas_sin_foto},
    ).execute()

    # ── reaplicar formato basico (congelar, filtros, encabezado) ─────────────
    print("Reaplicando formato...")

    # Eliminar bandings existentes
    meta2 = svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
    requests = []
    for s in meta2["sheets"]:
        if s["properties"]["sheetId"] == sheet_id_num:
            for band in s.get("bandedRanges", []):
                requests.append({"deleteBanding": {"bandedRangeId": band["bandedRangeId"]}})

    # Congelar fila 1
    requests.append({
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id_num,
                "gridProperties": {"frozenRowCount": 1},
            },
            "fields": "gridProperties.frozenRowCount",
        }
    })

    # Filtros
    requests.append({
        "setBasicFilter": {
            "filter": {
                "range": {
                    "sheetId": sheet_id_num,
                    "startRowIndex": 0,
                    "startColumnIndex": 0,
                    "endColumnIndex": n_cols,
                }
            }
        }
    })

    # Encabezado oscuro
    requests.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id_num,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 0,
                "endColumnIndex": n_cols,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": {"red": 0.17, "green": 0.24, "blue": 0.31},
                    "textFormat": {
                        "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                        "bold": True,
                        "fontSize": 11,
                    },
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE",
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)",
        }
    })

    # Altura encabezado
    requests.append({
        "updateDimensionProperties": {
            "range": {"sheetId": sheet_id_num, "dimension": "ROWS", "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": 36},
            "fields": "pixelSize",
        }
    })

    # Dropdown Estado (col E, indice 4)
    col_estado_idx = 4
    requests.append({
        "setDataValidation": {
            "range": {
                "sheetId": sheet_id_num,
                "startRowIndex": 1,
                "endRowIndex": n_filas + 1,
                "startColumnIndex": col_estado_idx,
                "endColumnIndex": col_estado_idx + 1,
            },
            "rule": {
                "condition": {
                    "type": "ONE_OF_LIST",
                    "values": [
                        {"userEnteredValue": "Disponible"},
                        {"userEnteredValue": "Reservado"},
                        {"userEnteredValue": "Vendido"},
                    ],
                },
                "showCustomUi": True,
                "strict": False,
            },
        }
    })

    # Anchos de columna (14 columnas ahora, sin Foto principal)
    anchos = [80, 220, 140, 90, 110, 180, 110, 100, 130, 70, 60, 300, 180, 200]
    for i, ancho in enumerate(anchos[:n_cols]):
        requests.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id_num,
                    "dimension": "COLUMNS",
                    "startIndex": i,
                    "endIndex": i + 1,
                },
                "properties": {"pixelSize": ancho},
                "fields": "pixelSize",
            }
        })

    # Banding alternado
    requests.append({
        "addBanding": {
            "bandedRange": {
                "range": {
                    "sheetId": sheet_id_num,
                    "startRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": n_cols,
                },
                "rowProperties": {
                    "headerColor":     {"red": 0.17, "green": 0.24, "blue": 0.31},
                    "firstBandColor":  {"red": 1.0,  "green": 1.0,  "blue": 1.0},
                    "secondBandColor": {"red": 0.95, "green": 0.97, "blue": 0.99},
                },
            }
        }
    })

    svc.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={"requests": requests},
    ).execute()

    # ── resumen final ─────────────────────────────────────────────────────────
    print()
    print("=" * 55)
    print("PULIDO FINAL COMPLETADO")
    print("=" * 55)
    print()
    print("A. Columnas finales:")
    for i, h in enumerate(nuevos_headers):
        print(f"   {col_letter(i)}: {h}")
    print()
    print(f"B. 'Foto principal' eliminada: {'si' if col_foto_princ >= 0 else 'ya no existia'}")
    print(f"C. Descripciones cortas aplicadas: {cambios_desc}")
    print(f"D. Sotheby's reformateados: {cambios_soth}")
    print()
    print("Listo para uso por la familia.")


if __name__ == "__main__":
    main()
