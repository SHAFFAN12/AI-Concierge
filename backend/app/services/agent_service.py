# backend/app/services/agent_service.py
import os
from typing import List, Dict, Any, AsyncGenerator

from langchain.agents import AgentExecutor, create_react_agent
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.prompts import PromptTemplate
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

# --- 3. Create the Agent ---

# The prompt template tells the agent how to reason and what tools it has.
# This is a standard ReAct (Reasoning and Acting) prompt, enhanced for multi-step and self-correction.
prompt_template = PromptTemplate.from_template("""
You are an AI assistant designed to help users interact with websites and answer questions.
Your goal is to be as helpful and autonomous as possible, completing tasks step-by-step.

You have access to the following tools:
{tools}

To use a tool, you MUST use the following format:
```
Thought: Do I need to use a tool? Yes
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
```
Always observe the results of your actions. If an action fails or returns an unexpected result,
analyze the observation and try a different approach or re-plan.

When you have a complete response to say to the user, or if you don't need to use a tool,
you MUST use the following format:
```
Thought: Do I need to use a tool? No
Final Answer: [your response here, including any actions the user needs to take on the frontend]
```
The "Final Answer" should be a comprehensive response that directly addresses the user's request.
If you suggest a frontend action (like a click or form fill), clearly state it in the Final Answer
so the user knows what to expect or confirm.

Begin!

Previous conversation history (for context, do not repeat yourself):
{chat_history}

New user input: {input}
{agent_scratchpad}
""")

# Create the agent using the LLM, tools, and prompt
agent = create_react_agent(llm, tools, prompt_template)

# The AgentExecutor is what runs the agent and executes the tools
# We set handle_parsing_errors=True to gracefully handle LLM parsing errors
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)

# --- 4. Define the main function to run the agent with streaming ---

async def run_agent_stream(user_input: str, chat_history: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
    """
    Runs the LangChain agent with the given user input and chat history,
    streaming intermediate steps and the final answer.
    """
    try:
        async for chunk in agent_executor.astream_log(
            {"input": user_input, "chat_history": chat_history},
            include_names=["Agent"], # Only stream events related to the main agent run
        ):
            yield json.dumps(chunk) + "\n" # Yield each chunk as a JSON string
    except Exception as e:
        error_message = {"error": f"Error running agent: {e}"}
        yield json.dumps(error_message) + "\n"
