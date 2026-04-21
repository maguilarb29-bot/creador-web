"""
actualizar_sheets_completo.py

Cambios según instrucciones del usuario (audio 7 abril 2026):

VENTAS:
  - Headers: idLote→Artículo, nombreComercial→Nombre, precioBaseUSD→Precio USD,
    precioVendidoUSD→Precio Vendido USD, precioVendidoCRC→Precio Vendido CRC,
    estadoComercial→Estado, imagenArchivo→Imagen, notas→Notas
  - Agregar "Vendido a Pablo Brenes" en notas de los 4 artículos vendidos

RESERVAS:
  - Headers: idLote→Artículo, nombreComercial→Nombre, estadoComercial→Estado,
    estadoReserva→Estado Reserva, reservadoPara→Reservado Para,
    precioBaseUSD→Precio USD, imagenArchivo→Imagen
  - Agregar columna: Precio CRC
  - Agregar reserva D11 (jarrones rosados) por Margarita

RESUMEN:
  - "Total de lotes" → "Total de elementos"
  - Corregir fórmulas/valores al conteo real del INVENTARIO_MAESTRO (510 total)
"""
from __future__ import annotations
import sys, io, json
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
    svc = build("sheets", "v4", credentials=creds, cache_discovery=False)
    return svc, sheet_id

