"""
sincronizar_sheets_completo.py

Sincroniza las 4 hojas del Google Sheet con solaris_catalogo.json (518 ítems).

Hojas que reescribe:
  1. INVENTARIO_MAESTRO  — 518 ítems (ARTÍCULOs + SETs), con estados reales
  2. RESERVAS            — 27 ítems cuyo estado == "Reservado"
  3. VENTAS              — 4 ítems cuyo estado == "Vendido"
  4. RESUMEN             — conteos actualizados

Columnas INVENTARIO_MAESTRO (A–M):
  A  Artículo       codigoItem
  B  Nombre         nombreES
  C  Categoría      categoria
  D  Tipo           ARTICULO / SET
  E  Precio USD     precioUSD
  F  Estado         Disponible / Reservado / Vendido  (dropdown)
  G  Reservado Para reservadoPara
  H  Sotheby's      "Lote N, pág X (est.)" o "Sí" o vacío
  I  Ref Sotheby's  refSothebys (número de lote)
  J  Página         paginaSothebys
  K  Estimación     estimacionSothebys
  L  Fotos          todas separadas por |
  M  Notas          notas

Reglas:
  - Nunca escribe sin leer primero
  - Fuente de verdad: solaris_catalogo.json
  - Códigos en nuevo formato (1A, 44AAA, 136DC)
  - Scripts guardados en Api_PG/scripts/ antes de ejecutar
"""
from __future__ import annotations
import json
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from google.oauth2 import service_account
from googleapiclient.discovery import build

# ─── rutas ───────────────────────────────────────────────────────────────────
SCRIPT_PATH  = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[2]
ENV_PATH     = PROJECT_ROOT / "pignatelli-app" / ".env.local"
CATALOGO     = PROJECT_ROOT / "Api_PG" / "data" / "solaris_catalogo.json"
SCOPES       = ["https://www.googleapis.com/auth/spreadsheets"]

# ─── orden de categorías ─────────────────────────────────────────────────────
CAT_ORDER = {
    "Ceramica":         0,
    "Decorativos":      1,
    "Electrodomesticos":2,
    "Muebles":          3,
    "Cristaleria":      4,
    "Joyas":            5,
    "Insumos Medicos":  6,
    "Arte en papel":    7,
    "Plateria":         8,
    "Utensilios":       9,
}

# ─── columnas INVENTARIO_MAESTRO ─────────────────────────────────────────────
INV_HEADERS = [
    "Artículo",       # A
    "Nombre",         # B
    "Categoría",      # C
    "Tipo",           # D  ARTICULO / SET
    "Precio USD",     # E
    "Estado",         # F  dropdown
    "Reservado Para", # G
    "Sotheby's",      # H  resumen legible
    "Ref Sotheby's",  # I  número de lote
    "Página",         # J
    "Estimación",     # K
    "Fotos",          # L  pipe-separated
    "Notas",          # M
]

# ─── columnas RESERVAS ───────────────────────────────────────────────────────
RES_HEADERS = [
    "Artículo",
    "Nombre",
    "Categoría",
    "Reservado Para",
    "Precio USD",
    "Foto principal",
    "Notas",
]

