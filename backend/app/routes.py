# app/routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.llm_provider import decide_action  # existing
from app.services.parse_booking import extract_booking_params
from app.services.booking_google import run_google_booking
from app.db import save_chat
from app.services.memory import get_memory, add_message
from app.services.search import run_search

router = APIRouter()

class ChatRequest(BaseModel):
    user_id: str
    message: str
    site_id: str = None

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # conversation history (memory)
    history = get_memory(request.user_id)

    # Ask the LLM for a plan (your decide_action should return a dict with type/message/params)
    plan = await decide_action(request.message)  # keep signature consistent with your existing function

    result = {"status": "no_action"}
    try:
        # support multiple key names
        action_type = plan.get("type") or plan.get("action_type") or plan.get("action") or "reply"

        if action_type == "booking":
            params = plan.get("params", {}) or {}

            # If LLM didn't supply a datetime/text, run structured extractor
            if not (params.get("text") or params.get("datetime_text") or params.get("when")):
                booking_params = await extract_booking_params(request.message)
                params.update(booking_params)

            # Prepare normalized params for Google booking
            booking_call_params = {
                "text": params.get("datetime_text") or params.get("text") or request.message,
                "summary": params.get("summary") or f"Appointment ({params.get('doctor_name') or params.get('specialty') or 'Consult'})",
                "attendee_emails": params.get("attendee_emails", []),
                "calendar_id": params.get("calendar_id")
            }

            result = await run_google_booking(booking_call_params)

        elif action_type == "search":
            result = await run_search(plan.get("params", {}))
        elif action_type == "reply":
            result = {"status": "ok", "note": plan.get("message") or plan.get("reply_message") or ""}
        else:
            result = {"status": "unknown", "note": plan.get("message") or str(plan)}

    except Exception as e:
        result = {"status": "failed", "error": str(e)}

    # persist chat and update memory
    await save_chat(request.user_id, request.message, plan, result, request.site_id)
    add_message(request.user_id, "user", request.message)
    add_message(request.user_id, "assistant", result.get("note") or result.get("status"))

    response = {
        "ok": True,
        "plan": plan,
        "result": result
    }

    # Simple autofill example
    if "my name is" in request.message.lower():
        name = request.message.lower().split("my name is")[-1].strip()
        response["action"] = {
            "type": "autofill",
            "payload": {
                "selector": "#name", # A common ID for a name field
                "value": name.title()
            }
        }

    return response
