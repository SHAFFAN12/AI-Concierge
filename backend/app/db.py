import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

# ======================================================
# MongoDB Configuration
# ======================================================
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "agentic_ai")

# Create a single Mongo client
client = AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB_NAME]


# ======================================================
# DB Dependency (for FastAPI)
# ======================================================
async def get_db():
    """Return the active MongoDB database instance."""
    return db


# ======================================================
# Save Booking
# ======================================================
async def save_booking(data: dict):
    """
    Save booking details extracted by AI to MongoDB.

    Args:
        data (dict): Booking details such as name, number, item, details, user_id, etc.
    Returns:
        str: The inserted booking document ID.
    """
    booking_collection = db["bookings"]

    doc = {
        "user_id": data.get("user_id"),
        "site_id": data.get("site_id"),
        "name": data.get("name"),
        "number": data.get("number"),
        "item": data.get("item"),
        "details": data.get("details"),
        "date": data.get("date") or datetime.utcnow(),
        "status": data.get("status", "pending"),
        "form_submitted": data.get("form_submitted", False),
        "created_at": datetime.utcnow()
    }

    result = await booking_collection.insert_one(doc)
    return str(result.inserted_id)


# ======================================================
# Save Chat  ✅ (this was missing)
# ======================================================
async def save_chat(user_id, message, plan, result, site_id=None):
    """
    Save chat interaction and AI result to MongoDB.
    """
    chat_collection = db["chats"]

    doc = {
        "user_id": user_id,
        "site_id": site_id,
        "message": message,
        "plan": plan,
        "result": result,
        "timestamp": datetime.utcnow()
    }

    await chat_collection.insert_one(doc)
    return True
