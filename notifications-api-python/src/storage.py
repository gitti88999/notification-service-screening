from datetime import datetime

from models import Notification, SENT, FAILED, RETRY_PENDING
from segmenter import min_sms_segments

notifications = []
next_id = 1


def add_notification(target_channels, message):
    global next_id

    if not isinstance(target_channels, list) or not target_channels:
        raise ValueError("targetChannels must be a non-empty list")

    if not isinstance(message, str) or not message.strip():
        raise ValueError("message must be a non-empty string")

    for channel in target_channels:
        if not isinstance(channel, dict):
            raise ValueError("each target channel must be an object")

        channel_type = channel.get("type")
        if channel_type not in {"email", "sms", "push"}:
            raise ValueError("invalid channel type")

        channel_value = channel.get("value")
        if not isinstance(channel_value, str) or not channel_value.strip():
            raise ValueError("channel value is required")

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
