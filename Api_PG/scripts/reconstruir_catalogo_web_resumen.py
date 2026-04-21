from pathlib import Path
import io, sys, re
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from google.oauth2 import service_account
from googleapiclient.discovery import build

PROJECT_ROOT = Path(r'c:\Users\Alejandro\Documents\Proyecto Pignatelli')
ENV_PATH = PROJECT_ROOT / 'pignatelli-app' / '.env.local'
SHEET_MASTER='INVENTARIO_MAESTRO'
SHEET_WEB='CATALOGO_WEB'
SHEET_RES='RESUMEN'
SHEET_RESERVAS='RESERVAS'
SHEET_VENTAS='VENTAS'

WEB_HEADERS=['idLote','slugWeb','nombreComercial','descripcionWeb','categoria','subtipo','ubicacion','estadoComercial','badgeSothebys','precioListaUSD','politicaPrecioWeb','monedaMostrar','precioDisplayTexto','imagenArchivo']

def load_env(path: Path):
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

def norm_slug(s):
    s=(s or '').strip().lower()
    repl={'á':'a','é':'e','í':'i','ó':'o','ú':'u','ñ':'n'}
    for a,b in repl.items():
        s=s.replace(a,b)
    return re.sub(r'[^a-z0-9]+','-',s).strip('-')

def parse_num(v):
    if v is None or v=='':
        return None
    if isinstance(v,(int,float)):
        return float(v)
    s=str(v).strip().replace('$','').replace('₡','').replace(',','')
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None

def fmt_usd(n):
    if n is None:
        return ''
    return f"${int(n)}" if abs(n-int(n))<1e-9 else f"${n:.2f}"

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

m=svc.spreadsheets().values().get(spreadsheetId=sid,range=f'{SHEET_MASTER}!A1:N',valueRenderOption='UNFORMATTED_VALUE').execute().get('values',[])
if not m:
    raise SystemExit('INVENTARIO_MAESTRO vacío')
headers=m[0]; rows=m[1:]
idx={h:i for i,h in enumerate(headers)}
for col in ['Artículo','Nombre','Categoría','Precio USD','Estado','Ubicación',"Sotheby's",'Descripción','Foto principal']:
    if col not in idx:
        raise SystemExit(f'Falta columna en maestro: {col}')

res_vals=svc.spreadsheets().values().get(spreadsheetId=sid,range=f'{SHEET_RESERVAS}!A2:A',valueRenderOption='UNFORMATTED_VALUE').execute().get('values',[])
ven_vals=svc.spreadsheets().values().get(spreadsheetId=sid,range=f'{SHEET_VENTAS}!A2:A',valueRenderOption='UNFORMATTED_VALUE').execute().get('values',[])
reservados={str(r[0]).strip() for r in res_vals if r and str(r[0]).strip()}
vendidos={str(r[0]).strip() for r in ven_vals if r and str(r[0]).strip()}
reservados_num={re.sub(r'[^0-9]','',x) for x in reservados}
vendidos_num={re.sub(r'[^0-9]','',x) for x in vendidos}

web_rows=[]
for r in rows:
    def g(col):
        i=idx[col]
        return r[i] if i < len(r) else ''
    code=str(g('Artículo')).strip()
    if not code:
        continue
    nombre=str(g('Nombre') or '').strip()
    if nombre.startswith('[REF]'):
        continue
    cat=str(g('Categoría') or '').strip()
    precio=parse_num(g('Precio USD'))
    soth=str(g("Sotheby's") or '').strip()
    desc=str(g('Descripción') or '').strip()
    ubi=str(g('Ubicación') or '').strip()
    estado=str(g('Estado') or '').strip() or 'Disponible'
    img=str(g('Foto principal') or '').strip()

    code_num=re.sub(r'^[A-Z]+','',code)
    if code in vendidos or code_num in vendidos_num:
        estado_eff='Vendido'
    elif code in reservados or code_num in reservados_num:
        estado_eff='Reservado'
    else:
        estado_eff=estado

    tiene_soth=bool(soth and soth.lower()!='no')
    if precio is None and not tiene_soth:
        continue

    badge='con valoración' if tiene_soth else 'sin valoración'
    politica='No disponible' if estado_eff in ('Vendido','Reservado') else ('Precio fijo' if precio is not None else 'Consultar')
    moneda='USD' if precio is not None else ''
    display=fmt_usd(precio)

    web_rows.append([
        code,norm_slug(cat),nombre,desc,cat,'',ubi,estado_eff,badge,
        precio if precio is not None else '',politica,moneda,display,img
    ])

