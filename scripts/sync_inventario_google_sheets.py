"""
Sincroniza el Inventario Maestro Solaris al Google Sheet existente.
Crea 5 pestañas nuevas (prefijo IM_) con la misma estética del Excel.

Credenciales : pignatelli-app/lib/service-account.json
Sheet ID      : de pignatelli-app/.env.local → GOOGLE_SHEETS_ID
"""

import json, re, os
from pathlib import Path
from collections import defaultdict
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

BASE      = Path(__file__).resolve().parent.parent
SA_FILE   = BASE / "pignatelli-app/lib/service-account.json"
ENV_FILE  = BASE / "pignatelli-app/.env.local"

# ── Leer SHEET_ID del .env.local ───────────────────────────────────────────
SHEET_ID = None
for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
    if line.startswith("GOOGLE_SHEETS_ID="):
        SHEET_ID = line.split("=", 1)[1].strip()
        break
assert SHEET_ID, "GOOGLE_SHEETS_ID no encontrado en .env.local"

# ── Auth ───────────────────────────────────────────────────────────────────
creds   = Credentials.from_service_account_file(
    str(SA_FILE),
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
service = build("sheets", "v4", credentials=creds, cache_discovery=False)
ss      = service.spreadsheets()

# ── Paleta (RGB 0-1) ───────────────────────────────────────────────────────
def rgb(h):
    h = h.lstrip("#")
    return {"red": int(h[0:2],16)/255, "green": int(h[2:4],16)/255, "blue": int(h[4:6],16)/255}

NAVY     = rgb("1A1A2E"); SLATE = rgb("2C3E50"); GRAY_HDR = rgb("37474F")
WHITE    = rgb("FFFFFF"); GOLD  = rgb("B8860B"); GOLD_LITE = rgb("FEF9E7")
BLACK    = rgb("1A1A1A")

CAT_COLORS = {
    "Arte en papel":    (rgb("5D4037"), rgb("FFF8E1")),
    "Ceramica":         (rgb("1565C0"), rgb("E3F2FD")),
    "Cristaleria":      (rgb("00695C"), rgb("E0F2F1")),
    "Decorativos":      (rgb("4A148C"), rgb("F3E5F5")),
    "Electrodomesticos":(rgb("424242"), rgb("F5F5F5")),
    "Insumos Medicos":  (rgb("558B2F"), rgb("F1F8E9")),
    "Joyas":            (rgb("880E4F"), rgb("FCE4EC")),
    "Muebles":          (rgb("2E7D32"), rgb("E8F5E9")),
    "Plateria":         (rgb("37474F"), rgb("ECEFF1")),
    "Utensilios":       (rgb("E65100"), rgb("FFF3E0")),
}

# ── Cargar datos ───────────────────────────────────────────────────────────
with open(BASE / "Api_PG/data/solaris_catalogo.json", encoding="utf-8-sig") as f:
    catalogo = json.load(f)

articulos = [a for a in catalogo if a.get("tipoEstructural") in ("ARTICULO","SET","LOTE")]
articulos.sort(key=lambda x: (x.get("categoria",""), x.get("codigoItem","")))
by_cat = defaultdict(list)
for a in articulos:
    by_cat[a["categoria"]].append(a)

def fmt_est(s):
    return s if s and s not in ["-",""] else "—"

def parse_est_range(s):
    if not s or s in ["-",""]: return 0, 0
    nums = re.findall(r"\d[\d,]*", s.replace(",",""))
    vals = [int(n) for n in nums if n]
    if len(vals) >= 2: return vals[0], vals[-1]
    if len(vals) == 1: return vals[0], vals[0]
    return 0, 0

# ── Helpers para requests de formato ─────────────────────────────────────
def cell_fmt(row, col, sid, bg=None, fg=None, bold=False, italic=False,
             size=10, halign="LEFT", valign="MIDDLE", wrap=True):
    fmt = {
        "textFormat": {
            "bold": bold, "italic": italic,
            "fontSize": size,
        },
        "horizontalAlignment": halign,
        "verticalAlignment": valign,
        "wrapStrategy": "WRAP" if wrap else "CLIP",
    }
    if bg: fmt["backgroundColor"] = bg
    if fg: fmt["textFormat"]["foregroundColor"] = fg
    return {
        "repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": row, "endRowIndex": row+1,
                      "startColumnIndex": col, "endColumnIndex": col+1},
            "cell": {"userEnteredFormat": fmt},
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,wrapStrategy)"
        }
    }

