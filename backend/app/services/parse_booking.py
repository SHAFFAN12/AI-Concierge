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

    # Phone number extraction (prioritize)
    number_match = re.search(r"(\d[\d\s-]{5,}\d)", user_message, re.IGNORECASE)
    if number_match:
        params["phone"] = number_match.group(1).strip()

    # Email extraction (prioritize)
    email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", user_message)
    if email_match:
        params["email"] = email_match.group(0).strip()

    # Name extraction
    name_match = re.search(r"I'm\s+([A-Z][a-z]+)", user_message, re.IGNORECASE)
    if name_match:
        params["name"] = name_match.group(1).strip()

    # Number of guests / participants / people
    guests_match = re.search(r"(\d+)\s+(?:people|guests|participants|members)", user_message, re.IGNORECASE)
    if guests_match:
        params["guests"] = int(guests_match.group(1))

    # Date & Time extraction
    dt = dateparser.parse(user_message, settings={'PREFER_DATES_FROM': 'future', 'RELATIVE_BASE': datetime(2025, 1, 1)})
    if dt:
        params["date"] = dt.strftime("%Y-%m-%d")
        params["time"] = dt.strftime("%H:%M")

    # Booking item/service
    item_match = re.search(r"book (?:a|an|the)?\s*([\w\s]+?)(?:(?:for|with|of|\.)|$)", user_message, re.IGNORECASE)
    if item_match:
        params["item"] = item_match.group(1).strip()

    # Additional details: Construct by removing all extracted parts from the original message
    temp_details = user_message
    for key, value in params.items():
        if isinstance(value, str):
            temp_details = temp_details.replace(value, "", 1)

    # Remove common phrases that introduce extracted data and extra spaces
    temp_details = re.sub(r"(?:my name is|I am|This is|number is|phone is|contact is|email is|book a|book an|book the|for|with|of|guests|people|participants|members|at|on|and)", "", temp_details, flags=re.IGNORECASE).strip()
    temp_details = re.sub(r"\s+", " ", temp_details).strip() # Remove extra spaces

    if temp_details:
        params["details"] = temp_details
    else:
        params.pop("details", None) # Remove if empty

    print(f"DEBUG: extract_booking_params returning: {params}")
    return params
