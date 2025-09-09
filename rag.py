import requests, json
from typing import List, Dict, Any
from utils import get_api_key, get_headers, get_gen_model

GEN_API_KEY = get_api_key()

GEN_MODEL = get_gen_model()

GEN_URL   = f"https://generativelanguage.googleapis.com/v1beta/{GEN_MODEL}:generateContent"

HEADERS = get_headers()

def summarize_from_quotes(
        question: str, 
        quotes: List[Dict[str, Any]]
        ) -> str | None:
    if not quotes:
        return None

    # Build LLM context: include section next to each passage
    ctx_lines = []
    for i, q in enumerate(quotes, 1):
        sec = (q.get("section") or "").strip()
        if sec:
            ctx_lines.append(f"[{i}] (Section: {sec})\n{q['quote']}")
        else:
            ctx_lines.append(f"[{i}]\n{q['quote']}")
    context = "\n\n".join(ctx_lines)
    prompt = (
        "Deine Aufgabe ist es, die Position der Partei zur gestellten Frage anhand der Passagen im 'context' zusammenzufassen."
        "Gib im ersten Satz zunächst ein Kurzfazit: Beantworte dabei, wie das Parteiprogramm die gestellte Frage beantwortet."
        "Fasse die Passagen darin sehr knapp im Sinne der Frage zusammen."
        "Nehme dabei schon Bezug auf die Inhalte der Passagen. Beschränke dich auf die Punkte, die der Partei am wichtigsten zu sein scheinen."
        "Wenn nach bestimmten Orten oder Stadtteilen gefragt wird, schränke ein, wenn diese Orte nicht explizit erwähnt werden"
        "Das Kurzfazit sollte einem der folgenden 4 Muster folgen: Die Partei fordert [...], Die Partei gibt an [...], Die Partei möchte [...] oder Die Partei hat in ihrem Programm keine explizite Position zu [...]."
        "Falls die Passagen alle nicht zur Frage passen, erwähne im Kurzfazit nur, dass die Partei zur Frage keine explizite Position bezieht."
        "Ziehe niemals Schlussfolgerungen zu Parteipositionen aus dem Fehlen thematisch relevanter Passagen."
        "Fasse dann die konkreten, zur Frage passenden politischen Positionen und Forderungen innerhalb der jeweiligen Passagen zusammen."
        "Falls die Inhalte einer Passage keine direkte Relevanz zur gestellten Frage haben, ignoriere sie und fasse sie nicht zusammen."
        "Schreibe dann lediglich: Die anderen Passagen befassen sich nicht mit der Thematik. Füge in diesem Fall keinesfalls hinzu, womit sich diese irrelevante Passage befasst!"
        "Ordne die Passagen dabei nach Relevanz, sodass relevantere Passagen zuerst behandelt werden."
        "Wenn die Relevanz unklar ist, fasse die Passage zusammen um keine wichtigen Positionen auszulassen, aber betone zunächst, dass die Relevanz nicht eindeutig ist."
        "Die Zusammenfassungen sollen aus maximal 3 kurzen Sätzen bestehen. Sie dürfen keine Bullet Points oder ähnliches enthalten."
        "Vermeide aufzählende Sprachmuster. Verlagere lange Nebensätze lieber in einen eigenen Satz."
        "Wenn du eine Passage zusammenfasst, ordne sie explizit der jeweiligen Passagen zu. Folge dabei immer dem Muster 'Passage #:'. Verwende nie Klammern um die Passagen-Nummer."
        "Verwende in der Zusammenfassung immer den Titel der Section. Nutze Formulierungen wie 'Im Abschnitt <i>'Section'</i> des Parteiprogramms steht, dass ...' oder 'Die Passage <i>'Section'</i> erwähnt ...'."
        "Nutze immer Anführungszeichen und die Kursiv-Tags um die Titel der Sections."
        "Vermeide insbesondere im Kurzfazit verschachtelte Sätze. Halte die Sätze kurz und prägnant."
        "Nenne niemals Inhalte, die nicht in den Passagen stehen!"
        "Formatiere die Antwort in HTML: <p><strong>Kurzfazit:</strong></p> <p>…dein Text…</p> <p><strong>Passage 1:</strong></p> <p>…Text…</p> <p><strong>Passage 2:</strong></p> <p>…Text…</p>"
        f"\n\nFrage: {question}\n\nZitate:\n{context}\n\nAntwort:"
    )
    r = requests.post(
        GEN_URL,
        headers=HEADERS,
        data=json.dumps({
            "contents":[
                {"role":"user","parts":[{"text":prompt}]}
                ],
            "generationConfig": {
                "temperature": 0.1,         # default = 1.0
                # "maxOutputTokens": 300    # optional: cap the output length
        }
      })
    ).json()
    text = ""
    for c in r.get("candidates", []):
        for p in c.get("content", {}).get("parts", []):
            if "text" in p: text += p["text"]
    return text.strip() or None

def print_party_answers_with_summary(answers: List[dict], question: str):
    for a in answers:
        print(f"\n=== {a['party']} ===")
        if a["status"] != "ok":
            print(a["message"])
            continue
        summary = summarize_from_quotes(a["party"], question, a["quotes"])
        print("✅ Kurzfazit:", summary)
        for i, q in enumerate(a["quotes"], 1):
            print(f"[{i}] 🧾 Aus dem Kapitel: \"{q['section']}\" (score {q['score']})")
            print(f"    “{q['quote']}”")
