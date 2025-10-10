import re
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.services.llm_provider import decide_action
from app.services.parse_booking import extract_booking_params
from app.services.memory import get_memory, add_message
from app.services.search import run_search
from app.services.scraper_service import analyze_website_forms, ai_map_fields
from app.scrapper.form_filler_async import auto_fill_and_submit_async

from bson import ObjectId
from typing import Optional


router = APIRouter()

class ChatRequest(BaseModel):
    user_id: str
    message: str
    current_url: Optional[str] = None
    domain: Optional[str] = None



@router.post("/chat")
async def chat_endpoint(req: Request):
    """
    Main chat route — handles AI actions like booking, search, or reply.
    This version submits booking **directly to the website's form**, no local DB storage.
    """
    # to solve 422 error, we first log the request body
    body = await req.json()
    print("Received request body:", body)
    
    try:
        request = ChatRequest(**body)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    history = get_memory(request.user_id)
    plan = await decide_action(request.message)
    result = {"status": "no_action"}
    site_id = None

    try:
        action_type = plan.get("type") or plan.get("action_type") or plan.get("action") or "reply"

        if action_type == "booking":
            print("🚀 Booking flow triggered with:", request.message)
            site_id = await get_or_create_site(request.current_url)
            await handle_booking_action(request, result, site_id)

        elif action_type == "search":
            result = await run_search(plan.get("params", {}))

        elif action_type == "reply":
            result = {"status": "ok", "note": plan.get("message") or plan.get("reply_message") or ""}

        else:
            result = {"status": "unknown", "note": plan.get("message") or str(plan)}

    except Exception as e:
        print("❌ Error in chat flow:", e)
        result = {"status": "failed", "error": str(e)}

    # 4️⃣ Save chat memory only (optional, local)
    from app.db import save_chat
    await save_chat(request.user_id, request.message, plan, result, site_id=site_id)
    add_message(request.user_id, "user", request.message)
    add_message(request.user_id, "assistant", result.get("note") or result.get("status"))

    return {
        "ok": True,
        "plan": plan,
        "result": result
    }

async def get_or_create_site(url: str) -> str:
    """Get or create a site in the database."""
    if not url:
        return None
    from app.db import db
    site = await db["sites"].find_one({"url": url})
    if site:
        return str(site["_id"])
    else:
        result = await db["sites"].insert_one({"url": url})
        return str(result.inserted_id)

async def handle_booking_action(request: ChatRequest, result: dict, site_id: str):
    booking_data = await extract_booking_params(request.message)

    form_submitted = False
    site_url = None
    action_payload = None

    if site_id:
        from app.db import db
        site = await db["sites"].find_one({"_id": ObjectId(site_id)})
        if site:
            site_url = site.get("url")

            # 🔍 Scrape forms dynamically
            forms = await analyze_website_forms(site_url)
            mapped_fields = await ai_map_fields(forms, booking_data)

            # 🧠 Build selectors for frontend autofill
            def build_selector(field):
                if field.get("name"):
                    return f'input[name="{field["name"]}"], textarea[name="{field["name"]}"], select[name="{field["name"]}"]'
                if field.get("id"):
                    return f'#{field["id"]}'
                if field.get("placeholder"):
                    return f'input[placeholder*="{field["placeholder"]}"], textarea[placeholder*="{field["placeholder"]}"]'
                return None

            fields_for_frontend = []
            for form in forms:
                for inp in form.get("fields", []):
                    for key, value in mapped_fields.items():
                        if key.lower() in (
                            inp.get("name", "").lower(),
                            inp.get("id", "").lower(),
                            inp.get("label", "").lower(),
                        ):
                            sel = build_selector(inp)
                            if sel:
                                fields_for_frontend.append({"selector": sel, "value": value})

            if not fields_for_frontend:
                for key, value in mapped_fields.items():
                    fields_for_frontend.append({
                        "selector": f'input[name*="{key}"i], input[id*="{key}"i]',
                        "value": value,
                    })

            # 🚀 Server-side submission
            submission_result = await auto_fill_and_submit_async(site_url, mapped_fields)
            form_submitted = submission_result.get("status") == "success"

            # Save for caching
            await db["sites"].update_one(
                {"_id": site["_id"]},
                {"$set": {"scraper_config": forms}}
            )

            # 🎯 Prepare action for frontend
            action_payload = {
                "type": "autofill",
                "payload": {
                    "fields": fields_for_frontend,
                    "submitted_on_server": form_submitted,
                },
            }

    result.update({
        "status": "success" if form_submitted else "failed",
        "booking_saved_on_website": form_submitted,
        "booking_details": booking_data,
        "action": action_payload,
    })