def merge_req(r1, r2, c1, c2, sid):
    return {"mergeCells": {
        "range": {"sheetId": sid, "startRowIndex": r1, "endRowIndex": r2,
                  "startColumnIndex": c1, "endColumnIndex": c2},
        "mergeType": "MERGE_ALL"
    }}

def col_width(sid, col, px):
    return {"updateDimensionProperties": {
        "range": {"sheetId": sid, "dimension": "COLUMNS",
                  "startIndex": col, "endIndex": col+1},
        "properties": {"pixelSize": px},
        "fields": "pixelSize"
    }}

def row_height(sid, row, px):
    return {"updateDimensionProperties": {
        "range": {"sheetId": sid, "dimension": "ROWS",
                  "startIndex": row, "endIndex": row+1},
        "properties": {"pixelSize": px},
        "fields": "pixelSize"
    }}

def freeze_req(sid, rows=3, cols=0):
    return {"updateSheetProperties": {
        "properties": {"sheetId": sid,
                       "gridProperties": {"frozenRowCount": rows, "frozenColumnCount": cols}},
        "fields": "gridProperties(frozenRowCount,frozenColumnCount)"
    }}

# ── Gestión de pestañas ────────────────────────────────────────────────────
def get_existing_sheets():
    meta = ss.get(spreadsheetId=SHEET_ID, fields="sheets(properties(sheetId,title))").execute()
    return {s["properties"]["title"]: s["properties"]["sheetId"]
            for s in meta.get("sheets", [])}

def delete_sheet(sid):
    ss.batchUpdate(spreadsheetId=SHEET_ID,
                   body={"requests": [{"deleteSheet": {"sheetId": sid}}]}).execute()

def create_sheet(title, index=0):
    resp = ss.batchUpdate(spreadsheetId=SHEET_ID, body={"requests": [{
        "addSheet": {"properties": {"title": title, "index": index,
                                    "gridProperties": {"rowCount": 1000, "columnCount": 20}}}
    }]}).execute()
    return resp["replies"][0]["addSheet"]["properties"]["sheetId"]

TABS = [
    "IM_Resumen",
    "IM_Inventario Completo",
    "IM_Ventas",
    "IM_Reservas Herederos",
    "IM_Sothebys",
]

def setup_tabs():
    existing = get_existing_sheets()
    ids = {}
    for i, name in enumerate(TABS):
        if name in existing:
            delete_sheet(existing[name])
        ids[name] = create_sheet(name, index=i)
    return ids

