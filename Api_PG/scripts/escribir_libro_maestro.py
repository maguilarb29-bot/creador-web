"""
escribir_libro_maestro.py

Reescribe el Google Sheets completo desde cero:
- INVENTARIO_MAESTRO  — columnas en español natural, orientado a los dueños
- DICCIONARIO         — referencia clara y limpia
- INSTRUCCIONES       — guía breve para gestores y herederos
- Conserva: RESERVAS, VENTAS, CATALOGO_WEB, RESUMEN
"""
from __future__ import annotations
import json, re
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCRIPT_PATH  = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[2]
ENV_PATH     = PROJECT_ROOT / "pignatelli-app" / ".env.local"
JSON_PATH    = PROJECT_ROOT / "Api_PG" / "data" / "solaris_catalogo.json"
SCOPES       = ["https://www.googleapis.com/auth/spreadsheets"]

# ── Categorías en español natural ──────────────────────────────────────────
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

CAT_ORDER = {"C":0,"D":1,"E":2,"F":3,"G":4,"J":5,"M":6,"P":7,"S":8,"U":9}

# ── Headers INVENTARIO_MAESTRO — en español natural ────────────────────────
HEADERS_IM = [
    "Código",           # A
    "Nombre",           # B
    "Descripción",      # C
    "Categoría",        # D
    "Ubicación",        # E
    "Precio USD",       # F
    "Condición",        # G  estado físico
    "Disponibilidad",   # H  Disponible / Reservado / Vendido
    "Reservado para",   # I
    "Visible en web",   # J  Sí / No
    "Sotheby's",        # K  Sí / No
    "Piezas",           # L  cantidad
    "Foto principal",   # M
    "Fotos adicionales",# N  separadas por |
    "Notas",            # O
]

# ── Helpers ─────────────────────────────────────────────────────────────────

def load_env(path: Path) -> dict:
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

def c(v) -> str:
    if v is None: return ""
    s = str(v).strip()
    return "" if s.lower() in {"none","null","0.0","0"} else s

def is_ref(item: dict) -> bool:
    fotos = [str(f).strip() for f in item.get("fotos",[]) if str(f).strip()]
    if "Ref del set" in str(item.get("notas","")): return True
    return len(fotos) == 1 and "-Ref-" in fotos[0]

def sort_key(item: dict):
    cat = str(item.get("catCodigo","")).strip()
    try: num = int(item.get("numItem",0) or 0)
    except: num = 10**9
    return (CAT_ORDER.get(cat,999), num, str(item.get("codigoItem","")))

def build_row(item: dict) -> list:
    fotos = [str(f).strip() for f in item.get("fotos",[]) if str(f).strip() and "-Ref-" not in str(f)]
    foto1 = fotos[0] if fotos else ""
    fotos_extra = " | ".join(fotos[1:]) if len(fotos) > 1 else ""

    precio = item.get("precioUSD")
    if precio in (None, 0, 0.0, "0", "0.0", ""): precio = ""

    nombre = c(item.get("nombreES")) or c(item.get("descripcionOriginal"))
    desc   = c(item.get("descripcionES"))
    cat_label = CAT_LABEL.get(str(item.get("catCodigo","")), c(item.get("categoria","")))
    condicion = c(item.get("estado")) or "Por evaluar"
    sothebys  = "Sí" if item.get("tieneSothebys") else "No"
    piezas    = item.get("cantidad") or 1
    notas     = c(item.get("notas"))
    if not c(item.get("nombreES")) and c(item.get("descripcionOriginal")):
        notas = ("PENDIENTE NOMBRE | " + notas).strip(" |")

    return [
        c(item.get("codigoItem")),  # A Código
        nombre,                      # B Nombre
        desc,                        # C Descripción
        cat_label,                   # D Categoría
        c(item.get("ubicacion")),    # E Ubicación
        precio,                      # F Precio USD
        condicion,                   # G Condición
        "Disponible",                # H Disponibilidad
        "",                          # I Reservado para
        "No",                        # J Visible en web
        sothebys,                    # K Sotheby's
        piezas,                      # L Piezas
        foto1,                       # M Foto principal
        fotos_extra,                 # N Fotos adicionales
        notas,                       # O Notas
    ]

# ── Contenido DICCIONARIO ────────────────────────────────────────────────────

DICCIONARIO = [
    ["Campo", "Descripción", "Valores posibles"],
    ["Código", "Identificador único del artículo según las fotos.", "Ej: F1, G48a, C136ca"],
    ["Nombre", "Nombre comercial del artículo en español.", ""],
    ["Descripción", "Descripción elegante del artículo para el catálogo.", ""],
    ["Categoría", "Tipo de artículo.", "Muebles / Cristalería / Porcelana y Cerámica / Decorativos y Arte / Platería / Joyería / Cuadros y Grabados / Utensilios / Electrodomésticos / Miscelánea"],
    ["Ubicación", "Dónde está físicamente el artículo.", "Ej: Living room, Master bedroom, Storage"],
    ["Precio USD", "Precio de venta en dólares. Vacío si no está definido.", "Número"],
    ["Condición", "Estado físico del artículo.", "Excelente / Muy bueno / Bueno / Regular / Con detalles / Por evaluar"],
    ["Disponibilidad", "Estado comercial actual.", "Disponible / Reservado / Vendido"],
    ["Reservado para", "Nombre del interesado cuando está reservado.", ""],
    ["Visible en web", "Si debe aparecer en el catálogo público.", "Sí / No"],
    ["Sotheby's", "Si el artículo aparece en la tasación de Sotheby's 2016.", "Sí / No"],
    ["Piezas", "Cantidad de piezas que componen el artículo.", "Número"],
    ["Foto principal", "Nombre del archivo de la foto principal.", ""],
    ["Fotos adicionales", "Nombres de fotos adicionales, separados por |.", ""],
    ["Notas", "Observaciones internas del gestor.", ""],
]

