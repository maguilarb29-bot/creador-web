"""
Casa Pignatelli — Servidor de inventario y ventas
Arrancar: python server.py
URL:      http://localhost:8080
"""
from flask import Flask, jsonify, request, send_from_directory, abort
import json, uuid
from datetime import datetime
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

BASE = Path(__file__).parent
DATA = BASE / "data"
CATALOGO_FILE      = DATA / "solaris_catalogo.json"
HEREDEROS_FILE     = DATA / "reservas_excel_entregable_2026-04-13.json"
TRANSACCIONES_FILE = DATA / "transacciones.json"
ESTADOS_FILE       = DATA / "estados.json"
CONTADORES_FILE    = DATA / "contadores.json"
EXCEL_VENTAS       = DATA / "Registro_Ventas_Reservas.xlsx"

app = Flask(__name__, static_folder=str(BASE))

# ── helpers ──────────────────────────────────────────────────
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def siguiente_factura():
    c = load_json(CONTADORES_FILE) if CONTADORES_FILE.exists() else {"ultimaFactura": 9}
    c["ultimaFactura"] = c.get("ultimaFactura", 9) + 1
    save_json(CONTADORES_FILE, c)
    return f"FAC-{c['ultimaFactura']:04d}"

def load_estados():
    if not ESTADOS_FILE.exists():
        return {}
    try:
        return load_json(ESTADOS_FILE)
    except Exception:
        return {}

def save_estado(codigo, estado, reservadoPara="", confirmadoHeredero=False):
    estados = load_estados()
    estados[codigo] = {
        "estado": estado,
        "reservadoPara": reservadoPara,
        "confirmadoHeredero": confirmadoHeredero,
    }
    save_json(ESTADOS_FILE, estados)

def catalogo_con_estados():
    catalogo = load_json(CATALOGO_FILE)
    estados = load_estados()
    for item in catalogo:
        e = estados.get(item["codigoItem"])
        if e:
            item["estado"] = e["estado"]
            item["reservadoPara"] = e.get("reservadoPara", "")
            item["confirmadoHeredero"] = e.get("confirmadoHeredero", False)
    return catalogo

def load_transacciones():
    if not TRANSACCIONES_FILE.exists():
        return {"transacciones": []}
    return load_json(TRANSACCIONES_FILE)

def header_cell(ws, row, col, value, bg="1a1209", fg="c9a227", bold=True, size=10):
    c = ws.cell(row=row, column=col, value=value)
    c.font = Font(bold=bold, color=fg, size=size)
    c.fill = PatternFill("solid", fgColor=bg)
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin = Side(border_style="thin", color="333333")
    c.border = Border(thin, thin, thin, thin)
    return c

def auto_width(ws, extra=3, max_w=60):
    from openpyxl.cell.cell import MergedCell
    for col in ws.columns:
        first = col[0]
        if isinstance(first, MergedCell):
            continue
        w = max((len(str(c.value)) for c in col if c.value and not isinstance(c, MergedCell)), default=8)
        ws.column_dimensions[first.column_letter].width = min(w + extra, max_w)

