# app/scraper/form_filler.py
from playwright.sync_api import sync_playwright
from typing import Dict, Any

def auto_fill_and_submit(url, field_data: dict):
    """
    field_data = {
        "name": "Shaffan",
        "phone": "454554",
        "guests": "5",
        "time": "5pm"
    }
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)

        for key, value in field_data.items():
            try:
                # fill input by name or placeholder
                page.fill(f'input[name="{key}"]', value)
            except:
                try:
                    page.fill(f'input[placeholder*="{key}"]', value)
                except:
                    print(f"Could not fill field: {key}")

        # Try clicking submit
        try:
            page.click('button[type="submit"], input[type="submit"]')
            print("✅ Form submitted successfully!")
        except:
            print("⚠️ Could not find submit button")

        browser.close()
