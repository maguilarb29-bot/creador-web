"""
actualizar_estados_inventario.py

1. Elimina duplicado D11 en RESERVAS (fila 17)
2. Actualiza códigos en RESERVAS (numeros → códigos catálogo)
3. Actualiza INVENTARIO_MAESTRO: Estado = Reservado / Vendido para artículos correspondientes
4. Actualiza VENTAS: idLote numérico → código catálogo
"""
from __future__ import annotations
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH     = PROJECT_ROOT / "pignatelli-app" / ".env.local"
SCOPES       = ["https://www.googleapis.com/auth/spreadsheets"]

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
    return build("sheets", "v4", credentials=creds, cache_discovery=False), sheet_id

# Mapa: numItem original → código catálogo
NUM_TO_COD = {
    8: "D8", 21: "P21", 22: "P22", 23: "F23", 28: "P28", 30: "D30",
    56: "F56", 77: "F77", 124: "F124", 130: "F130", 134: "F134",
    174: "S174", 181: "P181", 182: "P182", 11: "D11",
    # Ventas
    63: "F63", 70: "F70", 80: "P80", 135: "E135",
}

RESERVADOS_CODS = {"D8","P21","P22","F23","P28","D30","F56","F77","F124","F130","F134","S174","P181","P182","D11"}
VENDIDOS_CODS   = {"F63","F70","P80","E135"}

# Datos de RESERVAS completos
RESERVAS_DATA = [
    ["D8",   "Caballo Tang",                                                              "Reservado","Reservado","Adriano",      "",   "","D8-caballo-tang.jpg"],
    ["P21",  "Acuarela de dos leones y el sol",                                           "Reservado","Reservado","Adriano",      "",   "","P21-acuarela-de-dos-leones.jpg"],
    ["P22",  "3 grabados: Inocencio XII, Dogana Nuova y trabajadores",                   "Reservado","Reservado","Adriano",      "",   "","P22-grabado-antiguo-escena-de-trabajadores.jpg"],
    ["F23",  "Cómoda estilo Luis XV – valor estimado $2,000",                            "Reservado","Reservado","Margherita",   "",   "","F23-comoda-luis-xv.jpg"],
    ["P28",  "Pintura Belle Époque de los jardines de las Tullerías",                    "Reservado","Reservado","Adriano",      "",   "","P28-pintura-belle-epoque.jpg"],
    ["D30",  "Reloj cartel Luis XV bronce dorado, attr. Saint-Germain, circa 1748",      "Reservado","Reservado","Fabrizia",     "",   "","D30-reloj-cartel-luis-xv.jpg"],
    ["F56",  "2 cómodas bombé estilo Luis XV en nogal",                                  "Reservado","Reservado","Maria Cristina",0,  "","F56-comoda-bombe.jpg"],
    ["F77",  "Consola tallada de haya estilo Luis XV",                                   "Reservado","Reservado","Margherita",   0,   "","F77-consola-luis-xv.jpg"],
    ["F124", "Mesa de centro con tapa china pintada en negro, patas de latón",           "Reservado","Reservado","Maria Cristina","", "","F124-mesa-centro-china.jpg"],
    ["F130", "Juego de muebles de exterior con cojines: 1 sofá, 2 sillones y mesa",     "Reservado","Reservado","",             "",  "","F130-muebles-exterior.jpg"],
    ["F134", "Juego de comedor de exterior: 1 mesa y 6 sillas",                          "Reservado","Reservado","",             "",  "","F134-comedor-exterior.jpg"],
    ["S174", "2 soperas francesas de plata para salsa, Vevrat Paris, s. XIX",            "Reservado","Reservado","Fabrizia",     "",  "","S174-soperas-plata.jpg"],
    ["P181", "Pintura de una pareja en el campo",                                        "Reservado","Reservado","Adriano",      "",  "","P181-pintura-pareja.jpg"],
    ["P182", "2 figuras sobre terrazas chinas, siglo XVIII",                             "Reservado","Reservado","Adriano",      "",  "","P182-figuras-terrazas.jpg"],
    ["D11",  "Pareja de Jarrones Esféricos Rosas Cerámicos con Pedestal de Madera",     "Reservado","Reservado","Margherita",   150, "","D11-pareja-de-jarrones-esfericos-rosas.jpg"],
]