# ══════════════════════════════════════════════════════════════════════════════
# HOJA 1 — RESUMEN
# ══════════════════════════════════════════════════════════════════════════════
def build_resumen(sid):
    # Calcular totales
    vendidos       = [a for a in articulos if a.get("estado") == "Vendido"]
    reservados_lst = [a for a in articulos if a.get("reservadoPara") and a.get("estado") != "Vendido"]
    n_vend = len(vendidos);  n_res = len(reservados_lst)
    n_disp = len(articulos) - n_vend - n_res
    n_soth = sum(1 for a in articulos if a.get("tieneSothebys"))
    tot_usd = sum(a.get("precioUSD") or 0 for a in vendidos)
    tot_crc = sum(a.get("precioColones") or 0 for a in vendidos)
    tot_min = tot_max = 0
    for a in articulos:
        lo, hi = parse_est_range(a.get("estimacionSothebys",""))
        tot_min += lo; tot_max += hi

    values = []
    fmts   = []
    COLS   = 8

    # Títulos
    values.append(["INVENTARIO MAESTRO SOLARIS — SUCESIÓN PIGNATELLI"] + [""]*7)
    values.append(["Condominio Solaris  ·  Inventario completo documentado  ·  Abril 2026"] + [""]*7)
    values.append(["Valoraciones Sotheby's International Realty — Londres, 18 de enero de 2016"] + [""]*7)
    values.append([""]*8)  # spacer

    # KPIs fila labels (row 4) + valores (row 5)
    values.append(["TOTAL ARTÍCULOS", "", "DISPONIBLES", "", "RESERVADOS", "", "VENDIDOS", ""])
    values.append([str(len(articulos)), "", str(n_disp), "", str(n_res), "", str(n_vend), ""])
    values.append([""]*8)  # spacer

    # Ventas (rows 7-8)
    values.append(["VENTAS REALIZADAS", "", f"TOTAL USD  $ {tot_usd:,.2f}", "", "", f"TOTAL CRC  {tot_crc:,.2f}", "", ""])
    values.append([""]*8)  # spacer

    # Sotheby's (rows 9-10)
    values.append([f"TASADOS SOTHEBY'S  {n_soth} artículos", "",
                   f"EST. MÍNIMA  $ {tot_min:,}", "", "",
                   f"EST. MÁXIMA  $ {tot_max:,}", "", ""])
    values.append([""]*8)  # spacer

    # Tabla headers (row 11)
    values.append(["Categoría","Artículos","Disponibles","Reservados","Vendidos","Con Sotheby's","Est. Mín USD","Est. Máx USD"])

    # Filas por categoría
    cat_row_start = len(values)
    for cat in sorted(by_cat.keys()):
        items = by_cat[cat]
        n_v = sum(1 for a in items if a.get("estado") == "Vendido")
        n_r = sum(1 for a in items if a.get("reservadoPara") and a.get("estado") != "Vendido")
        n_d = len(items) - n_v - n_r
        n_s = sum(1 for a in items if a.get("tieneSothebys"))
        e_min = e_max = 0
        for a in items:
            lo, hi = parse_est_range(a.get("estimacionSothebys",""))
            e_min += lo; e_max += hi
        values.append([cat, len(items),
                        n_d if n_d else "—", n_r if n_r else "—",
                        n_v if n_v else "—", n_s if n_s else "—",
                        f"$ {e_min:,}" if e_min else "—",
                        f"$ {e_max:,}" if e_max else "—"])

    # Total fila
    values.append(["TOTAL", len(articulos), n_disp, n_res, n_vend, n_soth,
                    f"$ {tot_min:,}", f"$ {tot_max:,}"])

    return values, sid, cat_row_start

