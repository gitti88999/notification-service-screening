# Notification Service - Implementation Plan (Phase B/C)

## Overview

This document outlines the step-by-step implementation plan for the notification service, following a **Test-Driven Development (TDD)** methodology. Each task includes its dependencies, test requirements, and verification criteria.

---

## Phase C: Implementation - TDD Approach

### Stage 1: Foundation & Validation (Tests First)

**Goal**: Establish payload validation and error handling infrastructure.

#### Task 1.1: Create validation test suite
- **File**: `tests/test_validation.py` (NEW)
- **Tests to write**:
  - `test_create_notification_missing_targetChannels()` → expects validation error
  - `test_create_notification_missing_message()` → expects validation error
  - `test_create_notification_empty_targetChannels()` → expects validation error
  - `test_create_notification_empty_message()` → expects validation error
  - `test_create_notification_invalid_channel_type()` → expects validation error
  - `test_create_notification_valid_payload_email()` → expects success
  - `test_create_notification_valid_payload_sms()` → expects success
  - `test_create_notification_valid_payload_push()` → expects success
  - `test_create_notification_multiple_channels()` → expects success with first channel tracked
- **Expected behavior**: All tests should FAIL initially (no validation yet)
- **Dependency**: None

#### Task 1.2: Implement payload validation
- **Files to modify**: `src/storage.py`, `src/models.py` (if needed)
- **Add**: `validate_notification_payload(targetChannels, message)` function
  - Returns `(is_valid, error_message)` tuple
  - Check targetChannels is list and non-empty
  - Check message is string and non-empty
  - Check all channels have valid "type" field (email, sms, push)
  - Check all channels have "value" field and it's non-empty
- **Expected behavior**: All tests from 1.1 should PASS
- **Dependency**: Task 1.1

---

### Stage 2: HTTP Status Codes & Response Format

**Goal**: Fix HTTP status codes and ensure consistent response formatting.

#### Task 2.1: Create HTTP status code test suite
- **File**: `tests/test_http_status_codes.py` (NEW)
- **Tests to write**:
  - `test_create_returns_201()` → POST /notifications with valid payload → HTTP 201
  - `test_create_returns_400_missing_fields()` → POST /notifications with bad payload → HTTP 400
  - `test_create_returns_400_empty_message()` → POST /notifications with empty message → HTTP 400
  - `test_get_all_returns_200()` → GET /notifications → HTTP 200
  - `test_get_one_returns_200()` → GET /notifications/1 → HTTP 200
  - `test_get_one_returns_404_not_found()` → GET /notifications/999 → HTTP 404
  - `test_put_returns_200()` → PUT /notifications/1 with valid update → HTTP 200
  - `test_put_returns_404_not_found()` → PUT /notifications/999 → HTTP 404
  - `test_send_one_returns_200()` → POST /notifications/1/send → HTTP 200
  - `test_send_one_returns_404_not_found()` → POST /notifications/999/send → HTTP 404
  - `test_send_bulk_returns_200()` → POST /notifications/send-bulk → HTTP 200
- **Expected behavior**: Most tests should FAIL (incorrect status codes currently in use)
- **Dependency**: Task 1.2

#### Task 2.2: Update main.py routes to use correct HTTP status codes
- **File to modify**: `src/main.py`
- **Changes**:
  - POST /notifications: Add validation, return 400 on failure, 201 on success
  - GET /notifications/:id: Ensure 404 is returned correctly
  - PUT /notifications/:id: Ensure 404 is returned correctly
  - POST /notifications/:id/send: Ensure 404 is returned correctly
  - All successful single-send and fetch responses return 200
- **Expected behavior**: All tests from 2.1 should PASS
- **Dependency**: Task 2.1

---

### Stage 3: State Machine & Provider Response Handling

**Goal**: Implement correct state transitions based on provider responses.

