# app/routes.py
import re
import json
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.llm_provider import decide_action
from app.services.parse_booking import extract_booking_params
from app.services.search import run_search
from app.services.scraper_service import get_interactive_elements, ai_map_fields
from app.scrapper.form_filler_async import auto_fill_and_submit_async
from app.db import save_booking
from app.services.crawler_service import get_page_content_as_markdown

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []
    current_url: Optional[str] = None
    domain: Optional[str] = None

@router.post("/chat")
async def chat_endpoint(req: ChatRequest):
    
    # 1. Get page content and interactive elements
    page_content = await get_page_content_as_markdown(req.current_url)
    interactive_elements = await get_interactive_elements(req.current_url)
    
    # 2. Get AI's next action
    plan = await decide_action(
        prompt=req.message,
        page_content=page_content,
        interactive_elements=interactive_elements
    )
    
    result = {"status": "no_action", "plan": plan}
    action_type = plan.get("type") or plan.get("action_type") or plan.get("action") or "reply"

    # 3. Execute the action
    try:
        if action_type == "booking":
            await handle_booking_action(req, result)

        elif action_type == "search":
            result.update(await run_search(plan.get("parameters", {})))

        elif action_type == "click":
            # The frontend will handle the click, we just provide the selector
            result.update({
                "status": "action",
                "action": {
                    "type": "click",
                    "selector": plan.get("parameters", {}).get("selector")
                },
                "note": f"Clicking on element with selector: {plan.get('parameters', {}).get('selector')}"
            })

        elif action_type == "fill_form":
             # The frontend will handle filling the form, we just provide the instructions
            result.update({
                "status": "action",
                "action": {
                    "type": "fill_form",
                    "fields": plan.get("parameters", {}).get("fields")
                },
                "note": "Please fill the form with the provided details."
            })
        
        elif action_type == "reply":
            result.update({
                "status": "ok",
                "note": plan.get("parameters", {}).get("message")
            })

        else:
            result.update({"status": "unknown", "note": "Could not determine the action to take."})

    except Exception as e:
        print(f"❌ Error executing action '{action_type}': {e}")
        result.update({"status": "failed", "error": str(e)})

    return result


async def handle_booking_action(request: ChatRequest, result: dict):
    if not request.current_url:
        result.update({"status": "failed", "error": "Current URL is required for booking."})
        return

    try:
        booking_data = await extract_booking_params(request.message)
        if not booking_data:
            raise ValueError("Could not extract any booking details from the message.")

        # Re-using the get_interactive_elements to get form details
        # In a future refactor, this could be more efficient
        elements = await get_interactive_elements(request.current_url)
        forms = [el for el in elements if el.get('tag') == 'form']

        if not forms:
            raise ValueError("No forms found on the page to fill.")

        mapped_fields = await ai_map_fields(forms, booking_data)
        if not mapped_fields:
            raise ValueError("AI could not map booking data to any form fields.")

        # This part needs to be adapted for the new frontend-driven action
        # For now, we assume the first form is the target
        form_selector = forms[0].get('selector')
        
        # We are not submitting from the backend anymore. 
        # The plan should be to tell the frontend what to fill and where.
        
        fill_instructions = []
        for field_name, value in mapped_fields.items():
            # Find the selector for the field
            field_selector = None
            for form in forms:
                for field in form.get('fields', []):
                    if field.get('name') == field_name or field.get('id') == field_name:
                        field_selector = field.get('selector')
                        break
                if field_selector:
                    break
            
            if field_selector:
                fill_instructions.append({"selector": field_selector, "value": value})

        result.update({
            "status": "action",
            "action": {
                "type": "fill_form",
                "fields": fill_instructions
            },
            "note": "I've identified the form and the fields to fill. Please confirm to proceed.",
            "booking_details": booking_data,
        })
        
        # The actual booking saving should happen after the form is submitted by the user
        # This requires another endpoint or a different flow.
        # For now, we are just sending the instructions to the frontend.

    except Exception as e:
        print(f"❌ Error in booking action: {e}")
        result.update({"status": "failed", "error": str(e)})
