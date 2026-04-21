from pathlib import Path
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from google.oauth2 import service_account
from googleapiclient.discovery import build
root=Path(r'c:\Users\Alejandro\Documents\Proyecto Pignatelli')

def load_env(path):
    env={}
    for line in path.read_text(encoding='utf-8').splitlines():
        line=line.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k,v=line.split('=',1)
        v=v.strip()
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
col_s=idx["Sotheby's"]; col_code=idx['Artículo']
count=0; codes=[]
for r in rows:
    code=r[col_code] if col_code < len(r) else ''
    s=str(r[col_s]).strip() if col_s < len(r) else ''
    if s and s.lower()!='no':
        count+=1; codes.append(str(code))
print('INVENTARIO_MAESTRO')
print('  con sothebys (col I != No):', count)
print('  codigos:', ', '.join(codes))
