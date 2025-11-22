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
-   `scraper_service.py`: The "hands" of the agent, using Playwright to identify and analyze interactive elements on a page.
-   `db.py`: Handles database interaction with a MongoDB instance via the async `motor` library.
-   `main.py`: The main entrypoint for the application, where the FastAPI app is initialized and configured.
-   `routes.py` & `dashboard_routes.py`: Define the public-facing and administrative API endpoints, respectively.

## Prerequisites

-   Python 3.8+
-   MongoDB server
-   Redis server
-   A `GROQ_API_KEY` environment variable with a valid API key from [Groq](https://groq.com/).
-   Google Chrome browser (version 114)
-   ChromeDriver (version 114)

*Note: The requirement for a specific Chrome/ChromeDriver version is for the Selenium-based form filler. The Playwright-based scraper is more flexible.*

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

4.  **Install Playwright browser binaries:**
    ```bash
    playwright install
    ```

5.  **Set up environment variables:**
    Create a `.env` file in the `backend` directory and add your Groq API key:
    ```
    GROQ_API_KEY="your_groq_api_key_here"
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
