"""debug_sheet.py — verifica estado real del sheet"""
from __future__ import annotations
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCRIPT_PATH  = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[2]
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
        "client_email": env["GOOGLE_SERVICE_ACCOUNT_EMAIL"].strip(), "client_id": "",
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
        spreadsheetId=sheet_id,
        range="INVENTARIO_MAESTRO!A1:N",
        valueRenderOption="UNFORMATTED_VALUE",
    ).execute()
    filas = resp.get("values", [])
    headers = filas[0] if filas else []

    print(f"Headers ({len(headers)} cols):", [h for h in headers])
    print(f"Total filas de datos: {len(filas) - 1}")

    # Verificar primeros 3 articulos
    print("\n=== Primeros 3 articulos ===")
    for fila in filas[1:4]:
        def g(i): return fila[i] if i < len(fila) else ""
        print(f"  A={g(0)!r:10}  B={str(g(1))[:35]!r}  H={g(7)!r}  L={str(g(11))[:45]!r}")

    # Buscar articulos con Sotheby's
    print("\n=== Articulos con Sotheby's (col J) ===")
    count = 0
    for fila in filas[1:]:
        val_j = fila[9] if 9 < len(fila) else ""
        if val_j:
            val_a = fila[0] if 0 < len(fila) else ""
            val_l = fila[11] if 11 < len(fila) else ""
            print(f"  {val_a!r:8}  J={val_j!r}  L={str(val_l)[:40]!r}")
            count += 1
    print(f"  Total: {count}")

    # Verificar codigos vacios
    vacios = [fila[0] for fila in filas[1:] if not (fila[0] if fila else "")]
    print(f"\nCodigos vacios en col A: {len(vacios)}")
    if vacios:
        print(f"  Primeros: {vacios[:5]}")

if __name__ == "__main__":
    main()
