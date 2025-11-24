from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import os

from app.services.agent_service import run_agent_stream

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, Any]]] = []
    current_url: Optional[str] = None
    site_navigation: Optional[List[Dict[str, str]]] = []

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """
    This endpoint receives a user's message and chat history, and streams
    the LangChain agent's response, including intermediate steps.
    """
    
    # The user input will now include the current URL if it's available
    user_input = req.message
    if req.current_url:
        user_input += f"\n\n(The user is currently on this URL: {req.current_url})"

    async def event_generator():
        try:
            async for chunk in run_agent_stream(
                user_input=user_input,
                chat_history=req.history,
                current_url=req.current_url,
                site_navigation=req.site_navigation
            ):
                # logger.debug(f"CHUNK RECEIVED: {chunk}")
                # Each chunk is a dict, so we format it as a JSON string
                # and send it in SSE format with a double newline
                data_to_send = f"data: {json.dumps(chunk)}\n\n"
                # logger.debug(f"DATA SENT: {data_to_send}")
                yield data_to_send
        except Exception as e:
            logger.error(f"Error in chat stream: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")