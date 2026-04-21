"""
limpiar_hojas.py — Elimina hojas sobrantes y deja solo las 5 necesarias.
"""
from __future__ import annotations
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCRIPT_PATH  = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[2]
ENV_PATH     = PROJECT_ROOT / "pignatelli-app" / ".env.local"
SCOPES       = ["https://www.googleapis.com/auth/spreadsheets"]

CONSERVAR = {"INVENTARIO_MAESTRO", "RESERVAS", "VENTAS", "RESUMEN", "CATALOGO_WEB"}

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
    hojas = {s['properties']['title']: s['properties']['sheetId'] for s in meta['sheets']}
    print("Hojas actuales:", list(hojas.keys()))

    eliminar = [nombre for nombre in hojas if nombre not in CONSERVAR]
    if not eliminar:
        print("Nada que eliminar.")
        return

    requests = [{"deleteSheet": {"sheetId": hojas[n]}} for n in eliminar]
    for n in eliminar:
        print(f"  Eliminando: {n}")

    svc.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={"requests": requests}
    ).execute()

    print()
    print("Hojas finales:", CONSERVAR)

if __name__ == "__main__":
    main()
