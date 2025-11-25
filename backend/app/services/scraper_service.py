# app/services/scraper_service.py
from playwright.async_api import async_playwright
from typing import List, Dict, Any
import json
import re

from app.services.llm_provider import decide_action_raw
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def get_interactive_elements_with_crawl4ai(url: str) -> List[Dict[str, Any]]:
    """
    Uses crawl4ai to navigate to a URL and extract all interactive elements,
    including buttons, links, and form fields.
    """
    
    # JavaScript to be executed in the browser context to extract elements
    extraction_js = """() => {
        const interactive_elements = [];
        
        // Function to create a unique CSS selector
        const create_selector = (element) => {
            if (element.id) {
                return `#${element.id}`;
            }
            let path = '';
            while (element.parentElement) {
                let sibling_index = 1;
                let sibling = element.previousElementSibling;
                while (sibling) {
                    if (sibling.nodeName === element.nodeName) {
                        sibling_index++;
                    }
                    sibling = sibling.previousElementSibling;
                }
                const tag_name = element.nodeName.toLowerCase();
                const path_segment = `${tag_name}:nth-of-type(${sibling_index})`;
                path = path_segment + (path ? ' > ' + path : '');
                element = element.parentElement;
            }
            return path;
        };

        // Find all potential interactive elements
        document.querySelectorAll(
            'a, button, input, textarea, select, [role="button"], [onclick]'
        ).forEach(el => {
            const selector = create_selector(el);
            const tag_name = el.tagName.toLowerCase();
            
            let element_data = {
                selector: selector,
                tag: tag_name,
                text: el.innerText || el.value || '',
                aria_label: el.getAttribute('aria-label'),
                id: el.id,
                name: el.name,
                type: el.type,
                placeholder: el.placeholder,
                href: el.href,
            };
            
            interactive_elements.push(element_data);
        });
        return interactive_elements;
    }"""

    try:
        browser_config = BrowserConfig(
            headless=True,
            stealth=True,
            use_undetected_browser=True
        )
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            js_code=extraction_js,
            page_timeout=60000,
            delay_before_return_html=5.0
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=url, config=run_config)
            if result.success and result.extracted_data:
                return result.extracted_data
            elif result.error_message:
                print(f"Error getting interactive elements from {url} with crawl4ai: {result.error_message}")
                return []
            else:
                return []

    except Exception as e:
        print(f"Error getting interactive elements from {url} with crawl4ai: {e}")
        return []


