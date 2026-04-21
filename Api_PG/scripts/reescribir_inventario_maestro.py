"""
reescribir_inventario_maestro.py

Reescribe INVENTARIO_MAESTRO desde cero usando solaris_catalogo.json.
Formato final definitivo:

  A  Artículo        — codigoItem
  B  Nombre          — nombreES
  C  Categoría       — etiqueta en español
  D  Precio USD      — precioUSD
  E  Estado          — Disponible / Reservado / Vendido  (dropdown)
  F  Cliente         — vacío (texto libre)
  G  Monto pagado    — vacío ($ o ₡)
  H  Condición       — estado físico
  I  Ubicación       — ubicacion
  J  Sotheby's       — "Sotheby's #N (X,XXX USD)" o vacío
  K  Piezas          — cantidad
  L  Descripción     — corta, ~120 chars (nombreES + material si cabe)
  M  Fotos           — todas las fotos separadas por |
  N  Notas           — notas

No incluye columna 'Foto principal'.
No toca ninguna otra hoja.
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

CAT_LABEL = {
    "C": "Porcelana y Cerámica",
    "D": "Decorativos y Arte",
    "E": "Electrodomésticos",
    "F": "Muebles",
    "G": "Cristalería",
    "J": "Joyería",
    "M": "Miscelánea",
    "P": "Cuadros y Grabados",
    "S": "Platería",
    "U": "Utensilios",
}

CAT_ORDER = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "J": 5, "M": 6, "P": 7, "S": 8, "U": 9}

HEADERS = [
    "Artículo",       # A
    "Nombre",         # B
    "Categoría",      # C
    "Precio USD",     # D
    "Estado",         # E  dropdown
    "Cliente",        # F  texto libre
    "Monto pagado",   # G  $ o ₡
    "Condición",      # H
    "Ubicación",      # I
    "Sotheby's",      # J  referencia corta o vacío
    "Piezas",         # K
    "Descripción",    # L  corta ~120 chars
    "Fotos",          # M  todas separadas por |
    "Notas",          # N
]


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
        "type": "service_account", "project_id": "inventario-pignatelli",
        "private_key_id": "", "private_key": private_key,
        "client_email": env["GOOGLE_SERVICE_ACCOUNT_EMAIL"].strip(), "client_id": "",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "",
    }
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    svc = build("sheets", "v4", credentials=creds, cache_discovery=False)
    return svc, sheet_id


# ─── helpers de datos ────────────────────────────────────────────────────────

def is_ref(item: dict) -> bool:
    fotos = [str(f).strip() for f in item.get("fotos", []) if str(f).strip()]
    if "Ref del set" in str(item.get("notas", "")):
        return True
    return len(fotos) == 1 and "-ref-" in fotos[0].lower()


def is_structural_node(item: dict) -> bool:
    tipo = str(item.get("tipoEstructural", "") or "").strip().upper()
    return tipo in {"GRUPO", "SUBSET", "REF"}


def sort_key(item: dict):
    cat = str(item.get("catCodigo", "")).strip()
    try:
        num = int(item.get("numItem", 0) or 0)
    except Exception:
        num = 10 ** 9
    return (CAT_ORDER.get(cat, 999), num, str(item.get("codigoItem", "")))


def nombre_corto(item: dict) -> str:
    """Título corto ~45 chars. Toma la primera parte del nombreES (antes de ':')."""
    nombre = (item.get("nombreES") or "").strip()
    if not nombre:
        nombre = (item.get("descripcionOriginal") or "").strip()
    if not nombre:
        return ""
    # Quitar subtítulo tras ":"
    if ":" in nombre:
        nombre = nombre.split(":")[0].strip()
    if len(nombre) <= 45:
        return nombre
    # Truncar en límite de palabra
    return nombre[:42].rsplit(" ", 1)[0].rstrip(",") + "..."


def desc_corta(item: dict) -> str:
    """Descripción funcional ~70 chars: material | estilo | N piezas."""
    partes = []
    material = (item.get("materiales") or "").strip()
    estilo   = (item.get("estilo") or "").strip()
    cantidad = item.get("cantidad") or 1
    try:
        cantidad = int(cantidad)
    except (TypeError, ValueError):
        cantidad = 1

    if material:
        partes.append(material[:45])
    if estilo:
        partes.append(estilo[:30])
    if cantidad > 1:
        partes.append(f"{cantidad} piezas")

    resultado = " | ".join(partes)
    if resultado:
        return resultado[:75]

    # Fallback: nombre corto si no hay datos estructurados
    return nombre_corto(item)


def sothebys_ref(item: dict) -> str:
    """
    Devuelve referencia corta: 'Sotheby's #N (X,XXX USD)' o vacío.
    Extrae número y precio mínimo del campo refSothebys del JSON.
    """
    if not item.get("tieneSothebys"):
        return ""
    texto = (item.get("refSothebys") or "").strip()
    if not texto:
        return "Sotheby's"

    # Extraer número de referencia (acepta cualquier comilla/caracter entre Sotheby y #)
    m_num = re.search(r"Sotheby[^\d#\n]{0,6}#(\d+)", texto, re.IGNORECASE)
    if not m_num:
        return texto[:40]  # texto no parseable, truncado
    num = m_num.group(1)

    # Extraer precio mínimo
    m_precio = re.search(r"\$\s*([\d,]+)", texto)
    if m_precio:
        raw = m_precio.group(1).replace(",", "")
        try:
            valor = int(raw)
            return f"Sotheby's #{num} ({valor:,} USD)"
        except ValueError:
            pass

    return f"Sotheby's #{num}"


def build_row(item: dict) -> list:
    fotos = [str(f).strip() for f in item.get("fotos", []) if str(f).strip()]
    todas_fotos = " | ".join(fotos) if fotos else ""

    precio = item.get("precioUSD")
    if precio in (None, 0, 0.0, "0", "0.0", "", "0"):
        precio = ""

    condicion = (item.get("estado") or "").strip()
    if not condicion:
        condicion = "Por evaluar"

    cat_label = CAT_LABEL.get(str(item.get("catCodigo", "")), str(item.get("categoria", "")))
    piezas = item.get("cantidad") or 1

    return [
        str(item.get("codigoItem", "")).strip(),   # A Artículo
        nombre_corto(item),                         # B Nombre
        cat_label,                                  # C Categoría
        precio,                                     # D Precio USD
        "Disponible",                               # E Estado
        "",                                         # F Cliente
        "",                                         # G Monto pagado
        condicion,                                  # H Condición
        (item.get("ubicacion") or "").strip(),      # I Ubicación
        sothebys_ref(item),                         # J Sotheby's
        piezas,                                     # K Piezas
        desc_corta(item),                           # L Descripción
        todas_fotos,                                # M Fotos
        (item.get("notas") or "").strip(),          # N Notas
    ]


# ─── formato del sheet ───────────────────────────────────────────────────────

def col_letter(n: int) -> str:
    return chr(65 + n)


def aplicar_formato(svc, sheet_id: str, sheet_id_num: int, n_cols: int, n_filas: int):
    # Limpiar bandings existentes
    meta = svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
    requests = []
    for s in meta["sheets"]:
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

    # Encabezado oscuro, texto blanco, negrita
    requests.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id_num,
                "startRowIndex": 0, "endRowIndex": 1,
                "startColumnIndex": 0, "endColumnIndex": n_cols,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": {"red": 0.17, "green": 0.24, "blue": 0.31},
                    "textFormat": {
                        "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                        "bold": True, "fontSize": 11,
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

    # Dropdown Estado (col E, índice 4)
    requests.append({
        "setDataValidation": {
            "range": {
                "sheetId": sheet_id_num,
                "startRowIndex": 1, "endRowIndex": n_filas + 1,
                "startColumnIndex": 4, "endColumnIndex": 5,
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

    # Anchos de columna  A  B    C    D    E    F    G    H    I    J   K    L    M    N
    anchos =            [80, 220, 150, 90,  110, 180, 110, 110, 130, 130, 55, 250, 200, 200]
    for i, ancho in enumerate(anchos[:n_cols]):
        requests.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id_num,
                    "dimension": "COLUMNS",
                    "startIndex": i, "endIndex": i + 1,
                },
                "properties": {"pixelSize": ancho},
                "fields": "pixelSize",
            }
        })

    # Banding alternado filas
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


# ─── main ────────────────────────────────────────────────────────────────────

def main():
    print("Cargando catalogo JSON...")
    raw = json.loads(CATALOGO.read_text(encoding="utf-8"))
    items = list(raw.values()) if isinstance(raw, dict) else raw
    items = [i for i in items if isinstance(i, dict) and not is_ref(i) and not is_structural_node(i)]
    items.sort(key=sort_key)
    rows = [build_row(i) for i in items]
    print(f"  {len(rows)} articulos")

    svc, sheet_id = get_service()
    print("Conectando a Google Sheets...")

    meta = svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheet_id_num = None
    for s in meta["sheets"]:
        if s["properties"]["title"] == SHEET_NAME:
            sheet_id_num = s["properties"]["sheetId"]
            break
    print(f"  sheetId: {sheet_id_num}")

    n_cols  = len(HEADERS)
    n_filas = len(rows)

    # Limpiar
    print("Limpiando hoja...")
    svc.spreadsheets().values().clear(
        spreadsheetId=sheet_id,
        range=f"{SHEET_NAME}!A1:Z",
        body={},
    ).execute()

    # Escribir
    print("Escribiendo datos...")
    svc.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{SHEET_NAME}!A1:{col_letter(n_cols - 1)}{n_filas + 1}",
        valueInputOption="USER_ENTERED",
        body={"values": [HEADERS] + rows},
    ).execute()

    # Formato
    print("Aplicando formato...")
    aplicar_formato(svc, sheet_id, sheet_id_num, n_cols, n_filas)

    # Estadísticas
    sin_precio   = sum(1 for r in rows if r[3] == "")
    sin_ubic     = sum(1 for r in rows if r[8] == "")
    sin_cond     = sum(1 for r in rows if r[7] == "Por evaluar")
    con_sothebys = sum(1 for r in rows if r[9])
    sin_desc     = sum(1 for r in rows if not r[11])

    print()
    print("=" * 55)
    print("INVENTARIO_MAESTRO — REESCRITO")
    print("=" * 55)
    print()
    print("Columnas finales:")
    for i, h in enumerate(HEADERS):
        print(f"  {col_letter(i)}: {h}")
    print()
    print(f"Articulos escritos:    {n_filas}")
    print(f"Con Sotheby's ref:     {con_sothebys}")
    print(f"Sin descripcion corta: {sin_desc}")
    print(f"Sin precio:            {sin_precio}  <- los duenos definen")
    print(f"Sin ubicacion:         {sin_ubic}  <- los duenos definen")
    print(f"Sin condicion fisica:  {sin_cond}  <- los duenos evaluan")
    print()
    print("Formato aplicado:")
    print("  Fila 1 congelada")
    print("  Filtros activos en todas las columnas")
    print("  Encabezado oscuro texto blanco")
    print("  Filas alternadas blanco / azul suave")
    print("  Dropdown Estado: Disponible / Reservado / Vendido")
    print("  Anchos de columna ajustados")
    print()
    print("Listo para uso por la familia.")


if __name__ == "__main__":
    main()
