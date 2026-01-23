# app/db.py (Updated Structure)
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from typing import Dict, Any

# ======================================================
# MongoDB Client and DB Instance
# ======================================================
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "agentic_ai")

# 1. Client ko directly initialize kar dein
client = AsyncIOMotorClient(MONGO_URI)
# 2. db instance ko bhi directly export kar dein
db = client[MONGO_DB_NAME]


# ======================================================
# DB Dependency (for FastAPI) - This is what dashboard_routes.py tries to import
# ======================================================
# get_db function sirf FastAPI dependencies ke liye chahiye
async def get_db():
    """Return the active MongoDB database instance."""
    return db


# ======================================================
# Save Booking
# ======================================================
async def save_booking(data: Dict[str, Any]):
    """
    Save booking details extracted by AI to MongoDB.
    This version is more flexible and saves all keys from the data dict.
    """
    booking_collection = db["bookings"]

    # Start with the data provided
    doc = data.copy()

    # Ensure essential fields are present and add timestamps
    doc.setdefault("status", "pending")
    doc.setdefault("form_submitted", False)
    doc["created_at"] = doc.get("created_at") or datetime.utcnow()
    doc["date"] = doc.get("date") or datetime.utcnow()


    result = await booking_collection.insert_one(doc)
    return str(result.inserted_id)


# ======================================================
# Save Chat
# ======================================================
async def save_chat(user_id, message, plan, result, site_id=None):
    # ... (function body remains the same)
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