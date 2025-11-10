import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from typing import Dict, Any

from selenium.common.exceptions import TimeoutException
import time

async def auto_fill_and_submit_async(url: str, field_data: Dict[str, str]) -> Dict:
    """
    Fills and submits a form on a given URL using Selenium.

    Args:
        url (str): The URL of the page with the form.
        field_data (dict): A dictionary where keys are field identifiers (name, id, placeholder)
                           and values are the data to be filled.
    """
    print(f"🚀 Starting auto_fill_and_submit_async for URL: {url} with data: {field_data}")

    # Run synchronous Selenium operations in a separate thread
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _sync_fill_and_submit, url, field_data)
    return result

import time
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

def _sync_fill_and_submit(url: str, field_data: Dict[str, str]) -> Dict:
    options = Options()
    # options.add_argument("--headless") # Disabled for debugging
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--dns-server=8.8.8.8")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = None
    try:
        print("Attempting to install/update ChromeDriver...")
        service = ChromeService(ChromeDriverManager(version="114.0.5735.90").install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(120) # Increased timeout
        print("WebDriver initialized.")

        for i in range(3): # Retry navigation 3 times
            try:
                driver.get(url)
                print(f"Navigated to {url}")
                break
            except TimeoutException:
                print(f"Timeout loading page, retrying... ({i+1}/3)")
                time.sleep(5)
        else:
            raise Exception("Failed to load page after 3 retries")

        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # Define a mapping from logical field names to actual HTML form field names/ids
        field_mapping = {
            "name": "name",
            "email": "email",
            "phone": "phone",
            "guests": "guests",
            "date": "date",
            "time": "time",
        }

        all_fields_filled = True
        for logical_key, value in field_data.items():
            filled = False
            # Get the actual HTML field name/id from the mapping, or use the logical key if not found
            html_field_name = field_mapping.get(logical_key, logical_key)
            try:
                # Construct a robust XPath to find the element using the mapped HTML field name
                xpath_selector = f"//*[@name='{html_field_name}' or @id='{html_field_name}' or @aria-label='{html_field_name}' or contains(@placeholder, '{html_field_name}')]"
                elements = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, xpath_selector))
                )

                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        tag_name = element.tag_name
                        if tag_name == "select":
                            from selenium.webdriver.support.ui import Select
                            select = Select(element)
                            try:
                                select.select_by_value(value)
                                print(f"✅ Selected option with value '{value}' in '{logical_key}'")
                                filled = True
                            except:
                                try:
                                    select.select_by_visible_text(value)
                                    print(f"✅ Selected option with text '{value}' in '{logical_key}'")
                                    filled = True
                                except:
                                    print(f"⚠️ Could not select '{value}' in '{logical_key}'")
                        elif tag_name in ["input", "textarea"]:
                            element.clear()
                            element.send_keys(value)
                            print(f"✅ Filled '{logical_key}' with '{value}'")
                            filled = True
                        
                        if filled:
                            break
            except Exception as e:
                print(f"❌ Error processing field '{logical_key}': {e}")

            if not filled:
                all_fields_filled = False
                print(f"⚠️ Could not find or fill field: {logical_key}")

        if not all_fields_filled:
            raise Exception("Could not fill all the required fields.")

        # More intelligent submit button finding
        try:
            submit_button_xpaths = [
                "//button[@type='submit']",
                "//input[@type='submit']",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit')]",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'book')]",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'confirm')]",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'send')]",
            ]
            
            submit_button = None
            for xpath in submit_button_xpaths:
                try:
                    button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    if button:
                        submit_button = button
                        break
                except:
                    continue

            if submit_button:
                driver.execute_script("arguments[0].click();", submit_button)
                print("✅ Form submitted successfully!")
                
                # Wait for potential navigation or confirmation
                time.sleep(5) 
                
                return {"status": "success", "message": "Form submitted."}
            else:
                raise Exception("Submit button not found")

        except Exception as e:
            print(f"⚠️ Could not find or click submit button: {e}")
            return {"status": "failed", "message": f"Could not find or click submit button: {e}"}

    except Exception as e:
        print(f"❌ An error occurred during Selenium automation: {e}")
        return {"status": "failed", "message": f"An error occurred: {e}"}
    finally:
        if driver:
            driver.quit()
            print("Browser closed.")

