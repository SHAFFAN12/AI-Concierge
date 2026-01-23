# backend/app/services/crawler_service.py
import httpx
import html2text
import asyncio
import logging
from typing import Optional, List
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, BestFirstCrawlingStrategy
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer

logger = logging.getLogger(__name__)

async def get_page_content_as_markdown(url: str, js_code: Optional[str] = None, wait_for: Optional[str] = None) -> str:
    """
    Uses crawl4ai to fetch the fully rendered content of a given URL
    and return it in Markdown format. Falls back to httpx if it fails.
    """
    if not url or not url.startswith(('http://', 'https://')):
        logger.error(f"Invalid URL format: {url}")
        return ""

    try:
        logger.info(f"Crawling URL with crawl4ai: {url}")
        browser_config = BrowserConfig(
            headless=True,
            verbose=False,
            extra_args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            js_code=js_code,
            page_timeout=60000,
            wait_for=wait_for,
            remove_overlay_elements=True,
            scan_full_page=True,
        )
        
        # AsyncWebCrawler must use 'async with'
        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Use 'arun' instead of 'run' for async
            result = await crawler.arun(url=url, config=run_config)
            
            if result.success and result.markdown:
                logger.info(f"Successfully crawled {url}")
                return result.markdown
            else:
                raise Exception(f"Crawl4ai failed: {result.error_message}")

    except Exception as e:
        logger.warning(f"crawl4ai failed for {url}: {e}. Falling back to httpx.")
        return await _fallback_httpx(url)

async def _fallback_httpx(url: str) -> str:
    """Helper for httpx fallback logic."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True, timeout=30)
            response.raise_for_status()
            h = html2text.HTML2Text()
            h.ignore_links = True
            return h.handle(response.text)
    except Exception as e:
        logger.error(f"Httpx fallback failed: {e}")
        return f"Error: Failed to fetch the page."

async def get_page_content_with_elements(url: str, js_code: Optional[str] = None, wait_for: Optional[str] = None) -> dict:
    """Returns markdown content and metadata."""
    markdown = await get_page_content_as_markdown(url, js_code=js_code, wait_for=wait_for)
    if markdown.startswith("Error:"):
        return {"success": False, "error": markdown, "url": url}
            
    return {
        "success": True,
        "url": url,
        "markdown": markdown,
        "metadata": {}
    }

async def deep_crawl_website(url: str, max_depth: int = 2, max_pages: int = 10) -> List[dict]:
    """Performs a deep crawl using BFS Strategy."""
    try:
        browser_config = BrowserConfig(headless=True)
        strategy = BFSDeepCrawlStrategy(max_depth=max_depth, max_pages=max_pages)
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Note: Deep crawling in modern crawl4ai is integrated into arun/acrawl
            results = await crawler.arun(url=url, crawl_strategy=strategy)
            return results if isinstance(results, list) else [results]
    except Exception as e:
        logger.error(f"Deep crawl error: {e}")
        return [{"success": False, "error": str(e), "url": url}]

async def seed_and_crawl_website(url: str, query: str) -> List[dict]:
    """
    Discovery version. Since UrlSeeder is not in current crawl4ai, 
    this uses a best-effort adaptive crawl as a replacement.
    """
    return await adaptive_crawl_website(url, query)

async def adaptive_crawl_website(url: str, query: str) -> List[dict]:
    """Performs an adaptive crawl based on keyword relevance."""
    try:
        browser_config = BrowserConfig(headless=True)
        scorer = KeywordRelevanceScorer(keywords=[query])
        strategy = BestFirstCrawlingStrategy(
            scorer=scorer,
            score_threshold=0.5,
            max_pages=5
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            results = await crawler.arun(url=url, crawl_strategy=strategy)
            return results if isinstance(results, list) else [results]
    except Exception as e:
        logger.error(f"Adaptive crawl error: {e}")
        return [{"success": False, "error": str(e), "url": url}]

if __name__ == "__main__":
    async def test_crawler():
        test_url = "https://www.example.com"
        content = await get_page_content_as_markdown(test_url)
        print(f"\n--- Content for {test_url} ---\n")
        print(content[:500])

    asyncio.run(test_crawler())