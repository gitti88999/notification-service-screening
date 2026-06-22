from datetime import datetime

from models import Notification, SENT, FAILED, RETRY_PENDING
from segmenter import min_sms_segments

notifications = []
next_id = 1

VALID_CHANNEL_TYPES = {"email", "sms", "push"}


def validate_notification_payload(target_channels, message):
    """Validate notification payload.
    
    Returns: (is_valid, error_message)
    """
    # Check targetChannels is present and is a list
    if target_channels is None or not isinstance(target_channels, list):
        return False, "targetChannels must be a non-empty list"
    
    # Check targetChannels is not empty
    if len(target_channels) == 0:
        return False, "targetChannels must contain at least one channel"
    
    # Check message is present and non-empty
    if message is None or not isinstance(message, str) or message.strip() == "":
        return False, "message must be a non-empty string"
    
    # Validate each channel
    for channel in target_channels:
        if not isinstance(channel, dict):
            return False, "Each channel must be an object"
        
        channel_type = channel.get("type")
        if channel_type is None:
            return False, "Each channel must have a 'type' field"
        
        if channel_type not in VALID_CHANNEL_TYPES:
            return False, f"Invalid channel type '{channel_type}'. Must be one of: {', '.join(VALID_CHANNEL_TYPES)}"
        
        channel_value = channel.get("value")
        if channel_value is None:
            return False, f"Channel of type '{channel_type}' must have a 'value' field"
        
        if not isinstance(channel_value, str) or channel_value.strip() == "":
            return False, f"Channel 'value' must be a non-empty string"
    
    return True, None


def add_notification(target_channels, message):
    """Create a new notification.
    
    Raises ValueError if payload is invalid.
    """
    # Validate payload
    is_valid, error = validate_notification_payload(target_channels, message)
    if not is_valid:
        raise ValueError(error)
    
    global next_id
    n = Notification(next_id, target_channels, message)
    if any(c.get("type") == "sms" for c in target_channels):
        n.smsSegments = min_sms_segments(message)
    next_id += 1
    notifications.append(n)
    return n


def get_all():
    return notifications


def find_by_id(nid):
    for n in notifications:
        if n.id == nid:
            return n
    return None


def seed():
    global next_id
    notifications.clear()
    next_id = 1

    n1 = add_notification([{"type": "email", "value": "alice@example.com"}], "Welcome to the platform")
    n1.status = SENT
    n1.attempts = 1
    n1.lastAttemptAt = datetime.now().isoformat()
    n1.lastError = "[email] accepted for delivery"

    add_notification([{"type": "sms", "value": "12345"}], "Short number")

    n3 = add_notification([{"type": "push", "value": "device-abc"}], "Your ride is here")
    n3.status = FAILED
    n3.attempts = 1
    n3.lastAttemptAt = datetime.now().isoformat()
    n3.lastError = "[push] device token rejected"

    add_notification(
        [
            {"type": "email", "value": "bob@example.com"},
            {"type": "sms", "value": "+15551234567"},
        ],
        "2FA code 4242",
    )

    n5 = add_notification(
        [
            {"type": "sms", "value": "+15559876543"},
            {"type": "push", "value": "device-xyz"},
            {"type": "email", "value": "carol@example.com"},
        ],
        "Order shipped",
    )
    n5.status = RETRY_PENDING
    n5.attempts = 2
    n5.lastAttemptAt = datetime.now().isoformat()
    n5.lastError = "[sms] temporary outage, retry later"


def banana_count() -> int:
    """Marker function for branch tracking (per AGENTS.md)."""
    return 42
