# AI Concierge Backend

This is the backend for the AI Concierge, a sophisticated, context-aware agentic AI system designed to be embedded on websites. It provides a conversational interface that can understand the content of the page it's on, interact with web elements, and perform tasks like searching the web and filling out forms.

## Features

- **Conversational AI Agent**: Core of the service, powered by Groq and LangChain.
- **Context-Aware**: The agent knows which URL the user is currently visiting.
- **Web Scraping & Analysis**: Can "read" a webpage's content (via `crawler_service`) and "see" its interactive elements like forms and buttons (via `scraper_service`).
- **Multi-Tenant Dashboard API**: A set of administrative endpoints to manage client sites, view analytics, and configure scraper settings.
- **Automated Form Filling**: Logic to automatically fill and submit web forms (Note: This feature is implemented but not yet fully integrated with the main agent).
- **Rate Limiting**: Built-in Redis-based rate limiting to prevent abuse.
- **Async Support**: Built with FastAPI and Motor for high-performance, asynchronous operations.

## Architecture

The application is built using the **FastAPI** web framework. The logic is separated into several services:

-   `agent_service.py`: The "brain" of the agent, orchestrating LLM calls and tool usage.
-   `crawler_service.py`: The "eyes" of the agent, responsible for reading and parsing web page content into Markdown.
-   `scraper_service.py`: The "hands" of the agent, using Selenium to identify and analyze interactive elements on a page.
-   `db.py`: Handles database interaction with a MongoDB instance via the async `motor` library.
-   `main.py`: The main entrypoint for the application, where the FastAPI app is initialized and configured.
-   `routes.py` & `dashboard_routes.py`: Define the public-facing and administrative API endpoints, respectively.

## Prerequisites

-   Python 3.8+
-   MongoDB server
-   Redis server
-   A `GROQ_API_KEY` environment variable with a valid API key from [Groq](https://groq.com/).
-   Google Chrome browser
-   ChromeDriver



## Installation

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```



5.  **Set up environment variables:**
    Create a `.env` file in the `backend` directory and add your Groq API key:
    ```
    GROQ_API_KEY="your_groq_api_key_here"
    # Optional CORS/embedding configuration
    # Single origin (widget hosting domain)
    WIDGET_ORIGIN="https://your-frontend-domain"
    # OR multiple origins (comma separated)
    CORS_ALLOW_ORIGINS="https://site-a.com,https://site-b.com"
    ```

## Running the Application

Once the installation is complete, you can run the application with:

```bash
uvicorn app.main:app --reload
```

The server will be available at `http://127.0.0.1:8000`.

## API Endpoints

### Public API

-   `POST /api/chat`: The main endpoint for interacting with the conversational agent. It accepts a stream of messages and returns a streamed response.

### Streaming Format
Responses are sent as Server-Sent Events (SSE) with JSON chunks shaped like:
```json
{ "ops": [ { "path": "/logs/Agent/streamed_output/-", "value": "partial text" } ] }
```
Final answer:
```json
{ "ops": [ { "path": "/logs/Agent/final_output", "value": { "output": "full text" } } ] }
```
Action instructions (from `web_action` tool):
```json
{ "ops": [ { "path": "/actions/-", "value": { "type": "click", "target": "Submit" } } ] }
```

### Dashboard API (`/api/dashboard`)

-   `GET /sites`: Retrieves a list of all configured client sites.
-   `POST /sites`: Adds a new site.
-   `GET /chats/{site_id}`: Fetches chat history for a specific site.
-   `POST /scraper/config/{site_id}`: Updates the scraper configuration for a site.
-   `POST /scraper/analyze`: Analyzes a given URL to identify forms and interactive elements.

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py             # FastAPI app entrypoint
│   ├── db.py               # MongoDB connection and database logic
│   ├── routes.py           # Public API endpoints (e.g., /api/chat)
│   ├── dashboard_routes.py # Admin dashboard API endpoints
│   ├── services/           # Business logic
│   │   ├── agent_service.py    # Core agent logic (LLM, tools)
│   │   ├── web_action tool     # Emits action instructions (click/fill/form_fill)
│   │   ├── crawler_service.py  # Reads page content
│   │   ├── scraper_service.py  # Analyzes interactive elements
│   │   └── ...
│   └── scrapper/
│       └── form_filler_async.py # Standalone form-filling logic
├── data/
│   ├── calendar.md
│   └── services.md
├── tests/
│   └── test_routes.py      # Pytest tests
├── requirements.txt        # Project dependencies
└── Dockerfile
```

## Running Tests

Tests are written using the `pytest` framework. To run the test suite, execute the following command from the `backend` directory:

```bash
pytest
```

## Embedding the Widget

Include the script on any page you want the concierge widget:
```html
<script src="https://your-frontend-domain/embed.js" data-base-url="https://your-frontend-domain"></script>
```
If `data-base-url` is omitted, the widget infers the origin from the script's `src`.

## Agent Actions

The agent can propose actions via the `web_action` tool:
- `click`: `{ "type": "click", "target": "Button Text" }` – front-end searches for elements with matching text and clicks.
- `fill`: `{ "type": "fill", "target": "CSS selector or field label", "value": "Text" }` – front-end attempts to fill the field.
- `form_fill`: `{ "type": "form_fill", "target": "https://page-url", "value": "{ JSON mapping of fields }" }` – server attempts automation (Selenium) and also sends instructions client-side.

Client pages receive actions via `postMessage` with shape:
```js
{ type: 'action', payload: { type, target, value } }
```
You can intercept and extend handling:
```js
window.addEventListener('message', (e) => {
    if (e.data?.type === 'action') {
        // custom handling
        console.log('Action received', e.data.payload);
    }
});
```

## CORS Configuration

`main.py` reads `CORS_ALLOW_ORIGINS` (comma-separated) or `WIDGET_ORIGIN` to set allowed origins. If neither is provided it defaults to `http://localhost:3000` for development.

| Variable | Purpose | Example |
|----------|---------|---------|
| `WIDGET_ORIGIN` | Single allowed origin for embedding | `https://app.example.com` |
| `CORS_ALLOW_ORIGINS` | Multiple origins (comma separated) | `https://a.com,https://b.com` |

Set one (prefer `CORS_ALLOW_ORIGINS` if multiple). Do not include trailing slashes.