# ─── columnas VENTAS ─────────────────────────────────────────────────────────
VEN_HEADERS = [
    "Artículo",
    "Nombre",
    "Categoría",
    "Comprador",
    "Precio USD",
    "Foto principal",
    "Notas",
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
    sheet_id    = env["GOOGLE_SHEETS_ID"].strip()
    private_key = env["GOOGLE_PRIVATE_KEY"].replace("\\n", "\n").strip()
    info = {
        "type": "service_account",
        "project_id": "inventario-pignatelli",
        "private_key_id": "",
        "private_key": private_key,
        "client_email": env["GOOGLE_SERVICE_ACCOUNT_EMAIL"].strip(),
        "client_id": "",
        "auth_uri":  "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "",
    }
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    svc   = build("sheets", "v4", credentials=creds, cache_discovery=False)
    return svc, sheet_id


# ─── helpers ─────────────────────────────────────────────────────────────────

def sort_key(item: dict):
    cat   = str(item.get("categoria", "")).strip()
    num   = item.get("numItem")
    try:
        num_val = int(num)
    except (TypeError, ValueError):
        num_val = 10 ** 9
    codigo = str(item.get("codigoItem", "")).strip()
    return (CAT_ORDER.get(cat, 999), num_val, codigo)


def precio_val(item: dict):
    p = item.get("precioUSD")
    if p in (None, 0, 0.0, "0", "0.0", "", "0"):
        return ""
    return p


def sothebys_display(item: dict) -> str:
    """Descripción legible de Sotheby's: 'Lote N, pág X (est.)' o 'Sí' o vacío."""
    if not item.get("tieneSothebys"):
        return ""
    ref  = str(item.get("refSothebys", "") or "").strip()
    pag  = str(item.get("paginaSothebys", "") or "").strip()
    est  = str(item.get("estimacionSothebys", "") or "").strip()
    if ref or pag or est:
        partes = []
        if ref:
            partes.append(f"Lote {ref}")
        if pag:
            partes.append(f"pág {pag}")
        if est:
            partes.append(est)
        return ", ".join(partes)
    return "Sí"


def fotos_str(item: dict) -> str:
    fotos = [str(f).strip() for f in item.get("fotos", []) if str(f).strip()]
    return " | ".join(fotos)


def foto_principal(item: dict) -> str:
    fotos = [str(f).strip() for f in item.get("fotos", []) if str(f).strip()]
    return fotos[0] if fotos else ""


# ─── constructores de filas ──────────────────────────────────────────────────

def build_inv_row(item: dict) -> list:
    return [
        str(item.get("codigoItem", "")).strip(),           # A Artículo
        str(item.get("nombreES", "") or "").strip(),        # B Nombre
        str(item.get("categoria", "") or "").strip(),       # C Categoría
        str(item.get("tipoEstructural", "") or "").strip(), # D Tipo
        precio_val(item),                                   # E Precio USD
        str(item.get("estado", "Disponible") or "Disponible").strip(),  # F Estado
        str(item.get("reservadoPara", "") or "").strip(),   # G Reservado Para
        sothebys_display(item),                             # H Sotheby's
        str(item.get("refSothebys", "") or "").strip(),     # I Ref
        str(item.get("paginaSothebys", "") or "").strip(),  # J Página
        str(item.get("estimacionSothebys", "") or "").strip(), # K Estimación
        fotos_str(item),                                    # L Fotos
        str(item.get("notas", "") or "").strip(),           # M Notas
    ]


def build_res_row(item: dict) -> list:
    return [
        str(item.get("codigoItem", "")).strip(),
        str(item.get("nombreES", "") or "").strip(),
        str(item.get("categoria", "") or "").strip(),
        str(item.get("reservadoPara", "") or "").strip(),
        precio_val(item),
        foto_principal(item),
        str(item.get("notas", "") or "").strip(),
    ]


def build_ven_row(item: dict) -> list:
    return [
        str(item.get("codigoItem", "")).strip(),
        str(item.get("nombreES", "") or "").strip(),
        str(item.get("categoria", "") or "").strip(),
        str(item.get("reservadoPara", "") or "").strip(),  # comprador
        precio_val(item),
        foto_principal(item),
        str(item.get("notas", "") or "").strip(),
    ]


# ─── formato ─────────────────────────────────────────────────────────────────

def col_letter(n: int) -> str:
    """0 → A, 1 → B, ..., 25 → Z"""
    return chr(65 + n)


def aplicar_formato_inv(svc, sheet_id: str, sheet_id_num: int, n_cols: int, n_filas: int):
    meta = svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
    requests = []

    # Limpiar bandings existentes en esta hoja
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

    # Filtros en toda la tabla
    requests.append({
        "setBasicFilter": {
            "filter": {
                "range": {
                    "sheetId": sheet_id_num,
                    "startRowIndex": 0, "startColumnIndex": 0,
                    "endColumnIndex": n_cols,
                }
            }
        }
    })

    # Encabezado: fondo oscuro, texto blanco, negrita
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
            "range": {"sheetId": sheet_id_num, "dimension": "ROWS",
                      "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": 36},
            "fields": "pixelSize",
        }
    })

    # Dropdown Estado (col F = índice 5)
    requests.append({
        "setDataValidation": {
            "range": {
                "sheetId": sheet_id_num,
                "startRowIndex": 1, "endRowIndex": n_filas + 1,
                "startColumnIndex": 5, "endColumnIndex": 6,
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

    # Anchos de columna  A   B    C    D    E    F    G    H    I   J   K    L    M
    anchos =            [75, 240, 130, 80,  85,  100, 160, 140, 80, 55, 130, 220, 200]
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

    # Banding: filas alternadas blanco / azul suave
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
                    "secondBandColor": {"red": 0.94, "green": 0.97, "blue": 1.0},
                },
            }
        }
    })

    svc.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={"requests": requests},
    ).execute()


