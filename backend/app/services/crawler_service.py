# backend/app/services/crawler_service.py
import asyncio
import httpx
import html2text
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, SeedingConfig, AsyncUrlSeeder
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, BestFirstCrawlingStrategy
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

async def get_page_content_as_markdown(url: str, max_retries: int = 3, js_code: Optional[str] = None, wait_for: Optional[str] = None) -> str:
    """
    Uses crawl4ai to fetch the fully rendered content of a given URL
    and return it in Markdown format with retry logic and better error handling.
    Falls back to a simple HTTP request if crawl4ai fails.
    """
    if not url:
        logger.warning("Empty URL provided to crawler")
        return ""

    # Validate URL
    if not url.startswith(('http://', 'https://')):
        logger.error(f"Invalid URL format: {url}")
        return ""

    try:
        logger.info(f"Crawling URL with crawl4ai: {url}")
        browser_config = BrowserConfig(
            headless=True,
            verbose=False,
            stealth=True,
            use_undetected_browser=True,
            extra_args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            js_code=js_code,
            page_timeout=60000,
            delay_before_return_html=5.0,
            remove_overlay_elements=True,
            screenshot=False,
            wait_for_images=True,
            scan_full_page=True,
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=url, config=run_config)
            
            if result.success and result.markdown:
                logger.info(f"Successfully crawled {url} with crawl4ai")
                return result.markdown
            else:
                raise Exception(f"Crawl4ai failed: {result.error_message}")

    except Exception as e:
        logger.warning(f"crawl4ai failed for {url}: {e}. Falling back to httpx.")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, follow_redirects=True, timeout=30)
                response.raise_for_status()
                html = response.text
                h = html2text.HTML2Text()
                h.ignore_links = True
                markdown = h.handle(html)
                logger.info(f"Successfully fetched {url} with httpx.")
                return markdown
        except httpx.HTTPStatusError as http_err:
            logger.error(f"HTTP error fetching {url} with httpx: {http_err}")
            return f"Error: Failed to fetch the page with status code {http_err.response.status_code}."
        except Exception as http_e:
            logger.error(f"Error fetching {url} with httpx: {http_e}")
            return f"Error: Failed to fetch the page with httpx."


async def get_page_content_with_elements(url: str, js_code: Optional[str] = None, wait_for: Optional[str] = None) -> dict:
    """
    Enhanced version that returns both markdown content and structured data.
    """
    if not url or not url.startswith(('http://', 'https://')):
        return {"error": "Invalid URL", "content": "", "html": ""}
    
    try:
        markdown = await get_page_content_as_markdown(url, js_code=js_code, wait_for=wait_for)
        if markdown.startswith("Error:"):
            return {"success": False, "error": markdown}
            
        return {
            "success": True,
            "url": url,
            "markdown": markdown,
            "html": "",  # html is not available in the fallback
            "links": [],
            "media": [],
            "metadata": {}
        }
                
    except Exception as e:
        logger.error(f"Error in get_page_content_with_elements for {url}: {e}")
        return {
            "success": False,
            "error": str(e),
            "url": url
        }

async def deep_crawl_website(url: str, max_depth: int = 2, max_pages: int = 10) -> List[dict]:
    """
    Performs a deep crawl on a website up to a max_depth and max_pages.
    """
    try:
        browser_config = BrowserConfig(
            headless=True,
            verbose=False,
            stealth=True,
            use_undetected_browser=True,
        )
        
        strategy = BFSDeepCrawlStrategy(max_depth=max_depth, max_pages=max_pages)
        
        async with AsyncWebCrawler(config=browser_config, crawl_strategy=strategy) as crawler:
            results = await crawler.acrawl(url=url)
            return results
    except Exception as e:
        logger.error(f"Error in deep_crawl_website for {url}: {e}")
        return [{"success": False, "error": str(e), "url": url}]

async def seed_and_crawl_website(url: str, query: str) -> List[dict]:
    """
    Uses URL seeding to find relevant URLs from a sitemap and then crawls them.
    """
    try:
        seeder_config = SeedingConfig(
            url_regex=[f".*{query}.*"],
            max_pages=10
        )

        async with AsyncUrlSeeder(config=seeder_config) as seeder:
            urls = await seeder.aseed(url)

        browser_config = BrowserConfig(
            headless=True,
            verbose=False,
            stealth=True,
            use_undetected_browser=True,
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            results = await crawler.acrawl_many(urls=urls)
            return results
    except Exception as e:
        logger.error(f"Error in seed_and_crawl_website for {url}: {e}")
        return [{"success": False, "error": str(e), "url": url}]


async def adaptive_crawl_website(url: str, query: str) -> List[dict]:
    """
    Performs an adaptive crawl on a website using a query.
    """
    try:
        browser_config = BrowserConfig(
            headless=True,
            verbose=False,
            stealth=True,
            use_undetected_browser=True,
        )

        scorer = KeywordRelevanceScorer(keywords=[query])
        strategy = BestFirstCrawlingStrategy(
            scorer=scorer,
            score_threshold=0.5,
            max_pages=5
        )

        async with AsyncWebCrawler(config=browser_config, crawl_strategy=strategy) as crawler:
            results = await crawler.acrawl(url=url)
            return results
    except Exception as e:
        logger.error(f"Error in adaptive_crawl_website for {url}: {e}")
        return [{"success": False, "error": str(e), "url": url}]


if __name__ == "__main__":
    # Example usage for testing
    async def test_crawler():
        test_url = "https://www.example.com" # Replace with a dynamic JS site for better testing
        content = await get_page_content_as_markdown(test_url)
        print(f"\n--- Content for {test_url} ---\n")
        print(content[:1000]) # Print first 1000 characters

    asyncio.run(test_crawler())