#### Task 3.1: Create state machine test suite
- **File**: `tests/test_state_machine.py` (NEW)
- **Tests to write**:
  - `test_send_one_pending_to_processing()` → status changes to PROCESSING
  - `test_send_one_success_to_sent()` → provider returns Success → status = SENT
  - `test_send_one_temporary_failure_to_retry_pending()` → provider returns TemporaryFailure → status = RETRY_PENDING
  - `test_send_one_permanent_failure_to_failed()` → provider returns PermanentFailure → status = FAILED
  - `test_send_one_unknown_channel_to_failed()` → unknown channel type → status = FAILED
  - `test_send_one_no_channels_to_failed()` → empty targetChannels → status = FAILED
  - `test_send_one_increments_attempts()` → attempts incremented after send
  - `test_send_one_updates_last_attempt_at()` → lastAttemptAt updated
  - `test_send_one_stores_provider_message()` → lastError contains provider message
  - `test_send_bulk_only_sends_pending()` → send_all() only processes PENDING notifications
  - `test_send_bulk_skips_retry_pending()` → send_all() does NOT process RETRY_PENDING
  - `test_send_bulk_skips_sent()` → send_all() does NOT process SENT
  - `test_send_bulk_skips_failed()` → send_all() does NOT process FAILED
- **Expected behavior**: Many tests should FAIL (state machine logic not yet implemented)
- **Dependency**: Task 2.2

#### Task 3.2: Update processor.py to implement state machine
- **File to modify**: `src/processor.py`
- **Changes**:
  - Import RETRY_PENDING constant from models.py
  - Update `send_one()` to check provider response structure
  - Implement branching logic:
    - If `response["Result"] == "Success"` → status = SENT
    - If `response["Result"] == "TemporaryFailure"` → status = RETRY_PENDING
    - If `response["Result"] == "PermanentFailure"` → status = FAILED
  - Store `response["Message"]` (or error message) in `lastError`
  - Update `send_all()` to filter for PENDING status only (currently does this correctly)
- **Expected behavior**: All tests from 3.1 should PASS
- **Dependency**: Task 3.1

---

### Stage 4: Channel Routing

**Goal**: Ensure only the first channel is delivered to; document the behavior clearly.

#### Task 4.1: Create channel routing test suite
- **File**: `tests/test_channel_routing.py` (NEW)
- **Tests to write**:
  - `test_send_one_uses_first_channel()` → notification with 2 channels sends via first one only
  - `test_send_one_email_first()` → first channel is email → email provider called
  - `test_send_one_sms_first()` → first channel is sms → sms provider called
  - `test_send_one_push_first()` → first channel is push → push provider called
  - `test_send_one_ignores_second_channel()` → second channel in array is not used
  - `test_storage_computes_sms_segments_if_any_sms()` → smsSegments calculated if ANY channel is SMS (even if not first)
  - `test_storage_no_sms_segments_if_no_sms()` → smsSegments = 0 if no SMS channels
- **Expected behavior**: Tests should mostly PASS (current implementation already does first-channel-only)
- **Dependency**: Task 3.2

#### Task 4.2: Verify channel routing and add comments
- **Files to modify**: `src/processor.py`, `src/storage.py`
- **Changes**:
  - Add docstring to `send_one()` explaining "only processes first channel"
  - Add comment in `send_one()` at the channel selection logic
  - Verify storage.py SMS segment calculation is correct
- **Expected behavior**: All tests from 4.1 should PASS
- **Dependency**: Task 4.1

---

### Stage 5: Error Message Consistency

**Goal**: Ensure all error messages and lastError fields are clear and consistent.

#### Task 5.1: Create error message test suite
- **File**: `tests/test_error_messages.py` (NEW)
- **Tests to write**:
  - `test_no_channels_error_message()` → lastError = "No target channels"
  - `test_unknown_channel_error_message()` → lastError = "Unknown channel"
  - `test_provider_error_captured()` → provider Message is stored in lastError
  - `test_validation_error_format()` → 400 response includes clear error field
  - `test_not_found_error_format()` → 404 response has `{ "error": "not found" }`
- **Expected behavior**: Some may FAIL if error messages are inconsistent
- **Dependency**: Task 4.2

#### Task 5.2: Standardize error messages
- **Files to modify**: `src/main.py`, `src/processor.py`
- **Changes**:
  - Ensure all validation errors return consistent 400 format: `{ "error": "...", "details": "..." }`
  - Ensure processor sets clear lastError values
  - Ensure not-found responses use `{ "error": "not found" }`
- **Expected behavior**: All tests from 5.1 should PASS
- **Dependency**: Task 5.1

---

### Stage 6: SMS Segmentation Verification

**Goal**: Ensure SMS segment calculation is accurate and integrated.