# ── Excel export ─────────────────────────────────────────────
def rebuild_excel(transacciones):
    wb = Workbook()

    # ── Hoja Transacciones ──
    ws = wb.active
    ws.title = "Transacciones"
    ws.row_dimensions[1].height = 32

    cols_tx = ["ID Tiquete", "Fecha/Hora", "Tipo", "Heredero",
               "N° Artículos", "Est. Mín USD", "Est. Máx USD",
               "Precio Acordado USD", "Estado", "Notas"]
    for i, h in enumerate(cols_tx, 1):
        header_cell(ws, 1, i, h)

    for r, tx in enumerate(transacciones, 2):
        data_row = [
            tx["id"],
            tx["timestamp"][:16].replace("T", " "),
            tx["tipo"].upper(),
            tx["heredero"],
            len(tx.get("items", [])),
            tx.get("totalEstMinUSD", 0),
            tx.get("totalEstMaxUSD", 0),
            tx.get("totalAcordadoUSD") or "",
            tx["estado"].upper(),
            tx.get("notas", ""),
        ]
        row_color = "f0fff0" if tx["estado"] == "confirmado" else "fff0f0"
        for c_idx, val in enumerate(data_row, 1):
            cell = ws.cell(row=r, column=c_idx, value=val)
            cell.fill = PatternFill("solid", fgColor=row_color)
            thin = Side(border_style="thin", color="cccccc")
            cell.border = Border(thin, thin, thin, thin)
            cell.alignment = Alignment(vertical="center")

    auto_width(ws)

    # ── Hoja Detalle Artículos ──
    ws2 = wb.create_sheet("Detalle Artículos")
    ws2.row_dimensions[1].height = 32
    cols_det = ["ID Tiquete", "Heredero", "Tipo", "Código", "Artículo",
                "Categoría", "Est. Mín USD", "Est. Máx USD", "Precio Acordado", "Ref Sotheby's"]
    for i, h in enumerate(cols_det, 1):
        header_cell(ws2, 1, i, h)

    r2 = 2
    for tx in transacciones:
        for item in tx.get("items", []):
            row_color = "f0fff0" if tx["estado"] == "confirmado" else "fff0f0"
            vals = [
                tx["id"], tx["heredero"], tx["tipo"].upper(),
                item.get("codigoItem", ""), item.get("nombreES", ""),
                item.get("categoria", ""),
                item.get("estimMin", 0), item.get("estimMax", 0),
                item.get("precioAcordado") or "",
                item.get("refSothebys", ""),
            ]
            for c_idx, val in enumerate(vals, 1):
                cell = ws2.cell(row=r2, column=c_idx, value=val)
                cell.fill = PatternFill("solid", fgColor=row_color)
                thin = Side(border_style="thin", color="cccccc")
                cell.border = Border(thin, thin, thin, thin)
                cell.alignment = Alignment(vertical="center")
            r2 += 1

    auto_width(ws2)

    # ── Hoja Resumen ──
    ws3 = wb.create_sheet("Resumen")
    ws3.merge_cells("A1:D1")
    c = ws3["A1"]
    c.value = "Casa Pignatelli — Resumen de Ventas y Reservas"
    c.font = Font(bold=True, size=14, color="c9a227")
    c.fill = PatternFill("solid", fgColor="1a1209")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws3.row_dimensions[1].height = 40

    header_cell(ws3, 2, 1, "Heredero")
    header_cell(ws3, 2, 2, "Reservas")
    header_cell(ws3, 2, 3, "Ventas")
    header_cell(ws3, 2, 4, "Total Est. Máx USD")

    heirs = {}
    for tx in transacciones:
        if tx["estado"] != "confirmado":
            continue
        h = tx["heredero"]
        if h not in heirs:
            heirs[h] = {"reservas": 0, "ventas": 0, "max": 0}
        if tx["tipo"] == "reserva":
            heirs[h]["reservas"] += 1
        else:
            heirs[h]["ventas"] += 1
        heirs[h]["max"] += tx.get("totalEstMaxUSD", 0)

    for r3, (heir, v) in enumerate(sorted(heirs.items()), 3):
        ws3.cell(row=r3, column=1, value=heir)
        ws3.cell(row=r3, column=2, value=v["reservas"])
        ws3.cell(row=r3, column=3, value=v["ventas"])
        ws3.cell(row=r3, column=4, value=v["max"])

    auto_width(ws3)
    wb.save(EXCEL_VENTAS)
    return str(EXCEL_VENTAS.name)

# ── helpers de estado ────────────────────────────────────────
def parse_estimate(s):
    if not s: return {"min": 0, "max": 0}
    import re
    nums = re.findall(r"\d[\d,]*", s.replace("$", ""))
    if len(nums) >= 2:
        return {"min": int(nums[0].replace(",","")), "max": int(nums[1].replace(",",""))}
    return {"min": 0, "max": 0}

