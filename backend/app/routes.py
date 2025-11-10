# app/routes.py
import re
import json
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.services.llm_provider import decide_action
from app.services.parse_booking import extract_booking_params
from app.services.memory import get_memory, add_message
from app.services.search import run_search
from app.services.scraper_service import analyze_website_forms, ai_map_fields
from app.scrapper.form_filler_async import auto_fill_and_submit_async
from app.db import save_booking

from bson import ObjectId
from typing import Optional, Dict, Any # Added Dict, Any for type hints


router = APIRouter()

class ChatRequest(BaseModel):
    user_id: str
    message: str
    current_url: Optional[str] = None
    domain: Optional[str] = None


@router.post("/chat")
async def chat_endpoint(req: Request):
    # ... (chat_endpoint function remains the same as provided by you)
    # ... (Action dispatch logic remains the same)
    
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
            await handle_booking_action(request, result, site_id) # The key call

        elif action_type == "search":
            result = await run_search(plan.get("params", {}))

        elif action_type == "reply":
            result = {"status": "ok", "note": plan.get("message") or plan.get("reply_message") or ""}

        else:
            result = {"status": "unknown", "note": plan.get("message") or str(plan)}

    except Exception as e:
        print("❌ Error in chat flow:", e)
        result = {"status": "failed", "error": str(e)}

    # 4️⃣ Save chat memory 
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
    # ... (get_or_create_site function remains the same)
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
    if not request.current_url:
        result.update({"status": "failed", "error": "Current URL is required for booking."})
        return

    try:
        booking_data = await extract_booking_params(request.message)
        if not booking_data:
            raise ValueError("Could not extract any booking details from the message.")
        print(f"📝 Extracted booking data: {booking_data}")
    except Exception as e:
        print(f"❌ Error extracting booking params: {e}")
        result.update({"status": "failed", "error": f"Could not understand booking details: {e}"})
        return

    try:
        from app.db import db
        site = await db["sites"].find_one({"_id": ObjectId(site_id)})
        site_url = site.get("url") if site else request.current_url

        forms = await analyze_website_forms(site_url)
        if not forms:
            raise ValueError("No forms found on the page to fill.")
        print(f"📄 Scraped {len(forms)} forms from {site_url}")

        mapped_fields = await ai_map_fields(forms, booking_data)
        if not mapped_fields:
            raise ValueError("AI could not map booking data to any form fields.")
        print(f"🔗 AI Mapped fields: {mapped_fields}")

        submission_result = await auto_fill_and_submit_async(site_url, mapped_fields)
        form_submitted = submission_result.get("status") == "success"
        
        if form_submitted:
            print("✅ Form submission successful on the target website.")
            # Save booking to our database
            booking_data.update({
                "user_id": request.user_id,
                "site_id": site_id,
                "form_submitted": True,
                "submitted_data": mapped_fields
            })
            await save_booking(booking_data)
            print("💾 Booking details saved to local DB.")
            result.update({
                "status": "success",
                "note": "Booking successful!",
                "booking_details": booking_data,
            })
        else:
            print("⚠️ Form submission failed on the target website.")
            booking_data.update({"form_submitted": False})
            result.update({
                "status": "failed",
                "note": "Booking failed.",
                "booking_details": booking_data,
            })

    except Exception as e:
        print(f"❌ Error in booking action: {e}")
        result.update({"status": "failed", "error": str(e)})