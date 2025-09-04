def corpora_query(corpus_name, query, results_count=10, metadata_filters=None):
    body = {"query": query, "resultsCount": results_count}
    if metadata_filters:
        body["metadataFilters"] = metadata_filters
    return _post(f"{BASE}/{corpus_name}:query", body).json()["relevantChunks"]
