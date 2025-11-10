import asyncio
import sys # Import sys

if sys.platform == 'win32':
    # Windows par Playwright aur asyncio subprocesses ke liye zaroori
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    print("✅ AsyncIO policy set for Windows.")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router
from app.dashboard_routes import router as dashboard_router
from app.services.rag_service import add_documents
from app.services.knowledge_base import initialize_knowledge_base

app = FastAPI(title="Agentic AI Backend")


@app.on_event("startup")
async def startup_event():
    initialize_knowledge_base()
    print("✅ Knowledge base initialized")


# Allow frontend dev origin; in prod set strict origin list
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # change as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# mount API routes under /api
app.include_router(router, prefix="/api")
app.include_router(dashboard_router, prefix="/api/dashboard")
