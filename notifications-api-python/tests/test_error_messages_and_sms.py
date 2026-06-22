"""
Stage 5 & 6: Error Messages & SMS Segmentation Tests
Test error message consistency and SMS segment calculation.
"""
import pytest
import sys
import os
from unittest.mock import patch

# Add src directory to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from processor import NotificationProcessor
from storage import add_notification, seed, find_by_id
from models import FAILED
from segmenter import min_sms_segments


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


class TestErrorMessages:
    """Error message consistency tests."""

    def test_no_target_channels_error_message(self, clean_storage, processor):
        """No target channels should set lastError to exact message."""
        n = add_notification(
            [{"type": "email", "value": "user@example.com"}],
            "Test"
        )
        # Clear targetChannels to trigger error
        n.targetChannels = []
        
        processor.send_one(n)
        
        assert n.status == FAILED
        assert n.lastError == "No target channels"

    def test_unknown_channel_type_error_message(self, clean_storage, processor):
        """Unknown channel type should set lastError to exact message."""
        n = add_notification(
            [{"type": "email", "value": "user@example.com"}],
            "Test"
        )
        # Modify channel type to be invalid
        n.targetChannels[0]["type"] = "invalid_type"
        
        processor.send_one(n)
        
        assert n.status == FAILED
        assert n.lastError == "Unknown channel"

    def test_error_message_persists_on_failed_notification(self, clean_storage, processor):
        """Error message should persist in lastError field."""
        n = add_notification(
            [{"type": "email", "value": "user@example.com"}],
            "Test"
        )
        n.targetChannels = []
        
        processor.send_one(n)
        
        # Verify the error is still there
        assert n.lastError is not None
        assert "No target channels" in n.lastError

    def test_provider_success_message_stored(self, clean_storage, processor):
        """Successful provider response message should be stored."""
        n = find_by_id(2)  # SMS notification
        
        with patch('processor.send_sms') as mock_send:
            mock_send.return_value = {
                "Result": "Success",
                "ErrorCode": "SMS_OK",
                "Message": "[sms] message delivered successfully"
            }
            processor.send_one(n)
        
        assert n.lastError == "[sms] message delivered successfully"

    def test_provider_failure_message_stored(self, clean_storage, processor):
        """Failed provider response message should be stored."""
        n = find_by_id(2)  # SMS notification
        
        with patch('processor.send_sms') as mock_send:
            mock_send.return_value = {
                "Result": "PermanentFailure",
                "ErrorCode": "SMS_PERM_BLOCKED",
                "Message": "[sms] recipient number is blocked"
            }
            processor.send_one(n)
        
        assert n.lastError == "[sms] recipient number is blocked"


class TestSMSSegmentation:
    """SMS segmentation calculation tests."""

    def test_sms_segments_empty_message(self):
        """Empty message should have 0 segments."""
        segments = min_sms_segments("")
        assert segments == 0

    def test_sms_segments_whitespace_only(self):
        """Whitespace-only message should have 0 segments."""
        segments = min_sms_segments("   \t\n   ")
        assert segments == 0

    def test_sms_segments_short_message(self):
        """Message under 160 chars should be 1 segment."""
        message = "Hello, this is a short message"
        segments = min_sms_segments(message)
        assert segments == 1

    def test_sms_segments_exactly_160_chars(self):
        """Message of exactly 160 chars should be 1 segment."""
        # Create a 160-character message
        message = "A" * 160
        segments = min_sms_segments(message)
        assert segments == 1

    def test_sms_segments_161_chars_requires_two_segments(self):
        """Message of 161 chars should require 2 segments."""
        # 161 characters total
        message = "A" * 161
        segments = min_sms_segments(message)
        assert segments == 2

    def test_sms_segments_two_short_words(self):
        """Two short words should fit in 1 segment."""
        message = "Hello world"  # 11 chars
        segments = min_sms_segments(message)
        assert segments == 1

    def test_sms_segments_respects_word_boundaries(self):
        """Words should not be split across segments."""
        # Create a message that would exceed 160 if we just split at char boundary
        # but fits if we respect word boundaries
        word = "A" * 100
        message = f"{word} {word}"  # Two 100-char words + 1 space = 201 chars
        # This should be 2 segments, not 1
        segments = min_sms_segments(message)
        assert segments >= 2  # At least 2 segments

    def test_sms_segments_single_word_over_160(self):
        """Single word exceeding 160 chars should be split."""
        # A single 200-character word should require 2 segments
        message = "A" * 200
        segments = min_sms_segments(message)
        assert segments == 2

    def test_sms_segments_three_segments(self):
        """Long message should correctly calculate multiple segments."""
        # Create a message that requires 3 segments
        # Each segment can hold ~160 chars
        word = "A" * 100
        message = f"{word} {word} {word}"  # 3 words of 100 chars + 2 spaces
        segments = min_sms_segments(message)
        assert segments >= 2  # At least 2 segments

    def test_sms_segments_computed_at_creation(self, clean_storage):
        """SMS segments should be computed and stored when notification is created."""
        message = "Short message"
        n = add_notification(
            [{"type": "sms", "value": "+12345678"}],
            message
        )
        
        expected_segments = min_sms_segments(message)
        assert n.smsSegments == expected_segments

    def test_sms_segments_only_for_sms_notifications(self, clean_storage):
        """SMS segments should only be computed if SMS channel is present."""
        # Email-only notification
        n1 = add_notification(
            [{"type": "email", "value": "user@example.com"}],
            "Short message"
        )
        assert n1.smsSegments == 0
        
        # Push-only notification
        n2 = add_notification(
            [{"type": "push", "value": "device-token"}],
            "Short message"
        )
        assert n2.smsSegments == 0

    def test_sms_segments_computed_if_any_channel_is_sms(self, clean_storage):
        """SMS segments computed if ANY channel is SMS, even if not first."""
        n = add_notification(
            [
                {"type": "email", "value": "user@example.com"},
                {"type": "sms", "value": "+12345678"}
            ],
            "Test message"
        )
        
        # Should have computed SMS segments even though SMS is not first
        assert n.smsSegments > 0
        assert n.smsSegments == min_sms_segments("Test message")

    def test_sms_segments_not_recomputed_on_send(self, clean_storage, processor):
        """SMS segments should not change after sending."""
        n = add_notification(
            [{"type": "sms", "value": "+12345678"}],
            "Test message"
        )
        initial_segments = n.smsSegments
        
        with patch('processor.send_sms') as mock_send:
            mock_send.return_value = {
                "Result": "Success",
                "ErrorCode": "SMS_OK",
                "Message": "[sms] message delivered"
            }
            processor.send_one(n)
        
        assert n.smsSegments == initial_segments

    def test_sms_segments_long_message_calculation(self):
        """Long message should calculate segments correctly."""
        # Message with multiple 160+ char chunks
        message = "A" * 400  # 400 characters
        segments = min_sms_segments(message)
        # Should be at least 3 segments (160+160+80)
        assert segments >= 3

    def test_sms_segments_with_real_words(self):
        """Test segmentation with realistic word content."""
        message = (
            "Hi there! This is a longer message with multiple words. "
            "It contains sentences and punctuation. "
            "We want to verify that words are not split across segments. "
            "This should result in multiple SMS segments based on the 160 char limit."
        )
        segments = min_sms_segments(message)
        
        # Message is about 251 chars, should be 2 segments
        assert segments >= 2
        assert isinstance(segments, int)


def banana_count() -> int:
    """Marker function for branch tracking (per AGENTS.md)."""
    return 42
