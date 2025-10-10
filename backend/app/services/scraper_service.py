# app/services/scraper_service.py
import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict
from app.services.llm_provider import decide_action_raw

async def analyze_website_forms(url: str) -> List[Dict]:
    """
    Scrape all forms from a page and return fields dynamically.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()

    soup = BeautifulSoup(html, "html.parser")
    forms = []
    for form in soup.find_all("form"):
        fields = []
        for inp in form.find_all(["input", "textarea", "select"]):
            field_info = {
                "name": inp.get("name"),
                "id": inp.get("id"),
                "type": inp.get("type", "text"),
                "label": None  # optionally map label
            }
            label_tag = soup.find("label", {"for": inp.get("id")}) if inp.get("id") else None
            if label_tag:
                field_info["label"] = label_tag.text.strip()
            fields.append(field_info)
        forms.append({"action": form.get("action"), "method": form.get("method", "post"), "fields": fields})
    return forms

async def ai_map_fields(forms: List[Dict], booking_data: Dict) -> Dict:
    """
    Map booking_data keys to form fields dynamically using an LLM.
    """
    prompt = f"""I have booking data: {booking_data}
    I have found these forms on the website: {forms}
    Please map the booking data to the correct form fields and return a JSON object with the mapped fields.
    For example, if the booking data is {{"name": "John Doe"}} and the form field is <input name="full_name">, the result should be {{"full_name": "John Doe"}}.
    """
    mapped_fields_str = await decide_action_raw(prompt)
    try:
        mapped_fields = eval(mapped_fields_str)
    except:
        mapped_fields = {}
    return mapped_fields

async def autofill_and_submit_form(url: str, mapped_fields: Dict[str, str]) -> Dict:
    """
    Dynamically fills and submits form using mapped fields.
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
        if key in mapped_fields:
            payload[key] = mapped_fields[key]
        else:
            payload[key] = inp.get("value", "")

    action = form.get("action") or url
    method = form.get("method", "post").lower()

    if method == "post":
        async with session.post(action, data=payload) as resp:
            return {"status": "success" if resp.status==200 else "failed", "code": resp.status}
    else:
        async with session.get(action, params=payload) as resp:
            return {"status": "success" if resp.status==200 else "failed", "code": resp.status}