def fmt_resumen(sid, values, cat_row_start):
    reqs = []
    COLS = 8

    # Anchos de columna
    widths = [200,110,110,110,110,110,130,130]
    for i, w in enumerate(widths):
        reqs.append(col_width(sid, i, w))

    # Merge + formato filas de título
    for r, (bg, size, h) in enumerate([
        (NAVY, 16, 52), (SLATE, 10, 26), (rgb("3D5166"), 9, 20)
    ]):
        reqs.append(merge_req(r, r+1, 0, COLS, sid))
        reqs.append(cell_fmt(r, 0, sid, bg=bg, fg=WHITE, bold=True, size=size, halign="CENTER"))
        reqs.append(row_height(sid, r, h))

    # Spacer row 3
    reqs.append(merge_req(3, 4, 0, COLS, sid))
    reqs.append(cell_fmt(3, 0, sid, bg=rgb("EEF2F7")))
    reqs.append(row_height(sid, 3, 10))

    # KPI labels (row 4) + valores (row 5)
    kpi_def = [
        (0, 2, NAVY,         "TOTAL ARTÍCULOS"),
        (2, 4, rgb("1E8449"),"DISPONIBLES"),
        (4, 6, rgb("C0392B"),"RESERVADOS"),
        (6, 8, rgb("7B1FA2"),"VENDIDOS"),
    ]
    for c1, c2, bg, _ in kpi_def:
        reqs.append(merge_req(4, 5, c1, c2, sid))
        reqs.append(merge_req(5, 6, c1, c2, sid))
        reqs.append(cell_fmt(4, c1, sid, bg=bg, fg=rgb("CCCCCC"), bold=False, italic=True, size=9, halign="CENTER", valign="BOTTOM"))
        reqs.append(cell_fmt(5, c1, sid, bg=bg, fg=WHITE, bold=True, size=20, halign="CENTER", valign="TOP"))
    reqs.append(row_height(sid, 4, 22))
    reqs.append(row_height(sid, 5, 42))

    # Spacer 6
    reqs.append(merge_req(6, 7, 0, COLS, sid))
    reqs.append(cell_fmt(6, 0, sid, bg=rgb("EEF2F7")))
    reqs.append(row_height(sid, 6, 10))

    # Ventas (row 7) — 3 rangos sin solapamiento: (0,2) (2,5) (5,8)
    for c1, c2, bg in [(0,2,rgb("6A1B9A")),(2,5,rgb("7B1FA2")),(5,8,rgb("7B1FA2"))]:
        reqs.append(merge_req(7, 8, c1, c2, sid))
        reqs.append(cell_fmt(7, c1, sid, bg=bg, fg=WHITE, bold=True, size=11, halign="CENTER"))
    reqs.append(row_height(sid, 7, 34))

    # Spacer 8
    reqs.append(merge_req(8, 9, 0, COLS, sid))
    reqs.append(cell_fmt(8, 0, sid, bg=rgb("EEF2F7")))
    reqs.append(row_height(sid, 8, 10))

    # Sotheby's (row 9) — 3 rangos sin solapamiento: (0,2) (2,5) (5,8)
    for c1, c2, bg in [(0,2,rgb("0D47A1")),(2,5,rgb("1565C0")),(5,8,rgb("1565C0"))]:
        reqs.append(merge_req(9, 10, c1, c2, sid))
        reqs.append(cell_fmt(9, c1, sid, bg=bg, fg=WHITE, bold=True, size=11, halign="CENTER"))
    reqs.append(row_height(sid, 9, 34))

    # Spacer 10
    reqs.append(merge_req(10, 11, 0, COLS, sid))
    reqs.append(cell_fmt(10, 0, sid, bg=rgb("EEF2F7")))
    reqs.append(row_height(sid, 10, 12))

    # Headers tabla (row 11)
    for c in range(COLS):
        reqs.append(cell_fmt(11, c, sid, bg=GRAY_HDR, fg=WHITE, bold=True, size=9, halign="CENTER"))
    reqs.append(row_height(sid, 11, 28))

    # Filas categoría
    for i, cat in enumerate(sorted(by_cat.keys())):
        r = cat_row_start + i
        colors = CAT_COLORS.get(cat, (rgb("444444"), rgb("F5F5F5")))
        reqs.append(cell_fmt(r, 0, sid, bg=colors[1], fg=colors[0], bold=True, size=10))
        for c in range(1, COLS):
            reqs.append(cell_fmt(r, c, sid, bg=colors[1], size=10, halign="CENTER"))
        reqs.append(row_height(sid, r, 22))

    # Fila total
    tot_r = cat_row_start + len(by_cat)
    for c in range(COLS):
        reqs.append(cell_fmt(tot_r, c, sid, bg=SLATE, fg=WHITE, bold=True, size=10, halign="CENTER"))
    reqs.append(row_height(sid, tot_r, 24))

    reqs.append(freeze_req(sid, rows=3))
    return reqs

