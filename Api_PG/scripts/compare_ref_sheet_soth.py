import json, io, sys
from pathlib import Path
sys.stdout=io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
root=Path(r'c:\Users\Alejandro\Documents\Proyecto Pignatelli')
ref=json.loads((root/'docs'/'referencia_sothebys_pignatelli.json').read_text(encoding='utf-8'))
refs=ref.get('sothebys_references',[])+ref.get('manual_values',[])
ALIAS={'S1786a':'S178a','D69':'D60','S309a':'S309','S309b':'S309'}
codes=[]
for r in refs:
    raw=str(r.get('codigo_pignatelli','')).strip()
    for c in [x.strip() for x in raw.replace('/',',').split(',') if x.strip()]:
        codes.append(ALIAS.get(c,c))
ref_set=set(codes)

# sheet codes from last output hardcoded quick read from file generated maybe better load csv report has codes with sothebys? easier use google sheet call omitted; just load list produced previous run by reading txt? we'll query quickly from google using local script file
from google.oauth2 import service_account
from googleapiclient.discovery import build

def load_env(path):
    env={}
    for line in path.read_text(encoding='utf-8').splitlines():
        line=line.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k,v=line.split('=',1); v=v.strip()
        if v.startswith('"') and v.endswith('"'): v=v[1:-1]
        env[k.strip()]=v
    return env

env=load_env(root/'pignatelli-app'/'.env.local')
info={'type':'service_account','project_id':'inventario-pignatelli','private_key_id':'','private_key':env['GOOGLE_PRIVATE_KEY'].replace('\\n','\n').strip(),'client_email':env['GOOGLE_SERVICE_ACCOUNT_EMAIL'].strip(),'client_id':'','auth_uri':'https://accounts.google.com/o/oauth2/auth','token_uri':'https://oauth2.googleapis.com/token','auth_provider_x509_cert_url':'https://www.googleapis.com/oauth2/v1/certs','client_x509_cert_url':''}
creds=service_account.Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
svc=build('sheets','v4',credentials=creds,cache_discovery=False)
sid=env['GOOGLE_SHEETS_ID'].strip()
vals=svc.spreadsheets().values().get(spreadsheetId=sid, range='INVENTARIO_MAESTRO!A1:N600', valueRenderOption='UNFORMATTED_VALUE').execute().get('values',[])
headers=vals[0]; rows=vals[1:]
idx={h:i for i,h in enumerate(headers)}
cs=idx["Sotheby's"]; cc=idx['Artículo']
sheet_set={str(r[cc]).strip() for r in rows if cc < len(r) and cs < len(r) and str(r[cs]).strip() and str(r[cs]).strip().lower()!='no'}
print('ref set:',len(ref_set),'sheet set:',len(sheet_set))
print('ref not in sheet:',sorted(ref_set-sheet_set))
print('sheet not in ref:',sorted(sheet_set-ref_set))
