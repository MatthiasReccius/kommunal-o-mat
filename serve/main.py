from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from typing import List
import os, sys

# Damit Import der Funktionen aus dem Hauptverzeichnis klappt:
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
from retrieval import answer_per_party_strict
from rag import summarize_from_quotes

app = FastAPI()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# Optional: Statische Dateien mounten, falls serve/static genutzt wird
# from fastapi.staticfiles import StaticFiles
# app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

# Liste der verfügbaren Parteien (alle werden vorausgewählt)
ALL_PARTIES = ["Partei A", "Partei B", "Partei C", "..."]  # Platzhalter-Namen anpassen

# (Optional) Konfiguration des Corpus-Pfads/Names
CORPUS_NAME = "mein_corpus"  # Platzhalter: den tatsächlichen Corpus-Namen oder Pfad eintragen

@app.get("/", response_class=HTMLResponse)
def form_page(request: Request):
    # Initiales Laden der Seite mit Formular, alle Parteien vorausgewählt
    return templates.TemplateResponse("index.html", {
        "request": request,
        "parties": ALL_PARTIES,
        "selected_parties": ALL_PARTIES,  # alle Checkboxen standardmäßig angehakt
        "question": ""  # keine vorbefüllte Frage
    })

@app.post("/", response_class=HTMLResponse)
def submit_question(request: Request, 
                    question: str = Form(...), 
                    parties: List[str] = Form(...)):
    # Aufruf der Kernfunktion: Zitate pro Partei abrufen
    answers = answer_per_party_strict(CORPUS_NAME, question, parties, k_retrieve=5, max_quotes=5)
    # Für jede Partei ggf. Zusammenfassung erzeugen
    for ans in answers:
        if ans.get("status") == "ok":
            summary_text = summarize_from_quotes(ans["party"], question, ans["quotes"])
            ans["summary"] = summary_text
        # Bei status "no_info": ans["message"] enthält bereits den Hinweis-Text:contentReference[oaicite:6]{index=6}

    # Rendern des Templates mit den Ergebnissen
    return templates.TemplateResponse("index.html", {
        "request": request,
        "parties": ALL_PARTIES,
        "selected_parties": parties,
        "question": question,
        "answers": answers
    })

# (Optional) Manuelle Startmöglichkeit für uvicorn, z.B. bei direktem Aufruf von main.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
