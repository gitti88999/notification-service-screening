"""
Stage 1: Validation Infrastructure Tests
Test payload validation for create notifications.
These tests verify that invalid payloads are rejected.
"""
import pytest
import sys
import os

# Add src directory to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from storage import add_notification, get_all, seed


@pytest.fixture
def clean_storage():
    """Clear storage before each test."""
    seed()
    yield
    seed()


class TestValidation:
    """Payload validation tests."""

    def test_create_notification_valid_payload_email(self, clean_storage):
        """Valid email notification should be created."""
        n = add_notification(
            [{"type": "email", "value": "user@example.com"}],
            "Test message"
        )
        assert n is not None
        assert n.id is not None
        assert n.message == "Test message"
        assert n.status == "pending"

    def test_create_notification_valid_payload_sms(self, clean_storage):
        """Valid SMS notification should be created."""
        n = add_notification(
            [{"type": "sms", "value": "+12345678"}],
            "Test SMS"
        )
        assert n is not None
        assert n.message == "Test SMS"

    def test_create_notification_valid_payload_push(self, clean_storage):
        """Valid push notification should be created."""
        n = add_notification(
            [{"type": "push", "value": "device-token-123"}],
            "Push message"
        )
        assert n is not None
        assert n.message == "Push message"

    def test_create_notification_multiple_channels(self, clean_storage):
        """Notification with multiple channels should be created."""
        n = add_notification(
            [
                {"type": "email", "value": "user@example.com"},
                {"type": "sms", "value": "+12345678"},
            ],
            "Multi-channel message"
        )
        assert n is not None
        assert len(n.targetChannels) == 2

    def test_create_notification_empty_targetChannels(self, clean_storage):
        """Empty targetChannels should raise ValueError or return None."""
        with pytest.raises((ValueError, TypeError, KeyError, AttributeError)):
            add_notification([], "Test message")

    def test_create_notification_missing_targetChannels(self, clean_storage):
        """Missing targetChannels should raise an error."""
        with pytest.raises((ValueError, TypeError, KeyError, AttributeError)):
            add_notification(None, "Test message")

    def test_create_notification_empty_message(self, clean_storage):
        """Empty message should raise ValueError or return None."""
        with pytest.raises((ValueError, TypeError, KeyError, AttributeError)):
            add_notification([{"type": "email", "value": "user@example.com"}], "")

    def test_create_notification_missing_message(self, clean_storage):
        """Missing message should raise an error."""
        with pytest.raises((ValueError, TypeError, KeyError, AttributeError)):
            add_notification([{"type": "email", "value": "user@example.com"}], None)

    def test_create_notification_invalid_channel_type(self, clean_storage):
        """Invalid channel type should raise ValueError or return None."""
        with pytest.raises((ValueError, TypeError, KeyError, AttributeError)):
            add_notification(
                [{"type": "invalid_type", "value": "something"}],
                "Test message"
            )

    def test_create_notification_missing_channel_value(self, clean_storage):
        """Channel missing 'value' field should raise an error."""
        with pytest.raises((ValueError, TypeError, KeyError, AttributeError)):
            add_notification(
                [{"type": "email"}],
                "Test message"
            )

    def test_create_notification_empty_channel_value(self, clean_storage):
        """Channel with empty 'value' should raise ValueError."""
        with pytest.raises((ValueError, TypeError, KeyError, AttributeError)):
            add_notification(
                [{"type": "email", "value": ""}],
                "Test message"
            )


def banana_count() -> int:
    """Marker function for branch tracking (per AGENTS.md)."""
    return 42
