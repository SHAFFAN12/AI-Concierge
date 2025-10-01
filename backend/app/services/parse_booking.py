# app/services/parse_booking.py
import re
import json
from typing import Dict
from app.services.llm_provider import decide_action_raw

PROMPT = """
Extract booking details from the following user text. Return ONLY valid JSON (no extra text) with keys:
{
  "doctor_name": null,          # or string
  "specialty": null,            # or string
  "datetime_text": "Friday at 3pm",  # natural language date/time (preferred)
  "duration_minutes": 30,
  "attendee_emails": []
}

If you cannot find a doctor name or specialty set that field to null.
If you cannot parse a specific datetime, set "datetime_text" to the original text.
User text: >>>{user_text}<<<
"""

async def extract_booking_params(user_text: str) -> Dict:
    prompt = PROMPT.format(user_text=user_text)
    raw = await decide_action_raw(prompt)

    # remove markdown fences
    cleaned = re.sub(r"```(?:json)?", "", raw).strip("` \n")
    try:
        parsed = json.loads(cleaned)
        # normalize keys
        return {
            "doctor_name": parsed.get("doctor_name"),
            "specialty": parsed.get("specialty"),
            "datetime_text": parsed.get("datetime_text") or parsed.get("datetime") or user_text,
            "duration_minutes": parsed.get("duration_minutes", 30),
            "attendee_emails": parsed.get("attendee_emails", []),
        }
    except Exception:
        # fallback: keep user text as datetime_text
        return {
            "doctor_name": None,
            "specialty": None,
            "datetime_text": user_text,
            "duration_minutes": 30,
            "attendee_emails": [],
        }
