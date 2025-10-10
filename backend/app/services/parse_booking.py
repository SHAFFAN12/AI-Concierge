# app/services/parse_booking.py
import re
from typing import Dict
from datetime import datetime
import dateparser

async def extract_booking_params(user_message: str) -> Dict:
    """
    Extract dynamic booking parameters from user message.
    Works for ANY booking type: restaurant, doctor, travel, salon, etc.
    """
    params = {}

    # Name extraction
    name_match = re.search(r"(my name is|I am|This is)\s+([A-Za-z ]+)", user_message, re.IGNORECASE)
    if name_match:
        params["name"] = name_match.group(2).strip()

    # Number of guests / participants / people
    guests_match = re.search(r"(\d+)\s+(people|guests|participants|members)", user_message, re.IGNORECASE)
    if guests_match:
        params["guests"] = int(guests_match.group(1))

    # Date & Time extraction
    dt = dateparser.parse(user_message, settings={"PREFER_DATES_FROM": "future"})
    if dt:
        params["date"] = dt.strftime("%Y-%m-%d %H:%M")

    # Booking item/service
    item_match = re.search(r"book (?:a|an|the)?\s*([\w\s]+)", user_message, re.IGNORECASE)
    if item_match:
        params["item"] = item_match.group(1).strip()

    # Additional details
    details_match = re.search(r"for (.+)", user_message, re.IGNORECASE)
    if details_match:
        params["details"] = details_match.group(1).strip()

    return params
