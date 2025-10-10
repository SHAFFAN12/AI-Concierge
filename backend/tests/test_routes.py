from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, AsyncMock

client = TestClient(app)

def test_chat_endpoint_booking():
    with (patch("app.routes.decide_action", new_callable=AsyncMock) as mock_decide_action,
         patch("app.routes.extract_booking_params", new_callable=AsyncMock) as mock_extract_booking_params,
         patch("app.routes.analyze_website_forms", new_callable=AsyncMock) as mock_analyze_website_forms,
         patch("app.routes.ai_map_fields", new_callable=AsyncMock) as mock_ai_map_fields,
         patch("app.routes.auto_fill_and_submit_async", new_callable=AsyncMock) as mock_auto_fill_and_submit_async,
         patch("app.routes.get_or_create_site", new_callable=AsyncMock) as mock_get_or_create_site,
         patch("app.db.db", new_callable=AsyncMock) as mock_db):

        mock_decide_action.return_value = {"action_type": "booking"}
        mock_extract_booking_params.return_value = {"name": "test", "email": "test@test.com"}
        mock_analyze_website_forms.return_value = [{"action": "/book", "method": "post", "fields": [{"name": "name", "type": "text"}, {"name": "email", "type": "email"}]}]
        mock_ai_map_fields.return_value = {"name": "test", "email": "test@test.com"}
        mock_auto_fill_and_submit_async.return_value = {"status": "success"}
        mock_get_or_create_site.return_value = "615c7d8f3e3e3e3e3e3e3e3e"
        mock_db["sites"].find_one = AsyncMock(return_value={"_id": "615c7d8f3e3e3e3e3e3e3e3e", "url": "http://test.com"})
        mock_db["sites"].update_one = AsyncMock()
        mock_db["chats"].insert_one = AsyncMock()


        response = client.post("/api/chat", json={"user_id": "test_user", "message": "book a table", "current_url": "http://test.com"})

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["result"]["status"] == "success"
        assert data["result"]["booking_saved_on_website"] is True