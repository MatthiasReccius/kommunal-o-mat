import requests, json

def summarize_from_quotes(party: str, question: str, quotes: List[dict], max_tokens=1040):
    if not quotes:
        return None
    context = "\n\n".join(f"[{i}] {q['quote']}" for i, q in enumerate(quotes, 1))
    prompt = (
        "Fasse die Passagen im 'context' zusammen."
        "Gib im ersten Satz zunächst ein Kurzfazit: Beantworte dabei, wie das Parteiprogramm die gestellte Frage beantwortet."
        "Fasse die Passagen knapp zusammen, sofern sie in einem klarem inhaltlichen Zusammenhang zur Frage stehen."
        "Nehme dabei schon Bezug auf die Inhalte der Passagen. Beschränke dich auf die Punkte, die der Partei am wichtigsten zu sein scheinen."
        "Wenn nach bestimmten Orten oder Stadtteilen gefragt wird, schränke ein, wenn diese Orte nicht explizit erwähnt werden"
        "Das Kurzfazit sollte einem der folgenden 4 Muster folgen: Die Partei fordert [...], Die Partei gibt an [...], Die Partei möchte [...] oder Die Partei hat in ihrem Programm keine explizite Position zu [...]."
        "Falls die Passagen alle nicht zur Frage passen, erwähne im Kurzfazit nur, dass die Partei zur Frage keine explizite Position bezieht."
        "Ziehe niemals Schlussfolgerungen zu Parteipositionen aus dem Fehlen thematisch relevanter Passagen."
        "Fasse dann die konkreten, zur Frage passenden politischen Positionen und Forderungen innerhalb der jeweiligen Passagen zusammen."
        "Die Zusammenfassungen sollen aus bis zu 3-4 ganzen Sätzen bestehen und keine Bullet Points oder ähnliches enthalten."
        "Ordne die Passagen dabei nach Relevanz, sodass relevantere Passagen zuerst behandelt werden."
        "Wenn du eine Passage zusammenfasst, ordne sie explizit der jeweiligen Passagen zu. Folge dabei immer dem Muster Passage [#]:"
        "Falls die Inhalte einer Passage keine direkte Relevanz zur gestellten Frage haben, ignoriere sie und fasse sie nicht zusammen."
        "Schreibe dann lediglich: Passage [#] befasst sich nicht mit der Thematik. Füge in diesem Fall keinesfalls hinzu, womit sich diese irrelevante Passage befasst!"
        "Wenn die Relevanz unklar ist, fasse die Passage zusammen um keine wichtigen Positionen auszulassen, aber betone zunächst, dass die Relevanz nicht eindeutig ist."
        "Nenne niemals Inhalte, die nicht in den Passagen stehen!"
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
