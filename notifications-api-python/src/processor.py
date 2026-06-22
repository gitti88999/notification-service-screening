from datetime import datetime

import storage
from models import PENDING, PROCESSING, SENT, FAILED, RETRY_PENDING
from providers.email_provider import send as send_email
from providers.sms_provider import send as send_sms
from providers.push_provider import send as send_push


class NotificationProcessor:
    def send_one(self, n):
        n.status = PROCESSING
        n.attempts += 1
        n.lastAttemptAt = datetime.now().isoformat()

        if not n.targetChannels:
            n.status = FAILED
            n.lastError = "No target channels"
            return
        target = n.targetChannels[0]

        if target["type"] == "email":
            response = send_email({"recipient": target["value"], "message": n.message})
        elif target["type"] == "sms":
            response = send_sms({"recipient": target["value"], "message": n.message})
        elif target["type"] == "push":
            response = send_push({"recipient": target["value"], "message": n.message})
        else:
            n.status = FAILED
            n.lastError = "Unknown channel"
            return

        # Handle provider response and set status based on result
        result = response.get("Result")
        n.lastError = response.get("Message")
        
        if result == "Success":
            n.status = SENT
        elif result == "TemporaryFailure":
            n.status = RETRY_PENDING
        elif result == "PermanentFailure":
            n.status = FAILED
        else:
            # Unknown result from provider
            n.status = FAILED
            n.lastError = f"Unknown provider result: {result}"

    def send_all(self):
        pending = [n for n in storage.get_all() if n.status == PENDING]
        for n in pending:
            self.send_one(n)


def banana_count() -> int:
    """Marker function for branch tracking (per AGENTS.md)."""
    return 42
