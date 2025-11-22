# backend/app/services/crawler_service.py
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
import logging
from typing import Optional

logger = logging.getLogger(__name__)

async def get_page_content_as_markdown(url: str, max_retries: int = 3) -> str:
    """
    Uses crawl4ai to fetch the fully rendered content of a given URL
    and return it in Markdown format with retry logic and better error handling.
    """
    if not url:
        logger.warning("Empty URL provided to crawler")
        return ""

    # Validate URL
    if not url.startswith(('http://', 'https://')):
        logger.error(f"Invalid URL format: {url}")
        return ""

    for attempt in range(max_retries):
        try:
            logger.info(f"Crawling URL (attempt {attempt + 1}/{max_retries}): {url}")
            
            # Configure browser with realistic settings
            browser_config = BrowserConfig(
                headless=True,
                verbose=False,
                extra_args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox"
                ]
            )
            
            # Configure crawler run settings
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,  # Always fetch fresh content
                wait_for="networkidle",  # Wait for network to be idle
                page_timeout=30000,  # 30 second timeout
                delay_before_return_html=2.0,  # Wait 2 seconds for JS to render
                remove_overlay_elements=True,  # Remove popups/overlays
                screenshot=False,  # Don't take screenshots for performance
            )
            
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(
                    url=url,
                    config=run_config
                )
                
                if result.success and result.markdown:
                    content_length = len(result.markdown)
                    logger.info(f"Successfully crawled {url}, content length: {content_length}")
                    
                    # Basic content validation
                    if content_length < 50:
                        logger.warning(f"Content seems too short ({content_length} chars), may be incomplete")
                    
                    return result.markdown
                    
                elif result.error_message:
                    logger.error(f"Crawl4AI error for {url}: {result.error_message}")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying in 2 seconds...")
                        await asyncio.sleep(2)
                        continue
                else:
                    logger.warning(f"Crawl4AI returned no markdown content for {url}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)
                        continue
                        
        except asyncio.TimeoutError:
            logger.error(f"Timeout crawling {url} (attempt {attempt + 1})")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
                continue
        except Exception as e:
            logger.error(f"Error crawling URL {url} (attempt {attempt + 1}): {type(e).__name__}: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
                continue
    
    logger.error(f"Failed to crawl {url} after {max_retries} attempts")
    return ""


async def get_page_content_with_elements(url: str) -> dict:
    """
    Enhanced version that returns both markdown content and structured data.
    """
    if not url or not url.startswith(('http://', 'https://')):
        return {"error": "Invalid URL", "content": "", "html": ""}
    
    try:
        logger.info(f"Crawling URL with full data: {url}")
        
        browser_config = BrowserConfig(
            headless=True,
            verbose=False,
            extra_args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage"
            ]
        )
        
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_for="networkidle",
            page_timeout=30000,
            delay_before_return_html=2.0,
            remove_overlay_elements=True,
            screenshot=False,
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=url, config=run_config)
            
            if result.success:
                return {
                    "success": True,
                    "url": url,
                    "markdown": result.markdown or "",
                    "html": result.html or "",
                    "links": result.links.get("internal", [])[:20] if result.links else [],  # First 20 links
                    "media": result.media.get("images", [])[:10] if result.media else [],  # First 10 images
                    "metadata": {
                        "title": getattr(result, 'title', ''),
                        "description": getattr(result, 'description', ''),
                    }
                }
            else:
                return {
                    "success": False,
                    "error": result.error_message or "Unknown error",
                    "url": url
                }
                
    except Exception as e:
        logger.error(f"Error in get_page_content_with_elements for {url}: {e}")
        return {
            "success": False,
            "error": str(e),
            "url": url
        }

if __name__ == "__main__":
    # Example usage for testing
    async def test_crawler():
        test_url = "https://www.example.com" # Replace with a dynamic JS site for better testing
        content = await get_page_content_as_markdown(test_url)
        print(f"\n--- Content for {test_url} ---\n")
        print(content[:1000]) # Print first 1000 characters

    asyncio.run(test_crawler())