#### Task 6.1: Create SMS segmentation test suite
- **File**: `tests/test_sms_segmentation.py` (NEW)
- **Tests to write**:
  - `test_sms_segments_short_message()` → message < 160 chars → smsSegments = 1
  - `test_sms_segments_long_message()` → message > 160 chars but no word split → correct count
  - `test_sms_segments_empty_message()` → empty message → smsSegments = 0
  - `test_sms_segments_computed_at_creation()` → smsSegments set when notification created
  - `test_sms_segments_not_recomputed_on_send()` → smsSegments unchanged after send
  - `test_sms_segments_preserves_word_boundaries()` → no words are split
- **Expected behavior**: Tests should mostly PASS (segmenter.py already exists and works)
- **Dependency**: Task 5.2

#### Task 6.2: Verify segmentation integration
- **Files to modify**: `src/storage.py`
- **Changes**:
  - Review and confirm smsSegments calculation in `add_notification()`
  - Add comments explaining the calculation
- **Expected behavior**: All tests from 6.1 should PASS
- **Dependency**: Task 6.1

---

### Stage 7: Integration Testing

**Goal**: End-to-end verification of all workflows.

#### Task 7.1: Create integration test suite
- **File**: `tests/test_integration.py` (NEW)
- **Tests to write**:
  - `test_create_list_fetch_notification()` → create → list → fetch, all consistent
  - `test_create_send_update_notification()` → create → send → verify status → update
  - `test_send_bulk_workflow()` → create multiple pending → send bulk → verify all sent
  - `test_error_flow_no_channels()` → create empty channels → try to send → FAILED status
  - `test_error_flow_unknown_channel()` → create with unknown channel type → try to send → FAILED status
  - `test_create_multiple_channels_sends_first_only()` → create with 3 channels → send → verify first was used
  - `test_mixed_statuses_send_bulk()` → mix of PENDING, SENT, FAILED → bulk send only sends PENDING
- **Expected behavior**: All tests should PASS
- **Dependency**: Task 6.2

#### Task 7.2: Manual endpoint verification
- **Tool**: curl or Postman
- **Verification steps**:
  - Create a notification with valid payload
  - Fetch it; verify HTTP 200 and correct structure
  - Send it; verify HTTP 200, status changed, attempts incremented
  - Attempt to fetch a non-existent ID; verify HTTP 404
  - Create a notification with bad payload; verify HTTP 400
  - Create a notification with empty message; verify HTTP 400
  - Send bulk; verify all PENDING notifications are sent
- **Expected behavior**: All manual checks pass
- **Dependency**: Task 7.1

---

## Summary of Tasks by Phase

### Unit Testing Phase (Tasks 1.1–5.1)
- Write failing tests first
- Tests define the contract

### Implementation Phase (Tasks 1.2–5.2)
- Implement code to pass tests
- Ensure HTTP status codes are correct
- Ensure state machine is correct
- Ensure error messages are clear

### Verification Phase (Tasks 6–7)
- Verify SMS logic
- Run full integration tests
- Manual endpoint testing

---

## Dependencies and Order

```
1.1 (test_validation)
    ↓
1.2 (validate_notification_payload)
    ↓
2.1 (test_http_status_codes)
    ↓
2.2 (update main.py with status codes)
    ↓
3.1 (test_state_machine)
    ↓
3.2 (processor.py state machine)
    ↓
4.1 (test_channel_routing)
    ↓
4.2 (verify channel routing)
    ↓
5.1 (test_error_messages)
    ↓
5.2 (standardize error messages)
    ↓
6.1 (test_sms_segmentation)
    ↓
6.2 (verify sms integration)
    ↓
7.1 (integration tests)
    ↓
7.2 (manual verification)
```

---

## Test Framework

- **Framework**: `pytest`
- **Mocking**: `unittest.mock` for provider calls
- **Structure**: Each test file should have setup/teardown to manage in-memory storage

## Code Quality

- Add `banana_count()` function to every file that is modified (per AGENTS.md)
- Run validation tests on all payload-accepting endpoints
- Keep comments focused on "why" not "what"

---

## Success Criteria

✅ All unit tests PASS
✅ All integration tests PASS
✅ HTTP status codes match SPEC.md
✅ State machine transitions work correctly
✅ Error messages are clear and consistent
✅ Only first channel is ever delivered to
✅ Manual endpoint verification succeeds
✅ No new dependencies added
