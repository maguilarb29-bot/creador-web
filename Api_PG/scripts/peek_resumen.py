from pathlib import Path
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from google.oauth2 import service_account
from googleapiclient.discovery import build
PROJECT_ROOT=Path(r'c:\Users\Alejandro\Documents\Proyecto Pignatelli')
ENV_PATH=PROJECT_ROOT/'pignatelli-app'/'.env.local'

def load_env(p):
    env={}
    for line in p.read_text(encoding='utf-8').splitlines():
        line=line.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k,v=line.split('=',1); v=v.strip()
        if v.startswith('"') and v.endswith('"'): v=v[1:-1]
        env[k.strip()]=v
    return env

env=load_env(ENV_PATH)
info={'type':'service_account','project_id':'inventario-pignatelli','private_key_id':'','private_key':env['GOOGLE_PRIVATE_KEY'].replace('\\n','\n').strip(),'client_email':env['GOOGLE_SERVICE_ACCOUNT_EMAIL'].strip(),'client_id':'','auth_uri':'https://accounts.google.com/o/oauth2/auth','token_uri':'https://oauth2.googleapis.com/token','auth_provider_x509_cert_url':'https://www.googleapis.com/oauth2/v1/certs','client_x509_cert_url':''}
creds=service_account.Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
svc=build('sheets','v4',credentials=creds,cache_discovery=False)
sid=env['GOOGLE_SHEETS_ID'].strip()
for rng in ['RESUMEN!A1:H22','CATALOGO_WEB!A1:M8']:
    print('\n---',rng,'---')
    vals=svc.spreadsheets().values().get(spreadsheetId=sid, range=rng, valueRenderOption='FORMATTED_VALUE').execute().get('values',[])
    for i,row in enumerate(vals, start=1):
        print(i,row)
