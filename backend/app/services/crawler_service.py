# backend/app/services/crawler_service.py
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
import logging

logger = logging.getLogger(__name__)

async def get_page_content_as_markdown(url: str) -> str:
    """
    Uses crawl4ai to fetch the fully rendered content of a given URL
    and return it in Markdown format.
    """
    if not url:
        return ""

    try:
        # Configure the crawler to use a headless browser and extract markdown
        # We can add more configurations here if needed, e.g., proxies, user agents
        browser_config = BrowserConfig(
            headless=True,
            # You might want to configure a specific user agent to avoid bot detection
            # user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"
        )
        async with AsyncWebCrawler() as crawler:
            logger.info(f"Crawling URL: {url}")
            result = await crawler.arun(url=url)
            
            if result and result.markdown:
                logger.info(f"Successfully crawled {url}, content length: {len(result.markdown)}")
                return result.markdown
            else:
                logger.warning(f"Crawl4AI returned no markdown content for {url}")
                return ""
    except Exception as e:
        logger.error(f"Error crawling URL {url} with crawl4ai: {e}")
        return ""

if __name__ == "__main__":
    # Example usage for testing
    async def test_crawler():
        test_url = "https://www.example.com" # Replace with a dynamic JS site for better testing
        content = await get_page_content_as_markdown(test_url)
        print(f"\n--- Content for {test_url} ---\n")
        print(content[:1000]) # Print first 1000 characters

    asyncio.run(test_crawler())
