from pathlib import Path
import io, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import openpyxl
from google.oauth2 import service_account
from googleapiclient.discovery import build

PROJECT_ROOT = Path(r'c:\Users\Alejandro\Documents\Proyecto Pignatelli')
ENV_PATH = PROJECT_ROOT / 'pignatelli-app' / '.env.local'
XLSX_MAIN = PROJECT_ROOT / 'docs' / 'Condominio Solaris-Belongings-01032026 (3).xlsx'
SHEET_MASTER='INVENTARIO_MAESTRO'
SHEET_RESERVAS='RESERVAS'


def load_env(path):
    env={}
    for line in path.read_text(encoding='utf-8').splitlines():
        line=line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k,v=line.split('=',1)
        v=v.strip()
        if v.startswith('"') and v.endswith('"'):
            v=v[1:-1]
        env[k.strip()]=v
    return env

def parse_price(v):
    if v is None:
        return None
    if isinstance(v,(int,float)):
        if float(v)==0:
            return None
        return float(v)
    s=str(v).strip().replace('$','').replace(',','')
    if not s:
        return None
    try:
        n=float(s)
        return None if n==0 else n
    except:
        return None

def is_root_code(code):
    return bool(re.match(r'^[A-Z]+\d+$', code or ''))

def num_from_code(code):
    m=re.match(r'^[A-Z]+(\d+)', code or '')
    return int(m.group(1)) if m else None

# --- auth sheets ---
env=load_env(ENV_PATH)
info={
    'type':'service_account','project_id':'inventario-pignatelli','private_key_id':'',
    'private_key':env['GOOGLE_PRIVATE_KEY'].replace('\\n','\n').strip(),
    'client_email':env['GOOGLE_SERVICE_ACCOUNT_EMAIL'].strip(),'client_id':'',
    'auth_uri':'https://accounts.google.com/o/oauth2/auth','token_uri':'https://oauth2.googleapis.com/token',
    'auth_provider_x509_cert_url':'https://www.googleapis.com/oauth2/v1/certs','client_x509_cert_url':''
}
creds=service_account.Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
svc=build('sheets','v4',credentials=creds,cache_discovery=False)
sid=env['GOOGLE_SHEETS_ID'].strip()

# --- load owner price map from xlsx main ---
wb=openpyxl.load_workbook(XLSX_MAIN, data_only=True, read_only=True)
ws=wb.active
owner_price_by_num={}
for row in ws.iter_rows(min_row=6, max_row=500, values_only=True):
    item_num=row[1]
    if item_num is None:
        continue
    try:
        item_num=int(item_num)
    except:
        continue
    ask_usd=parse_price(row[7])
    owner_price_by_num[item_num]=ask_usd
wb.close()

print(f'Items cargados desde Excel jefes: {len(owner_price_by_num)}')

# --- read INVENTARIO_MAESTRO ---
vals=svc.spreadsheets().values().get(
    spreadsheetId=sid,
    range=f'{SHEET_MASTER}!A1:N600',
    valueRenderOption='UNFORMATTED_VALUE'
).execute().get('values',[])
headers=vals[0]
rows=vals[1:]
idx={h:i for i,h in enumerate(headers)}

for need in ['Artículo','Nombre','Precio USD','Estado','Cliente']:
    if need not in idx:
        raise SystemExit(f'Falta columna {need} en maestro')

updates=[]
roots_updated=0
subs_cleared=0

for rnum,row in enumerate(rows, start=2):
    code = str(row[idx['Artículo']]).strip() if idx['Artículo'] < len(row) else ''
    if not code:
        continue

    # root: tomar precio del documento de jefes por numItem
    if is_root_code(code):
        num=num_from_code(code)
        p=owner_price_by_num.get(num, None)
        # None => vacío
        updates.append({'range':f'{SHEET_MASTER}!D{rnum}','values':[[p if p is not None else '']]})
        roots_updated += 1
    else:
        # subitem: limpiar precio (regla tuya)
        updates.append({'range':f'{SHEET_MASTER}!D{rnum}','values':[['']]})
        subs_cleared += 1

# D11 reservado por Margherita
# actualizar en maestro
for rnum,row in enumerate(rows, start=2):
    code = str(row[idx['Artículo']]).strip() if idx['Artículo'] < len(row) else ''
    if code=='D11':
        updates.append({'range':f'{SHEET_MASTER}!E{rnum}','values':[['Reservado']]})
        updates.append({'range':f'{SHEET_MASTER}!F{rnum}','values':[['Margherita']]})
        break

# batch update maestro
svc.spreadsheets().values().batchUpdate(
    spreadsheetId=sid,
    body={'valueInputOption':'USER_ENTERED','data':updates}
).execute()

print(f'Precios aplicados en raíces: {roots_updated}')
print(f'Precios limpiados en sub-items: {subs_cleared}')

# Upsert en RESERVAS para idLote=11
res_vals=svc.spreadsheets().values().get(
    spreadsheetId=sid,
    range=f'{SHEET_RESERVAS}!A1:G300',
    valueRenderOption='UNFORMATTED_VALUE'
).execute().get('values',[])
res_headers=res_vals[0] if res_vals else ['idLote','nombreComercial','estadoComercial','estadoReserva','reservadoPara','precioBaseUSD','imagenArchivo']
res_rows=res_vals[1:] if len(res_vals)>1 else []

row_11=None
for i,r in enumerate(res_rows, start=2):
    if r and str(r[0]).strip()=='11':
        row_11=i
        break

res_payload=['11','2 jarrones rosados','Reservado','Reservado','Margherita','','11.jpg']
if row_11:
    svc.spreadsheets().values().update(
        spreadsheetId=sid,
        range=f'{SHEET_RESERVAS}!A{row_11}:G{row_11}',
        valueInputOption='USER_ENTERED',
        body={'values':[res_payload]}
    ).execute()
    print('RESERVAS: item 11 actualizado')
else:
    insert_at=len(res_rows)+2
    svc.spreadsheets().values().update(
        spreadsheetId=sid,
        range=f'{SHEET_RESERVAS}!A{insert_at}:G{insert_at}',
        valueInputOption='USER_ENTERED',
        body={'values':[res_payload]}
    ).execute()
    print('RESERVAS: item 11 agregado')

print('OK')
