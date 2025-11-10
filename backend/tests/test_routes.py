import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, AsyncMock, MagicMock
import json

client = TestClient(app)

@pytest.fixture
def mock_db():
    with patch("app.db.db", new_callable=MagicMock) as mock_db:
        mock_db["sites"].find_one = AsyncMock(return_value={"_id": "615c7d8f3e3e3e3e3e3e3e3e", "url": "http://test.com"})
        mock_db["sites"].update_one = AsyncMock()
        mock_db["chats"].insert_one = AsyncMock()
        mock_db["bookings"].insert_one = AsyncMock()
        yield mock_db

def test_chat_endpoint_booking_e2e_success(mock_db):
    with (patch("app.routes.decide_action", new_callable=AsyncMock) as mock_decide_action,
         patch("app.routes.extract_booking_params", new_callable=AsyncMock) as mock_extract_booking_params,
         patch("app.routes.analyze_website_forms", new_callable=AsyncMock) as mock_analyze_forms,
         patch("app.routes.ai_map_fields", new_callable=AsyncMock) as mock_ai_map,
         patch("app.routes.auto_fill_and_submit_async", new_callable=AsyncMock) as mock_autofill,
         patch("app.routes.get_or_create_site", new_callable=AsyncMock) as mock_get_site,
         patch("app.db.save_booking", new_callable=AsyncMock) as mock_save_booking):

        # Setup mocks
        mock_decide_action.return_value = {"action_type": "booking", "message": "I'll book that."}
        mock_extract_booking_params.return_value = {"name": "John Doe", "email": "john@example.com"}
        mock_get_site.return_value = "615c7d8f3e3e3e3e3e3e3e3e"
        mock_analyze_forms.return_value = [{"fields": [{"name": "full_name"}, {"name": "email"}]}]
        mock_ai_map.return_value = {"full_name": "John Doe", "email": "john@example.com"}
        mock_autofill.return_value = {"status": "success", "message": "Form submitted."}

        # Make request
        response = client.post("/api/chat", json={
            "user_id": "test_user_success",
            "message": "Book a table for John Doe, email john@example.com",
            "current_url": "http://test.com"
        })

        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] is True
        assert data["result"]["status"] == "success"
        assert data["result"]["booking_saved_on_website"] is True
        assert "Form submitted." in data["result"]["message"]
        
        # Verify that save_booking was called correctly
        mock_save_booking.assert_called_once()
        saved_data = mock_save_booking.call_args[0][0]
        assert saved_data["name"] == "John Doe"
        assert saved_data["email"] == "john@example.com"
        assert saved_data["form_submitted"] is True

def test_chat_endpoint_booking_form_fail(mock_db):
    with (patch("app.routes.decide_action", new_callable=AsyncMock) as mock_decide_action,
         patch("app.routes.extract_booking_params", new_callable=AsyncMock) as mock_extract_booking_params,
         patch("app.routes.analyze_website_forms", new_callable=AsyncMock) as mock_analyze_forms,
         patch("app.routes.ai_map_fields", new_callable=AsyncMock) as mock_ai_map,
         patch("app.routes.auto_fill_and_submit_async", new_callable=AsyncMock) as mock_autofill,
         patch("app.routes.get_or_create_site", new_callable=AsyncMock) as mock_get_site,
         patch("app.db.save_booking", new_callable=AsyncMock) as mock_save_booking):

        # Setup mocks for failure case
        mock_decide_action.return_value = {"action_type": "booking"}
        mock_extract_booking_params.return_value = {"name": "Jane Doe"}
        mock_get_site.return_value = "615c7d8f3e3e3e3e3e3e3e3e"
        mock_analyze_forms.return_value = [{"fields": [{"name": "name"}]}]
        mock_ai_map.return_value = {"name": "Jane Doe"}
        mock_autofill.return_value = {"status": "failed", "message": "Could not find submit button."}

        # Make request
        response = client.post("/api/chat", json={
            "user_id": "test_user_fail",
            "message": "Book for Jane Doe",
            "current_url": "http://test.com"
        })

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert data["ok"] is True
        assert data["result"]["status"] == "failed"
        assert data["result"]["booking_saved_on_website"] is False
        assert "Could not find submit button" in data["result"]["message"]
        
        # Ensure booking was NOT saved
        mock_save_booking.assert_not_called()