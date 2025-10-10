# app/scrapper/form_filler_async.py
print("✅ Loading form_filler_async.py")
from playwright.async_api import async_playwright
from typing import Dict, Any

async def auto_fill_and_submit_async(url, field_data: dict):
    """
    Fills and submits a form on a given URL using Playwright.

    Args:
        url (str): The URL of the page with the form.
        field_data (dict): A dictionary where keys are field identifiers (name, id, placeholder)
                           and values are the data to be filled.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url)
            print(f"Navigated to {url}")

            for key, value in field_data.items():
                filled = False
                # Try to fill by name, id, or placeholder for input and textarea
                for selector_type in ['name', 'id', 'placeholder']:
                    for element_type in ['input', 'textarea']:
                        try:
                            selector = f'{element_type}[{selector_type}*="{key}"i]'
                            await page.fill(selector, value, timeout=1000)
                            print(f"Filled '{key}' in {element_type} with selector {selector_type}")
                            filled = True
                            break
                        except Exception:
                            continue
                    if filled:
                        break
                
                if not filled:
                    # Try to select an option in a select element
                    try:
                        selector = f'select[name*="{key}"i], select[id*="{key}"i]'
                        await page.select_option(selector, value, timeout=1000)
                        print(f"Selected '{value}' in select for '{key}'")
                        filled = True
                    except Exception:
                        pass

                if not filled:
                    print(f"⚠️ Could not fill field: {key}")

            # Try clicking a submit button
            try:
                await page.click('button[type="submit"], input[type="submit"]', timeout=2000)
                print("✅ Form submitted successfully!")
            except Exception:
                print("⚠️ Could not find or click submit button")

        except Exception as e:
            print(f"❌ An error occurred: {e}")
        finally:
            await browser.close()
            print("Browser closed.")
