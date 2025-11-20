import os
import re
import json
from typing import List, Dict, Any
import httpx  # Use httpx for async requests
from dotenv import load_dotenv

# ==========================================================
# Load environment variables
# ==========================================================
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY not found in .env")

# ==========================================================
# Groq Cloud Configuration
# ==========================================================
API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.1-8b-instant"  
HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

# Updated System Prompt to include interactive elements
SYSTEM_PROMPT = """
You are an expert AI assistant that determines the user's intent and extracts relevant parameters.

Based on the user's message, decide which action to take. The available actions are:
- "booking": If the user wants to book something.
- "search": If the user is asking a question that can be answered from the knowledge base or the provided webpage content.
- "click": If the user wants to click on a button or link. Use the 'selector' to identify the element.
- "fill_form": If the user wants to fill out a form. Use the 'selector' for each field.
- "extract": If the user wants to extract specific information from the current page.
- "reply": If the user is just making a statement or asking a simple question.

Return a JSON object with the following structure:
{
  "type": "action_type",
  "parameters": {
    "param1": "value1",
    ...
  }
}

Example for "click":
User message: "Click on the 'Contact Us' button."
{
  "type": "click",
  "parameters": {
    "selector": "#contact-us-button-selector"
  }
}

Example for "fill_form":
User message: "Fill the form with my name John Doe and email john.doe@example.com."
{
  "type": "fill_form",
  "parameters": {
    "fields": [
      {"selector": "#name-field-selector", "value": "John Doe"},
      {"selector": "#email-field-selector", "value": "john.doe@example.com"}
    ]
  }
}
"""

# ==========================================================
# MAIN DECISION FUNCTION
# ==========================================================
async def decide_action(
    prompt: str,
    page_content: str = "",
    interactive_elements: List[Dict[str, Any]] = None
) -> dict:
    
    dynamic_system_prompt = SYSTEM_PROMPT
    
    if page_content:
        dynamic_system_prompt += f"\nHere is the content of the current webpage in Markdown format:\n---\n{page_content[:4000]}\n---"

    if interactive_elements:
        # Simplified representation of interactive elements for the prompt
        elements_summary = [
            f"- Tag: '{el.get('tag')}', Text: '{el.get('text', '')[:50]}', Selector: '{el.get('selector')}'"
            for el in interactive_elements
        ]
        dynamic_system_prompt += f"\nHere is a list of interactive elements available on the page. Use their 'selector' to perform actions like 'click' or 'fill_form'.\n---\n{json.dumps(elements_summary[:20], indent=2)}
---"

    dynamic_system_prompt += "\nBased on the user message and the context, what is the next action? Return ONLY the JSON object."

    async with httpx.AsyncClient() as client:
        try:
            payload = {
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": dynamic_system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
            }

            response = await client.post(API_URL, headers=HEADERS, json=payload, timeout=60)

            if response.status_code != 200:
                print("❌ Groq API error:", response.text)
                return {"type": "reply", "parameters": {"message": "Sorry, I'm having trouble understanding you right now."}}

            data = response.json()
            raw_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            try:
                return json.loads(raw_text)
            except json.JSONDecodeError:
                return {"type": "reply", "parameters": {"message": "Sorry, I received an invalid response from the AI."}}

        except Exception as e:
            print("decide_action error:", e)
            return {"type": "reply", "parameters": {"message": "Sorry, an error occurred."}}

# ==========================================================
# RAW PROMPT FUNCTION (for structured tasks)
# ==========================================================
async def decide_action_raw(prompt: str) -> str:
    async with httpx.AsyncClient() as client:
        try:
            payload = {
                "model": MODEL_NAME,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
            }

            response = await client.post(API_URL, headers=HEADERS, json=payload, timeout=120)

            if response.status_code != 200:
                print("❌ Groq API error:", response.text)
                return ""

            data = response.json()
            raw_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return raw_text.strip()

        except Exception as e:
            print("decide_action_raw error:", e)
            return ""