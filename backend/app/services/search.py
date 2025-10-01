# from playwright.async_api import async_playwright

# async def run_search(params: dict):
#     query = params.get("query")
#     if not query:
#         return {"status": "failed", "error": "No search query provided."}

#     search_url = f"https://example.com/search?q={query}"

#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=True)
#         try:
#             page = await browser.new_page()
#             await page.goto(search_url)

#             results = await page.locator(".search-result").all_inner_texts()

#             return {"status": "success", "results": results[:5]}
#         except Exception as e:
#             return {"status": "failed", "error": str(e)}
#         finally:
#             await browser.close()





from app.services.rag_service import search_documents

async def run_search(params: dict) -> dict:
    query = params.get("query", "")
    results = search_documents(query)
    
    if results:
        answer = "\n".join(results)
    else:
        answer = "Sorry, I couldn’t find any information about that."
    
    return {"status": "ok", "note": answer}
