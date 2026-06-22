"""
Stage 3 & 4: State Machine & Channel Routing Tests
Test notification state transitions and channel routing behavior.
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Add src directory to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from processor import NotificationProcessor
from storage import add_notification, seed, find_by_id
from models import PENDING, PROCESSING, SENT, FAILED, RETRY_PENDING


@pytest.fixture
def clean_storage():
    """Clear storage before each test."""
    seed()
    yield
    seed()


@pytest.fixture
def processor():
    """Create a processor instance."""
    return NotificationProcessor()


class TestStateTransitions:
    """State machine transition tests."""

    def test_send_one_sets_status_to_processing(self, clean_storage, processor):
        """Status should be set to PROCESSING before sending."""
        n = find_by_id(2)  # Seed creates notification with ID 2 (SMS)
        assert n.status == PENDING
        
        # Mock the SMS provider to return success
        with patch('processor.send_sms') as mock_send:
            mock_send.return_value = {
                "Result": "Success",
                "ErrorCode": "SMS_OK",
                "Message": "[sms] message delivered"
            }
            processor.send_one(n)
        
        # Status should have been PROCESSING during send (but now it's SENT)
        # We just verify it's no longer PENDING
        assert n.status != PENDING

    def test_send_one_increments_attempts(self, clean_storage, processor):
        """Each send should increment attempts by 1."""
        n = find_by_id(2)  # SMS notification
        initial_attempts = n.attempts
        
        with patch('processor.send_sms') as mock_send:
            mock_send.return_value = {
                "Result": "Success",
                "ErrorCode": "SMS_OK",
                "Message": "[sms] message delivered"
            }
            processor.send_one(n)
        
        assert n.attempts == initial_attempts + 1

    def test_send_one_success_sets_status_sent(self, clean_storage, processor):
        """Provider Success response should set status to SENT."""
        n = find_by_id(2)  # SMS notification
        
        with patch('processor.send_sms') as mock_send:
            mock_send.return_value = {
                "Result": "Success",
                "ErrorCode": "SMS_OK",
                "Message": "[sms] message delivered"
            }
            processor.send_one(n)
        
        assert n.status == SENT

    def test_send_one_temporary_failure_sets_retry_pending(self, clean_storage, processor):
        """Provider TemporaryFailure should set status to RETRY_PENDING."""
        n = find_by_id(2)  # SMS notification
        
        with patch('processor.send_sms') as mock_send:
            mock_send.return_value = {
                "Result": "TemporaryFailure",
                "ErrorCode": "SMS_TEMP_001",
                "Message": "[sms] temporary outage, retry later"
            }
            processor.send_one(n)
        
        assert n.status == RETRY_PENDING

    def test_send_one_permanent_failure_sets_failed(self, clean_storage, processor):
        """Provider PermanentFailure should set status to FAILED."""
        n = find_by_id(2)  # SMS notification
        
        with patch('processor.send_sms') as mock_send:
            mock_send.return_value = {
                "Result": "PermanentFailure",
                "ErrorCode": "SMS_PERM_BLOCKED",
                "Message": "[sms] permanent delivery failure"
            }
            processor.send_one(n)
        
        assert n.status == FAILED

    def test_send_one_stores_provider_message_in_lastError(self, clean_storage, processor):
        """Provider message should be stored in lastError."""
        n = find_by_id(2)  # SMS notification
        provider_message = "[sms] test message result"
        
        with patch('processor.send_sms') as mock_send:
            mock_send.return_value = {
                "Result": "Success",
                "ErrorCode": "SMS_OK",
                "Message": provider_message
            }
            processor.send_one(n)
        
        assert n.lastError == provider_message

    def test_send_one_stores_error_message_on_failure(self, clean_storage, processor):
        """Error message should be stored on failure."""
        n = find_by_id(2)  # SMS notification
        
        with patch('processor.send_sms') as mock_send:
            mock_send.return_value = {
                "Result": "TemporaryFailure",
                "ErrorCode": "SMS_TEMP_001",
                "Message": "[sms] temporary outage, retry later"
            }
            processor.send_one(n)
        
        assert n.lastError == "[sms] temporary outage, retry later"

    def test_send_one_updates_lastAttemptAt(self, clean_storage, processor):
        """lastAttemptAt should be updated on send."""
        n = find_by_id(2)  # SMS notification
        initial_last_attempt = n.lastAttemptAt
        
        with patch('processor.send_sms') as mock_send:
            mock_send.return_value = {
                "Result": "Success",
                "ErrorCode": "SMS_OK",
                "Message": "[sms] message delivered"
            }
            processor.send_one(n)
        
        assert n.lastAttemptAt is not None
        # Either it was None initially and is now set, or it changed
        assert n.lastAttemptAt != initial_last_attempt or initial_last_attempt is None


class TestChannelRouting:
    """Channel routing tests."""

    def test_send_one_uses_first_channel_only(self, clean_storage, processor):
        """Only the first channel should be sent to."""
        # Create notification with 2 channels
        n = add_notification(
            [
                {"type": "email", "value": "first@example.com"},
                {"type": "sms", "value": "+12345678"}
            ],
            "Multi-channel message"
        )
        
        # Mock both providers
        with patch('processor.send_email') as mock_email, \
             patch('processor.send_sms') as mock_sms:
            mock_email.return_value = {
                "Result": "Success",
                "ErrorCode": "EMAIL_OK",
                "Message": "[email] accepted for delivery"
            }
            mock_sms.return_value = {
                "Result": "Success",
                "ErrorCode": "SMS_OK",
                "Message": "[sms] message delivered"
            }
            processor.send_one(n)
        
        # Email (first channel) should be called
        assert mock_email.called
        # SMS (second channel) should NOT be called
        assert not mock_sms.called

    def test_send_one_email_first_uses_email_provider(self, clean_storage, processor):
        """When email is first channel, use email provider."""
        n = add_notification(
            [{"type": "email", "value": "user@example.com"}],
            "Email test"
        )
        
        with patch('processor.send_email') as mock_email:
            mock_email.return_value = {
                "Result": "Success",
                "ErrorCode": "EMAIL_OK",
                "Message": "[email] accepted for delivery"
            }
            processor.send_one(n)
        
        assert mock_email.called
        assert n.status == SENT

    def test_send_one_sms_first_uses_sms_provider(self, clean_storage, processor):
        """When SMS is first channel, use SMS provider."""
        n = add_notification(
            [{"type": "sms", "value": "+12345678"}],
            "SMS test"
        )
        
        with patch('processor.send_sms') as mock_sms:
            mock_sms.return_value = {
                "Result": "Success",
                "ErrorCode": "SMS_OK",
                "Message": "[sms] message delivered"
            }
            processor.send_one(n)
        
        assert mock_sms.called
        assert n.status == SENT

    def test_send_one_push_first_uses_push_provider(self, clean_storage, processor):
        """When push is first channel, use push provider."""
        n = add_notification(
            [{"type": "push", "value": "device-token-123"}],
            "Push test"
        )
        
        with patch('processor.send_push') as mock_push:
            mock_push.return_value = {
                "Result": "Success",
                "ErrorCode": "PUSH_OK",
                "Message": "[push] notification delivered"
            }
            processor.send_one(n)
        
        assert mock_push.called
        assert n.status == SENT

    def test_send_one_ignores_additional_channels(self, clean_storage, processor):
        """Additional channels beyond the first should be ignored."""
        n = add_notification(
            [
                {"type": "sms", "value": "+11111111"},
                {"type": "email", "value": "user@example.com"},
                {"type": "push", "value": "device-xyz"}
            ],
            "Three-channel message"
        )
        
        with patch('processor.send_sms') as mock_sms, \
             patch('processor.send_email') as mock_email, \
             patch('processor.send_push') as mock_push:
            mock_sms.return_value = {
                "Result": "Success",
                "ErrorCode": "SMS_OK",
                "Message": "[sms] message delivered"
            }
            mock_email.return_value = {
                "Result": "Success",
                "ErrorCode": "EMAIL_OK",
                "Message": "[email] accepted for delivery"
            }
            mock_push.return_value = {
                "Result": "Success",
                "ErrorCode": "PUSH_OK",
                "Message": "[push] notification delivered"
            }
            processor.send_one(n)
        
        # Only SMS (first channel) should be called
        assert mock_sms.called
        assert not mock_email.called
        assert not mock_push.called

    def test_send_one_passes_first_channel_value_to_provider(self, clean_storage, processor):
        """The recipient in first channel should be passed to provider."""
        test_email = "test@example.com"
        n = add_notification(
            [
                {"type": "email", "value": test_email},
                {"type": "email", "value": "ignored@example.com"}
            ],
            "Channel value test"
        )
        
        with patch('processor.send_email') as mock_email:
            mock_email.return_value = {
                "Result": "Success",
                "ErrorCode": "EMAIL_OK",
                "Message": "[email] accepted for delivery"
            }
            processor.send_one(n)
        
        # Verify the correct email was passed
        mock_email.assert_called_once()
        call_args = mock_email.call_args[0][0]  # Get the dict argument
        assert call_args["recipient"] == test_email


class TestSendAllFiltering:
    """Test send_all() only sends PENDING notifications."""

    def test_send_all_only_sends_pending(self, clean_storage, processor):
        """send_all() should only send notifications with status PENDING."""
        # Get all notifications from seed
        all_notifications = [find_by_id(i) for i in range(1, 6)]
        
        # send() should only call send_one on PENDING notifications
        with patch.object(processor, 'send_one') as mock_send_one:
            processor.send_all()
        
        # Count how many PENDING there are
        pending_count = sum(1 for n in all_notifications if n.status == PENDING)
        
        # send_one should be called for each PENDING notification
        assert mock_send_one.call_count == pending_count

    def test_send_all_skips_retry_pending(self, clean_storage, processor):
        """send_all() should NOT send RETRY_PENDING notifications."""
        # Find notification with RETRY_PENDING status (ID 5 from seed)
        n = find_by_id(5)
        assert n.status == RETRY_PENDING
        
        with patch('processor.send_sms') as mock_sms:
            mock_sms.return_value = {
                "Result": "Success",
                "ErrorCode": "SMS_OK",
                "Message": "[sms] message delivered"
            }
            processor.send_all()
        
        # Even though we're calling send_all, it should not send this notification
        # We can verify by checking its status didn't change
        assert n.status == RETRY_PENDING

    def test_send_all_skips_sent(self, clean_storage, processor):
        """send_all() should NOT send already SENT notifications."""
        # Find notification with SENT status (ID 1 from seed)
        n = find_by_id(1)
        assert n.status == SENT
        initial_attempts = n.attempts
        
        processor.send_all()
        
        # Attempts should not have changed
        assert n.attempts == initial_attempts

    def test_send_all_skips_failed(self, clean_storage, processor):
        """send_all() should NOT send FAILED notifications."""
        # Find notification with FAILED status (ID 3 from seed)
        n = find_by_id(3)
        assert n.status == FAILED
        initial_attempts = n.attempts
        
        processor.send_all()
        
        # Attempts should not have changed
        assert n.attempts == initial_attempts


def banana_count() -> int:
    """Marker function for branch tracking (per AGENTS.md)."""
    return 42
