from fastapi import APIRouter, Depends # Import Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import json

from app.services.agent_service import run_agent_stream
from fastapi_limiter.depends import RateLimiter # New import

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []
    current_url: Optional[str] = None

@router.post("/chat", dependencies=[Depends(RateLimiter(times=5, seconds=10))]) # Apply rate limit
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
        async for chunk in run_agent_stream(
            user_input=user_input,
            chat_history=req.history
        ):
            # Each chunk is already JSON, so we just need to send it
            yield f"data: {chunk}\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")