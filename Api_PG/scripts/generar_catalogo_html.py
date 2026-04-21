"""
generar_catalogo_html.py
Genera solaris_catalogo.html desde solaris_catalogo.json.
- Carrusel con flechas para ítems con múltiples fotos
- Filtros por categoría, estado y Sotheby's
- Modal zoom al hacer click en imagen
"""
import sys, io, json, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path

PROJECT  = Path("C:/Users/Alejandro/Documents/Proyecto Pignatelli")
CATALOGO = PROJECT / "Api_PG/data/solaris_catalogo.json"
OUT_HTML = PROJECT / "Api_PG/solaris_catalogo.html"
IMG_BASE = "images/fotos-Solaris-inventory/Todas las Fotos"

cat = json.loads(CATALOGO.read_text(encoding="utf-8"))

# Solo ARTÍCULOs (hojas), no SETs
articulos = [it for it in cat if it.get("tipoEstructural") != "SET"]

from collections import defaultdict
by_cat = defaultdict(list)
for it in articulos:
    by_cat[it.get("categoria", "Sin clasificar")].append(it)

cat_order = ["Muebles","Arte en papel","Decorativos","Plateria",
             "Ceramica","Cristaleria","Utensilios","Joyas",
             "Electrodomesticos","Insumos Medicos","Sin clasificar"]
cats_present = [c for c in cat_order if c in by_cat]
for c in by_cat:
    if c not in cats_present:
        cats_present.append(c)

def get_fotos(it):
    f = it.get("fotos", [])
    if isinstance(f, str): f = [f] if f else []
    return f

def precio_fmt(it):
    p = it.get("precioUSD")
    if not p: return ""
    try: return f"${float(p):,.0f}"
    except: return str(p)

def estado_badge(it):
    e = it.get("estado", "")
    r = it.get("reservadoPara", "")
    if e == "Vendido":
        return '<span class="badge-estado vendido">Vendido</span>'
    if e == "Reservado":
        return f'<span class="badge-estado reservado">Reservado · {r}</span>'
    return ""

def card_html(it, idx):
    code   = it.get("codigoItem", "")
    fotos  = get_fotos(it)
    nom    = it.get("nombreES", "") or code
    desc   = it.get("descripcionES", "") or ""
    precio = precio_fmt(it)
    soth   = it.get("tieneSothebys", False)
    ref_s  = it.get("refSothebys", "")
    pag_s  = it.get("paginaSothebys", "")
    est_s  = it.get("estimacionSothebys", "")
    estado = it.get("estado", "Disponible")
    n      = len(fotos)

    # CSS classes
    cls = "card"
    if soth:          cls += " sothebys-card"
    if estado == "Reservado": cls += " reservado-card"
    if estado == "Vendido":   cls += " vendido-card"

    # ── Carrusel de imágenes ──────────────────────────────────────
    if n == 0:
        carousel = '<div class="no-foto">Sin foto</div>'
    elif n == 1:
        src = f"{IMG_BASE}/{fotos[0]}"
        carousel = f'''<img src="{src}" alt="{nom}" loading="lazy" onclick="openModal('{src}')">'''
    else:
        # múltiples fotos → carrusel
        slides = ""
        for i, foto in enumerate(fotos):
            src = f"{IMG_BASE}/{foto}"
            display = "block" if i == 0 else "none"
            slides += f'<img src="{src}" alt="{nom} {i+1}" loading="lazy" style="display:{display}" onclick="openModal(\'{src}\')" data-slide="{i}">'

        carousel = f'''
<div class="carousel" id="c{idx}">
  {slides}
  <button class="carr-btn carr-prev" onclick="slide({idx},-1)">&#8249;</button>
  <button class="carr-btn carr-next" onclick="slide({idx},1)">&#8250;</button>
  <div class="carr-counter" id="cc{idx}">1 / {n}</div>
</div>'''

    # ── Badges superiores ─────────────────────────────────────────
    badges = ""
    if soth: badges += '<span class="badge-s">SOTHEBY\'S</span>'
    if n > 1: badges += f'<span class="badge-f">{n} fotos</span>'

    soth_ref = ""
    if soth and ref_s:
        lot_txt = f"Lote {ref_s}" if ref_s else ""
        page_txt = f" - Pag. {pag_s}" if pag_s else ""
        est_txt = f" - {est_s}" if est_s else ""
        soth_ref = f'<div class="ref-s"><span class="ref-label">Valoracion Sotheby\'s:</span> {lot_txt}{page_txt}{est_txt}</div>'

    precio_html = ""
    if precio:
        precio_label = "Precio comercial" if soth else "Precio"
        precio_html = f'<div class="precio"><span class="precio-label">{precio_label}:</span> {precio}</div>'
    estado_html  = estado_badge(it)
    desc_html    = f'<div class="card-desc">{desc}</div>' if desc else ""

    return f'''<div class="{cls}" data-code="{code}" data-name="{nom.lower()}" data-soth="{'1' if soth else '0'}" data-estado="{estado}">
  <div class="card-img">
    {carousel}
    <div class="card-badges">{badges}</div>
    <div class="card-code">{code}</div>
  </div>
  <div class="card-body">
    <div class="card-title">{nom}</div>
    {precio_html}
    {estado_html}
    {desc_html}
    {soth_ref}
  </div>
</div>'''