# ─── escribir hoja genérica ──────────────────────────────────────────────────

def rewrite_sheet(svc, sheet_id: str, sheet_name: str, headers: list, rows: list[list]):
    end_col = col_letter(len(headers) - 1)
    n_total = len(rows) + 1  # +1 header

    print(f"  Limpiando {sheet_name}...")
    svc.spreadsheets().values().clear(
        spreadsheetId=sheet_id,
        range=f"{sheet_name}!A1:Z",
        body={},
    ).execute()

    print(f"  Escribiendo {len(rows)} filas en {sheet_name}...")
    svc.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{sheet_name}!A1:{end_col}{n_total}",
        valueInputOption="USER_ENTERED",
        body={"values": [headers] + rows},
    ).execute()


# ─── RESUMEN ─────────────────────────────────────────────────────────────────

def rewrite_resumen(svc, sheet_id: str, stats: dict):
    sheet_name = "RESUMEN"
    print(f"  Actualizando {sheet_name}...")
    rows = [
        ["Concepto",             "Cantidad"],
        ["Total de ítems",       stats["total"]],
        ["Disponibles",          stats["disponibles"]],
        ["Reservados",           stats["reservados"]],
        ["Vendidos",             stats["vendidos"]],
        ["Con Sotheby's",        stats["sothebys"]],
        ["ARTÍCULOs",            stats["articulos"]],
        ["SETs",                 stats["sets"]],
        ["Categorías",           stats["categorias"]],
        ["", ""],
        ["Fecha de sincronización", "=TODAY()"],
    ]

    svc.spreadsheets().values().clear(
        spreadsheetId=sheet_id,
        range=f"{sheet_name}!A1:Z",
        body={},
    ).execute()
    svc.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{sheet_name}!A1:B{len(rows)}",
        valueInputOption="USER_ENTERED",
        body={"values": rows},
    ).execute()


# ─── main ────────────────────────────────────────────────────────────────────