# ══════════════════════════════════════════════════════════════════════════════
# HOJA 2 — INVENTARIO COMPLETO
# ══════════════════════════════════════════════════════════════════════════════
def build_inventario(sid):
    COLS = 9
    values = []
    values.append(["INVENTARIO COMPLETO — CONDOMINIO SOLARIS · Sucesión Pignatelli"] + [""]*8)
    values.append(["Todos los artículos documentados  ·  Ordenados por categoría  ·  Abril 2026"] + [""]*8)
    values.append(["N°","CÓDIGO","DESCRIPCIÓN DEL OBJETO","CATEGORÍA",
                   "REF. SOTHEBY'S","ESTIMACIÓN (USD)","ESTADO","RESERVADO / COMPRADOR","NOTAS"])

    cat_bands = {}  # row → cat
    num = 0
    for cat in sorted(by_cat.keys()):
        items = by_cat[cat]
        cat_bands[len(values)] = cat
        values.append([f"  {cat.upper()}  —  {len(items)} artículo{'s' if len(items)>1 else ''}"] + [""]*8)
        for art in items:
            num += 1
            persona = art.get("reservadoPara","")
            estado  = art.get("estado","Disponible")
            if estado == "Vendido":    est_txt = "Vendido"
            elif persona:              est_txt = "Reservado"
            else:                      est_txt = "Disponible"
            ref = f"Ref. {art['refSothebys']}" if art.get("refSothebys") else "—"
            est = fmt_est(art.get("estimacionSothebys",""))
            values.append([
                num,
                art["codigoItem"],
                art.get("nombreES","").capitalize()[:60],
                cat,
                ref,
                est,
                est_txt,
                persona if persona else "—",
                art.get("notas","") or ""
            ])

    values.append([""] + [f"TOTAL — {num} artículos"] + [""]*7)
    return values, cat_bands

def fmt_inventario(sid, values, cat_bands):
    reqs = []
    widths = [50, 90, 380, 110, 120, 160, 110, 200, 240]
    for i, w in enumerate(widths):
        reqs.append(col_width(sid, i, w))

    COLS = 9
    reqs.append(merge_req(0, 1, 0, COLS, sid))
    reqs.append(cell_fmt(0, 0, sid, bg=NAVY, fg=WHITE, bold=True, size=14, halign="CENTER"))
    reqs.append(row_height(sid, 0, 36))
    reqs.append(merge_req(1, 2, 0, COLS, sid))
    reqs.append(cell_fmt(1, 0, sid, bg=SLATE, fg=WHITE, italic=True, size=10, halign="CENTER"))
    reqs.append(row_height(sid, 1, 22))
    for c in range(COLS):
        reqs.append(cell_fmt(2, c, sid, bg=GRAY_HDR, fg=WHITE, bold=True, size=9, halign="CENTER"))
    reqs.append(row_height(sid, 2, 26))

    for r, cat in cat_bands.items():
        colors = CAT_COLORS.get(cat, (rgb("444444"), rgb("F5F5F5")))
        reqs.append(merge_req(r, r+1, 0, COLS, sid))
        reqs.append(cell_fmt(r, 0, sid, bg=colors[0], fg=WHITE, bold=True, size=11))
        reqs.append(row_height(sid, r, 24))

    reqs.append(freeze_req(sid, rows=3))
    return reqs

# ══════════════════════════════════════════════════════════════════════════════
# HOJA 3 — VENTAS
# ══════════════════════════════════════════════════════════════════════════════
def build_ventas(sid):
    vendidos = [a for a in articulos if a.get("estado") == "Vendido"]
    vendidos.sort(key=lambda x: x.get("codigoItem",""))
    values = []
    values.append(["VENTAS REALIZADAS — CONDOMINIO SOLARIS · Sucesión Pignatelli"] + [""]*8)
    values.append(["Artículos vendidos  ·  Precios en USD y CRC  ·  17 de marzo de 2026"] + [""]*8)
    values.append(["N°","CÓDIGO","DESCRIPCIÓN","COMPRADOR","CATEGORÍA",
                   "PRECIO (USD)","PRECIO (CRC)","FECHA VENTA","FOTO PRINCIPAL"])
    for i, art in enumerate(vendidos):
        fotos = art.get("fotos",[])
        values.append([
            i+1,
            art["codigoItem"],
            art.get("nombreES","").capitalize()[:60],
            art.get("reservadoPara",""),
            art.get("categoria",""),
            f"$ {art.get('precioUSD',0):,.2f}",
            f"CRC {art.get('precioColones',0):,.2f}",
            art.get("fechaVenta","—") or "—",
            fotos[0] if fotos else "—"
        ])
    tot_usd = sum(a.get("precioUSD") or 0 for a in vendidos)
    tot_crc = sum(a.get("precioColones") or 0 for a in vendidos)
    values.append(["","TOTAL VENTAS","","","",
                   f"$ {tot_usd:,.2f}", f"CRC {tot_crc:,.2f}","",""])
    return values

