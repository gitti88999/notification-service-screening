# Notification Service Specification

## Overview

This service manages notification records and triggers delivery through one of three supported channels: email, SMS, or push. It stores notifications in memory and exposes CRUD and send endpoints.

## Notification payload

### Required fields
- `targetChannels`: array of channel descriptors (at least one)
- `message`: non-empty string

### Channel descriptor shape
Each element in `targetChannels` is an object with:
- `type`: one of `email`, `sms`, `push`
- `value`: recipient identifier
  - email: email address
  - sms: phone number
  - push: device token

### Validation
- `targetChannels` must be a non-empty array
- `message` must be a non-empty string
- Invalid payloads result in HTTP 400 with error details

## Notification model

Each notification object contains:
- `id`: integer
- `targetChannels`: list of channels
- `message`: string
- `status`: one of `pending`, `processing`, `sent`, `retry_pending`, `failed`
- `createdAt`: ISO timestamp
- `attempts`: integer
- `lastAttemptAt`: ISO timestamp or null
- `lastError`: last provider message or error string
- `smsSegments`: integer, computed for SMS notifications

## State machine

Notification lifecycle:

```
pending → processing → sent
       ↓
       → retry_pending (if TemporaryFailure)
       ↓
       → failed (if PermanentFailure or no channels)
```

### State transitions in `send_one()`:
1. **pending → processing**: Immediately upon entry to `send_one()`
2. **processing → sent**: After provider returns Success or any response (current behavior preserved)
3. **processing → retry_pending**: If provider returns `Result = "TemporaryFailure"` (NEW)
4. **processing → failed**: If provider returns `Result = "PermanentFailure"` OR no target channels OR unknown channel type (UPDATED)

### Retry behavior:
- `send_all()` only sends notifications with `status == pending`
- Notifications with `status == retry_pending` are NOT automatically retried in bulk sends; manual intervention or separate retry logic required
- Each send increments `attempts`

## Channel routing and delivery

### Channel selection
- **Only the first channel** (index 0) in `targetChannels` is delivered to
- Additional channels in the array are ignored in the current implementation
- This keeps delivery simple and deterministic

### Supported channels and behavior

#### email
- Valid recipient must contain `@`
- Provider returns one of:
  - `Result = "Success"` → status becomes `sent`
  - `Result = "TemporaryFailure"` → status becomes `retry_pending`
  - `Result = "PermanentFailure"` → status becomes `failed`

#### sms
- Valid recipient must be at least 7 characters
- Provider returns one of:
  - `Result = "Success"` → status becomes `sent`
  - `Result = "TemporaryFailure"` → status becomes `retry_pending`
  - `Result = "PermanentFailure"` → status becomes `failed`
- SMS segments are calculated at creation time (160-character limit, no word splitting)

#### push
- Valid recipient must be non-empty
- Provider returns one of:
  - `Result = "Success"` → status becomes `sent`
  - `Result = "TemporaryFailure"` → status becomes `retry_pending`
  - `Result = "PermanentFailure"` → status becomes `failed`

## Error handling

### Validation errors (HTTP 400)
- Missing or malformed `targetChannels`
- Missing or empty `message`
- Invalid channel type in `targetChannels`
- Empty `targetChannels` array

### Not-found errors (HTTP 404)
- Notification ID does not exist on GET, PUT, or single send

### Processing errors (notification-level)
- No target channels → status `failed`, `lastError = "No target channels"`
- Unsupported channel type → status `failed`, `lastError = "Unknown channel"`
- Provider-level invalid request → stored as structured response in `lastError`

## HTTP routes and status codes

### POST /notifications (Create)
- **Request**: `{ "targetChannels": [...], "message": "..." }`
- **Success**: HTTP 201, returns created notification object
- **Validation failure**: HTTP 400, returns error details

### GET /notifications (List all)
- **Success**: HTTP 200, returns array of notification objects

### GET /notifications/:id (Fetch one)
- **Success**: HTTP 200, returns notification object
- **Not found**: HTTP 404, `{ "error": "not found" }`

### PUT /notifications/:id (Update)
- **Request**: JSON object with fields to update
- **Success**: HTTP 200, returns updated notification object
- **Not found**: HTTP 404, `{ "error": "not found" }`

### POST /notifications/:id/send (Send single)
- **Success**: HTTP 200, returns updated notification object
- **Not found**: HTTP 404, `{ "error": "not found" }`

### POST /notifications/send-bulk (Send all pending)
- **Success**: HTTP 200, returns array of all notification objects (with updated statuses)

## Storage and persistence

- Notifications are stored in-memory in `storage.notifications`
- IDs are generated using a global `next_id` counter
- `storage.seed()` populates initial sample notifications on startup
- Persistence is ephemeral; a restart clears all state
- Thread-safety: synchronous execution assumed; simple list access for MVP

## Concurrency

- Current implementation uses synchronous, single-threaded execution
- No explicit locking required for MVP
- Storage operations are atomic at the Python operation level
- Concurrent HTTP requests are handled by Flask's default threading; notification objects are mutated in place without explicit synchronization

---

## Implementation priorities

1. **HTTP Status Code Fixes** (400 for bad payload, 201 for creation, 200 for single send)
2. **Payload Validation** (targetChannels and message)
3. **State Machine Logic** (TEMPORARY_FAILURE → retry_pending, PERMANENT_FAILURE → failed)
4. **Channel Delivery** (explicit first-channel-only routing)
5. **Error Message Consistency** (clear lastError values)