async def get_interactive_elements(url: str) -> List[Dict[str, Any]]:
    """
    Uses Playwright to navigate to a URL and extract all interactive elements,
    including buttons, links, and form fields.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url)
            
            # Use page.evaluate to run JavaScript in the browser context
            elements = await page.evaluate("""() => {
                const interactive_elements = [];
                
                // Function to create a unique CSS selector
                const create_selector = (element) => {
                    if (element.id) {
                        return `#${element.id}`;
                    }
                    let path = '';
                    while (element.parentElement) {
                        let sibling_index = 1;
                        let sibling = element.previousElementSibling;
                        while (sibling) {
                            if (sibling.nodeName === element.nodeName) {
                                sibling_index++;
                            }
                            sibling = sibling.previousElementSibling;
                        }
                        const tag_name = element.nodeName.toLowerCase();
                        const path_segment = `${tag_name}:nth-of-type(${sibling_index})`;
                        path = path_segment + (path ? ' > ' + path : '');
                        element = element.parentElement;
                    }
                    return path;
                };

                // Find all potential interactive elements
                document.querySelectorAll(
                    'a, button, input, textarea, select, [role="button"], [onclick]'
                ).forEach(el => {
                    const selector = create_selector(el);
                    const tag_name = el.tagName.toLowerCase();
                    
                    let element_data = {
                        selector: selector,
                        tag: tag_name,
                        text: el.innerText || el.value || '',
                        aria_label: el.getAttribute('aria-label'),
                        id: el.id,
                        name: el.name,
                        type: el.type,
                        placeholder: el.placeholder,
                        href: el.href,
                    };
                    
                    interactive_elements.push(element_data);
                });
                return interactive_elements;
            }""",)

            await browser.close()
            return elements

        except Exception as e:
            await browser.close()
            print(f"Error getting interactive elements from {url}: {e}")
            return []

async def analyze_website_forms(url: str) -> List[Dict]:
    """
    Scrape all forms from a page and return fields dynamically.
    This function is kept for now but could be merged with get_interactive_elements.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url)
            
            forms = []
            for form_element in await page.locator('form').all():
                form_details = {
                    "action": await form_element.get_attribute('action'),
                    "method": await form_element.get_attribute('method') or 'post',
                    "fields": [],
                }
                
                # Inputs
                for field in await form_element.locator('input, textarea, select').all():
                    tag = await field.evaluate('element => element.tagName.toLowerCase()')
                    field_info = {
                        "tag": tag,
                        "name": await field.get_attribute('name'),
                        "id": await field.get_attribute('id'),
                        "type": await field.get_attribute('type') or 'text',
                        "placeholder": await field.get_attribute('placeholder'),
                        "label": await field.evaluate('el => el.labels ? el.labels[0].innerText : null'),
                    }
                    if tag == 'select':
                        field_info['options'] = await field.evaluate('el => Array.from(el.options).map(o => ({value: o.value, text: o.innerText}))')
                    
                    form_details['fields'].append(field_info)
                
                forms.append(form_details)

            await browser.close()
            return forms

        except Exception as e:
            await browser.close()
            print(f"Error analyzing forms on {url}: {e}")
            return []


async def ai_map_fields(forms: List[Dict], booking_data: Dict) -> Dict:
    """
    Map booking_data keys to form fields dynamically using an LLM.
    """
    if not forms:
        return {}

    form_details_for_prompt = []
    for i, form in enumerate(forms):
        form_details_for_prompt.append(f"Form #{i+1}:")
        for field in form.get("fields", []):
            details = f"  - Field: name='{field.get('name')}', id='{field.get('id')}', type='{field.get('type')}'"
            if field.get("label"):
                details += f", label='{field.get('label')}'"
            if field.get('placeholder'):
                details += f", placeholder='{field.get('placeholder')}'"
            if field.get('aria-label'):
                details += f", aria-label='{field.get('aria-label')}'"
            if field.get("options"):
                options_str = ", ".join([f"{opt['text']}({opt['value']})" for opt in field["options"]])
                details += f", options=[{options_str}]"
            form_details_for_prompt.append(details)

    forms_str = "\n".join(form_details_for_prompt)

    prompt = f"""
You are an expert AI assistant. Map user's booking information to the correct fields of a web form.

User's booking data:
{json.dumps(booking_data, indent=2)}

Available forms on the website:
{forms_str}

Instructions:
1. Match user's data to form fields using 'name', 'id', 'label', 'placeholder', 'aria-label'.
2. For `<select>` fields, choose the appropriate `value` from the provided `options` list.
3. For `radio` buttons, select the `value` that matches the user's intent.
4. For `checkbox` fields, use `true` if the user's intent implies checking it, otherwise `false`.
5. Return only a JSON object mapping form field keys to user data.
6. Include only fields you are confident about.

Example:
{{
  "name": "John Doe",
  "email": "john.doe@example.com",
  "phone": "1234567890",
  "guests": "2",
  "date": "2025-12-25",
  "time": "18:00"
}}

Provide only the JSON mapping object.
"""

    mapped_fields_str = await decide_action_raw(prompt)

    try:
        cleaned_str = re.sub(r"```json|```", "", mapped_fields_str).strip()
        mapped_fields = json.loads(cleaned_str)
    except (json.JSONDecodeError, TypeError):
        try:
            mapped_.fields = eval(cleaned_str)
        except Exception:
            mapped_fields = {}

    return mapped_fields