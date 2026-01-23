import logging
from playwright.async_api import async_playwright
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def auto_fill_and_submit_async(target_url: str, field_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Navigates to the target URL, fills the form fields based on field_data,
    and attempts to submit the form.
    
    field_data: A dictionary where keys are selectors (or field names) and values are the values to fill.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            logger.info(f"Navigating to {target_url} for form filling...")
            await page.goto(target_url, wait_until="networkidle")
            
            filled_fields = []
            failed_fields = []
            
            for selector, value in field_data.items():
                try:
                    # Try to find the element by selector, name, or label
                    # This is a simplified approach; a more robust one would use the AI mapping logic
                    # But for this function, we assume keys are selectors or names
                    
                    # Check if it's a valid selector
                    element = page.locator(selector).first
                    if await element.count() == 0:
                         # Try searching by name attribute
                         element = page.locator(f"[name='{selector}']").first
                    
                    if await element.count() > 0:
                        await element.fill(str(value))
                        filled_fields.append(selector)
                    else:
                        failed_fields.append(selector)
                        logger.warning(f"Could not find field: {selector}")
                        
                except Exception as e:
                    failed_fields.append(selector)
                    logger.error(f"Error filling field {selector}: {e}")
            
            # Attempt to submit
            # Look for a submit button
            submit_button = page.locator("button[type='submit'], input[type='submit']").first
            if await submit_button.count() > 0:
                await submit_button.click()
                # Wait for navigation or some indication of success
                try:
                    await page.wait_for_load_state("networkidle", timeout=5000)
                except:
                    pass # Timeout is okay, maybe it didn't navigate
                
                success = True
                message = "Form submitted successfully."
            else:
                success = False
                message = "Could not find a submit button."
            
            return {
                "success": success,
                "message": message,
                "filled_fields": filled_fields,
                "failed_fields": failed_fields
            }
            
        except Exception as e:
            logger.error(f"Error in auto_fill_and_submit_async: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            await browser.close()