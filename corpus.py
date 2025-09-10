import requests, json
from collections import defaultdict
from utils import _post, _get, _check_key

def corpora_list():
    return _get(f"{BASE}/corpora").json().get("corpora", [])
  
def corpora_delete(corpus_name, force=True):
    url = f"{BASE}/{corpus_name}"
    params = {"force": str(force).lower()}
    r = requests.delete(url, headers=HEADERS, params=params)
    r.raise_for_status()

def corpora_create(display_name, corpus_id=None):
    body = {"displayName": display_name}
    if corpus_id:
        body["name"] = f"corpora/{corpus_id}"
    r = _post(f"{BASE}/corpora", body)
    if r.status_code == 409:  # already exists
        for c in corpora_list():
            if (corpus_id and c["name"] == f"corpora/{corpus_id}") or c.get("displayName") == display_name:
                return c["name"]
        raise RuntimeError("Corpus exists but not found via list()")
    return r.json()["name"]

def documents_list(
        corpus_name, 
        BASE_API = "https://generativelanguage.googleapis.com/v1beta", 
        page_size=20
        ):
    url = f"{BASE_API}/corpora/{corpus_name}/documents"
    out, token = [], None
    while True:
        params = {"pageSize": page_size}
        if token:
            params["pageToken"] = token
        data = _get(url, params).json()
        out.extend(data.get("documents", []))
        token = data.get("nextPageToken")
        if not token:
            break
    return out

def documents_create(corpus_name, display_name, custom_metadata=None):
    body = {"displayName": display_name}
    if custom_metadata:
        body["customMetadata"] = custom_metadata
    return _post(f"{BASE}/{corpus_name}/documents", body).json()["name"]

def ensure_document(corpus_name, display_name, custom_metadata=None):
    for d in documents_list(corpus_name):
        if d.get("displayName") == display_name:
            return d["name"]
    return documents_create(corpus_name, display_name, custom_metadata)

def _mk_payload(items):
        return {"requests": [{
            "parent": document_name,
            "chunk": {
                "data": {"stringValue": it["stringValue"]},
                "customMetadata": it.get("customMetadata", [])
            }
        } for it in items]}

def chunks_batch_create(document_name, chunk_items, *, diagnose_tokens=False):
    url = f"{BASE}/{document_name}/chunks:batchCreate"

    for i in range(0, len(chunk_items), BATCH_SIZE):
        batch = chunk_items[i:i+BATCH_SIZE]
        try:
            _post(url, _mk_payload(batch))
        except requests.HTTPError as e:
            resp = e.response
            print(f"⚠️ batchCreate failed (HTTP {resp.status_code}) for batch {i}-{i+len(batch)-1}")
            try:
                print("Server says:", resp.text[:800])
            except Exception:
                pass

            # Fallback: find the bad item(s)
            print("→ Diagnosing items in this batch individually ...")
            for j, it in enumerate(batch, start=i):
                s = it["stringValue"]
                if not isinstance(s, str):
                    print(f"  ❌ item {j}: not a string")
                    continue
                if s.strip() == "":
                    print(f"  ❌ item {j}: empty/whitespace-only chunk")
                    continue
                bad_chars = [c for c in s if ord(c) < 9 or (11 <= ord(c) <= 12) or (14 <= ord(c) <= 31)]
                # (tab=9, lf=10, cr=13 are fine; others under 32 are suspicious)
                if bad_chars:
                    print(f"  ⚠️ item {j}: contains control chars {[hex(ord(c)) for c in bad_chars[:5]]} (showing up to 5)")

                # optional token count (costs API calls)
                tok = None
                if diagnose_tokens:
                    try:
                        tok = count_tokens(s)  # uses gemini-1.5-flash:countTokens
                    except Exception as ce:
                        tok = f"countTokens failed: {ce}"

                # Try uploading this single chunk to confirm failure
                try:
                    _post(url, _mk_payload([it]))
                except requests.HTTPError as e2:
                    print(f"  ❌ item {j} REJECTED")
                    print(f"     chars={len(s)} tokens={tok}")
                    print("     head:", s[:120].replace("\n"," ⏎ "))
                    print("     tail:", s[-120:].replace("\n"," ⏎ "))
                else:
                    print(f"  ✅ item {j} OK (chars={len(s)} tokens={tok})")

            # Stop here so you can fix the offending chunk(s) upstream
            raise

def build_lokalomat_corpus(jsonl_file):
    _check_key()

    corpus_name = corpora_create(CORPUS_DISPLAY_NAME, CORPUS_ID)
    print("Using corpus:", corpus_name)

    doc_by_party = {}
    pending = defaultdict(list)

    with jsonl_file.open("r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)

            # NFC everywhere (text + metadata)
            party   = nfc(rec["party"])
            section = nfc(rec.get("section", ""))
            text    = nfc(rec["text"])  # content unchanged except normalization

            if party not in doc_by_party:
                doc_by_party[party] = ensure_document(
                    corpus_name,
                    display_name=party,
                    custom_metadata=[
                        {"key": "party", "stringValue": party},
                        {"key": "city",  "stringValue": CITY},
                        {"key": "year",  "stringValue": YEAR},
                    ],
                )

            # one JSON record => one Chunk
            pending[doc_by_party[party]].append({
                "stringValue": text,
                "customMetadata": [
                    {"key": "party",   "stringValue": party},
                    {"key": "section", "stringValue": section},
                    {"key": "city",    "stringValue": CITY},
                    {"key": "year",    "stringValue": YEAR},
                ]
            })

    for doc_name, items in pending.items():
        print(f"Uploading {len(items)} chunks → {doc_name}")
        chunks_batch_create(doc_name, items)

    print("Done; corpus is ready.")
    return corpus_name
