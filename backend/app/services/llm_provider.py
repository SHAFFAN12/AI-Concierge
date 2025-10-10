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
MODEL_NAME = "llama-3.1-8b-instant"  # ✅ Updated model
HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

SYSTEM_PROMPT = """
You are an intelligent AI concierge for a website.
You can take actions: booking, search, or reply.

You must return ONLY JSON with this structure:
{
  "action_type": "booking" | "search" | "reply",
  "parameters": {...},
  "reply_message": "..."
}

Examples:
User: "book a ticket from Karachi to Lahore"
{
  "action_type": "booking",
  "parameters": {"item": "ticket", "details": "from Karachi to Lahore"},
  "reply_message": "I will book a ticket from Karachi to Lahore for you."
}
"""

# ==========================================================
# MAIN DECISION FUNCTION
# ==========================================================
async def decide_action(user_input: str, session_id: str = "default", memory: dict = None) -> dict:
    try:
        # Build conversation prompt
        conversation = SYSTEM_PROMPT
        if memory:
            conversation += f"\nPrevious conversation:\n{json.dumps(memory, indent=2)}"
        conversation += f"\nUser: {user_input}"

        # Send request to Groq Cloud
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input}
            ],
            "temperature": 0.3,
        }

        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)

        if response.status_code != 200:
            print("❌ Groq API error:", response.text)
            return {"type": "error", "params": {}, "message": f"Groq API error: {response.text}"}

        data = response.json()
        raw_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        print("RAW OUTPUT:", raw_text)

        # Clean markdown or code block fences
        cleaned_text = re.sub(r"```(?:json)?", "", raw_text).strip("` \n")

        try:
            result = json.loads(cleaned_text)
            return {
                "type": result.get("action_type", "reply"),
                "params": result.get("parameters", {}),
                "message": result.get("reply_message", raw_text)
            }
        except json.JSONDecodeError:
            # fallback if not valid JSON
            return {"type": "reply", "params": {}, "message": raw_text}

    except Exception as e:
        print("Error in decide_action:", e)
        return {"type": "error", "params": {}, "message": "⚠️ I'm having trouble understanding your request."}


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

        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)

        if response.status_code != 200:
            print("❌ Groq API error:", response.text)
            return ""

        data = response.json()
        raw_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return raw_text.strip()

    except Exception as e:
        print("decide_action_raw error:", e)
        return ""