def fmt_ventas(sid, n_ventas):
    reqs = []
    widths = [50,90,340,200,120,130,180,120,320]
    for i, w in enumerate(widths):
        reqs.append(col_width(sid, i, w))
    COLS = 9
    reqs.append(merge_req(0, 1, 0, COLS, sid))
    reqs.append(cell_fmt(0, 0, sid, bg=rgb("7B1FA2"), fg=WHITE, bold=True, size=14, halign="CENTER"))
    reqs.append(row_height(sid, 0, 36))
    reqs.append(merge_req(1, 2, 0, COLS, sid))
    reqs.append(cell_fmt(1, 0, sid, bg=rgb("6A1B9A"), fg=WHITE, italic=True, size=10, halign="CENTER"))
    reqs.append(row_height(sid, 1, 22))
    for c in range(COLS):
        reqs.append(cell_fmt(2, c, sid, bg=GRAY_HDR, fg=WHITE, bold=True, size=9, halign="CENTER"))
    reqs.append(row_height(sid, 2, 26))
    for r in range(3, 3 + n_ventas):
        bg = rgb("F3E5F5") if (r-3) % 2 == 0 else WHITE
        for c in range(COLS):
            reqs.append(cell_fmt(r, c, sid, bg=bg, size=10))
        reqs.append(cell_fmt(r, 1, sid, bg=bg, fg=rgb("7B1FA2"), bold=True, size=10, halign="CENTER"))
        reqs.append(cell_fmt(r, 5, sid, bg=bg, fg=rgb("1F4E79"), bold=True, size=10, halign="CENTER"))
        reqs.append(cell_fmt(r, 6, sid, bg=bg, fg=rgb("27AE60"), bold=True, size=10, halign="CENTER"))
        reqs.append(row_height(sid, r, 22))
    tot_r = 3 + n_ventas
    for c in range(COLS):
        reqs.append(cell_fmt(tot_r, c, sid, bg=rgb("7B1FA2"), fg=WHITE, bold=True, size=10, halign="CENTER"))
    reqs.append(row_height(sid, tot_r, 24))
    reqs.append(freeze_req(sid, rows=3))
    return reqs

# ══════════════════════════════════════════════════════════════════════════════
# HOJA 4 — RESERVAS HEREDEROS
# ══════════════════════════════════════════════════════════════════════════════
import csv as _csv

HEREDERO_COLORS = {
    "Adriano Pignatelli":   (rgb("1A5276"), rgb("D6EAF8")),
    "Diego Pignatelli":     (rgb("1E8449"), rgb("D5F5E3")),
    "Fabrizia Pignatelli":  (rgb("7D3C98"), rgb("E8DAEF")),
    "Margherita Pignatelli":(rgb("B7770D"), rgb("FDEBD0")),
    "Maria Cristina Smith": (rgb("922B21"), rgb("FADBD8")),
}

def build_reservas(sid):
    reservas_path = BASE / "docs/reservas_herederos_maestro_2026-04-13.csv"
    soth_path     = BASE / "docs/sothebys_maestro_2026-04-13.csv"
    with open(reservas_path, newline="", encoding="utf-8-sig") as f:
        reservas = list(_csv.DictReader(f))
    with open(soth_path, newline="", encoding="utf-8-sig") as f:
        soth_rows = list(_csv.DictReader(f))
    soth_by_cod = {}
    for r in soth_rows:
        for parte in r.get("codigo_actual","").split(";"):
            cod = re.sub(r"-\d+$","",parte.strip()).strip()
            if cod: soth_by_cod[cod] = r.get("estimacion","").strip()
    cat_lk = {a["codigoItem"]: a.get("categoria","") for a in articulos}

    from collections import defaultdict as _dd
    por_heredero = _dd(list)
    for r in reservas:
        por_heredero[r["heredero"]].append(r)

    values = []
    values.append(["RESERVAS DE HEREDEROS — Sucesión Pignatelli"] + [""]*5)
    values.append(["Artículos reservados por heredero  ·  Valoraciones Sotheby's enero 2016"] + [""]*5)
    values.append(["N°","CÓDIGO","DESCRIPCIÓN","HEREDERO","CATEGORÍA","ESTIMACIÓN (USD)"])

    band_rows = {}
    num = 0
    for heredero in sorted(por_heredero.keys()):
        items_h = por_heredero[heredero]
        band_rows[len(values)] = heredero
        values.append([f"  {heredero.upper()}  —  {len(items_h)} artículo{'s' if len(items_h)>1 else ''}"] + [""]*5)
        for r in items_h:
            num += 1
            cod = r["codigo"].strip()
            est = soth_by_cod.get(cod,"—")
            if est in ["-",""]: est = "—"
            values.append([num, cod, r["nombre"].capitalize()[:60],
                           heredero, cat_lk.get(cod,""), est])
    values.append(["",f"TOTAL — {num} artículos reservados","","","",""])
    return values, band_rows

