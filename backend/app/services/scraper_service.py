# app/services/scraper_service.py
import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict
from app.services.llm_provider import decide_action_raw
import re
import json
from urllib.parse import urljoin

async def analyze_website_forms(url: str) -> List[Dict]:
    """
    Scrape all forms from a page and return fields dynamically.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                html = await response.text()
    except aiohttp.ClientError as e:
        print(f"Error fetching URL {url}: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    forms = []
    for form in soup.find_all("form"):
        fields = []
        for inp in form.find_all(["input", "textarea", "select"]):
            field_info = {
                "name": inp.get("name"),
                "id": inp.get("id"),
                "type": inp.get("type", "text"),
                "placeholder": inp.get("placeholder"),
                "value": inp.get("value"),
                "aria-label": inp.get("aria-label"),
                "label": None,
                "options": []
            }

            # 1. Find label by 'for' attribute
            if inp.get("id"):
                label_tag = soup.find("label", {"for": inp.get("id")})
                if label_tag:
                    field_info["label"] = label_tag.text.strip()

            # 2. If no label, find by wrapping label
            if not field_info["label"]:
                parent_label = inp.find_parent("label")
                if parent_label:
                    field_info["label"] = parent_label.text.strip()

            # 3. If it's a select, get options
            if inp.name == "select":
                field_info["options"] = [
                    {"value": opt.get("value"), "text": opt.text.strip()}
                    for opt in inp.find_all("option")
                ]

            fields.append(field_info)
        forms.append({
            "action": form.get("action"),
            "method": form.get("method", "post").lower(),
            "fields": fields
        })
    return forms


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

    # Fix for SyntaxError: join first, then use variable in f-string
    forms_str = "\n".join(form_details_for_prompt)

    prompt = f"""
You are an expert AI assistant. Map user's booking information to the correct fields of a web form.

User's booking data:
{json.dumps(booking_data, indent=2)}

Available forms on the website:
{forms_str}

Instructions:
1. Match user's data to form fields using 'name', 'id', 'label', 'placeholder', 'aria-label'.
2. For <select> fields, use the 'value' of the option matching user's data.
3. Return only a JSON object mapping form field keys to user data.
4. Include only fields you are confident about.

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
        # Clean the response and parse JSON
        cleaned_str = re.sub(r"```json|```", "", mapped_fields_str).strip()
        mapped_fields = json.loads(cleaned_str)
    except (json.JSONDecodeError, TypeError):
        try:
            mapped_fields = eval(cleaned_str)
        except Exception:
            mapped_fields = {}

    return mapped_fields


async def autofill_and_submit_form(url: str, mapped_fields: Dict[str, str]) -> Dict:
    """
    Dynamically fills and submits a form using mapped fields.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()

        soup = BeautifulSoup(html, "html.parser")
        form = soup.find("form")
        if not form:
            return {"status": "failed", "message": "No form found"}

        payload = {}
        for inp in form.find_all(["input", "textarea", "select"]):
            key = inp.get("name") or inp.get("id")
            if not key:
                continue
            if key in mapped_fields:
                payload[key] = mapped_fields[key]
            else:
                payload[key] = inp.get("value", "")

        action = form.get("action") or url
        action = urljoin(url, action)  # Resolve relative URL
        method = form.get("method", "post").lower()

        try:
            if method == "post":
                async with session.post(action, data=payload) as resp:
                    return {"status": "success" if resp.status == 200 else "failed", "code": resp.status}
            else:
                async with session.get(action, params=payload) as resp:
                    return {"status": "success" if resp.status == 200 else "failed", "code": resp.status}
        except aiohttp.ClientError as e:
            return {"status": "failed", "message": str(e)}
