def _check_key():
    if not GEMINI_API_KEY:
        raise RuntimeError("Set GOOGLE_API_KEY in your environment")

def _post(url, body):
    r = requests.post(url, headers=HEADERS, data=json.dumps(body))
    if r.status_code == 409: # request not completed due to conflict with target 
        return r  # caller may handle conflicts
    r.raise_for_status()
    return r

def _get(url, params=None):
    r = requests.get(url, headers=HEADERS, params=params or {})
    r.raise_for_status()
    return r