def fmt_reservas(sid, band_rows):
    reqs = []
    widths = [50,90,360,200,120,160]
    for i, w in enumerate(widths):
        reqs.append(col_width(sid, i, w))
    COLS = 6
    reqs.append(merge_req(0,1,0,COLS,sid))
    reqs.append(cell_fmt(0,0,sid,bg=NAVY,fg=WHITE,bold=True,size=14,halign="CENTER"))
    reqs.append(row_height(sid,0,36))
    reqs.append(merge_req(1,2,0,COLS,sid))
    reqs.append(cell_fmt(1,0,sid,bg=SLATE,fg=WHITE,italic=True,size=10,halign="CENTER"))
    reqs.append(row_height(sid,1,22))
    for c in range(COLS):
        reqs.append(cell_fmt(2,c,sid,bg=GRAY_HDR,fg=WHITE,bold=True,size=9,halign="CENTER"))
    reqs.append(row_height(sid,2,26))
    for r, heredero in band_rows.items():
        colors = HEREDERO_COLORS.get(heredero,(rgb("444444"),rgb("F5F5F5")))
        reqs.append(merge_req(r,r+1,0,COLS,sid))
        reqs.append(cell_fmt(r,0,sid,bg=colors[0],fg=WHITE,bold=True,size=11))
        reqs.append(row_height(sid,r,24))
    reqs.append(freeze_req(sid,rows=3))
    return reqs

# ══════════════════════════════════════════════════════════════════════════════
# HOJA 5 — SOTHEBY'S
# ══════════════════════════════════════════════════════════════════════════════
def build_sothebys(sid):
    con_soth = [a for a in articulos if a.get("tieneSothebys")]
    con_soth.sort(key=lambda x: (x.get("categoria",""),x.get("codigoItem","")))
    values = []
    values.append(["ARTÍCULOS CON VALORACIÓN SOTHEBY'S — Sucesión Pignatelli"] + [""]*6)
    values.append(["Sotheby's International Realty · Londres · 18 de enero de 2016  |  Valores en USD"] + [""]*6)
    values.append(["N°","CÓDIGO","DESCRIPCIÓN","REF. SOTHEBY'S","PÁG.","ESTIMACIÓN (USD)","ESTADO / RESERVADO"])

    band_rows = {}
    num = 0
    cat_actual = None
    for art in con_soth:
        cat = art.get("categoria","")
        if cat != cat_actual:
            band_rows[len(values)] = cat
            cat_count = sum(1 for a in con_soth if a.get("categoria") == cat)
            values.append([f"  {cat.upper()}  —  {cat_count} artículo{'s' if cat_count>1 else ''}"] + [""]*6)
            cat_actual = cat
        num += 1
        res = art.get("reservadoPara","")
        estado_txt = res if res else "Disponible"
        values.append([num, art["codigoItem"],
                        art.get("nombreES","").capitalize()[:60],
                        f"Ref. {art.get('refSothebys','')}",
                        str(art.get("paginaSothebys","")),
                        fmt_est(art.get("estimacionSothebys","")),
                        estado_txt])
    values.append(["",f"TOTAL — {num} artículos con valoración Sotheby's","","","","",""])
    return values, band_rows

