import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build

SA_FILE  = Path("C:/Users/Alejandro/Documents/Proyecto Pignatelli/pignatelli-app/lib/service-account.json")
sa_info  = json.loads(SA_FILE.read_text(encoding="utf-8"))
sheet_id = "1X6l9MeiFgXKRmVyRYBwsMnjwkWz971BsrBK3lbWJ-u4"  # from .env.local

creds = service_account.Credentials.from_service_account_info(
    sa_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
svc = build("sheets", "v4", credentials=creds, cache_discovery=False)

meta = svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
sheets = [s["properties"]["title"] for s in meta["sheets"]]
print("Hojas:", sheets)

for name in ["INVENTARIO_MAESTRO", "RESERVAS", "VENTAS", "RESUMEN"]:
    # Headers + first 4 data rows
    r1 = svc.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"{name}!A1:Z5",
        valueRenderOption="UNFORMATTED_VALUE").execute()
    rows = r1.get("values", [])
    # Total count
    r2 = svc.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"{name}!A:A",
        valueRenderOption="UNFORMATTED_VALUE").execute()
    total = len(r2.get("values", []))
    print(f"\n{'='*55}")
    print(f"  {name}  ({total} filas)")
    print(f"{'='*55}")
    for i, row in enumerate(rows, 1):
        print(f"  {i}: {row}")
