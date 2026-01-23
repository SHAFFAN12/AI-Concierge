# app/dashboard_routes.py
import asyncio
from fastapi import APIRouter, Depends
from app.db import get_db
from bson.objectid import ObjectId
from app.services.scraper_service import analyze_website_forms


router = APIRouter()

@router.get("/sites")
async def get_sites(db = Depends(get_db)):
    sites = await db["sites"].find().to_list(100)
    for site in sites:
        site["_id"] = str(site["_id"])
    return sites

@router.post("/sites")
async def create_site(site_data: dict, db = Depends(get_db)):
    result = await db["sites"].insert_one(site_data)
    return {"status": "ok", "id": str(result.inserted_id)}

@router.get("/sites/{site_id}/chats")
async def get_site_chats(site_id: str, db = Depends(get_db)):
    chats = await db["chats"].find({"site_id": site_id}).to_list(100)
    for chat in chats:
        chat["_id"] = str(chat["_id"])
    return chats

@router.get("/sites/{site_id}/analytics")
async def get_site_analytics(site_id: str, db = Depends(get_db)):
    # For now, just return the number of chats
    num_chats = await db["chats"].count_documents({"site_id": site_id})
    return {"num_chats": num_chats}

@router.put("/sites/{site_id}/scraper-config")
async def update_scraper_config(site_id: str, scraper_config: dict, db = Depends(get_db)):
    try:
        obj_id = ObjectId(site_id)
    except Exception:
        return {"status": "failed", "error": "Invalid site ID."}

    result = await db["sites"].update_one(
        {"_id": obj_id},
        {"$set": {"scraper_config": scraper_config}}
    )

    if result.modified_count == 1:
        return {"status": "ok"}
    else:
        return {"status": "failed", "error": "Site not found."}


@router.post("/analyze-site")
async def analyze_site(data: dict):
    url = data.get("url")
    if not url:
        return {"status": "failed", "error": "URL is required"}
    result = await asyncio.to_thread(analyze_website_forms, url)
    return result