def fmt_sothebys(sid, band_rows):
    reqs = []
    widths = [50,90,360,130,60,160,200]
    for i, w in enumerate(widths):
        reqs.append(col_width(sid, i, w))
    COLS = 7
    reqs.append(merge_req(0,1,0,COLS,sid))
    reqs.append(cell_fmt(0,0,sid,bg=NAVY,fg=WHITE,bold=True,size=14,halign="CENTER"))
    reqs.append(row_height(sid,0,36))
    reqs.append(merge_req(1,2,0,COLS,sid))
    reqs.append(cell_fmt(1,0,sid,bg=SLATE,fg=WHITE,italic=True,size=10,halign="CENTER"))
    reqs.append(row_height(sid,1,22))
    for c in range(COLS):
        reqs.append(cell_fmt(2,c,sid,bg=GRAY_HDR,fg=WHITE,bold=True,size=9,halign="CENTER"))
    reqs.append(row_height(sid,2,26))
    for r, cat in band_rows.items():
        colors = CAT_COLORS.get(cat,(rgb("444444"),rgb("F5F5F5")))
        reqs.append(merge_req(r,r+1,0,COLS,sid))
        reqs.append(cell_fmt(r,0,sid,bg=colors[0],fg=WHITE,bold=True,size=11))
        reqs.append(row_height(sid,r,24))
    reqs.append(freeze_req(sid,rows=3))
    return reqs

# ══════════════════════════════════════════════════════════════════════════════
# MAIN — Enviar todo al Sheet
# ══════════════════════════════════════════════════════════════════════════════
def write_values(sid, values, tab_name):
    # Convertir todo a strings seguros
    def safe(v):
        if v is None: return ""
        return str(v)
    clean = [[safe(c) for c in row] for row in values]
    ss.values().update(
        spreadsheetId=SHEET_ID,
        range=f"'{tab_name}'!A1",
        valueInputOption="USER_ENTERED",
        body={"values": clean}
    ).execute()

def apply_formats(reqs):
    # Google Sheets limita a 30,000 celdas por request — dividir si es necesario
    CHUNK = 500
    for i in range(0, len(reqs), CHUNK):
        ss.batchUpdate(
            spreadsheetId=SHEET_ID,
            body={"requests": reqs[i:i+CHUNK]}
        ).execute()

def main():
    print("Creando pestañas…")
    ids = setup_tabs()

    # ── Resumen ──
    print("Sincronizando IM_Resumen…")
    sid = ids["IM_Resumen"]
    vals, _, cat_row = build_resumen(sid)
    write_values(sid, vals, "IM_Resumen")
    apply_formats(fmt_resumen(sid, vals, cat_row))

    # ── Inventario completo ──
    print("Sincronizando IM_Inventario Completo…")
    sid = ids["IM_Inventario Completo"]
    vals, cat_bands = build_inventario(sid)
    write_values(sid, vals, "IM_Inventario Completo")
    apply_formats(fmt_inventario(sid, vals, cat_bands))

    # ── Ventas ──
    print("Sincronizando IM_Ventas…")
    sid = ids["IM_Ventas"]
    vendidos = [a for a in articulos if a.get("estado") == "Vendido"]
    vals = build_ventas(sid)
    write_values(sid, vals, "IM_Ventas")
    apply_formats(fmt_ventas(sid, len(vendidos)))

    # ── Reservas ──
    print("Sincronizando IM_Reservas Herederos…")
    sid = ids["IM_Reservas Herederos"]
    vals, band_rows = build_reservas(sid)
    write_values(sid, vals, "IM_Reservas Herederos")
    apply_formats(fmt_reservas(sid, band_rows))

    # ── Sotheby's ──
    print("Sincronizando IM_Sothebys…")
    sid = ids["IM_Sothebys"]
    vals, band_rows = build_sothebys(sid)
    write_values(sid, vals, "IM_Sothebys")
    apply_formats(fmt_sothebys(sid, band_rows))

    print(f"\nOK — 5 pestañas sincronizadas en Sheet {SHEET_ID}")
    print("Prefijo IM_ para no colisionar con pestañas existentes.")

if __name__ == "__main__":
    main()
