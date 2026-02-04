import logging
import json
import asyncio
from typing import List, Dict, Any, AsyncGenerator, Optional

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

from app.services.llm_provider import llm
from app.services.scraper_service import get_interactive_elements_with_crawl4ai
from app.services.crawler_service import get_page_content_as_markdown, deep_crawl_website, seed_and_crawl_website, adaptive_crawl_website
from app.services.menu_parser import parse_menu_from_markdown
from app.services.booking import auto_fill_and_submit_async
from app.services.cache import scrape_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 1. Define Tools ---

@tool
async def scrape_webpage(url: str, user_agent: Optional[str] = None, verify_ssl: bool = True) -> Dict[str, Any]:
    """
    Fetch + analyze a single page. Returns: title, truncated content, interactive summary, menu_items (structured list), counts.
    Also returns interactive elements. Use this to understand the content and what actions
    are possible on the page. Always returns detailed information about the page.
    """
    try:
        # Check cache first - DISABLED to ensure fresh form data
        # cached = scrape_cache.get(url)
        # if cached:
        #     logger.info(f"Using cached scrape for {url}")
        #     return cached

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
            elements = await get_interactive_elements_with_crawl4ai(url)
        except Exception as elem_error:
            logger.warning(f"Could not get interactive elements: {elem_error}")
            elements = []
        
        # Extract key information from content
        lines = content.split('\n')
        title = next((line.strip('# ') for line in lines if line.startswith('# ')), 'No title found')
        
        # Parse menu items heuristically
        menu_items = parse_menu_from_markdown(content)
        
        result = {
            "success": True,
            "url": url,
            "title": title,
            "content": content[:4000],
            "content_length": len(content),
            "interactive_elements_count": len(elements),
            "has_forms": any(el.get('tag') in ['input', 'textarea', 'select'] for el in elements) if elements else False,
            "has_buttons": any(el.get('tag') == 'button' for el in elements) if elements else False,
            "interactive_elements": [
                {k: v for k, v in el.items() if k in ['tag', 'text', 'selector', 'id', 'name', 'type', 'aria_label', 'placeholder']} 
                for el in elements 
                if el.get('tag') in ['input', 'textarea', 'select', 'button'] or (el.get('tag') == 'a' and len(el.get('text', '')) < 30)
            ][:50], # Limit to 50 key elements to save tokens
            "sample_links": [el.get('text', '')[:50] for el in elements if el.get('tag') == 'a'][:5],
            "menu_items": menu_items,
            "menu_items_count": len(menu_items),
        }
        
        # Cache the result
        scrape_cache.set(url, result)
        return result

    except Exception as e:
        logger.error(f"Error in scrape_webpage for {url}: {e}")
        return {
            "success": False,
            "error": f"Unexpected error while scraping: {type(e).__name__}: {str(e)}",
            "url": url
        }

@tool
async def deep_crawl(url: str, max_depth: int = 1, max_pages: int = 5) -> List[Dict[str, Any]]:
    """
    Perform a deep crawl on a website starting from the given URL.
    
    Args:
        url: The starting URL to crawl.
        max_depth: The maximum depth to crawl. Defaults to 1.
        max_pages: The maximum number of pages to crawl. Defaults to 5.
    """
    return await asyncio.to_thread(deep_crawl_website, url, max_depth, max_pages)

@tool
async def seeded_crawl(url: str, query: str) -> List[Dict[str, Any]]:
    """
    Discover and crawl relevant URLs from a website's sitemap based on a query.
    
    Args:
        url: The URL of the website to find the sitemap for.
        query: The query to filter URLs from the sitemap.
    """
    return await asyncio.to_thread(seed_and_crawl_website, url, query)

@tool
async def adaptive_crawl(url: str, query: str) -> List[Dict[str, Any]]:
    """
    Perform an adaptive crawl on a website to find information relevant to a query.
    
    Args:
        url: The starting URL to crawl.
        query: The query to guide the adaptive crawl.
    """
    return await asyncio.to_thread(adaptive_crawl_website, url, query)


@tool
async def web_action(action_type: str, url: str, selector: str = None, value: str = None, wait_for: Optional[str] = None) -> Dict[str, Any]:
    """
    Perform a generic action on a website.
    
    Args:
        action_type: One of "click", "fill", "select", "hover", "scroll", "navigate", "extract".
        url: The URL to perform the action on (mostly for context, actions are applied to current page).
        selector: CSS selector for the target element (required for click, fill, select, hover, scroll-to-element).
        value: Value to fill/select/navigate-to. For scroll, can be "top", "bottom", or specific coordinates.
        wait_for: Optional selector to wait for after action.
    """
    try:
        # This is a placeholder for the actual implementation
        # result = await perform_action(url, action_type, selector, value, wait_for)
        return {"success": True, "message": f"Action '{action_type}' performed on {url}."}
    except Exception as e:
        logger.error(f"Error in web_action: {e}")
        return {"success": False, "error": str(e)}

@tool
async def fill_form(url: str, form_data: Dict[str, str]) -> Dict[str, Any]:
    """
    Fill multiple form fields at once. Use this for forms.
    
    Args:
        url: The URL where the form is located.
        form_data: A dictionary where keys are CSS selectors (or field names/ids) and values are the values to fill.
    """
    return {"success": True, "message": f"Form filled with {len(form_data)} fields."}

# --- 2. Tool Registry and LLM Binding ---