# ── Rutas API ────────────────────────────────────────────────
@app.route("/api/catalogo")
def api_catalogo():
    return jsonify(catalogo_con_estados())

@app.route("/api/herederos")
def api_herederos():
    return jsonify(load_json(HEREDEROS_FILE))

@app.route("/api/transacciones")
def api_transacciones():
    return jsonify(load_transacciones())

@app.route("/api/transaccion", methods=["POST"])
def api_crear_transaccion():
    body = request.get_json(force=True)
    items = body.get("items", [])
    tipo  = body.get("tipo", "reserva")
    heredero = body.get("heredero", "").strip()
    notas    = body.get("notas", "").strip()

    if not items:
        return jsonify({"error": "Sin artículos"}), 400
    if not heredero:
        return jsonify({"error": "Debe indicar el heredero o comprador"}), 400

    tx_id = f"TX-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:4].upper()}"

    total_min = sum(i.get("estimMin", 0) or 0 for i in items)
    total_max = sum(i.get("estimMax", 0) or 0 for i in items)
    total_acordado = sum(i.get("precioAcordado", 0) or 0 for i in items) or None

    tx = {
        "id": tx_id,
        "timestamp": datetime.now().isoformat(),
        "tipo": tipo,
        "heredero": heredero,
        "items": items,
        "totalEstMinUSD": total_min,
        "totalEstMaxUSD": total_max,
        "totalAcordadoUSD": total_acordado,
        "notas": notas,
        "estado": "confirmado",
    }

    data = load_transacciones()
    data["transacciones"].append(tx)
    save_json(TRANSACCIONES_FILE, data)

    # Actualizar estado
    nuevo_estado = "Reservado" if tipo == "reserva" else "Vendido"
    for i in items:
        save_estado(i["codigoItem"], nuevo_estado, heredero)
    rebuild_excel(data["transacciones"])

    return jsonify({"success": True, "transaccion": tx})

@app.route("/api/reservar-item", methods=["POST"])
def api_reservar_item():
    body = request.get_json(force=True)
    codigo   = body.get("codigoItem", "").strip()
    heredero = body.get("heredero", "").strip()
    if not codigo or not heredero:
        return jsonify({"error": "Faltan datos"}), 400

    catalogo = catalogo_con_estados()
    item = next((i for i in catalogo if i["codigoItem"] == codigo), None)
    if not item:
        return jsonify({"error": "Artículo no encontrado"}), 404

    save_estado(codigo, "Reservado", heredero, False)

    # Registrar transacción
    est = parse_estimate(item.get("estimacionSothebys", ""))
    data = load_transacciones()
    tx_id = f"TX-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:4].upper()}"
    tx = {
        "id": tx_id,
        "timestamp": datetime.now().isoformat(),
        "tipo": "reserva",
        "heredero": heredero,
        "items": [{
            "codigoItem":        codigo,
            "nombreES":          item.get("nombreES", ""),
            "categoria":         item.get("categoria", ""),
            "estimMin":          est["min"],
            "estimMax":          est["max"],
            "estimacionSothebys":item.get("estimacionSothebys", ""),
            "refSothebys":       item.get("refSothebys", ""),
            "fotos":             item.get("fotos", []),
        }],
        "totalEstMinUSD": est["min"],
        "totalEstMaxUSD": est["max"],
        "notas": "Reserva directa Sotheby's",
        "estado": "confirmado",
    }
    data["transacciones"].append(tx)
    save_json(TRANSACCIONES_FILE, data)
    rebuild_excel(data["transacciones"])
    return jsonify({"success": True, "transaccion": tx})

