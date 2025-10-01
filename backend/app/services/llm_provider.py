import os
import re
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_PROMPT = """
You are an intelligent AI concierge for a website.
Your goal is to understand the user's request and determine the best course of action.

You can choose one of three actions:
1.  **booking**: If the user wants to book an appointment, schedule a service, or make a reservation.
    - For booking, you must extract the 'item' to be booked and the 'details'.
2.  **search**: If the user is looking for information on the site.
    - For search, you must extract the 'query'.
3.  **reply**: If the request doesn't require booking/search, and you can provide a direct answer.

You must always return ONLY a JSON object with the following structure:
{
  "action_type": "booking" | "search" | "reply",
  "parameters": { ... },
  "reply_message": "..."
}

Here are some examples:

User: "book a ticket from karachi to lahore"
{
  "action_type": "booking",
  "parameters": {
    "item": "ticket",
    "details": "from Karachi to Lahore"
  },
  "reply_message": "I will book a ticket from Karachi to Lahore for you."
}

User: "I want to see a doctor"
{
  "action_type": "booking",
  "parameters": {
    "item": "appointment",
    "details": "with a doctor"
  },
  "reply_message": "I will book an appointment with a doctor for you."
}

User: "what is the weather like today?"
{
    "action_type": "search",
    "parameters": {
        "query": "weather today"
    },
    "reply_message": "I will search for the weather today."
}

User: "hello"
{
    "action_type": "reply",
    "parameters": {},
    "reply_message": "Hi there! How can I help you?"
}
"""

async def decide_action(user_input: str, session_id: str = "default", memory: dict = None) -> dict:
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")

        # Prepare conversation context
        conversation = SYSTEM_PROMPT
        if memory:
            conversation += f"\nPrevious conversation:\n{json.dumps(memory, indent=2)}"
        conversation += f"\nUser: {user_input}"

        # Call Gemini
        response = model.generate_content(conversation)

        raw_text = response.text.strip()
        print("RAW OUTPUT:", raw_text)

        # Clean markdown fences if present
        cleaned_text = re.sub(r"```(?:json)?", "", raw_text).strip("` \n")

        try:
            result = json.loads(cleaned_text)
            return {
                "type": result.get("action_type", "reply"),
                "params": result.get("parameters", {}),
                "message": result.get("reply_message", raw_text)
            }
        except json.JSONDecodeError:
            # Fallback if not valid JSON
            return {"type": "reply", "params": {}, "message": raw_text}

    except Exception as e:
        print(f"Error in decide_action: {e}")
        return {"type": "error", "params": {}, "message": "⚠️ I'm having trouble understanding your request."}
    

# inside app/services/llm_provider.py (add this function)
async def decide_action_raw(prompt: str) -> str:
    """
    Call Gemini/LLM with a raw prompt and return raw text.
    Use for structured extraction prompts.
    """
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        # pass simple string prompt (no system role)
        response = model.generate_content(f"{prompt}")
        raw_text = response.text or ""
        return raw_text.strip()
    except Exception as e:
        print("decide_action_raw error:", e)
        return ""