def main():
    # 1. Cargar y clasificar
    print("Cargando solaris_catalogo.json...")
    raw = json.loads(CATALOGO.read_text(encoding="utf-8"))
    items = raw if isinstance(raw, list) else list(raw.values())
    items = [i for i in items if isinstance(i, dict)]

    total       = len(items)
    disponibles = [i for i in items if i.get("estado") == "Disponible"]
    reservados  = [i for i in items if i.get("estado") == "Reservado"]
    vendidos    = [i for i in items if i.get("estado") == "Vendido"]
    con_soth    = [i for i in items if i.get("tieneSothebys")]
    articulos   = [i for i in items if i.get("tipoEstructural") == "ARTICULO"]
    sets        = [i for i in items if i.get("tipoEstructural") == "SET"]
    categorias  = len(set(i.get("categoria", "") for i in items if i.get("categoria")))

    print(f"  Total: {total} | Disponibles: {len(disponibles)} | "
          f"Reservados: {len(reservados)} | Vendidos: {len(vendidos)}")
    print(f"  ARTÍCULOs: {len(articulos)} | SETs: {len(sets)} | "
          f"Sotheby's: {len(con_soth)} | Categorías: {categorias}")

    # Ordenar por categoría → numItem → codigoItem
    items_sorted = sorted(items, key=sort_key)

    # Construir filas
    inv_rows = [build_inv_row(i) for i in items_sorted]
    res_rows = [build_res_row(i) for i in sorted(reservados, key=sort_key)]
    ven_rows = [build_ven_row(i) for i in sorted(vendidos, key=sort_key)]

    stats = {
        "total":       total,
        "disponibles": len(disponibles),
        "reservados":  len(reservados),
        "vendidos":    len(vendidos),
        "sothebys":    len(con_soth),
        "articulos":   len(articulos),
        "sets":        len(sets),
        "categorias":  categorias,
    }

    # 2. Conectar
    print("\nConectando a Google Sheets...")
    svc, sheet_id = get_service()

    # Obtener IDs de hojas para aplicar formato
    meta = svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheet_id_map = {s["properties"]["title"]: s["properties"]["sheetId"]
                    for s in meta["sheets"]}
    print(f"  Hojas encontradas: {list(sheet_id_map.keys())}")

    # 3. INVENTARIO_MAESTRO
    print("\n[1/4] INVENTARIO_MAESTRO")
    rewrite_sheet(svc, sheet_id, "INVENTARIO_MAESTRO", INV_HEADERS, inv_rows)
    if "INVENTARIO_MAESTRO" in sheet_id_map:
        print("  Aplicando formato...")
        aplicar_formato_inv(svc, sheet_id,
                            sheet_id_map["INVENTARIO_MAESTRO"],
                            len(INV_HEADERS), len(inv_rows))
    print(f"  OK — {len(inv_rows)} filas escritas")

    # 4. RESERVAS
    print("\n[2/4] RESERVAS")
    rewrite_sheet(svc, sheet_id, "RESERVAS", RES_HEADERS, res_rows)
    print(f"  OK — {len(res_rows)} reservas escritas")

    # 5. VENTAS
    print("\n[3/4] VENTAS")
    rewrite_sheet(svc, sheet_id, "VENTAS", VEN_HEADERS, ven_rows)
    print(f"  OK — {len(ven_rows)} ventas escritas")

    # 6. RESUMEN
    print("\n[4/4] RESUMEN")
    rewrite_resumen(svc, sheet_id, stats)
    print("  OK")

    # 7. Resumen final
    print()
    print("=" * 60)
    print("SINCRONIZACIÓN COMPLETA")
    print("=" * 60)
    print(f"  INVENTARIO_MAESTRO : {len(inv_rows)} ítems (A–M, 13 columnas)")
    print(f"  RESERVAS           : {len(res_rows)} reservas")
    print(f"  VENTAS             : {len(ven_rows)} ventas (Pablo Brenes)")
    print(f"  RESUMEN            : conteos actualizados")
    print()
    print("Distribución por estado:")
    print(f"  Disponibles : {len(disponibles)}")
    print(f"  Reservados  : {len(reservados)}")
    print(f"  Vendidos    : {len(vendidos)}")
    print()
    print("Sotheby's:")
    print(f"  Con valoración : {len(con_soth)}")
    soth_completos = [i for i in con_soth if i.get("refSothebys") or i.get("paginaSothebys")]
    print(f"  Con datos completos : {len(soth_completos)}")
    if soth_completos:
        for i in soth_completos:
            print(f"    {i['codigoItem']} → Lote {i.get('refSothebys','')} pág {i.get('paginaSothebys','')} {i.get('estimacionSothebys','')}")
    print()
    print("Categorías:")
    cats = {}
    for i in items:
        c = i.get("categoria", "?")
        cats[c] = cats.get(c, 0) + 1
    for cat, n in sorted(cats.items()):
        print(f"  {cat:<22} {n:>3}")


if __name__ == "__main__":
    main()