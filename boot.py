import os, sys, traceback
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/__boot")
def boot_info():
    return {
        "python": sys.version,
        "port_env": os.getenv("PORT"),
        "corpus_name": os.getenv("CORPUS_NAME"),
        "gen_model": os.getenv("GEN_MODEL"),
        "genai_api_key_len": len(os.getenv("GENAI_API_KEY") or "")
    }

try:
    print("BOOT: importing serve.main:app …", flush=True)
    from serve.main import app as real_app
    app = real_app
    print("BOOT: imported serve.main:app OK", flush=True)
except Exception:
    print("BOOT: FAILED importing serve.main", flush=True)
    traceback.print_exc()  # <-- exact stack in Cloud Run logs
    # keep serving the minimal app so you can inspect /__boot

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")), workers=1)
