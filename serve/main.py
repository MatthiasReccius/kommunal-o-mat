from dotenv import load_dotenv
load_dotenv()
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import List
# from retrieval import answer_per_party_strict
# from rag import summarize_from_quotes
from pathlib import Path
import os, sys
import uvicorn


# Damit der Import der Funktionen aus dem Hauptverzeichnis klappt:
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

app = FastAPI()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# Liste der verfügbaren Parteien (alle werden vorausgewählt)
ALL_PARTIES = ["SPD", "CDU", "Grüne", "Linke", "AfD", "FDP", "Die PARTEI"]

# Konfiguration des Corpus-Pfads/Names (ggf. anpassen oder über Umgebungsvariable setzen)
CORPUS_NAME = os.getenv("CORPUS_NAME")

@app.get("/", response_class=HTMLResponse)
def form_page(request: Request):
    """Zeigt das Formular für die Fragen-Eingabe an (GET /)."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "parties": ALL_PARTIES,
        "selected_parties": ALL_PARTIES,  # alle Checkboxen standardmäßig angehakt
        "question": ""   # keine vorbefüllte Frage
    })

@app.post("/", response_class=HTMLResponse)
def submit_question(
    request: Request, 
    question: str = Form(...), 
    parties: List[str] = Form(...)
):
    """Verarbeitet die Formular-Eingabe und zeigt die Ergebnisse an (POST /)."""
    # 1) Parallel retrieval (already inside answer_per_party_strict)
    from retrieval import answer_per_party_strict
    from rag import summarize_from_quotes

    answers = answer_per_party_strict(CORPUS_NAME, question, parties, k_retrieve=5, max_quotes=5)

    # 2) Parallel summarization per party (only for status == "ok" with quotes)
    idxs_to_sum = [i for i,a in enumerate(answers) if a.get("status") == "ok" and a.get("quotes")]
    if idxs_to_sum:
        # Be kind to quotas/rate limits
        max_workers = min(len(idxs_to_sum), 8)

        def _summarize(i: int):
            a = answers[i]
            try:
                # If your summarize_from_quotes supports a max_tokens param, add it here for speed:
                # s = summarize_from_quotes(question, a["quotes"], max_tokens=240)
                s = summarize_from_quotes(question, a["quotes"])
                return (i, s, None)
            except Exception as e:
                return (i, None, str(e))

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futs = [pool.submit(_summarize, i) for i in idxs_to_sum]
            for fut in as_completed(futs):
                i, s, err = fut.result()
                if err:
                    answers[i]["summary_status"] = "error"
                    answers[i]["summary_error"] = err
                else:
                    answers[i]["summary"] = s

    for a in answers:
        party = a.get("party") or ""
        slug  = LOGO_SLUG.get(party)
        fname = _find_logo_filename(slug) if slug else None
        if fname:
            a["logo_url"] = request.url_for("static", path=f"logos/{fname}")
            a["logo_is_pdf"] = fname.lower().endswith(".pdf")
        else:
            a["logo_url"] = None
            a["logo_is_pdf"] = False

    party_logo_urls = {}
    for p in ALL_PARTIES:
        slug = LOGO_SLUG.get(p)
        fname = _find_logo_filename(slug) if slug else None
        url = request.url_for("static", path=f"logos/{fname}") if fname else None
        party_logo_urls[p] = url if url and not fname.lower().endswith(".pdf") else None

    # 3) Render
    return templates.TemplateResponse("index.html", {
        "request": request,
        "parties": ALL_PARTIES,
        "selected_parties": parties,
        "question": question,
        "answers": answers,
        "party_logo_urls": party_logo_urls,
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("serve.main:app", host="0.0.0.0", port=port, workers=1)


app.mount("/static", StaticFiles(directory="static"), name="static")

LOGO_SLUG = {
    "AfD": "afd",
    "CDU": "cdu",
    "Die Partei": "diepartei",
    "FDP": "fdp",
    "Grüne": "gruene",
    "Linke": "linke",
    "SPD": "spd",
}
_IMG_EXTS = [".svg", ".png", ".webp", ".jpg", ".jpeg", ".gif"]
_ALL_EXTS = _IMG_EXTS + [".pdf"]

def _find_logo_filename(slug: str) -> str | None:
    base = Path("static/logos")
    if not slug: 
        return None
    # 1) exact slug + preferred extensions
    for ext in _ALL_EXTS:
        p = base / f"{slug}{ext}"
        if p.exists():
            return p.name
    # 2) fuzzy: any file containing slug (case-insensitive)
    slug_flat = slug.replace("-", "").lower()
    cand = []
    for p in base.glob("*"):
        if p.is_file():
            stem_flat = p.stem.replace("-", "").lower()
            if slug_flat in stem_flat:
                cand.append(p)
    if not cand:
        return None
    # prefer image extensions over pdf
    def _rank(p): 
        ext = p.suffix.lower()
        return (_ALL_EXTS.index(ext) if ext in _ALL_EXTS else 999, len(p.name))
    cand.sort(key=_rank)
    return cand[0].name
