import os
import sys
import pickle
import base64
import subprocess
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

BASE_DIR = Path(__file__).parent
client_secret_file = BASE_DIR / "client_secret.json"
token_file = BASE_DIR / "token.pickle"

SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.force-ssl'
]

print("=" * 65)
print("        AUTORIZADOR DO CANAL YOUTUBE - NICOSAURUS")
print("=" * 65)

if not client_secret_file.exists():
    print("[ERRO] client_secret.json não encontrado na pasta do projeto!")
    input("\nPressione Enter para fechar...")
    sys.exit(1)

flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_file), SCOPES)
print("\n[1/3] Abrindo o seu navegador padrão para você autorizar o canal...")
print("      - Selecione a conta do canal Nicosaurus")
print("      - Se aparecer 'Google não verificou este app', clique em 'Avançado' -> 'Acessar (não seguro)'")
print("      - Clique em 'Continuar' / 'Permitir'\n")

try:
    credentials = flow.run_local_server(port=0, open_browser=True)
except Exception as e:
    print(f"\n[ERRO] Falha na autorização: {e}")
    input("\nPressione Enter para fechar...")
    sys.exit(1)

with open(token_file, 'wb') as f:
    pickle.dump(credentials, f)

print("\n[2/3] Autenticado com sucesso! token.pickle salvo no seu PC.")

with open(token_file, 'rb') as f:
    token_b64 = base64.b64encode(f.read()).decode('utf-8')

copied = False
try:
    subprocess.run("clip", input=token_b64.encode('utf-8'), check=True, shell=True)
    copied = True
except Exception:
    pass

print("\n[3/3] TOKEN GERADO COM SUCESSO!")
if copied:
    print("\n" + "*" * 65)
    print(">>> O NOVO TOKEN JÁ FOI COPIADO PARA O SEU TECLADO (Ctrl + V)! <<<")
    print("*" * 65)

print("\nCódigo gerado para o GitHub Actions:\n")
print("-" * 65)
print(token_b64)
print("-" * 65)
print("\nInstrução final:")
print("1. Vá em seu repositório no GitHub -> Settings -> Secrets and variables -> Actions")
print("2. Edite o segredo YOUTUBE_TOKEN_BASE64 e cole (Ctrl + V)")
print("=" * 65)

input("\nPressione Enter para fechar...")
