from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List
from retrieval import answer_per_party_strict
from rag import summarize_from_quotes
import os, sys

# Damit der Import der Funktionen aus dem Hauptverzeichnis klappt:
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

app = FastAPI()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# Liste der verfügbaren Parteien (alle werden vorausgewählt)
ALL_PARTIES = ["SPD", "CDU", "Grüne", "Linke", "AfD", "FDP", "Die PARTEI"]

# Konfiguration des Corpus-Pfads/Names (ggf. anpassen oder über Umgebungsvariable setzen)
CORPUS_NAME = os.environ["CORPUS_NAME"]

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
def submit_question(request: Request, 
                    question: str = Form(...), 
                    parties: List[str] = Form(...)):
    """Verarbeitet die Formular-Eingabe und zeigt die Ergebnisse an (POST /)."""
    # Zitate pro Partei abrufen (für jede gewählte Partei relevante Textstellen finden)
    answers = answer_per_party_strict(CORPUS_NAME, question, parties, k_retrieve=5, max_quotes=5)
    # Für jede Partei ggf. eine Zusammenfassung der Zitate erzeugen:contentReference[oaicite:1]{index=1}
    for ans in answers:
        if ans.get("status") == "ok":
            summary_text = summarize_from_quotes(question, ans["quotes"], ans["section"])
            ans["summary"] = summary_text
        # Bei status "no_info": ans["message"] enthält bereits den Hinweistext:contentReference[oaicite:2]{index=2}

    # Template mit den Ergebnissen rendern
    return templates.TemplateResponse("index.html", {
        "request": request,
        "parties": ALL_PARTIES,
        "selected_parties": parties,
        "question": question,
        "answers": answers
    })

# Optionale Startmöglichkeit mit uvicorn, falls main.py direkt ausgeführt wird
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
