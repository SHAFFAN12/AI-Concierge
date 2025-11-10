import os
import re
import json
import requests
from dotenv import load_dotenv

# ==========================================================
# Load environment variables
# ==========================================================
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY not found in .env")

# ==========================================================
# Groq Cloud Configuration (Updated)
# ==========================================================
API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.1-8b-instant"  
HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

SYSTEM_PROMPT = """
You are an expert AI assistant that determines the user's intent and extracts relevant parameters.

Based on the user's message, decide which action to take. The available actions are:
- "booking": If the user wants to book something (e.g., a table, an appointment).
- "search": If the user is asking a question that can be answered from the knowledge base.
- "reply": If the user is just making a statement or asking a simple question that doesn't require any action.

Return a JSON object with the following structure:
{
  "type": "action_type",
  "parameters": {
    "param1": "value1",
    "param2": "value2"
  }
}

For example:

User message: "book a table for 5 guests for 11 Novenmber 2025 at 9pm. My name is shaffan email address is sdsdd@mail.com and phone number is +925555444411."

{
  "type": "booking",
  "parameters": {
    "item": "table",
    "details": "for 5 guests on 11 November 2025 at 9pm",
    "name": "shaffan",
    "email": "sdsdd@mail.com",
    "phone": "+925555444411"
  }
}

User message: "what are the services you offer?"

{
  "type": "search",
  "parameters": {
    "query": "services offered"
  }
}

User message: "hello"

{
  "type": "reply",
  "parameters": {
    "message": "Hello! How can I help you today?"
  }
}
"""

# ==========================================================
# MAIN DECISION FUNCTION
# ==========================================================
async def decide_action(prompt: str) -> dict:
    try:
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }

        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)

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
    try:
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
        }

        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=120)

        if response.status_code != 200:
            print("❌ Groq API error:", response.text)
            return ""

        data = response.json()
        raw_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return raw_text.strip()

    except Exception as e:
        print("decide_action_raw error:", e)
        return ""
