import asyncio
import sys
import os

# Policy is now handled in run.py for Windows compatibility


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router
from app.dashboard_routes import router as dashboard_router
from app.services.rag_service import add_documents
from app.services.knowledge_base import initialize_knowledge_base

app = FastAPI(title="Agentic AI Backend")


@app.on_event("startup")
async def startup_event():
    await initialize_knowledge_base()
    print("✅ Knowledge base initialized")


"""CORS configuration
In development we default to http://localhost:3000.
Production origin(s) can be provided via either:
 - WIDGET_ORIGIN=https://your-frontend-domain
 - CORS_ALLOW_ORIGINS=https://a.com,https://b.com (comma separated)
The first available variable is used. Falls back to localhost.
"""
origins_env = os.getenv("CORS_ALLOW_ORIGINS") or os.getenv("WIDGET_ORIGIN")
allow_origins = [o.strip() for o in origins_env.split(",") if o.strip()] if origins_env else ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# mount API routes under /api
app.include_router(router, prefix="/api")
app.include_router(dashboard_router, prefix="/api/dashboard")