def main():
    svc, sheet_id = get_service()
    meta = svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheet_ids = {s["properties"]["title"]: s["properties"]["sheetId"]
                 for s in meta["sheets"]}
    print("Hojas disponibles:", list(sheet_ids.keys()))

    updates = []  # batchUpdate values
    format_requests = []  # batchUpdate format/structure

    # ================================================================
    # VENTAS — leer estado actual
    # ================================================================
    print("\n--- VENTAS ---")
    resp = svc.spreadsheets().values().get(
        spreadsheetId=sheet_id, range="VENTAS!A1:I",
        valueRenderOption="UNFORMATTED_VALUE"
    ).execute()
    ventas_rows = resp.get("values", [])
    if not ventas_rows:
        print("  VENTAS vacía, saltando.")
    else:
        headers = ventas_rows[0]
        print(f"  Headers actuales: {headers}")
        for i, r in enumerate(ventas_rows[1:], 2):
            print(f"  Fila {i}: {r}")

        # Detectar columnas
        def idx(h, default):
            try: return headers.index(h)
            except: return default

        col_notas = idx("notas", len(headers)-1)

        # Nuevos headers (8 columnas: A-H)
        new_ventas_headers = [
            "Artículo", "Nombre", "Precio USD",
            "Precio Vendido USD", "Precio Vendido CRC",
            "Estado", "Imagen", "Notas"
        ]
        updates.append({
            "range": "VENTAS!A1:H1",
            "values": [new_ventas_headers]
        })
        print(f"  Nuevos headers: {new_ventas_headers}")

        # Agregar "Vendido a Pablo Brenes" en notas de cada fila de datos
        # La columna notas queda en H (índice 7)
        for i, row in enumerate(ventas_rows[1:], 2):
            # Obtener nota actual
            nota_actual = row[col_notas] if col_notas < len(row) else ""
            nota_actual = str(nota_actual).strip() if nota_actual else ""
            # Agregar Pablo Brenes si no está ya
            if "Pablo Brenes" not in nota_actual:
                nueva_nota = f"{nota_actual} | Vendido a Pablo Brenes".strip(" | ")
            else:
                nueva_nota = nota_actual
            updates.append({
                "range": f"VENTAS!H{i}",
                "values": [[nueva_nota]]
            })
            print(f"  Fila {i}: notas → '{nueva_nota}'")

    # ================================================================
    # RESERVAS — leer estado actual
    # ================================================================
    print("\n--- RESERVAS ---")
    resp2 = svc.spreadsheets().values().get(
        spreadsheetId=sheet_id, range="RESERVAS!A1:J",
        valueRenderOption="UNFORMATTED_VALUE"
    ).execute()
    res_rows = resp2.get("values", [])
    if not res_rows:
        print("  RESERVAS vacía.")
        res_headers = []
    else:
        res_headers = res_rows[0]
        print(f"  Headers actuales: {res_headers}")
        for i, r in enumerate(res_rows[1:], 2):
            print(f"  Fila {i}: {r}")

    # Nuevos headers RESERVAS — agregar columna "Precio CRC" al final de Precio USD
    # Orden: Artículo | Nombre | Estado | Estado Reserva | Reservado Para | Precio USD | Precio CRC | Imagen
    new_res_headers = [
        "Artículo", "Nombre", "Estado", "Estado Reserva",
        "Reservado Para", "Precio USD", "Precio CRC", "Imagen"
    ]
    updates.append({
        "range": "RESERVAS!A1:H1",
        "values": [new_res_headers]
    })
    print(f"  Nuevos headers: {new_res_headers}")

    # Verificar si D11 ya está en RESERVAS
    codigos_reserva = []
    for row in res_rows[1:]:
        codigos_reserva.append(row[0] if row else "")

    if "D11" not in codigos_reserva:
        # Agregar D11 al final
        next_row = len(res_rows) + 1
        updates.append({
            "range": f"RESERVAS!A{next_row}:H{next_row}",
            "values": [["D11", "Pareja de Jarrones Esféricos Rosas Cerámicos", "Reservado", "Reservado", "Margarita", 150, "", "D11-pareja-de-jarrones-esfericos-rosas.jpg"]]
        })
        print(f"  Fila {next_row}: D11 reservado por Margarita → agregada")
    else:
        print("  D11 ya existe en RESERVAS.")

    # ================================================================
    # RESUMEN — leer y corregir
    # ================================================================
    print("\n--- RESUMEN ---")
    resp3 = svc.spreadsheets().values().get(
        spreadsheetId=sheet_id, range="RESUMEN!A1:E30",
        valueRenderOption="UNFORMATTED_VALUE"
    ).execute()
    res_sum = resp3.get("values", [])
    for i, r in enumerate(res_sum, 1):
        print(f"  Fila {i}: {r}")

    # Contar desde INVENTARIO_MAESTRO real
    resp_inv = svc.spreadsheets().values().get(
        spreadsheetId=sheet_id, range="INVENTARIO_MAESTRO!A2:E",
        valueRenderOption="UNFORMATTED_VALUE"
    ).execute()
    inv_rows = resp_inv.get("values", [])
    total = len([r for r in inv_rows if r and r[0]])
    disponibles = len([r for r in inv_rows if len(r)>4 and r[4]=="Disponible"])
    reservados   = len([r for r in inv_rows if len(r)>4 and r[4]=="Reservado"])
    vendidos     = len([r for r in inv_rows if len(r)>4 and r[4]=="Vendido"])
    con_precio   = len([r for r in inv_rows if len(r)>3 and r[3] not in ("","0","0.0",None)])
    print(f"\n  Conteo real INVENTARIO_MAESTRO:")
    print(f"    Total:       {total}")
    print(f"    Disponibles: {disponibles}")
    print(f"    Reservados:  {reservados}")
    print(f"    Vendidos:    {vendidos}")
    print(f"    Con precio:  {con_precio}")

    # Actualizar celdas del RESUMEN — buscar filas con "Total de lotes" etc.
    # Basado en el screenshot: A3=Total de lotes, B3=0 → corregir
    resumen_updates = []
    for i, row in enumerate(res_sum, 1):
        if not row: continue
        label = str(row[0]).strip() if row else ""
        if "lotes" in label.lower() and "total" in label.lower():
            resumen_updates.append({"range": f"RESUMEN!A{i}", "values": [["Total de elementos"]]})
            resumen_updates.append({"range": f"RESUMEN!B{i}", "values": [[total]]})
            print(f"  Fila {i}: 'Total de lotes' → 'Total de elementos': {total}")
        elif "disponib" in label.lower():
            resumen_updates.append({"range": f"RESUMEN!B{i}", "values": [[disponibles]]})
            print(f"  Fila {i}: Disponibles → {disponibles}")
        elif "reservad" in label.lower():
            resumen_updates.append({"range": f"RESUMEN!B{i}", "values": [[reservados]]})
            print(f"  Fila {i}: Reservados → {reservados}")
        elif "vendid" in label.lower():
            resumen_updates.append({"range": f"RESUMEN!B{i}", "values": [[vendidos]]})
            print(f"  Fila {i}: Vendidos → {vendidos}")
        elif "visible" in label.lower():
            resumen_updates.append({"range": f"RESUMEN!B{i}", "values": [[total]]})
            print(f"  Fila {i}: Visibles en web → {total}")
        elif "sotheby" in label.lower():
            resumen_updates.append({"range": f"RESUMEN!B{i}", "values": [[53]]})
            print(f"  Fila {i}: Con Sotheby's → 53")
    updates.extend(resumen_updates)

    # ================================================================
    # Enviar todas las actualizaciones
    # ================================================================
    if updates:
        print(f"\nEnviando {len(updates)} actualizaciones...")
        svc.spreadsheets().values().batchUpdate(
            spreadsheetId=sheet_id,
            body={"valueInputOption": "USER_ENTERED", "data": updates}
        ).execute()
        print("OK")
    else:
        print("Sin actualizaciones.")

    print("\n" + "="*55)
    print("ACTUALIZACIÓN COMPLETA")
    print("="*55)
    print("  VENTAS:   Headers renombrados + Pablo Brenes en notas")
    print("  RESERVAS: Headers renombrados + Precio CRC + D11/Margarita")
    print("  RESUMEN:  'lotes'→'elementos' + conteos reales")

if __name__ == "__main__":
    main()
