"""
actualizar_d7_en_sheets.py
D7 → D7a (dos fotos: D7a + D7ab) + D7b (nueva fila)
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / "pignatelli-app" / ".env.local"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET = "INVENTARIO_MAESTRO"

FOTO_D7A_P = "D7a-coleccion-de-figurines-chinos-de.jpg"
FOTO_D7A_A = "D7ab-coleccion-de-figurines-chinos-de.jpg"
FOTO_D7B_P = "D7b-coleccion-de-figurines-chinos-de.jpg"
SOTHEBYS_VAL = "Lote #217 — $280 - $420"

def load_env(path):
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, v = line.split("=", 1); v = v.strip()
        if v.startswith('"') and v.endswith('"'): v = v[1:-1]
        env[k.strip()] = v
    return env

def get_service():
    env = load_env(ENV_PATH)
    sheet_id = env["GOOGLE_SHEETS_ID"].strip()
    pk = env["GOOGLE_PRIVATE_KEY"].replace("\\n", "\n").strip()
    info = {
        "type": "service_account", "project_id": "inventario-pignatelli",
        "private_key_id": "", "private_key": pk,
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

    resp = svc.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"{SHEET}!A1:O",
        valueRenderOption="UNFORMATTED_VALUE"
    ).execute()
    filas = resp.get("values", [])
    headers = filas[0]

    col_foto_p = headers.index("Foto principal") if "Foto principal" in headers else 12
    col_foto_a = col_foto_p + 1
    col_sothy  = headers.index("Sotheby's") if "Sotheby's" in headers else 9
    n_cols = len(headers)

    # Encontrar fila D7
    d7_row_num = None
    d7_row_data = None
    for i, f in enumerate(filas[1:], start=2):
        if f and f[0] == "D7":
            d7_row_num = i
            d7_row_data = f
            break

    if not d7_row_num:
        print("ERROR: D7 no encontrado en la hoja")
        return
    print(f"D7 encontrado en fila {d7_row_num}")

    # 1. Actualizar D7 → D7a
    updates = [
        {"range": f"{SHEET}!A{d7_row_num}",                           "values": [["D7a"]]},
        {"range": f"{SHEET}!{chr(65+col_foto_p)}{d7_row_num}",        "values": [[FOTO_D7A_P]]},
        {"range": f"{SHEET}!{chr(65+col_foto_a)}{d7_row_num}",        "values": [[FOTO_D7A_A]]},
        {"range": f"{SHEET}!{chr(65+col_sothy)}{d7_row_num}",         "values": [[SOTHEBYS_VAL]]},
    ]
    svc.spreadsheets().values().batchUpdate(
        spreadsheetId=sheet_id,
        body={"valueInputOption": "USER_ENTERED", "data": updates}
    ).execute()
    print(f"Fila {d7_row_num}: D7 → D7a con fotos y Sotheby's OK")

    # 2. Insertar fila vacía después de D7a para D7b
    meta = svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheet_id_num = next(
        s["properties"]["sheetId"] for s in meta["sheets"]
        if s["properties"]["title"] == SHEET
    )
    svc.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={"requests": [{
            "insertDimension": {
                "range": {"sheetId": sheet_id_num, "dimension": "ROWS",
                          "startIndex": d7_row_num, "endIndex": d7_row_num + 1},
                "inheritFromBefore": True
            }
        }]}
    ).execute()
    print(f"Fila {d7_row_num+1}: insertada para D7b")

    # 3. Escribir D7b — copia de D7a modificada
    d7b = list(d7_row_data) + [""] * (n_cols - len(d7_row_data))
    d7b[0]          = "D7b"
    d7b[col_foto_p] = FOTO_D7B_P
    d7b[col_foto_a] = ""
    d7b[col_sothy]  = SOTHEBYS_VAL

    svc.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{SHEET}!A{d7_row_num+1}:{chr(65+n_cols-1)}{d7_row_num+1}",
        valueInputOption="USER_ENTERED",
        body={"values": [d7b[:n_cols]]}
    ).execute()
    print(f"Fila {d7_row_num+1}: D7b escrita con foto {FOTO_D7B_P}")

    print()
    print("=" * 50)
    print("D7 → D7a + D7b  LISTO")
    print("  D7a fotos: D7a-... | D7ab-...")
    print("  D7b fotos: D7b-...")
    print(f"  Ambos: Sotheby's {SOTHEBYS_VAL}")

if __name__ == "__main__":
    main()
