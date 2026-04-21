from pathlib import Path
import io, sys, csv, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from google.oauth2 import service_account
from googleapiclient.discovery import build

PROJECT_ROOT = Path(r'c:\Users\Alejandro\Documents\Proyecto Pignatelli')
ENV_PATH = PROJECT_ROOT / 'pignatelli-app' / '.env.local'
OUT_CSV = PROJECT_ROOT / 'docs' / 'reporte_precios_vs_sothebys.csv'
OUT_MD  = PROJECT_ROOT / 'docs' / 'reporte_precios_vs_sothebys.md'
SHEET = 'INVENTARIO_MAESTRO'


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


def parse_num(v):
    if v is None or v=='': return None
    if isinstance(v,(int,float)): return float(v)
    s=str(v).replace('$','').replace('₡','').replace(',','').strip()
    if not s: return None
    try: return float(s)
    except: return None


def parse_sothebys_low(s):
    if not s or str(s).strip().lower()=='no':
        return None
    t=str(s)
    # Manual — $1,500 or Lote #123 — $420 - $700
    m=re.search(r'\$\s*([0-9][0-9,\.]*)', t)
    if not m: return None
    raw=m.group(1).replace(',','')
    try:
        return float(raw)
    except:
        return None


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

vals=svc.spreadsheets().values().get(
    spreadsheetId=sid,
    range=f'{SHEET}!A1:N600',
    valueRenderOption='UNFORMATTED_VALUE'
).execute().get('values',[])
headers=vals[0]
rows=vals[1:]
idx={h:i for i,h in enumerate(headers)}

records=[]
for r in rows:
    def g(col):
        i=idx[col]
        return r[i] if i < len(r) else ''
    code=str(g('Artículo')).strip()
    if not code:
        continue
    if not re.match(r'^[A-Z]+\d+$', code):
        continue  # solo raíz
    nombre=str(g('Nombre')).strip()
    precio=parse_num(g('Precio USD'))
    soth=str(g("Sotheby's")).strip()
    soth_low=parse_sothebys_low(soth)
    estado=str(g('Estado')).strip()
    cliente=str(g('Cliente')).strip()
    if precio is None and not soth_low and (not soth or soth.lower()=='no'):
        continue

    diff=None
    ratio=None
    if precio is not None and soth_low is not None and soth_low != 0:
        diff=precio - soth_low
        ratio=precio / soth_low

    records.append({
        'codigo':code,
        'nombre':nombre,
        'estado':estado,
        'cliente':cliente,
        'precio_jefes_usd':precio,
        'sothebys_ref':soth,
        'sothebys_low_usd':soth_low,
        'diferencia_usd':diff,
        'ratio_vs_sothebys':ratio,
    })

records.sort(key=lambda x: (x['codigo']))

# write csv
with OUT_CSV.open('w', newline='', encoding='utf-8') as f:
    w=csv.writer(f)
    w.writerow(['codigo','nombre','estado','cliente','precio_jefes_usd','sothebys_ref','sothebys_low_usd','diferencia_usd','ratio_vs_sothebys'])
    for x in records:
        w.writerow([
            x['codigo'], x['nombre'], x['estado'], x['cliente'],
            '' if x['precio_jefes_usd'] is None else round(x['precio_jefes_usd'],2),
            x['sothebys_ref'],
            '' if x['sothebys_low_usd'] is None else round(x['sothebys_low_usd'],2),
            '' if x['diferencia_usd'] is None else round(x['diferencia_usd'],2),
            '' if x['ratio_vs_sothebys'] is None else round(x['ratio_vs_sothebys'],4),
        ])

# summary
total=len(records)
with_price=sum(1 for x in records if x['precio_jefes_usd'] is not None)
with_soth=sum(1 for x in records if x['sothebys_low_usd'] is not None)
both=[x for x in records if x['precio_jefes_usd'] is not None and x['sothebys_low_usd'] is not None]

# biggest discounts vs Sotheby's low
discounts=sorted([x for x in both if x['diferencia_usd'] < 0], key=lambda x: x['diferencia_usd'])[:15]

with OUT_MD.open('w', encoding='utf-8') as f:
    f.write('# Reporte Precio Jefes vs Sothebys\n\n')
    f.write(f'- Registros incluidos (raíz con precio y/o Sothebys): **{total}**\n')
    f.write(f'- Con precio jefes: **{with_price}**\n')
    f.write(f'- Con referencia Sothebys (valor mínimo detectable): **{with_soth}**\n')
    f.write(f'- Con ambos comparables: **{len(both)}**\n\n')
    f.write('## Top diferencias (precio jefes menor que Sothebys low)\n\n')
    f.write('| Código | Precio jefes USD | Sothebys low USD | Diferencia USD | Ratio |\n')
    f.write('|---|---:|---:|---:|---:|\n')
    for x in discounts:
        f.write(f"| {x['codigo']} | {x['precio_jefes_usd']:.2f} | {x['sothebys_low_usd']:.2f} | {x['diferencia_usd']:.2f} | {x['ratio_vs_sothebys']:.3f} |\n")

print('Reporte generado:')
print(' ', OUT_CSV)
print(' ', OUT_MD)
print('\nResumen:')
print('  registros:', total)
print('  con precio:', with_price)
print('  con sothebys:', with_soth)
print('  comparables:', len(both))
print('\nTop 8 descuentos:')
for x in discounts[:8]:
    print(f"  {x['codigo']}: jefes={x['precio_jefes_usd']:.2f} vs soth={x['sothebys_low_usd']:.2f} (diff {x['diferencia_usd']:.2f})")