@app.route("/api/confirmar-item", methods=["POST"])
def api_confirmar_item():
    body = request.get_json(force=True)
    codigo = body.get("codigoItem", "").strip()
    estados = load_estados()
    e = estados.get(codigo, {})
    save_estado(codigo, e.get("estado", "Reservado"), e.get("reservadoPara", ""), True)
    return jsonify({"success": True})

@app.route("/api/liberar-item", methods=["POST"])
def api_liberar_item():
    body = request.get_json(force=True)
    codigo = body.get("codigoItem", "").strip()
    catalogo = catalogo_con_estados()
    item = next((i for i in catalogo if i["codigoItem"] == codigo), None)
    if not item:
        return jsonify({"error": "No encontrado"}), 404

    save_estado(codigo, "Disponible", "", False)

    # Cancelar transacciones activas de este artículo
    data = load_transacciones()
    for tx in data["transacciones"]:
        if tx["estado"] == "confirmado" and any(
            i.get("codigoItem") == codigo for i in tx.get("items", [])
        ):
            tx["estado"]      = "cancelado"
            tx["canceladoEn"] = datetime.now().isoformat()
    save_json(TRANSACCIONES_FILE, data)
    rebuild_excel(data["transacciones"])
    return jsonify({"success": True})

@app.route("/api/transaccion/<tx_id>/cancelar", methods=["POST"])
def api_cancelar(tx_id):
    data = load_transacciones()
    tx = next((t for t in data["transacciones"] if t["id"] == tx_id), None)
    if not tx:
        return jsonify({"error": "No encontrado"}), 404

    tx["estado"] = "cancelado"
    tx["canceladoEn"] = datetime.now().isoformat()

    # Revertir estado
    for i in tx.get("items", []):
        save_estado(i["codigoItem"], "Disponible", "")

    save_json(TRANSACCIONES_FILE, data)
    rebuild_excel(data["transacciones"])
    return jsonify({"success": True})

@app.route("/api/transaccion/<tx_id>/numero-factura", methods=["POST"])
def api_numero_factura(tx_id):
    data = load_transacciones()
    tx = next((t for t in data["transacciones"] if t["id"] == tx_id), None)
    if not tx:
        return jsonify({"error": "No encontrado"}), 404
    if not tx.get("numeroFactura"):
        tx["numeroFactura"] = siguiente_factura()
        save_json(TRANSACCIONES_FILE, data)
    return jsonify({"numeroFactura": tx["numeroFactura"]})

@app.route("/api/excel/descargar")
def api_descargar_excel():
    from flask import send_file
    if not EXCEL_VENTAS.exists():
        data = load_transacciones()
        rebuild_excel(data.get("transacciones", []))
    return send_file(str(EXCEL_VENTAS), as_attachment=True,
                     download_name="Pignatelli_Ventas_Reservas.xlsx")

# ── Archivos estáticos ───────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(str(BASE), "panel_herederos.html")

@app.route("/images/<path:filename>")
def serve_images(filename):
    from flask import send_file
    import urllib.parse
    decoded = urllib.parse.unquote(filename)
    full_path = BASE / "images" / decoded
    if full_path.exists():
        return send_file(str(full_path))
    # Fallback: buscar solo por nombre de archivo en Todas las Fotos
    nombre = Path(decoded).name
    fallback = BASE / "images" / "fotos-Solaris-inventory" / "Todas las Fotos" / nombre
    if fallback.exists():
        return send_file(str(fallback))
    abort(404)

@app.route("/data/<path:filename>")
def serve_data(filename):
    return send_from_directory(str(BASE / "data"), filename)

@app.route("/<path:filename>")
def static_files(filename):
    full = BASE / filename
    if full.exists() and full.is_file():
        return send_from_directory(str(BASE), filename)
    abort(404)

if __name__ == "__main__":
    print("\nCasa Pignatelli - Servidor activo")
    print("  http://localhost:8090\n")
    app.run(host="0.0.0.0", port=8090, debug=False, use_reloader=False, threaded=True)
