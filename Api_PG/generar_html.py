#!/usr/bin/env python3
"""Genera solaris_catalogo.html desde solaris_catalogo.json"""
import json, os, re, csv
from collections import defaultdict

BASE      = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE, "data", "solaris_catalogo.json")
FOTOS_DIR = os.path.join(BASE, "images", "fotos-Solaris-inventory", "Todas las Fotos")
OUTPUT    = os.path.join(BASE, "solaris_catalogo.html")
SOTH_CSV  = os.path.join(os.path.dirname(BASE), "docs", "sothebys_maestro_2026-04-13.csv")

with open(DATA_FILE, encoding="utf-8-sig") as f:
    catalogo = json.load(f)

# Lookup Sotheby's desde CSV
soth_lookup = {}
with open(SOTH_CSV, newline="", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        est = row.get("estimacion","").strip()
        for parte in row.get("codigo_actual","").split(";"):
            cod = re.sub(r"-\d+$","", parte.strip()).strip()
            if cod and est and est != "-":
                soth_lookup[cod] = est

# Todos los items reales
todos = [a for a in catalogo if a.get("tipoEstructural") in ("ARTICULO","SET","LOTE")]

# Cada codigo aparece como tarjeta individual
articulos = todos

# Identificar SETs y sub-items para badges visuales (sin ocultar ninguna tarjeta)
set_codigos = {a["codigoItem"] for a in todos if a.get("tipoEstructural") == "SET"}

# Indice de fotos en disco
foto_cache = {}
if os.path.isdir(FOTOS_DIR):
    for fname in os.listdir(FOTOS_DIR):
        foto_cache[fname.lower()] = fname

def foto_principal(a):
    for foto in (a.get("fotos") or []):
        if foto.lower() in foto_cache:
            return f"images/fotos-Solaris-inventory/Todas las Fotos/{foto_cache[foto.lower()]}"
    return None

# Agrupar por categoria
by_cat = defaultdict(list)
for a in articulos:
    by_cat[a.get("categoria","Sin categoria")].append(a)

CAT_COLORS = {
    "Arte en papel":     "#5D4037",
    "Ceramica":          "#1565C0",
    "Cristaleria":       "#00695C",
    "Decorativos":       "#4A148C",
    "Electrodomesticos": "#424242",
    "Insumos Medicos":   "#558B2F",
    "Joyas":             "#880E4F",
    "Muebles":           "#2E7D32",
    "Plateria":          "#37474F",
    "Utensilios":        "#E65100",
}

ESTADO_STYLE = {
    "Disponible": ("disponible", "Disponible"),
    "Reservado":  ("reservado",  "Reservado"),
    "Vendido":    ("vendido",    "Vendido"),
}

_card_id = 0

def card_html(a):
    global _card_id
    _card_id += 1
    cid    = f"c{_card_id}"

    cod    = a.get("codigoItem","")
    nombre = (a.get("nombreES") or "Sin nombre").capitalize()
    cat    = a.get("categoria","")
    estado = a.get("estado","Disponible")
    para   = a.get("reservadoPara","")
    precio = a.get("precioUSD")
    soth     = a.get("tieneSothebys", False)
    soth_est = soth_lookup.get(cod, "")
    notas    = a.get("notas","") or ""
    fotos    = a.get("fotos") or []

    srcs = []
    for foto in fotos:
        if foto.lower() in foto_cache:
            srcs.append(f"images/fotos-Solaris-inventory/Todas las Fotos/{foto_cache[foto.lower()]}")

    est_cls, est_lbl = ESTADO_STYLE.get(estado, ("disponible","Disponible"))
    badge_soth = '<span class="badge-s">Sotheby\'s</span>' if soth else ""
    # Badge SET: padre = "SET REF." | sub-item = "▸ CODIGO_PADRE"
    padre_cod = a.get("codigoPadre","")
    if a.get("tipoEstructural") == "SET":
        badge_set = '<span class="badge-set">SET · Ref.</span>'
    elif padre_cod and padre_cod in set_codigos:
        badge_set = f'<span class="badge-sub">▸ {padre_cod}</span>'
    else:
        badge_set = ""

    # Bloque de imagen / carrusel
    if len(srcs) == 0:
        img_block = '<div class="no-foto">Sin foto</div>'
    elif len(srcs) == 1:
        img_block = f'<img src="{srcs[0]}" alt="{nombre}" loading="lazy" onclick="ampliar(\'{srcs[0]}\')">'
    else:
        slides = ""
        dots   = ""
        for i, src in enumerate(srcs):
            act = " active" if i == 0 else ""
            slides += f'<div class="slide{act}"><img src="{src}" alt="{nombre} {i+1}" loading="lazy" onclick="ampliar(\'{src}\')"></div>'
            dots   += f'<span class="dot{act}" onclick="irSlide(\'{cid}\',{i})"></span>'
        n = len(srcs)
        img_block = f"""<div class="carousel" id="{cid}">
  <div class="slides">{slides}</div>
  <button class="carr-btn prev" onclick="moverSlide('{cid}',-1)">&#8249;</button>
  <button class="carr-btn next" onclick="moverSlide('{cid}',1)">&#8250;</button>
  <div class="dots">{dots}</div>
  <div class="foto-counter">1/{n}</div>
</div>"""

    if precio:
        lbl_precio = "Precio venta" if estado == "Vendido" else "Precio sugerido"
        precio_html = f'<div class="precio"><span class="precio-lbl">{lbl_precio}</span> $ {precio:,.0f} USD</div>'
    else:
        precio_html = ""
    soth_html = f'<div class="soth-est"><span class="soth-lbl">Referencia Sotheby\'s</span> {soth_est}</div>' if soth_est else ""

    para_html = ""
    if para:
        if estado == "Vendido":
            para_html = f'<div class="para vendido-txt">Vendido a: <b>{para}</b></div>'
        else:
            para_html = f'<div class="para reservado-txt">Reservado: <b>{para}</b></div>'

    notas_html = f'<div class="notas">{notas[:100]}</div>' if notas else ""

    return f"""
    <div class="card {est_cls}-card" data-estado="{estado}" data-cat="{cat}" data-cod="{cod}" data-txt="{nombre.lower()} {cod.lower()} {cat.lower()} {para.lower()}">
      <div class="card-img">
        {img_block}
        <div class="card-badges">{badge_soth}{badge_set}</div>
        <div class="card-code">{cod}</div>
        <div class="estado-badge {est_cls}">{est_lbl}</div>
      </div>
      <div class="card-body">
        <div class="card-title">{nombre[:70]}</div>
        <div class="card-cat">{cat}</div>
        {precio_html}
        {soth_html}
        {para_html}
        {notas_html}
      </div>
    </div>"""

# Estadisticas globales
n_total = len(articulos)
n_disp  = sum(1 for a in articulos if a.get("estado","Disponible") == "Disponible")
n_res   = sum(1 for a in articulos if a.get("estado") == "Reservado")
n_vend  = sum(1 for a in articulos if a.get("estado") == "Vendido")

# Tabs y paneles
cats_sorted = sorted(by_cat.keys())
tabs_html   = ""
panels_html = ""
for i, cat in enumerate(cats_sorted):
    items   = sorted(by_cat[cat], key=lambda x: x.get("codigoItem",""))
    color   = CAT_COLORS.get(cat, "#444444")
    active  = "active" if i == 0 else ""
    tabs_html += (
        f'<button class="tab-btn {active}" '
        f'style="--cat-color:{color}" '
        f'onclick="mostrarTab(\'{cat}\')" id="tab-{cat}">'
        f'{cat} <span class="tab-count">{len(items)}</span></button>\n'
    )
    cards = "".join(card_html(a) for a in items)
    panels_html += f'<div class="tab-panel {active}" id="panel-{cat}"><div class="grid">{cards}</div></div>\n'

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Catalogo Solaris — Pignatelli</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',sans-serif;background:#f5f0eb;color:#333}}

/* HEADER */
header{{background:#1A1A2E;color:#E8D5B7;padding:18px 28px;display:flex;align-items:center;gap:20px;flex-wrap:wrap}}
header h1{{font-size:1.6rem;font-weight:300;letter-spacing:2px;flex:1}}
.kpi{{display:flex;gap:12px;flex-wrap:wrap}}
.kpi-box{{background:rgba(255,255,255,0.08);border-radius:8px;padding:6px 14px;text-align:center}}
.kpi-box .num{{font-size:1.4rem;font-weight:700;line-height:1}}
.kpi-box .lbl{{font-size:0.68rem;opacity:.7;text-transform:uppercase;letter-spacing:1px}}
.kpi-box.disp .num{{color:#4CAF50}}
.kpi-box.res  .num{{color:#EF5350}}
.kpi-box.vend .num{{color:#CE93D8}}

/* FILTROS */
.toolbar{{background:#fff;border-bottom:1px solid #ddd;padding:10px 20px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}}
.toolbar input{{flex:1;min-width:200px;max-width:380px;padding:7px 14px;border:1px solid #ccc;border-radius:20px;font-size:0.9rem;outline:none}}
.toolbar input:focus{{border-color:#1A1A2E}}
.filtros{{display:flex;gap:6px;flex-wrap:wrap}}
.fil-btn{{border:none;padding:5px 14px;border-radius:16px;cursor:pointer;font-size:0.82rem;font-weight:600;transition:all .2s}}
.fil-btn.all{{background:#1A1A2E;color:#fff}}
.fil-btn.disp{{background:#E8F5E9;color:#2E7D32;border:1px solid #A5D6A7}}
.fil-btn.res {{background:#FFEBEE;color:#C62828;border:1px solid #EF9A9A}}
.fil-btn.vend{{background:#F3E5F5;color:#6A1B9A;border:1px solid #CE93D8}}
.fil-btn.active{{opacity:1;box-shadow:0 0 0 2px currentColor}}

/* TABS */
.tabs{{background:#2C3E50;padding:0 16px;display:flex;flex-wrap:wrap;gap:2px;overflow-x:auto}}
.tab-btn{{background:none;border:none;color:#B0BEC5;padding:11px 14px;cursor:pointer;font-size:0.85rem;border-bottom:3px solid transparent;transition:all .2s;white-space:nowrap}}
.tab-btn:hover{{color:#ECEFF1;background:rgba(255,255,255,0.05)}}
.tab-btn.active{{color:#fff;border-bottom-color:var(--cat-color,#CFB53B)}}
.tab-count{{background:rgba(255,255,255,0.12);padding:1px 7px;border-radius:10px;font-size:0.72rem;margin-left:4px}}

/* GRID */
.tab-panel{{display:none;padding:18px}}
.tab-panel.active{{display:block}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px}}

/* CARD */
.card{{background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.07);transition:transform .2s,box-shadow .2s}}
.card:hover{{transform:translateY(-3px);box-shadow:0 8px 24px rgba(0,0,0,.13)}}
.card.reservado-card{{border-left:4px solid #EF5350}}
.card.vendido-card{{border-left:4px solid #AB47BC;opacity:.68;filter:grayscale(35%) brightness(.9);pointer-events:auto}}
.card.vendido-card:hover{{opacity:.78;transform:none;box-shadow:0 2px 8px rgba(0,0,0,.07)}}
.card-img{{position:relative;height:190px;background:#EEE;overflow:hidden}}
.card-img img{{width:100%;height:100%;object-fit:cover;cursor:zoom-in;transition:transform .3s}}
.card-img img:hover{{transform:scale(1.04)}}
.no-foto{{height:100%;display:flex;align-items:center;justify-content:center;color:#aaa;font-size:.85rem}}
.card-badges{{position:absolute;top:7px;left:7px;display:flex;gap:4px;flex-wrap:wrap}}
.badge-s{{background:#CFB53B;color:#fff;padding:2px 7px;border-radius:4px;font-size:.68rem;font-weight:700}}
.badge-f{{background:rgba(0,0,0,.45);color:#fff;padding:2px 7px;border-radius:4px;font-size:.68rem}}
.badge-set{{background:#1565C0;color:#fff;padding:2px 7px;border-radius:4px;font-size:.68rem;font-weight:700}}
.badge-sub{{background:#546E7A;color:#fff;padding:2px 7px;border-radius:4px;font-size:.68rem;font-weight:600}}
.card-code{{position:absolute;bottom:7px;right:7px;background:rgba(0,0,0,.55);color:#fff;padding:2px 8px;border-radius:4px;font-size:.72rem;font-family:monospace;font-weight:700}}
.estado-badge{{position:absolute;top:7px;right:7px;padding:2px 8px;border-radius:4px;font-size:.68rem;font-weight:700}}
.estado-badge.disponible{{background:#E8F5E9;color:#2E7D32}}
.estado-badge.reservado {{background:#FFEBEE;color:#C62828}}
.estado-badge.vendido   {{background:#F3E5F5;color:#6A1B9A}}
.card-body{{padding:11px 13px}}
.card-title{{font-size:.9rem;font-weight:600;color:#1A1A2E;margin-bottom:3px;line-height:1.3}}
.card-cat{{font-size:.72rem;color:#888;margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px}}
.precio{{color:#1F4E79;font-weight:700;font-size:.9rem;margin-bottom:5px}}
.para{{font-size:.78rem;margin-bottom:4px}}
.reservado-txt{{color:#C62828}}
.vendido-txt{{color:#6A1B9A}}
.notas{{font-size:.72rem;color:#999;font-style:italic;margin-top:4px}}
.precio{{font-size:.82rem;color:#1F4E79;margin-bottom:4px;display:flex;align-items:center;gap:5px;font-weight:600}}
.precio-lbl{{background:#1F4E79;color:#fff;padding:1px 6px;border-radius:3px;font-size:.66rem;font-weight:700;white-space:nowrap}}
.soth-est{{font-size:.82rem;color:#7B5A00;margin-bottom:5px;display:flex;align-items:center;gap:5px;font-weight:600}}
.soth-lbl{{background:#CFB53B;color:#fff;padding:1px 6px;border-radius:3px;font-size:.66rem;font-weight:700;white-space:nowrap}}

/* MODAL */
#modal{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.88);z-index:9999;align-items:center;justify-content:center}}
#modal.open{{display:flex}}
#modal img{{max-width:90vw;max-height:90vh;object-fit:contain;border-radius:6px;box-shadow:0 8px 40px rgba(0,0,0,.6)}}
#modal-close{{position:fixed;top:16px;right:22px;color:#fff;font-size:2.2rem;cursor:pointer;z-index:10000;line-height:1}}

/* CARRUSEL */
.carousel{{position:relative;height:100%;overflow:hidden}}
.slides{{height:100%;display:flex;transition:none}}
.slide{{min-width:100%;height:100%;flex-shrink:0;display:none}}
.slide.active{{display:block}}
.slide img{{width:100%;height:100%;object-fit:cover;cursor:zoom-in;transition:transform .3s}}
.slide img:hover{{transform:scale(1.04)}}
.carr-btn{{position:absolute;top:50%;transform:translateY(-50%);background:rgba(0,0,0,.45);color:#fff;border:none;width:28px;height:44px;font-size:1.3rem;cursor:pointer;z-index:10;transition:background .2s;line-height:1}}
.carr-btn:hover{{background:rgba(0,0,0,.7)}}
.carr-btn.prev{{left:0;border-radius:0 4px 4px 0}}
.carr-btn.next{{right:0;border-radius:4px 0 0 4px}}
.dots{{position:absolute;bottom:26px;left:50%;transform:translateX(-50%);display:flex;gap:5px;z-index:10}}
.dot{{width:7px;height:7px;border-radius:50%;background:rgba(255,255,255,.5);cursor:pointer;transition:background .2s}}
.dot.active{{background:#fff}}
.foto-counter{{position:absolute;bottom:8px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,.5);color:#fff;font-size:.68rem;padding:1px 8px;border-radius:10px;z-index:10}}

/* sin resultados */
.empty{{padding:40px;text-align:center;color:#aaa;font-size:.95rem}}
</style>
</head>
<body>

<header>
  <h1>Catalogo Solaris &mdash; Pignatelli</h1>
  <div class="kpi">
    <div class="kpi-box"><div class="num">{n_total}</div><div class="lbl">Total</div></div>
    <div class="kpi-box disp"><div class="num">{n_disp}</div><div class="lbl">Disponibles</div></div>
    <div class="kpi-box res"><div class="num">{n_res}</div><div class="lbl">Reservados</div></div>
    <div class="kpi-box vend"><div class="num">{n_vend}</div><div class="lbl">Vendidos</div></div>
  </div>
</header>

<div class="toolbar">
  <input type="text" id="busqueda" placeholder="Buscar por nombre, codigo, cliente..." oninput="filtrar()">
  <div class="filtros">
    <button class="fil-btn all active" onclick="setFiltro('all',this)">Todos</button>
    <button class="fil-btn disp" onclick="setFiltro('Disponible',this)">Disponibles</button>
    <button class="fil-btn res"  onclick="setFiltro('Reservado',this)">Reservados</button>
    <button class="fil-btn vend" onclick="setFiltro('Vendido',this)">Vendidos</button>
  </div>
</div>

<div class="tabs">
{tabs_html}</div>
{panels_html}

<div id="modal" onclick="cerrarModal()">
  <span id="modal-close">&times;</span>
  <img id="modal-img" src="" alt="">
</div>

<script>
let filtroEstado = 'all';

function mostrarTab(cat) {{
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('tab-' + cat).classList.add('active');
  document.getElementById('panel-' + cat).classList.add('active');
  filtrar();
}}

function setFiltro(estado, btn) {{
  filtroEstado = estado;
  document.querySelectorAll('.fil-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  filtrar();
}}

function filtrar() {{
  const q = document.getElementById('busqueda').value.toLowerCase().trim();
  document.querySelectorAll('.card').forEach(card => {{
    const txt    = card.dataset.txt || '';
    const estado = card.dataset.estado || '';
    const matchQ = !q || txt.includes(q);
    const matchE = filtroEstado === 'all' || estado === filtroEstado;
    card.style.display = (matchQ && matchE) ? '' : 'none';
  }});
}}

function moverSlide(cid, dir) {{
  event.stopPropagation();
  const car    = document.getElementById(cid);
  const slides = car.querySelectorAll('.slide');
  const dots   = car.querySelectorAll('.dot');
  const counter= car.querySelector('.foto-counter');
  let idx = [...slides].findIndex(s => s.classList.contains('active'));
  slides[idx].classList.remove('active');
  dots[idx].classList.remove('active');
  idx = (idx + dir + slides.length) % slides.length;
  slides[idx].classList.add('active');
  dots[idx].classList.add('active');
  if (counter) counter.textContent = (idx+1) + '/' + slides.length;
}}

function irSlide(cid, idx) {{
  event.stopPropagation();
  const car    = document.getElementById(cid);
  const slides = car.querySelectorAll('.slide');
  const dots   = car.querySelectorAll('.dot');
  const counter= car.querySelector('.foto-counter');
  slides.forEach(s => s.classList.remove('active'));
  dots.forEach(d => d.classList.remove('active'));
  slides[idx].classList.add('active');
  dots[idx].classList.add('active');
  if (counter) counter.textContent = (idx+1) + '/' + slides.length;
}}

function ampliar(src) {{
  document.getElementById('modal-img').src = src;
  document.getElementById('modal').classList.add('open');
  event.stopPropagation();
}}

function cerrarModal() {{
  document.getElementById('modal').classList.remove('open');
}}

document.addEventListener('keydown', e => {{ if(e.key==='Escape') cerrarModal(); }});
</script>
</body>
</html>
"""

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(html)

print(f"OK  {OUTPUT}")
print(f"    Total   : {n_total} articulos")
print(f"    Disp    : {n_disp} | Reservados: {n_res} | Vendidos: {n_vend}")
for cat in cats_sorted:
    print(f"    {cat}: {len(by_cat[cat])}")
