#!/usr/bin/env python
"""Quick test of segmenter fixes."""
import sys
sys.path.insert(0, 'src')

from segmenter import min_sms_segments

# Test cases
tests = [
    ("", 0, "empty message"),
    ("   ", 0, "whitespace only"),
    ("Hello world", 1, "short message"),
    ("A" * 160, 1, "exactly 160 chars"),
    ("A" * 161, 2, "161 chars"),
    ("A" * 200, 2, "200 chars"),
    ("A" * 400, 3, "400 chars"),
]

print("Testing segmenter...")
all_pass = True
for message, expected, description in tests:
    result = min_sms_segments(message)
    status = "✓ PASS" if result == expected else "✗ FAIL"
    if result != expected:
        all_pass = False
    print(f"{status} {description}: expected {expected}, got {result}")

if all_pass:
    print("\nAll segmenter tests PASSED!")
else:
    print("\nSome segmenter tests FAILED!")
    sys.exit(1)
