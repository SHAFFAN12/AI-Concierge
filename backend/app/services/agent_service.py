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
from app.scrapper.form_filler_async import auto_fill_and_submit_async

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

# Tool 2: Enhanced tool for scraping a webpage
@tool
async def scrape_webpage(url: str) -> Dict[str, Any]:
    """
    Scrapes a webpage to get its content in Markdown format and a list of all
    interactive elements. Use this to understand the content and what actions
    are possible on the page. Always returns detailed information about the page.
    """
    try:
        # Get page content with retries
        content = await get_page_content_as_markdown(url)
        
        if not content:
            return {
                "success": False,
                "error": "Failed to retrieve page content. The page may be inaccessible, require authentication, or block automated access.",
                "url": url,
                "suggestion": "Try accessing the page manually or check if the URL is correct."
            }
        
        # Try to get interactive elements (non-blocking if it fails)
        try:
            elements = await get_interactive_elements(url)
        except Exception as elem_error:
            logger.warning(f"Could not get interactive elements: {elem_error}")
            elements = []
        
        # Extract key information from content
        lines = content.split('\n')
        title = next((line.strip('# ') for line in lines if line.startswith('# ')), 'No title found')
        
        # Limit content length for LLM context
        max_content_length = 4000
        truncated_content = content[:max_content_length]
        if len(content) > max_content_length:
            truncated_content += f"\n\n[Content truncated. Total length: {len(content)} characters]"
        
        return {
            "success": True,
            "url": url,
            "title": title,
            "content": truncated_content,
            "content_length": len(content),
            "interactive_elements_count": len(elements),
            "has_forms": any(el.get('tag') in ['input', 'textarea', 'select'] for el in elements) if elements else False,
            "has_buttons": any(el.get('tag') == 'button' for el in elements) if elements else False,
            "sample_links": [el.get('text', '')[:50] for el in elements if el.get('tag') == 'a'][:5],
        }
    except Exception as e:
        logger.error(f"Error in scrape_webpage for {url}: {e}")
        return {
            "success": False,
            "error": f"Unexpected error while scraping: {type(e).__name__}: {str(e)}",
            "url": url
        }

@tool
async def web_action(action_type: str, target: str, value: str = "") -> Dict[str, Any]:
    """Create (and optionally execute) a web action instruction.
    action_type: one of 'click', 'fill', 'form_fill'.
    target: text label / selector / URL (for form_fill).
    value: value to fill OR JSON string of field mapping for form_fill.
    Returns an action dict that the frontend can dispatch. For form_fill, server attempts automation too.
    """
    action: Dict[str, Any] = {"type": action_type, "target": target, "value": value}
    if action_type == "form_fill":
        try:
            # value expected to be JSON mapping
            field_data = json.loads(value) if value else {}
            result = await auto_fill_and_submit_async(target, field_data)
            action["server_automation_result"] = result
        except Exception as e:
            action["server_automation_error"] = str(e)
    return {"action": action}

tools = [search_tool, scrape_webpage, web_action]

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

Tools available:
- duckduckgo_search: general web search.
- scrape_webpage(url): understand page content and interactive elements.
- web_action(action_type, target, value): propose or execute an action. Use this to:
    * click a button or link (action_type='click', target is visible text)
    * fill a single field (action_type='fill', target is a CSS selector or field label text, value is text to enter)
    * fill and submit a form (action_type='form_fill', target is the page URL, value is a JSON mapping of fields)

When using tools, ALWAYS provide a response after calling the tool explaining what you found or what action you're taking.
After calling scrape_webpage, summarize the page content for the user.
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
        in_tool_call = False
        tool_call_buffer = ""
        max_iterations = 5
        iteration = 0
        
        # Agent loop - execute tools and get responses
        while iteration < max_iterations:
            iteration += 1
            tool_executed = False
            
            # Stream the response
            async for chunk in llm_with_tools.astream(messages):
                # Check if the chunk has tool calls
                if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                    tool_executed = True
                    for tool_call in chunk.tool_calls:
                        name = tool_call.get('name')
                        args = tool_call.get('args', {})
                        
                        # Notify tool call
                        yield {
                            "ops": [{
                                "path": f"/logs/Agent/steps/{iteration}/start",
                                "value": {"name": f"Tool:{name}", "args": args}
                            }]
                        }
                        
                        # Execute the tool
                        tool_result = None
                        try:
                            if name == 'duckduckgo_search':
                                tool_result = search_tool.run(args.get('query', ''))
                            elif name == 'scrape_webpage':
                                tool_result = await scrape_webpage.ainvoke(args)
                            elif name == 'web_action':
                                tool_result = await web_action.ainvoke(args)
                                # If action tool, emit action instruction
                                yield {
                                    "ops": [{
                                        "path": "/actions/-",
                                        "value": {"type": args.get('action_type'), "target": args.get('target'), "value": args.get('value')}
                                    }]
                                }
                        except Exception as e:
                            tool_result = {"error": str(e)}
                        
                        # Add tool result to messages
                        from langchain_core.messages import ToolMessage
                        messages.append(AIMessage(content="", tool_calls=[tool_call]))
                        messages.append(ToolMessage(
                            content=str(tool_result),
                            tool_call_id=tool_call.get('id', 'unknown')
                        ))
                        
                        # Notify tool completion
                        yield {
                            "ops": [{
                                "path": f"/logs/Agent/steps/{iteration}/end",
                                "value": {"name": f"Tool:{name}", "result": str(tool_result)[:200]}
                            }]
                        }
                
                # Check for content
                if hasattr(chunk, 'content') and chunk.content:
                    content = chunk.content
                    
                    # Check if we're entering or exiting a tool call
                    if '<' in content:
                        in_tool_call = True
                        tool_call_buffer += content
                        if '>' in content:
                            if '</' in tool_call_buffer or '/>' in tool_call_buffer:
                                in_tool_call = False
                                tool_call_buffer = ""
                            elif '>' in tool_call_buffer:
                                in_tool_call = True
                        continue
                    elif in_tool_call:
                        tool_call_buffer += content
                        if '>' in content:
                            if '</' in tool_call_buffer or '/>' in tool_call_buffer:
                                in_tool_call = False
                                tool_call_buffer = ""
                        continue
                    else:
                        # Normal content - not in a tool call
                        full_response += content
                        # Send streaming content
                        yield {
                            "ops": [{
                                "path": "/logs/Agent/streamed_output/-",
                                "value": content
                            }]
                        }
            
            # If no tool was executed, we're done
            if not tool_executed:
                break
        
        # Send final output
        if full_response:
            yield {
                "ops": [{
                    "path": "/logs/Agent/final_output",
                    "value": {"output": full_response}
                }]
            }
        elif iteration >= max_iterations:
            # If we hit max iterations without a response
            yield {
                "ops": [{
                    "path": "/logs/Agent/final_output",
                    "value": {"output": "I've completed the requested actions."}
                }]
            }
                
    except Exception as e:
        error_message = {"error": f"Error running agent: {str(e)}"}
        yield error_message
