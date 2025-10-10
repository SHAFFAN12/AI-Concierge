# app/services/booking_google.py
import os
import dateparser
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json")
CALENDAR_ID = os.environ.get("GOOGLE_CALENDAR_ID", "primary")
TIMEZONE = os.environ.get("GOOGLE_TIMEZONE", "Asia/Karachi")
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def _get_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    # cache_discovery=False avoids some network/timeouts
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    return service

def _parse_datetime(natural_text: str, reference: datetime | None = None):
    """
    Return (start_dt, end_dt) or (None, None)
    """
    if reference is None:
        reference = datetime.now()
    start = dateparser.parse(natural_text, settings={"RELATIVE_BASE": reference})
    if not start:
        return None, None
    end = start + timedelta(minutes=30)  # default 30m
    return start, end

def check_availability(start_dt: datetime, end_dt: datetime, calendar_id: str = CALENDAR_ID):
    service = _get_service()
    body = {
        "timeMin": start_dt.isoformat(),
        "timeMax": end_dt.isoformat(),
        "items": [{"id": calendar_id}],
    }
    resp = service.freebusy().query(body=body).execute()
    busy = resp.get("calendars", {}).get(calendar_id, {}).get("busy", [])
    return len(busy) == 0

def create_event(summary: str, start_dt: datetime, end_dt: datetime, attendees=None, description: str = "", calendar_id: str = CALENDAR_ID):
    service = _get_service()
    event_body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": TIMEZONE},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": TIMEZONE},
    }
    if attendees:
        event_body["attendees"] = [{"email": a} for a in attendees]
    created = service.events().insert(calendarId=calendar_id, body=event_body, sendUpdates="all").execute()
    return created

async def run_google_booking(params: dict) -> dict:
    """
    params:
      - text: natural language time (eg "Friday at 3pm")
      - summary: event summary/title
      - attendee_emails: optional list
      - calendar_id: optional
    """
    text = params.get("text") or params.get("datetime_text") or params.get("when") or ""
    summary = params.get("summary", "Appointment")
    attendees = params.get("attendee_emails", [])
    calendar_id = params.get("calendar_id", CALENDAR_ID)

    if not text:
        return {"status": "failed", "error": "No date/time provided."}

    start_dt, end_dt = _parse_datetime(text)
    if not start_dt:
        return {"status": "failed", "error": "Unable to parse date/time from text."}

    try:
        free = check_availability(start_dt, end_dt, calendar_id=calendar_id)
    except Exception as e:
        return {"status": "failed", "error": f"free/busy check error: {str(e)}"}

    if not free:
        return {"status": "unavailable", "note": f"Requested slot {start_dt.isoformat()} is busy."}

    try:
        created = create_event(summary, start_dt, end_dt, attendees=attendees, calendar_id=calendar_id)
        return {
            "status": "ok",
            "note": f"Appointment booked: {summary} on {start_dt.strftime('%c')}",
            "event": {
                "id": created.get("id"),
                "htmlLink": created.get("htmlLink"),
                "start": created.get("start"),
                "end": created.get("end"),
            }
        }
    except Exception as e:
        return {"status": "failed", "error": f"Failed to create event: {str(e)}"}