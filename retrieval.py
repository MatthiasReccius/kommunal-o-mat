from utils import normalize_question

def _validate_question(q: str, min_len: int, max_len: int) -> str | None:
    if len(q) < min_len:
        return f"Die Frage ist zu kurz (min. {min_len} Zeichen)."
    if len(q) > max_len:
        return f"Die Frage ist zu lang (max. {max_len} Zeichen)."
    return None
    
def corpora_query(corpus_name, query, results_count=10, metadata_filters=None):
    body = {"query": query, "resultsCount": results_count}
    if metadata_filters:
        body["metadataFilters"] = metadata_filters
    return _post(f"{BASE}/{corpus_name}:query", body).json()["relevantChunks"]

def map_party_to_doc(corpus_name: str):
    docs = documents_list(corpus_name)
    by_norm = { _norm(d["displayName"]): d["name"] for d in docs }
    party_map = { _norm(d["displayName"]): d["displayName"] for d in docs }
    return by_norm, party_map

def retrieve_party_hits(corpus_name: str, party_name: str, question: str, k: int = 5):
    docs_map, party_map = map_party_to_doc(corpus_name)
    party_path = docs_map.get(_norm(party_name))
    if not party_path:
        return [], party_name  # unknown party label
    # Use corpora_query instead of documents_query
    hits = corpora_query(party_path, question, results_count=k)
    return hits, party_map[_norm(party_name)]

#### Build grounded answers ----
def build_party_answer_from_hits(
    hits: list, 
    question: str, 
    party_display: str,
    max_quotes: int = 3, 
    min_chars: int = 40
    ) -> dict:
    """
    Returns:
      {
        'party': ..., 'status': 'ok'|'no_info',
        'quotes': [
           {'section': str, 'score': float, 'quote': str, 'highlights': [{'start':..,'end':..}]}
        ]
      }
    """
    quotes = []
    for h in hits:
        chunk = h.get("chunk", {})
        text  = ((chunk.get("data") or {}).get("stringValue") or "")
        if not text.strip():
            continue
        section = _meta_get(chunk.get("customMetadata"), "section")
        score   = float(h.get("chunkRelevanceScore", 0.0))

        quotes.append({
            "section": section,
            "score": round(score, 3),
            "quote": text
        })
        if len(quotes) >= max_quotes:
            break

    if not quotes:
        return {
            "party": party_display,
            "status": "no_info",
            "message": f"Das Programm der Partei {party_display} enthält keine eindeutig relevanten Passagen zur Frage."
        }

    return {
        "party": party_display,
        "status": "ok",
        "quotes": quotes
    }

#### Collect per-party quotes ----
# k_retrieve != max_quotes only makes sense if post-retrival re-ranking occurs
def answer_per_party_strict(
    corpus_name: str, 
    question: str, 
    parties: List[str],
    k_retrieve: int = 3, 
    max_quotes: int = 3
    ):
    results = []
    for p in parties:
        hits, party_map = retrieve_party_hits(corpus_name, p, question, k=k_retrieve)
        results.append(
            build_party_answer_from_hits(hits, question, party_map, max_quotes=max_quotes)
        )
    return results
