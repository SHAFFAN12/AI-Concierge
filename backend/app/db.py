import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

# Get MongoDB connection details from environment variables
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "agentic_ai")

# Create a single client instance
client = AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB_NAME]

async def get_db():
    """Dependency to get the database instance."""
    return db

async def save_chat(user_id: str, message: str, plan: dict, result: dict, site_id: str = None):
    """Saves a chat interaction to the database."""
    chat_collection = db["chats"]
    doc = {
        "user_id": user_id,
        "user_message": message,
        "ai_plan": plan,
        "ai_result": result,
        "created_at": datetime.utcnow()
    }
    if site_id:
        doc["site_id"] = site_id
    await chat_collection.insert_one(doc)