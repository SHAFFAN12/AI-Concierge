import logging
from playwright.async_api import async_playwright, Page, ElementHandle
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

async def perform_action(
    url: str, 
    action_type: str, 
    selector: Optional[str] = None, 
    value: Optional[str] = None,
    wait_for: Optional[str] = None
) -> Dict[str, Any]:
    """
    Performs a generic action on a website.
    
    Args:
        url: The URL to navigate to (or current URL if in a session - though this is stateless for now).
        action_type: One of "navigate", "click", "fill", "select", "hover", "scroll", "extract".
        selector: CSS or XPath selector for the target element.
        value: Value to fill/select, or attribute to extract.
        wait_for: Optional selector to wait for after action.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # In a real agentic loop, we'd want to persist context, but for now we launch fresh
        # This limits multi-step actions that depend on state, but fits the current architecture.
        # To improve, we'd need a persistent browser session manager.
        page = await browser.new_page()
        
        try:
            logger.info(f"Performing action '{action_type}' on {url}")
            
            # Always navigate first since we are stateless
            # Optimization: In the future, pass a browser_context_id to reuse sessions
            await page.goto(url, wait_until="networkidle")
            
            result = {"success": True, "message": "Action completed", "data": None}
            
            if action_type == "navigate":
                pass # Already done
                
            elif action_type == "click":
                if not selector:
                    raise ValueError("Selector required for click")
                await page.click(selector)
                
            elif action_type == "fill":
                if not selector or value is None:
                    raise ValueError("Selector and value required for fill")
                
                # Check if input has a value
                current_value = await page.input_value(selector)
                if current_value:
                    logger.info(f"Clearing existing value for selector: {selector}")
                    await page.fill(selector, "")
                
                await page.fill(selector, value)
                
            elif action_type == "select":
                if not selector or value is None:
                    raise ValueError("Selector and value required for select")
                await page.select_option(selector, value)
                
            elif action_type == "hover":
                if not selector:
                    raise ValueError("Selector required for hover")
                await page.hover(selector)
                
            elif action_type == "scroll":
                if selector:
                    element = page.locator(selector)
                    await element.scroll_into_view_if_needed()
                else:
                    # Scroll to bottom if no selector
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    
            elif action_type == "extract":
                if not selector:
                    # Extract full text if no selector
                    result["data"] = await page.content()
                else:
                    if value == "text" or value is None:
                        result["data"] = await page.inner_text(selector)
                    elif value == "html":
                        result["data"] = await page.inner_html(selector)
                    else:
                        # Extract attribute (e.g., "href", "src")
                        result["data"] = await page.get_attribute(selector, value)
            
            else:
                raise ValueError(f"Unknown action type: {action_type}")

            # Wait if requested
            if wait_for:
                await page.wait_for_selector(wait_for, timeout=5000)
                
            # If we clicked/filled, maybe wait for navigation?
            if action_type in ["click", "fill", "select"]:
                 try:
                     await page.wait_for_load_state("networkidle", timeout=2000)
                 except:
                     pass

            return result

        except Exception as e:
            logger.error(f"Error in perform_action: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
        finally:
            await browser.close()