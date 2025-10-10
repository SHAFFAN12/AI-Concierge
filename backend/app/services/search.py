from app.services.rag_service import search_documents

async def run_search(params: dict) -> dict:
    query = params.get("query", "")
    results = search_documents(query)
    
    if results:
        answer = "\n".join(results)
    else:
        answer = "Sorry, I couldn’t find any information about that."
    
    return {"status": "ok", "note": answer}
