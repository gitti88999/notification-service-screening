# Notification Service Screening - Notes

## Repository overview

This workspace contains three implementations of a notification API:

- `notifications-api-dotnet/` - .NET implementation
- `notifications-api-python/` - Python implementation
- `notifications-api-typescript/` - TypeScript implementation

The current screening target is the Python implementation in `notifications-api-python/`.

## Python app structure

- `notifications-api-python/README.md`
  - Describes install and run instructions, plus API endpoints.
- `notifications-api-python/AGENTS.md`
  - Contains project house rules and agent guidance for editing the repo.
- `notifications-api-python/requirements.txt`
  - Lists dependencies.
- `notifications-api-python/src/`
  - `main.py` - Flask app setup and HTTP route handlers.
  - `models.py` - Data shapes for notifications and channels.
  - `processor.py` - Notification send flow.
  - `segmenter.py` - SMS message segmentation.
  - `storage.py` - In-memory storage and seeded data.
  - `providers/` - Channel-specific delivery modules:
    - `email_provider.py`
    - `push_provider.py`
    - `sms_provider.py`

## Current behavior and architecture

- The service exposes CRUD routes for notifications plus send operations:
  - `POST /notifications`
  - `GET /notifications`
  - `GET /notifications/:id`
  - `PUT /notifications/:id`
  - `POST /notifications/:id/send`
  - `POST /notifications/send-bulk`
- Notifications are held in-memory only; restarting resets state.
- Delivery is abstracted by provider modules.
- There is an existing agent note about not adding dependencies unless necessary and preserving current route shapes.

## Phase A Complete

### Documents created:
- `SPEC.md` - Complete specification with clarifications on:
  - Payload validation requirements (targetChannels non-empty array, message non-empty string)
  - State machine: pending → processing → sent/retry_pending/failed
  - TemporaryFailure → retry_pending; PermanentFailure → failed
  - Channel routing: Only first channel (index 0) is delivered to
  - HTTP status codes: 400 for bad payload, 201 for creation, 200 for success, 404 for not found
  - Error handling and storage semantics

- `IMPLEMENTATION_PLAN.md` - TDD-first step-by-step plan with 7 stages:
  1. Validation infrastructure (tests first)
  2. HTTP status code fixes
  3. State machine implementation
  4. Channel routing verification
  5. Error message consistency
  6. SMS segmentation verification
  7. Integration and manual testing

### Key architectural decisions:
- In-memory only; no persistence
- Synchronous execution, no explicit concurrency locking (MVP)
- Only first channel processed; additional channels ignored
- Retry semantics: retry_pending requires manual retry, not auto-retried in bulk
- HTTP 400 for validation failures, 404 for not found
- Tests written first (TDD), then implementation