def main():
    svc, sheet_id = get_service()
    meta = svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheet_id_map = {s["properties"]["title"]: s["properties"]["sheetId"]
                    for s in meta["sheets"]}

    updates = []
    format_reqs = []

    # ============================================================
    # 1. RESERVAS — reescribir completo con códigos correctos
    # ============================================================
    print("Reescribiendo RESERVAS con códigos catálogo...")
    # Limpiar rango completo primero
    svc.spreadsheets().values().clear(
        spreadsheetId=sheet_id, range="RESERVAS!A1:Z", body={}
    ).execute()

    headers = ["Artículo","Nombre","Estado","Estado Reserva","Reservado Para","Precio USD","Precio CRC","Imagen"]
    all_rows = [headers] + RESERVAS_DATA
    svc.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"RESERVAS!A1:H{len(all_rows)}",
        valueInputOption="USER_ENTERED",
        body={"values": all_rows}
    ).execute()
    print(f"  RESERVAS reescrita: {len(RESERVAS_DATA)} reservas + header")

    # ============================================================
    # 2. INVENTARIO_MAESTRO — actualizar Estado col E
    # ============================================================
    print("\nActualizando Estados en INVENTARIO_MAESTRO...")
    resp = svc.spreadsheets().values().get(
        spreadsheetId=sheet_id, range="INVENTARIO_MAESTRO!A2:E",
        valueRenderOption="UNFORMATTED_VALUE"
    ).execute()
    inv_rows = resp.get("values", [])

    estado_updates = []
    for i, row in enumerate(inv_rows, start=2):
        cod = row[0] if row else ""
        if not cod: continue
        if cod in VENDIDOS_CODS:
            estado_updates.append({"range": f"INVENTARIO_MAESTRO!E{i}", "values": [["Vendido"]]})
        elif cod in RESERVADOS_CODS:
            estado_updates.append({"range": f"INVENTARIO_MAESTRO!E{i}", "values": [["Reservado"]]})

    if estado_updates:
        svc.spreadsheets().values().batchUpdate(
            spreadsheetId=sheet_id,
            body={"valueInputOption": "USER_ENTERED", "data": estado_updates}
        ).execute()
        vendidos_n  = sum(1 for u in estado_updates if u["values"]==["Vendido"])
        reservados_n = sum(1 for u in estado_updates if u["values"]==["Reservado"])
        print(f"  Vendidos marcados:   {vendidos_n}")
        print(f"  Reservados marcados: {reservados_n}")

    # ============================================================
    # 3. VENTAS — actualizar códigos (de numérico a string)
    # ============================================================
    print("\nActualizando códigos en VENTAS...")
    resp3 = svc.spreadsheets().values().get(
        spreadsheetId=sheet_id, range="VENTAS!A2:A",
        valueRenderOption="UNFORMATTED_VALUE"
    ).execute()
    ventas_cods = resp3.get("values", [])
    ventas_updates = []
    for i, row in enumerate(ventas_cods, start=2):
        val = row[0] if row else ""
        try:
            num = int(float(val))
            cod = NUM_TO_COD.get(num)
            if cod:
                ventas_updates.append({"range": f"VENTAS!A{i}", "values": [[cod]]})
                print(f"  Fila {i}: {num} → {cod}")
        except:
            pass  # already a string code

    if ventas_updates:
        svc.spreadsheets().values().batchUpdate(
            spreadsheetId=sheet_id,
            body={"valueInputOption": "USER_ENTERED", "data": ventas_updates}
        ).execute()

    # ============================================================
    # 4. RESUMEN — recontar con estados actualizados
    # ============================================================
    print("\nActualizando RESUMEN con conteos reales...")
    resp4 = svc.spreadsheets().values().get(
        spreadsheetId=sheet_id, range="INVENTARIO_MAESTRO!A2:E",
        valueRenderOption="UNFORMATTED_VALUE"
    ).execute()
    inv2 = resp4.get("values", [])
    total      = len([r for r in inv2 if r and r[0]])
    disponibles = len([r for r in inv2 if len(r)>4 and r[4]=="Disponible"])
    reservados  = len([r for r in inv2 if len(r)>4 and r[4]=="Reservado"])
    vendidos    = len([r for r in inv2 if len(r)>4 and r[4]=="Vendido"])

    resp5 = svc.spreadsheets().values().get(
        spreadsheetId=sheet_id, range="RESUMEN!A1:E20",
        valueRenderOption="UNFORMATTED_VALUE"
    ).execute()
    res_rows = resp5.get("values", [])
    res_updates = []
    for i, row in enumerate(res_rows, 1):
        if not row: continue
        label = str(row[0]).strip().lower()
        if "total" in label:
            res_updates += [
                {"range": f"RESUMEN!A{i}", "values": [["Total de elementos"]]},
                {"range": f"RESUMEN!B{i}", "values": [[total]]}
            ]
        elif "disponib" in label:
            res_updates += [
                {"range": f"RESUMEN!B{i}", "values": [[disponibles]]},
                {"range": f"RESUMEN!E{i}", "values": [[disponibles]]} if len(row)>4 else {"range": f"RESUMEN!B{i}", "values": [[disponibles]]}
            ]
        elif "reservad" in label:
            res_updates += [
                {"range": f"RESUMEN!B{i}", "values": [[reservados]]},
                {"range": f"RESUMEN!E{i}", "values": [[reservados]]} if len(row)>4 else {"range": f"RESUMEN!B{i}", "values": [[reservados]]}
            ]
        elif "vendid" in label:
            res_updates += [
                {"range": f"RESUMEN!B{i}", "values": [[vendidos]]},
                {"range": f"RESUMEN!E{i}", "values": [[vendidos]]} if len(row)>4 else {"range": f"RESUMEN!B{i}", "values": [[vendidos]]}
            ]
        elif "visible" in label:
            res_updates.append({"range": f"RESUMEN!B{i}", "values": [[total]]})
        elif "sotheby" in label:
            res_updates.append({"range": f"RESUMEN!B{i}", "values": [[53]]})

    # Deduplicate ranges
    seen = set()
    deduped = []
    for u in res_updates:
        if u["range"] not in seen:
            seen.add(u["range"])
            deduped.append(u)

    if deduped:
        svc.spreadsheets().values().batchUpdate(
            spreadsheetId=sheet_id,
            body={"valueInputOption": "USER_ENTERED", "data": deduped}
        ).execute()

    print(f"  Total: {total} | Disponibles: {disponibles} | Reservados: {reservados} | Vendidos: {vendidos}")

    print()
    print("=" * 55)
    print("ACTUALIZACIÓN DE ESTADOS — COMPLETA")
    print("=" * 55)
    print(f"  RESERVAS:            15 reservas con códigos catálogo")
    print(f"  INVENTARIO_MAESTRO:  {len(vendidos_n if False else estado_updates)} estados actualizados")
    print(f"  VENTAS:              códigos actualizados")
    print(f"  RESUMEN:             conteos corregidos")

if __name__ == "__main__":
    main()
