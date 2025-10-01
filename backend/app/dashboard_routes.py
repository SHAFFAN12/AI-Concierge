# app/dashboard_routes.py
from fastapi import APIRouter, Depends
from app.db import get_db

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
