import base64
from pathlib import Path

BASE_DIR = Path(__file__).parent

token_path = BASE_DIR / "token.pickle"
secret_path = BASE_DIR / "client_secret.json"

print("=" * 60)
print("     GITHUB ACTIONS CREDENTIAL ENCODER ")
print("=" * 60)

if token_path.exists():
    with open(token_path, "rb") as f:
        token_encoded = base64.b64encode(f.read()).decode("utf-8")
    print("\n--- COPY THIS FOR YOUTUBE_TOKEN_BASE64 ---")
    print(token_encoded)
    print("------------------------------------------")
else:
    print("\n[!] token.pickle not found. Make sure you authenticated at least once locally first.")

if secret_path.exists():
    with open(secret_path, "rb") as f:
        secret_encoded = base64.b64encode(f.read()).decode("utf-8")
    print("\n--- COPY THIS FOR CLIENT_SECRET_BASE64 ---")
    print(secret_encoded)
    print("------------------------------------------")
else:
    print("\n[!] client_secret.json not found.")

print("\nCopy these values and add them as Repository Secrets in your GitHub repo!")
