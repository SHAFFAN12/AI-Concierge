# backend/app/services/agent_service.py
import os
import json
from typing import List, Dict, Any, AsyncGenerator

from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq

from app.services.crawler_service import get_page_content_as_markdown
from app.services.scraper_service import get_interactive_elements

# --- 1. Initialize the LLM ---
# We use the same Groq LLM as before
llm = ChatGroq(
    temperature=0,
    model_name="llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY")
)

# --- 2. Define Tools ---

# Tool 1: A simple web search tool
search_tool = DuckDuckGoSearchRun()

# Tool 2: A custom tool for scraping a webpage
@tool
async def scrape_webpage(url: str) -> Dict[str, Any]:
    """
    Scrapes a webpage to get its content in Markdown format and a list of all
    interactive elements. Use this to understand the content and what actions
    are possible on the page.
    """
    try:
        content = await get_page_content_as_markdown(url)
        elements = await get_interactive_elements(url)
        return {
            "content": content,
            "interactive_elements": elements,
            "url": url # Include the URL in the output for context
        }
    except Exception as e:
        return {"error": f"Failed to scrape webpage: {e}", "url": url}

tools = [search_tool, scrape_webpage]

# Bind tools to LLM
llm_with_tools = llm.bind_tools(tools)

# --- 3. Define the main function to run the agent with streaming ---

async def run_agent_stream(user_input: str, chat_history: List[Dict[str, str]]) -> AsyncGenerator[Dict, None]:
    """
    Runs the LangChain agent with the given user input and chat history,
    streaming intermediate steps and the final answer.
    """
    try:
        # Build message history
        messages = [
            SystemMessage(content="""You are an AI assistant designed to help users interact with websites and answer questions.
Your goal is to be as helpful and autonomous as possible, completing tasks step-by-step.

When you need to search for information, use the duckduckgo_search tool.
When you need to scrape a webpage, use the scrape_webpage tool.

Always think through your approach and use tools when necessary to provide accurate information.""")
        ]
        
        # Add chat history
        for msg in chat_history:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                messages.append(AIMessage(content=msg.get("content", "")))
        
        # Add current user input
        messages.append(HumanMessage(content=user_input))
        
        full_response = ""
        
        # Stream the response
        async for chunk in llm_with_tools.astream(messages):
            # Check if the chunk has tool calls
            if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                for tool_call in chunk.tool_calls:
                    # Send tool call notification
                    yield {
                        "ops": [{
                            "path": f"/logs/Agent/steps/0/start",
                            "value": {"name": f"Tool:{tool_call.get('name')}"}
                        }]
                    }
            
            # Check for content
            if hasattr(chunk, 'content') and chunk.content:
                full_response += chunk.content
                # Send streaming content
                yield {
                    "ops": [{
                        "path": "/logs/Agent/streamed_output/-",
                        "value": chunk.content
                    }]
                }
        
        # Send final output
        if full_response:
            yield {
                "ops": [{
                    "path": "/logs/Agent/final_output",
                    "value": {"output": full_response}
                }]
            }
                
    except Exception as e:
        error_message = {"error": f"Error running agent: {str(e)}"}
        yield error_message
