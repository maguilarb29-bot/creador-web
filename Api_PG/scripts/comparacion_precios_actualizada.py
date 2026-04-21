from pathlib import Path
import io, sys, re, csv
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from google.oauth2 import service_account
from googleapiclient.discovery import build

ROOT=Path(r'c:\Users\Alejandro\Documents\Proyecto Pignatelli')
ENV=ROOT/'pignatelli-app'/'.env.local'
OUT_CSV=ROOT/'docs'/'comparacion_precios_duenos_vs_sothebys_actualizada.csv'
OUT_MD=ROOT/'docs'/'comparacion_precios_duenos_vs_sothebys_actualizada.md'


def load_env(path):
    env={}
    for line in path.read_text(encoding='utf-8').splitlines():
        line=line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k,v=line.split('=',1)
        v=v.strip()
        if v.startswith('"') and v.endswith('"'): v=v[1:-1]
        env[k.strip()]=v
    return env

def num(v):
    if v is None or v=='': return None
    if isinstance(v,(int,float)): return float(v)
    s=str(v).strip().replace('$','').replace('₡','').replace(',','')
    if not s: return None
    try: return float(s)
    except: return None

def parse_sothebys_range(text):
    t=str(text or '').strip()
    if not t or t.lower()=='no':
        return (None,None)
    vals=[m.group(1) for m in re.finditer(r'\$\s*([0-9][0-9,\.]*)', t)]
    vals=[num(v) for v in vals]
    vals=[v for v in vals if v is not None]
    if not vals:
        return (None,None)
    if len(vals)==1:
        return (vals[0],vals[0])
    return (vals[0], vals[1])

env=load_env(ENV)
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
    range='INVENTARIO_MAESTRO!A1:N800',
    valueRenderOption='UNFORMATTED_VALUE'
).execute().get('values',[])

if not vals:
    raise SystemExit('INVENTARIO_MAESTRO vacío')

headers=vals[0]
rows=vals[1:]
idx={h:i for i,h in enumerate(headers)}

required=['Artículo','Nombre','Precio USD',"Sotheby's",'Estado','Cliente']
for c in required:
    if c not in idx:
        raise SystemExit(f'Falta columna: {c}')

records=[]
for r in rows:
    code=str(r[idx['Artículo']]).strip() if idx['Artículo'] < len(r) else ''
    if not code:
        continue
    nombre=str(r[idx['Nombre']]).strip() if idx['Nombre'] < len(r) else ''
    precio_dueno=num(r[idx['Precio USD']] if idx['Precio USD']<len(r) else None)
    s_txt=str(r[idx["Sotheby's"]]).strip() if idx["Sotheby's"] < len(r) else ''
    s_low, s_high = parse_sothebys_range(s_txt)
    estado=str(r[idx['Estado']]).strip() if idx['Estado']<len(r) else ''
    cliente=str(r[idx['Cliente']]).strip() if idx['Cliente']<len(r) else ''

    comparable = (precio_dueno is not None and s_low is not None)
    diff_low = (precio_dueno - s_low) if comparable else None
    ratio_low = (precio_dueno / s_low) if comparable and s_low else None

    records.append({
        'codigo':code,
        'nombre':nombre,
        'estado':estado,
        'cliente':cliente,
        'precio_dueno_usd':precio_dueno,
        'sothebys_ref':s_txt,
        'sothebys_low_usd':s_low,
        'sothebys_high_usd':s_high,
        'dif_vs_soth_low_usd':diff_low,
        'ratio_vs_soth_low':ratio_low,
    })

# report subsets
con_precio=[x for x in records if x['precio_dueno_usd'] is not None]
con_soth=[x for x in records if x['sothebys_low_usd'] is not None]
comparables=[x for x in records if x['precio_dueno_usd'] is not None and x['sothebys_low_usd'] is not None]

# sort comparables by biggest discount vs sothebys low
comparables_sorted=sorted(comparables, key=lambda x: x['dif_vs_soth_low_usd'])

# write CSV full comparable rows first then all rows with one side
with OUT_CSV.open('w', newline='', encoding='utf-8') as f:
    w=csv.writer(f)
    w.writerow(['codigo','nombre','estado','cliente','precio_dueno_usd','sothebys_ref','sothebys_low_usd','sothebys_high_usd','dif_vs_soth_low_usd','ratio_vs_soth_low'])
    for x in sorted(records, key=lambda r: r['codigo']):
        w.writerow([
            x['codigo'],x['nombre'],x['estado'],x['cliente'],
            '' if x['precio_dueno_usd'] is None else round(x['precio_dueno_usd'],2),
            x['sothebys_ref'],
            '' if x['sothebys_low_usd'] is None else round(x['sothebys_low_usd'],2),
            '' if x['sothebys_high_usd'] is None else round(x['sothebys_high_usd'],2),
            '' if x['dif_vs_soth_low_usd'] is None else round(x['dif_vs_soth_low_usd'],2),
            '' if x['ratio_vs_soth_low'] is None else round(x['ratio_vs_soth_low'],4),
        ])

# summary stats
sum_precio=sum(x['precio_dueno_usd'] for x in con_precio if x['precio_dueno_usd'] is not None)
sum_slow=sum(x['sothebys_low_usd'] for x in comparables if x['sothebys_low_usd'] is not None)
mean_ratio=(sum(x['ratio_vs_soth_low'] for x in comparables if x['ratio_vs_soth_low'] is not None)/len(comparables)) if comparables else None

with OUT_MD.open('w', encoding='utf-8') as f:
    f.write('# Comparación Actualizada: Precio Dueños vs Sotheby\'s\n\n')
    f.write(f'- Registros inventario evaluados: **{len(records)}**\n')
    f.write(f'- Con precio de dueños: **{len(con_precio)}**\n')
    f.write(f'- Con referencia Sotheby\'s (mínimo detectable): **{len(con_soth)}**\n')
    f.write(f'- Comparables directos (ambos): **{len(comparables)}**\n')
    f.write(f'- Suma precios dueños (items con precio): **USD {sum_precio:,.2f}**\n')
    if comparables:
        f.write(f'- Suma Sotheby\'s low (comparables): **USD {sum_slow:,.2f}**\n')
        f.write(f'- Ratio promedio (dueños / Sotheby\'s low): **{mean_ratio:.3f}x**\n')
    f.write('\n## Top 15 diferencias (dueños por debajo de Sotheby\'s low)\n\n')
    f.write('| Código | Precio dueños USD | Sotheby\'s low USD | Diferencia USD | Ratio |\n')
    f.write('|---|---:|---:|---:|---:|\n')
    for x in comparables_sorted[:15]:
        f.write(f"| {x['codigo']} | {x['precio_dueno_usd']:.2f} | {x['sothebys_low_usd']:.2f} | {x['dif_vs_soth_low_usd']:.2f} | {x['ratio_vs_soth_low']:.3f} |\n")

print('Reporte actualizado generado:')
print(' ', OUT_CSV)
print(' ', OUT_MD)
print('\nResumen rápido:')
print('  inventario evaluado:', len(records))
print('  con precio dueños:', len(con_precio))
print('  con Sothebys:', len(con_soth))
print('  comparables:', len(comparables))
if comparables:
    print('  ratio promedio dueños/sothebys_low:', round(mean_ratio,3))
    print('\nTop 10 diferencias (USD):')
    for x in comparables_sorted[:10]:
        print(f"   {x['codigo']}: dueños={x['precio_dueno_usd']:.2f}, soth_low={x['sothebys_low_usd']:.2f}, diff={x['dif_vs_soth_low_usd']:.2f}")