# ── Contenido INSTRUCCIONES ──────────────────────────────────────────────────

INSTRUCCIONES = [
    ["GUÍA DE USO — Inventario Pignatelli / Solaris"],
    [""],
    ["HOJAS DEL LIBRO"],
    ["INVENTARIO_MAESTRO", "Base completa de todos los artículos. Aquí se gestiona todo."],
    ["CATALOGO_WEB", "Artículos preparados para mostrar en la web. Se alimenta del maestro."],
    ["RESERVAS", "Seguimiento de reservas activas con datos del interesado."],
    ["VENTAS", "Registro histórico de artículos vendidos."],
    ["RESUMEN", "Vista ejecutiva con totales, por categoría y estado comercial."],
    ["DICCIONARIO", "Referencia de campos y valores válidos."],
    [""],
    ["FLUJO DE TRABAJO"],
    ["1.", "Capturar o corregir información en INVENTARIO_MAESTRO."],
    ["2.", "Cuando un artículo esté listo para mostrarse: cambiar 'Visible en web' a Sí."],
    ["3.", "Si hay un interesado: cambiar 'Disponibilidad' a Reservado y anotar el nombre en 'Reservado para'."],
    ["4.", "Cuando se concrete una venta: cambiar a Vendido y registrar en la hoja VENTAS."],
    ["5.", "Revisar RESUMEN periódicamente para ver el estado general de la colección."],
    [""],
    ["REGLAS IMPORTANTES"],
    ["—", "El código de cada artículo viene de la foto y no se modifica."],
    ["—", "Un artículo con código F1a y F1b son piezas distintas, aunque vengan del mismo lote original."],
    ["—", "Las fotos de referencia (marcadas con -Ref-) son solo trazabilidad interna, no se venden."],
    ["—", "Si el precio está vacío, significa que aún no ha sido definido por los propietarios."],
    ["—", "Sotheby's = Sí significa que ese artículo aparece en la tasación de Londres 2016."],
]

# ── Main ────────────────────────────────────────────────────────────────────

def main():
    print("Cargando catálogo JSON...")
    with JSON_PATH.open(encoding="utf-8") as f:
        raw = json.load(f)
    items = list(raw.values()) if isinstance(raw, dict) else raw
    items = [i for i in items if isinstance(i, dict) and not is_ref(i)]
    items.sort(key=sort_key)
    rows_im = [build_row(i) for i in items]
    print(f"  Artículos: {len(rows_im)}")

    print("Conectando a Google Sheets...")
    svc, sheet_id = get_service()

    meta = svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
    hojas = {s['properties']['title']: s['properties']['sheetId'] for s in meta['sheets']}
    print(f"  Hojas existentes: {list(hojas.keys())}")

    def limpiar_y_escribir(nombre_hoja, datos, rango_col):
        if nombre_hoja not in hojas:
            print(f"  Hoja '{nombre_hoja}' no existe — omitida")
            return
        n_filas = len(datos)
        svc.spreadsheets().values().clear(
            spreadsheetId=sheet_id,
            range=f"{nombre_hoja}!A1:Z1000",
            body={}
        ).execute()
        svc.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"{nombre_hoja}!A1:{rango_col}{n_filas}",
            valueInputOption="USER_ENTERED",
            body={"values": datos}
        ).execute()
        print(f"  {nombre_hoja}: {n_filas} filas escritas")

    # INVENTARIO_MAESTRO
    print("Escribiendo INVENTARIO_MAESTRO...")
    datos_im = [HEADERS_IM] + rows_im
    limpiar_y_escribir("INVENTARIO_MAESTRO", datos_im, "O")

    # DICCIONARIO
    print("Escribiendo DICCIONARIO...")
    limpiar_y_escribir("DICCIONARIO", DICCIONARIO, "C")

    # INSTRUCCIONES
    print("Escribiendo INSTRUCCIONES...")
    limpiar_y_escribir("INSTRUCCIONES", INSTRUCCIONES, "B")

    # Estadísticas
    con_sothebys  = sum(1 for r in rows_im if r[10] == "Sí")
    sin_precio    = sum(1 for r in rows_im if r[5] == "")
    sin_desc      = sum(1 for r in rows_im if not str(r[2]).strip())
    sin_foto      = sum(1 for r in rows_im if not str(r[12]).strip())
    pendiente_nom = sum(1 for r in rows_im if "PENDIENTE NOMBRE" in str(r[14]))

    print()
    print("=" * 50)
    print(f"Artículos escritos:      {len(rows_im)}")
    print(f"Con referencia Sotheby's:{con_sothebys}")
    print(f"Sin precio definido:     {sin_precio}")
    print(f"Sin descripción:         {sin_desc}")
    print(f"Sin foto:                {sin_foto}")
    print(f"Pendiente nombre:        {pendiente_nom}")
    print("=" * 50)
    print()
    print("Columnas INVENTARIO_MAESTRO:")
    for i, h in enumerate(HEADERS_IM):
        print(f"  {chr(65+i)}: {h}")

if __name__ == "__main__":
    main()
