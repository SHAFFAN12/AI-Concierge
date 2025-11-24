import logging
import json
import asyncio
from typing import List, Dict, Any, AsyncGenerator

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

from app.services.llm_provider import llm
from app.services.scraper_service import get_interactive_elements
from app.services.crawler_service import get_page_content_as_markdown
from app.services.menu_parser import parse_menu_from_markdown
from app.services.booking import auto_fill_and_submit_async
from app.services.cache import scrape_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize search tool
search_tool = DuckDuckGoSearchRun()

@tool
async def scrape_webpage(url: str) -> Dict[str, Any]:
    """
    Fetch + analyze a page. Returns: title, truncated content, interactive summary, menu_items (structured list), counts.
    Also returns interactive elements. Use this to understand the content and what actions
    are possible on the page. Always returns detailed information about the page.
    """
    try:
        # Check cache first
        cached = scrape_cache.get(url)
        if cached:
            logger.info(f"Using cached scrape for {url}")
            return cached

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

        # Parse menu items heuristically
        menu_items = parse_menu_from_markdown(content)
        
        result = {
            "success": True,
            "url": url,
            "title": title,
            "content": truncated_content,
            "content_length": len(content),
            "interactive_elements_count": len(elements),
            "has_forms": any(el.get('tag') in ['input', 'textarea', 'select'] for el in elements) if elements else False,
            "has_buttons": any(el.get('tag') == 'button' for el in elements) if elements else False,
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
async def web_action(action_type: str, url: str, selector: str = None, value: str = None, wait_for: str = None) -> Dict[str, Any]:
    """
    Perform a generic action on a website.
    
    Args:
        action_type: One of "click", "fill", "select", "hover", "scroll", "navigate", "extract".
        url: The URL to perform the action on.
        selector: CSS selector for the target element (required for click, fill, select, hover).
        value: Value to fill/select, or attribute to extract.
        wait_for: Optional selector to wait for after action.
    """
    try:
        result = await perform_action(url, action_type, selector, value, wait_for)
        return result
    except Exception as e:
        logger.error(f"Error in web_action: {e}")
        return {"success": False, "error": str(e)}

tools = [search_tool, scrape_webpage, web_action]

# Bind tools to LLM
llm_with_tools = llm.bind_tools(tools)

# --- 3. Define the main function to run the agent with streaming ---

async def run_agent_stream(user_input: str, chat_history: List[Dict[str, str]], current_url: str = None, site_navigation: List[Dict[str, str]] = None) -> AsyncGenerator[Dict, None]:
    """
    Runs the LangChain agent with the given user input and chat history,
    streaming intermediate steps and the final answer.
    """
    try:
        # Define System Prompt with Context
        system_prompt = """You are an AI assistant designed to help users interact with websites and answer questions."""
        
        if current_url:
            system_prompt += f"\n\n**CURRENT CONTEXT**: The user is currently browsing: {current_url}\n"
            system_prompt += "Your primary job is to assist with THIS website. If the user asks about 'this site' or 'here', refer to this URL. "
            system_prompt += "You should proactively `scrape_webpage` on this URL if the user asks a question about the content."

        if site_navigation:
            system_prompt += "\n\n**SITE NAVIGATION** (Detected from page):\n"
            for nav in site_navigation:
                system_prompt += f"- {nav.get('label')}: {nav.get('url')}\n"
            system_prompt += "\nUse this navigation list to understand the website structure.\n"
            system_prompt += "**CRITICAL**: If the user asks a question that might be answered on one of these other pages (e.g., 'How much does it cost?' -> check '/pricing'), you MUST use the `scrape_webpage` tool on that specific URL to find the answer."

        system_prompt += """
You have access to the following tools:

1.  `duckduckgo_search`: Use this to find information on the web.
2.  `scrape_webpage`: Use this to extract content from a specific URL. It returns markdown text and a list of interactive elements.
3.  `web_action`: Use this to interact with a website. You can click buttons, fill forms, select options, etc.

**How to use `web_action`:**
- To click a button/link: `web_action(action_type="click", url="...", selector="button#submit")`
- To fill a form: `web_action(action_type="fill", url="...", selector="input[name='q']", value="search term")`
- To select an option: `web_action(action_type="select", url="...", selector="select#country", value="US")`
- To extract text: `web_action(action_type="extract", url="...", selector=".price")`

**Strategy:**
1.  If you need to find a website, search for it first.
2.  If you need to act on a website, first `scrape_webpage` to see the content and find selectors.
3.  Then use `web_action` to perform the necessary steps.
4.  Always confirm the action was successful.

**Important:**
- When using `web_action`, be precise with selectors. Use the ones found in the scrape result if possible.
- If a tool fails, try a different approach or ask the user for clarification.
"""
        
        # Initialize messages
        messages = [SystemMessage(content=system_prompt)]

        # Add chat history
        for msg in chat_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        # Add current user input
        messages.append(HumanMessage(content=user_input))

        # Bind tools to LLM
        tools = [DuckDuckGoSearchRun(), scrape_webpage, web_action]
        llm_with_tools = llm.bind_tools(tools)

        # Agent Loop
        while True:
            # Invoke LLM
            response = await llm_with_tools.ainvoke(messages)
            messages.append(response)

            # Check if tool call is needed
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    # Stream tool usage
                    yield {"content": f"<tool_code>{tool_name}({tool_args})</tool_code>\n"}

                    # Execute tool
                    tool_result = None
                    if tool_name == "duckduckgo_search":
                        search = DuckDuckGoSearchRun()
                        tool_result = await search.ainvoke(tool_args)
                    elif tool_name == "scrape_webpage":
                        tool_result = await scrape_webpage.ainvoke(tool_args)
                    elif tool_name == "web_action":
                        tool_result = await web_action.ainvoke(tool_args)

                    # Stream tool output
                    yield {"content": f"<tool_output>{str(tool_result)[:500]}...</tool_output>\n"}

                    # Add result to messages
                    messages.append(
                        HumanMessage(
                            content=json.dumps(tool_result),
                            name=tool_name,
                            tool_call_id=tool_call["id"],
                        )
                    )
            else:
                # Final answer
                yield {"content": response.content}
                break

    except Exception as e:
        logger.error(f"Error in agent stream: {e}")
        yield {"error": str(e)}
