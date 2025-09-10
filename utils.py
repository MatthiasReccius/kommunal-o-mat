import requests, json, unicodedata, re, os

def _check_key():
    if not GEMINI_API_KEY:
        raise RuntimeError("Set GOOGLE_API_KEY in your environment")

def _post(url, body):
    r = requests.post(url, headers=HEADERS, data=json.dumps(body))
    if r.status_code == 409: # request not completed due to conflict with target 
        return r  # caller may handle conflicts
    r.raise_for_status()
    return r

def require_env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v

def get_api_key() -> str:
    return require_env("GENAI_API_KEY")

def get_gen_model() -> str:
    return require_env("GEN_MODEL")

def get_headers() -> dict:
    return {
        "Content-Type": "application/json",
        "x-goog-api-key": get_api_key(),
    }

GEN_API_KEY = get_api_key()

HEADERS = {
    "Content-Type": "application/json",
    "x-goog-api-key": GEN_API_KEY,
}

def _get(url, params=None):
    r = requests.get(url, headers=HEADERS, params=params or {})
    r.raise_for_status()
    return r

def count_tokens(text: str, model: str = "models/gemini-2.0-flash") -> int:
    # Eigentlich möchte ich Token-Anzahl für das Embedding-Modell embedding-001
    # Annahme: embedding-001 und gemini-2.0-flash teilen sich Tokenizer
    """Fragt bei Google ab, wie viele Tokens der Text hat."""
    url = f"{BASE}/{model}:countTokens"
    body = {"contents": [{"role":"user","parts":[{"text": text}]}]}
    r = requests.post(url, headers=HEADERS, data=json.dumps(body))
    r.raise_for_status()
    return r.json().get("totalTokens", 0)

def _norm(s: str) -> str:
    # NFC normalization to avoid "Grüne" vs "Grüne" issues
    return unicodedata.normalize("NFC", s).strip()

# Get metadata associated with chunk (party, section, ...)
def _meta_get(meta_list, key, default="—"):
    if not isinstance(meta_list, list):
        return default
    for m in meta_list:
        if m.get("key") == key:
            return m.get("stringValue") or m.get("numericValue") or default
    return default

def normalize_question(q: str) -> str:
    """Normalize Unicode and collapse whitespace in a free-text question."""
    q = unicodedata.normalize("NFC", q or "")
    q = re.sub(r"\s+", " ", q).strip()
    return q
