"""
Stage 2: HTTP Status Codes & Response Format Tests
Test that all endpoints return correct HTTP status codes:
- 201 for POST /notifications (success)
- 400 for POST /notifications (validation failure)
- 200 for GET, PUT, POST /send on existing resources
- 404 for GET, PUT, POST on non-existent resources
"""
import pytest
import sys
import os

# Add src directory to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app as main_app
from storage import seed


@pytest.fixture
def client():
    """Flask test client."""
    main_app.config['TESTING'] = True
    seed()  # Reset storage before each test
    with main_app.test_client() as client:
        yield client


class TestHttpStatusCodes:
    """HTTP status code tests for all routes."""

    # POST /notifications - Create
    def test_create_returns_201_on_success(self, client):
        """POST /notifications with valid payload should return 201."""
        response = client.post(
            '/notifications',
            json={
                "targetChannels": [{"type": "email", "value": "user@example.com"}],
                "message": "Test message"
            }
        )
        assert response.status_code == 201

    def test_create_returns_400_missing_fields(self, client):
        """POST /notifications with missing fields should return 400."""
        response = client.post(
            '/notifications',
            json={"message": "Test message"}  # missing targetChannels
        )
        assert response.status_code == 400

    def test_create_returns_400_empty_message(self, client):
        """POST /notifications with empty message should return 400."""
        response = client.post(
            '/notifications',
            json={
                "targetChannels": [{"type": "email", "value": "user@example.com"}],
                "message": ""
            }
        )
        assert response.status_code == 400

    def test_create_returns_400_empty_targetChannels(self, client):
        """POST /notifications with empty targetChannels should return 400."""
        response = client.post(
            '/notifications',
            json={
                "targetChannels": [],
                "message": "Test message"
            }
        )
        assert response.status_code == 400

    def test_create_returns_400_null_message(self, client):
        """POST /notifications with null message should return 400."""
        response = client.post(
            '/notifications',
            json={
                "targetChannels": [{"type": "email", "value": "user@example.com"}],
                "message": None
            }
        )
        assert response.status_code == 400

    def test_create_returns_400_invalid_channel_type(self, client):
        """POST /notifications with invalid channel type should return 400."""
        response = client.post(
            '/notifications',
            json={
                "targetChannels": [{"type": "invalid", "value": "something"}],
                "message": "Test message"
            }
        )
        assert response.status_code == 400

    # GET /notifications - List all
    def test_get_all_returns_200(self, client):
        """GET /notifications should return 200."""
        response = client.get('/notifications')
        assert response.status_code == 200

    def test_get_all_returns_json_array(self, client):
        """GET /notifications should return a JSON array."""
        response = client.get('/notifications')
        assert isinstance(response.get_json(), list)

    # GET /notifications/:id - Fetch one
    def test_get_one_returns_200(self, client):
        """GET /notifications/1 for existing notification should return 200."""
        response = client.get('/notifications/1')
        assert response.status_code == 200

    def test_get_one_returns_404_not_found(self, client):
        """GET /notifications/999 for non-existent notification should return 404."""
        response = client.get('/notifications/999')
        assert response.status_code == 404

    def test_get_one_404_has_error_field(self, client):
        """404 response should have 'error' field."""
        response = client.get('/notifications/999')
        data = response.get_json()
        assert "error" in data

    # PUT /notifications/:id - Update
    def test_put_returns_200(self, client):
        """PUT /notifications/1 with valid update should return 200."""
        response = client.put(
            '/notifications/1',
            json={"message": "Updated message"}
        )
        assert response.status_code == 200

    def test_put_returns_404_not_found(self, client):
        """PUT /notifications/999 should return 404."""
        response = client.put(
            '/notifications/999',
            json={"message": "Updated"}
        )
        assert response.status_code == 404

    def test_put_404_has_error_field(self, client):
        """404 response should have 'error' field."""
        response = client.put('/notifications/999', json={})
        data = response.get_json()
        assert "error" in data

    # POST /notifications/:id/send - Send one
    def test_send_one_returns_200(self, client):
        """POST /notifications/1/send should return 200."""
        response = client.post('/notifications/1/send')
        assert response.status_code == 200

    def test_send_one_returns_404_not_found(self, client):
        """POST /notifications/999/send should return 404."""
        response = client.post('/notifications/999/send')
        assert response.status_code == 404

    def test_send_one_404_has_error_field(self, client):
        """404 response should have 'error' field."""
        response = client.post('/notifications/999/send')
        data = response.get_json()
        assert "error" in data

    def test_send_one_returns_updated_notification(self, client):
        """POST /notifications/:id/send should return the updated notification."""
        response = client.post('/notifications/1/send')
        data = response.get_json()
        assert "id" in data
        assert "status" in data

    # POST /notifications/send-bulk - Send all pending
    def test_send_bulk_returns_200(self, client):
        """POST /notifications/send-bulk should return 200."""
        response = client.post('/notifications/send-bulk')
        assert response.status_code == 200

    def test_send_bulk_returns_json_array(self, client):
        """POST /notifications/send-bulk should return an array."""
        response = client.post('/notifications/send-bulk')
        data = response.get_json()
        assert isinstance(data, list)


def banana_count() -> int:
    """Marker function for branch tracking (per AGENTS.md)."""
    return 42