def sort_key(code):
    m=re.match(r'^([A-Z]+)(\d+)([a-z]*)$',code)
    return ('ZZ',10**9,code) if not m else (m.group(1),int(m.group(2)),m.group(3))
web_rows.sort(key=lambda x: sort_key(str(x[0])))

svc.spreadsheets().values().clear(spreadsheetId=sid,range=f'{SHEET_WEB}!A1:Z',body={}).execute()
svc.spreadsheets().values().update(
    spreadsheetId=sid,
    range=f'{SHEET_WEB}!A1:N{len(web_rows)+1}',
    valueInputOption='USER_ENTERED',
    body={'values':[WEB_HEADERS]+web_rows}
).execute()

total=len(web_rows)
disp=sum(1 for r in web_rows if r[7]=='Disponible')
resv=sum(1 for r in web_rows if r[7]=='Reservado')
vend=sum(1 for r in web_rows if r[7]=='Vendido')
soth_count=sum(1 for r in web_rows if r[8]=='con valoración')
base_total=sum(float(r[9]) for r in web_rows if isinstance(r[9],(int,float)))

ventas_rows=svc.spreadsheets().values().get(spreadsheetId=sid,range=f'{SHEET_VENTAS}!A2:H',valueRenderOption='UNFORMATTED_VALUE').execute().get('values',[])
vend_total=0.0
for r in ventas_rows:
    if len(r)>3:
        n=parse_num(r[3])
        if n is not None:
            vend_total+=n

cat_counter=Counter(r[4] for r in web_rows if r[4])
updates=[
    {'range':f'{SHEET_RES}!B3','values':[[total]]},
    {'range':f'{SHEET_RES}!B4','values':[[disp]]},
    {'range':f'{SHEET_RES}!B5','values':[[resv]]},
    {'range':f'{SHEET_RES}!B6','values':[[vend]]},
    {'range':f'{SHEET_RES}!B7','values':[[total]]},
    {'range':f'{SHEET_RES}!B8','values':[[soth_count]]},
    {'range':f'{SHEET_RES}!B11','values':[[base_total]]},
    {'range':f'{SHEET_RES}!B12','values':[[vend_total]]},
    {'range':f'{SHEET_RES}!E4','values':[[disp]]},
    {'range':f'{SHEET_RES}!E5','values':[[resv]]},
    {'range':f'{SHEET_RES}!E6','values':[[vend]]},
    {'range':f'{SHEET_RES}!E7','values':[[0]]},
]
svc.spreadsheets().values().clear(spreadsheetId=sid,range=f'{SHEET_RES}!D11:E25',body={}).execute()
cat_values=[[c,n] for c,n in sorted(cat_counter.items(), key=lambda x:(-x[1],x[0]))[:15]]
if cat_values:
    updates.append({'range':f'{SHEET_RES}!D11:E{10+len(cat_values)}','values':cat_values})
svc.spreadsheets().values().batchUpdate(spreadsheetId=sid,body={'valueInputOption':'USER_ENTERED','data':updates}).execute()

print('OK: CATALOGO_WEB y RESUMEN actualizados')
print('  filas web:', total)
print('  estados -> disp/res/vend:', disp, resv, vend)
print('  con sothebys:', soth_count)
print('  total precio base usd:', base_total)
print('  total vendido usd:', vend_total)