# ── Build HTML ────────────────────────────────────────────────────
tabs_html   = ""
panels_html = ""
total_all   = len(articulos)

tabs_html += f'<button class="tab-btn active" onclick="showTab(\'all\',this)">Todo <span class="tab-count">{total_all}</span></button>'
for c in cats_present:
    cid = re.sub(r'\s+', '_', c)
    tabs_html += f'<button class="tab-btn" onclick="showTab(\'{cid}\',this)">{c} <span class="tab-count">{len(by_cat[c])}</span></button>'

# Global index for carousels
idx = 0
all_cards = ""
for it in articulos:
    all_cards += card_html(it, idx)
    idx += 1

panels_html += f'<div class="tab-panel active" id="panel-all"><div class="grid">{all_cards}</div></div>'

for c in cats_present:
    cid = re.sub(r'\s+', '_', c)
    cards = ""
    for it in by_cat[c]:
        cards += card_html(it, idx)
        idx += 1
    panels_html += f'<div class="tab-panel" id="panel-{cid}"><div class="grid">{cards}</div></div>'

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Catálogo Solaris — Pignatelli</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',sans-serif;background:#f5f0eb;color:#333}}
header{{background:#2c1810;color:#e8d5b7;padding:20px 30px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}}
header h1{{font-size:1.8rem;font-weight:300;letter-spacing:2px}}
.badge-total{{background:#8b6914;color:#fff;padding:4px 12px;border-radius:20px;font-size:.85rem}}
.search-bar{{padding:12px 20px;background:#fff;border-bottom:1px solid #ddd;display:flex;gap:12px;align-items:center;flex-wrap:wrap}}
.search-bar input{{flex:1;max-width:400px;padding:8px 14px;border:1px solid #ccc;border-radius:20px;font-size:.9rem;outline:none}}
.search-bar input:focus{{border-color:#c9a227}}
.filtros{{display:flex;gap:10px;flex-wrap:wrap;align-items:center}}
.filtros label{{font-size:.82rem;cursor:pointer;display:flex;align-items:center;gap:4px}}
.tabs{{background:#3d2314;padding:0 20px;display:flex;flex-wrap:wrap;gap:2px}}
.tab-btn{{background:none;border:none;color:#c4a882;padding:12px 14px;cursor:pointer;font-size:.85rem;border-bottom:3px solid transparent;transition:all .2s;white-space:nowrap}}
.tab-btn:hover{{color:#f0d9a0;background:rgba(255,255,255,.05)}}
.tab-btn.active{{color:#f0d9a0;border-bottom-color:#c9a227}}
.tab-count{{background:rgba(255,255,255,.15);padding:1px 6px;border-radius:10px;font-size:.72rem;margin-left:4px}}
.tab-panel{{display:none;padding:20px}}
.tab-panel.active{{display:block}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:16px}}
.card{{background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);transition:transform .2s,box-shadow .2s}}
.card:hover{{transform:translateY(-3px);box-shadow:0 6px 20px rgba(0,0,0,.15)}}
.sothebys-card{{border:2px solid #c9a227}}
.reservado-card{{border:2px solid #2c6e49}}
.vendido-card{{opacity:.6}}
.card-img{{position:relative;height:200px;background:#e8e0d5;overflow:hidden}}
.card-img>img,.carousel img{{width:100%;height:100%;object-fit:cover;cursor:zoom-in}}
.no-foto{{height:100%;display:flex;align-items:center;justify-content:center;color:#aaa;font-size:.85rem}}
.carousel{{position:relative;width:100%;height:100%}}
.carousel img{{position:absolute;top:0;left:0;width:100%;height:100%;object-fit:cover;cursor:zoom-in}}
.carr-btn{{position:absolute;top:50%;transform:translateY(-50%);background:rgba(0,0,0,.55);color:#fff;border:none;font-size:1.6rem;line-height:1;padding:4px 10px;cursor:pointer;z-index:10;border-radius:4px;transition:background .15s}}
.carr-btn:hover{{background:rgba(0,0,0,.8)}}
.carr-prev{{left:4px}}
.carr-next{{right:4px}}
.carr-counter{{position:absolute;bottom:6px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,.55);color:#fff;font-size:.7rem;padding:2px 8px;border-radius:10px;z-index:10}}
.card-badges{{position:absolute;top:8px;left:8px;display:flex;gap:4px;flex-wrap:wrap;z-index:5}}
.badge-s{{background:#c9a227;color:#fff;padding:2px 7px;border-radius:4px;font-size:.68rem;font-weight:700}}
.badge-f{{background:rgba(0,0,0,.5);color:#fff;padding:2px 7px;border-radius:4px;font-size:.68rem}}
.card-code{{position:absolute;bottom:8px;right:8px;background:rgba(0,0,0,.6);color:#fff;padding:2px 7px;border-radius:4px;font-size:.72rem;font-family:monospace;z-index:5}}
.card-body{{padding:12px}}
.card-title{{font-size:.92rem;font-weight:600;color:#2c1810;margin-bottom:6px;line-height:1.3}}
.precio{{color:#8b6914;font-weight:700;font-size:.9rem;margin-bottom:4px}}
.precio-label{{color:#6d5733;font-weight:600}}
.badge-estado{{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.72rem;margin:4px 0}}
.badge-estado.reservado{{background:#2c6e49;color:#fff}}
.badge-estado.vendido{{background:#888;color:#fff}}
.card-desc{{font-size:.78rem;color:#666;line-height:1.5;margin:4px 0}}
.ref-s{{font-size:.72rem;color:#8b6914;margin-top:6px;line-height:1.4}}
.ref-label{{font-weight:700}}
.hidden{{display:none!important}}
#modal{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.9);z-index:9999;align-items:center;justify-content:center}}
#modal.open{{display:flex}}
#modal img{{max-width:92vw;max-height:92vh;object-fit:contain;border-radius:4px}}
#modal-close{{position:fixed;top:18px;right:22px;color:#fff;font-size:2.2rem;cursor:pointer;z-index:10000;line-height:1}}
</style>
</head>
<body>
<header>
  <h1>Catálogo Solaris &mdash; Pignatelli</h1>
  <span class="badge-total">{total_all} artículos</span>
</header>
<div class="search-bar">
  <input type="text" id="search" placeholder="Buscar por nombre o código..." oninput="filterCards()">
  <div class="filtros">
    <label><input type="checkbox" id="f-disp" checked onchange="filterCards()"> Disponibles</label>
    <label><input type="checkbox" id="f-res"  checked onchange="filterCards()"> Reservados</label>
    <label><input type="checkbox" id="f-vend" checked onchange="filterCards()"> Vendidos</label>
    <label><input type="checkbox" id="f-soth" onchange="filterCards()"> Solo Sotheby's</label>
  </div>
</div>
<div class="tabs">{tabs_html}</div>
{panels_html}
<div id="modal" onclick="closeModal()">
  <span id="modal-close">&times;</span>
  <img id="modal-img" src="" alt="">
</div>
<script>
// ── Carrusel ──────────────────────────────────────────────────────
const carState = {{}};
function slide(idx, dir) {{
  const c = document.getElementById('c' + idx);
  if (!c) return;
  const imgs = c.querySelectorAll('img');
  const n = imgs.length;
  if (!carState[idx]) carState[idx] = 0;
  imgs[carState[idx]].style.display = 'none';
  carState[idx] = (carState[idx] + dir + n) % n;
  imgs[carState[idx]].style.display = 'block';
  const counter = document.getElementById('cc' + idx);
  if (counter) counter.textContent = (carState[idx] + 1) + ' / ' + n;
}}
// ── Modal ─────────────────────────────────────────────────────────
function openModal(src) {{
  document.getElementById('modal-img').src = src;
  document.getElementById('modal').classList.add('open');
}}
function closeModal() {{
  document.getElementById('modal').classList.remove('open');
  document.getElementById('modal-img').src = '';
}}
document.addEventListener('keydown', e => {{ if (e.key === 'Escape') closeModal(); }});
// ── Tabs ──────────────────────────────────────────────────────────
function showTab(id, btn) {{
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('panel-' + id).classList.add('active');
  btn.classList.add('active');
  filterCards();
}}
// ── Filtros ───────────────────────────────────────────────────────
function filterCards() {{
  const q        = document.getElementById('search').value.toLowerCase();
  const showDisp = document.getElementById('f-disp').checked;
  const showRes  = document.getElementById('f-res').checked;
  const showVend = document.getElementById('f-vend').checked;
  const onlySoth = document.getElementById('f-soth').checked;
  document.querySelectorAll('.card').forEach(card => {{
    const name   = card.dataset.name || '';
    const code   = card.dataset.code.toLowerCase();
    const estado = card.dataset.estado;
    const isSoth = card.dataset.soth === '1';
    const matchQ = !q || name.includes(q) || code.includes(q);
    const matchE = (showDisp && estado === 'Disponible') ||
                   (showRes  && estado === 'Reservado')  ||
                   (showVend && estado === 'Vendido');
    const matchS = !onlySoth || isSoth;
    card.classList.toggle('hidden', !(matchQ && matchE && matchS));
  }});
}}
</script>
</body>
</html>"""

OUT_HTML.write_text(html, encoding="utf-8")
print(f"Generado: {OUT_HTML.name}")
print(f"Artículos: {len(articulos)} | Categorías: {len(cats_present)}")