tool_registry = {
    "duckduckgo_search": DuckDuckGoSearchRun(),
    "scrape_webpage": scrape_webpage,
    "deep_crawl": deep_crawl,
    "seeded_crawl": seeded_crawl,
    "adaptive_crawl": adaptive_crawl,
    "web_action": web_action,
    "fill_form": fill_form,
}

tools = list(tool_registry.values())
llm_with_tools = llm.bind_tools(tools)

# --- 3. Main Agent Function ---

async def run_agent_stream(user_input: str, chat_history: List[Dict[str, str]], current_url: str = None, site_navigation: List[Dict[str, str]] = None) -> AsyncGenerator[Dict, None]:
    """
    Runs the LangChain agent with the given user input and chat history,
    streaming intermediate steps and the final answer.
    """
    try:
        # Define System Prompt with Context
        system_prompt = """You are an AI assistant designed to help users interact with websites and answer questions.
You have access to a comprehensive suite of tools for web scraping and interaction."""

        if current_url:
            system_prompt += f"\n\n**CURRENT CONTEXT**: The user is currently browsing: {current_url}\n"
            system_prompt += "Your primary job is to assist with THIS website. If the user asks about 'this site' or 'here', refer to this URL. "
            system_prompt += "You should proactively `scrape_webpage` on this URL ONLY if the user asks a question about the content OR if you need to inspect the page to find correct selectors for a form fill or interaction. Do NOT scrape if the user only asks to perform a GENERIC action (scroll, navigate) unless explicitly requested."
            system_prompt += "\n**IMPORTANT**: When filling date inputs, ALWAYS use the format `YYYY-MM-DD` (e.g., 2024-01-30) regardless of how it appears on screen, unless you are certain it is a text field requiring a different format."
            system_prompt += "\n**IMPORTANT**: When filling time inputs, ONLY use ISO format (HH:mm) if it is a strict `<input type='time'>`. If the user specifies a particular format (e.g., '10 PM') and the field appears to be a text input or supports it, USE THE USER'S FORMAT EXACTLY."
            system_prompt += "\n**CRITICAL**: When using `fill_form` or `web_action`, YOU MUST CALL THE TOOL via the defined function. DO NOT print the tool call as text (e.g., <function=...>). DO NOT use keys like `[name]`. Use standard CSS selectors or descriptive names as keys."
            system_prompt += "\n**NEGATIVE CONSTRAINT**: Do NOT output any XML-like tags such as <form_data> or <function>. Doing so is a verification failure."
            system_prompt += "\n**ACTION REQUIREMENT**: If the user asks to perform an action (like filling a form, clicking, booking), you MUST generate a tool call (e.g., `fill_form`, `web_action`). Do not just state that you will do it. You must physically invoke the tool."

        if site_navigation:
            system_prompt += "\n\n**SITE NAVIGATION** (Detected from page):\n"
            for nav in site_navigation:
                system_prompt += f"- {nav.get('label')}: {nav.get('url')}\n"
            system_prompt += "\nUse this navigation list to understand the website structure.\n"
            system_prompt += "**CRITICAL**: If the user asks a question that might be answered on one of these other pages (e.g., 'How much does it cost?' -> check '/pricing'), you MUST use the `scrape_webpage` tool on that specific URL to find the answer."

        # Initialize messages
        messages = [SystemMessage(content=system_prompt)]
        for msg in chat_history:
            messages.append(HumanMessage(content=msg["content"]) if msg["role"] == "user" else AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=user_input))

        # Agent Loop
        while True:
            import time
            start_time = time.time()
            response = await llm_with_tools.ainvoke(messages)
            end_time = time.time()
            logger.info(f"LLM Response Time: {end_time - start_time:.4f} seconds")
            messages.append(response)

            if not response.tool_calls:
                yield {"content": response.content}
                break

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                yield {"content": f"<tool_code>{tool_name}({json.dumps(tool_args)})</tool_code>\n"}

                if tool_name == "web_action":
                    # Emit specific action event for the frontend to handle
                    yield {"action": tool_args}
                    yield {"content": "Task successfully performed."}
                    return

                elif tool_name == "fill_form":
                    # Decompose fill_form into multiple web_action events
                    form_data = tool_args.get("form_data", {})
                    for selector, value in form_data.items():
                        action_payload = {
                            "action_type": "fill",
                            "selector": selector,
                            "value": str(value)
                        }
                        yield {"action": action_payload}
                        # Small delay to ensure frontend processes order if needed, though usually not strictly necessary with async streams
                        await asyncio.sleep(0.5) 
                    
                    yield {"content": f"Form filled with {len(form_data)} fields."}
                    # Break out of the loop to prevent further LLM calls
                    return

                if tool_name in tool_registry:
                    tool_function = tool_registry[tool_name]
                    tool_result = await tool_function.ainvoke(tool_args)
                    if tool_name not in ["web_action", "fill_form"]:
                        yield {"content": f"<tool_output>{str(tool_result)}</tool_output>\n"}
                    messages.append(
                        HumanMessage(
                            content=json.dumps(tool_result),
                            name=tool_name,
                            tool_call_id=tool_call["id"],
                        )
                    )
                else:
                    yield {"content": f"<tool_output>Error: Tool '{tool_name}' not found.</tool_output>\n"}
            
            await asyncio.sleep(0.1) # Reduced delay for better responsiveness


    except Exception as e:
        logger.error(f"Error in agent stream: {e}")
        yield {"error": str(e)}