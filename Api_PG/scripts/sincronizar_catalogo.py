"""
sincronizar_catalogo.py
Sincroniza el catálogo público con el estado actual del Google Sheet.
Uso: python sincronizar_catalogo.py
"""
import csv, json, os, re, subprocess, sys, tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(__file__).parent.parent
ROOT = BASE.parent

# ── Cargar credenciales ──────────────────────────────────────
env = {}
env_path = ROOT / "pignatelli-app" / ".env.local"
with open(env_path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"')

SHEET_ID    = env["GOOGLE_SHEETS_ID"]
SA_EMAIL    = env["GOOGLE_SERVICE_ACCOUNT_EMAIL"]
PRIVATE_KEY = env["GOOGLE_PRIVATE_KEY"].encode().decode('unicode_escape')

from google.oauth2 import service_account
from googleapiclient.discovery import build

creds = service_account.Credentials.from_service_account_info({
    "type": "service_account", "project_id": "inventario-pignatelli",
    "private_key_id": "key", "private_key": PRIVATE_KEY,
    "client_email": SA_EMAIL, "token_uri": "https://oauth2.googleapis.com/token"
}, scopes=["https://www.googleapis.com/auth/spreadsheets"])

service = build("sheets", "v4", credentials=creds)

# ── Leer INVENTARIO_MAESTRO ──────────────────────────────────
print("📥 Leyendo Google Sheet...")
result = service.spreadsheets().values().get(
    spreadsheetId=SHEET_ID, range="INVENTARIO_MAESTRO!A1:K600"
).execute()
rows = result.get("values", [])
headers = rows[0]
data = rows[1:]

# Mapear columnas por nombre (funciona con 7 o 11 columnas)
h = {name: i for i, name in enumerate(headers)}
idx_cod      = h.get("Artículo", 0)
idx_nombre   = h.get("Nombre", 1)
idx_precio   = h.get("Precio USD", 3)
idx_minimo   = h.get("Mínimo", 5)
idx_estado   = h.get("Estado", 6)
idx_comprador= h.get("Reservado / Comprador", 7)
idx_ref_soth = h.get("Ref Sotheby's", 8)
idx_pag_soth = h.get("Página", 9)
idx_est_soth = h.get("Estimación Sotheby's", 4)

max_idx = max(idx_cod, idx_nombre, idx_precio, idx_minimo, idx_estado, idx_comprador, idx_ref_soth, idx_pag_soth, idx_est_soth)

sheet_estados = {}
for row in data:
    row = row + [""] * (max_idx + 1 - len(row))
    cod       = row[idx_cod].strip()
    nombre    = row[idx_nombre].strip()
    precio    = row[idx_precio].strip()
    minimo    = row[idx_minimo].strip()
    estado    = row[idx_estado].strip() or "Disponible"
    comprador = row[idx_comprador].strip()
    ref_soth  = row[idx_ref_soth].strip()
    pag_soth  = row[idx_pag_soth].strip()
    est_soth  = row[idx_est_soth].strip()
    if cod:
        sheet_estados[cod] = {
            "estado": estado,
            "reservadoPara": comprador,
            "nombre": nombre,
            "precio": precio,
            "precioMinimo": minimo,
            "refSothebys": ref_soth,
            "paginaSothebys": pag_soth,
            "estimacionSothebys": est_soth,
        }

# ── Cargar catálogo JSON ─────────────────────────────────────
CATALOGO = BASE / "data" / "solaris_catalogo.json"
with open(CATALOGO, encoding="utf-8") as f:
    catalogo = json.load(f)

def parse_precio(s):
    s = s.strip().replace("$","")
    if not s or s in ("—",""): return None
    token = s.split()[0].replace(".","")
    if "," in token:
        l, r = token.split(",", 1)
        if len(r) == 2: return float(l + "." + r)
        elif len(r) == 3: return float(l + r)
    try: return float(token)
    except: return None

# ── Aplicar cambios ──────────────────────────────────────────
cambios = 0
for item in catalogo:
    cod = item["codigoItem"]
    if cod not in sheet_estados:
        # No está en sheet → resetear a Disponible
        if item.get("estado","Disponible") != "Disponible":
            item["estado"] = "Disponible"
            item["reservadoPara"] = ""
            cambios += 1
        continue

    s = sheet_estados[cod]

    # Estado y comprador
    if item.get("estado","Disponible") != s["estado"] or item.get("reservadoPara","") != s["reservadoPara"]:
        item["estado"] = s["estado"]
        item["reservadoPara"] = s["reservadoPara"]
        cambios += 1

    # Nombre (si cambió en sheet)
    if s["nombre"] and s["nombre"] != item.get("nombreES",""):
        item["nombreES"] = s["nombre"]
        cambios += 1

    # Precio vendible: solo "Precio USD" (columna D). "Minimo" (F) es confirmacion.
    precio_sheet = parse_precio(s["precio"])
    if precio_sheet is not None and precio_sheet != item.get("precioUSD"):
        item["precioUSD"] = precio_sheet
        cambios += 1

    # Precio Mínimo (columna F del Sheet)
    minimo_sheet = parse_precio(s.get("precioMinimo", ""))
    if minimo_sheet is not None and minimo_sheet != item.get("precioMinimoUSD"):
        item["precioMinimoUSD"] = minimo_sheet
        cambios += 1

    # Sotheby's fields (solo actualiza si Sheet tiene valores)
    if s.get("refSothebys") and s["refSothebys"] != item.get("refSothebys",""):
        item["refSothebys"] = s["refSothebys"]
        cambios += 1
    if s.get("paginaSothebys") and s["paginaSothebys"] != item.get("paginaSothebys",""):
        item["paginaSothebys"] = s["paginaSothebys"]
        cambios += 1
    if s.get("estimacionSothebys") and s["estimacionSothebys"] != item.get("estimacionSothebys",""):
        item["estimacionSothebys"] = s["estimacionSothebys"]
        cambios += 1

print(f"✅ {cambios} cambios detectados")

# Guardar JSON
with open(CATALOGO, "w", encoding="utf-8") as f:
    json.dump(catalogo, f, ensure_ascii=False, indent=2)

n_res  = sum(1 for i in catalogo if i.get("estado") == "Reservado")
n_vend = sum(1 for i in catalogo if i.get("estado") == "Vendido")
n_disp = sum(1 for i in catalogo if i.get("estado","Disponible") == "Disponible")
print(f"   Disponible:{n_disp} | Reservado:{n_res} | Vendido:{n_vend}")

# ── Regenerar HTML estático (solo Api_PG_Deploy/index.html) ──
# NOTA: solaris_catalogo.html es dinámico (carga de /api/catalogo), NO se regenera
print("🔨 Generando HTML estático (backup)...")
subprocess.run([sys.executable, str(BASE / "generar_html.py")], check=True, capture_output=True)

# generar_html.py ya escribe directo a Api_PG_Deploy/index.html

# ── Git commit y push ─────────────────────────────────────────
print("📤 Subiendo a GitHub...")
os.chdir(str(ROOT))
subprocess.run(["git", "add",
    "Api_PG/data/solaris_catalogo.json",
    "Api_PG/solaris_catalogo.html",
    "Api_PG_Deploy/index.html"], check=True)

result = subprocess.run(["git", "diff", "--cached", "--quiet"])
if result.returncode == 0:
    print("ℹ️  Sin cambios para commitear")
else:
    subprocess.run(["git", "commit", "-m", f"Sync catalogo: {n_disp} disp / {n_res} res / {n_vend} vend"], check=True)
    subprocess.run(["git", "push"], check=True)

    # ── Deploy en servidor ────────────────────────────────────
    print("🚀 Desplegando en servidor...")
    subprocess.run([
        "ssh", "root@24.199.89.36",
        "cd /app && git checkout Api_PG/data/solaris_catalogo.json && git pull && systemctl restart pignatelli"
    ], check=True)

print("\n✅ SINCRONIZACIÓN COMPLETA")
print(f"   🌐 https://catalogo.pignatelli.uk/publico")
