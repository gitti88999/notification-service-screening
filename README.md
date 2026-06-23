# Notification Service Task

## How I did it
* I worked with a TDD workflow. I wrote the tests first for each stage, watched them fail (RED), and then implemented the code to make them pass (GREEN).
* I built a state machine in `processor.py` to handle the notification statuses based on the provider responses (Success, TemporaryFailure, PermanentFailure) and update the logs.
* I fixed the SMS segment algorithm in `segmenter.py` so it can split words. I fixed the edge case where words longer than 160 characters caused it to return 0 or crash.
* I added input validation at the API route (`POST /notifications`) to return a 400 Bad Request immediately if the payload is broken.

## What differed
* **Then vs. Now**: When I first did this task as a screening assignment before the course, I just focused on writing basic code that "works" for the happy path. Returning to it now, the course gave me a deep perspective.
* **Architecture & Patterns**: Instead of writing loose functions, I implemented a state machine to handle error states and retries. 
* **TDD Mindset**: In the first attempt, I barely thought about edge cases. This time, working with TDD forced me to think about failures and boundaries *before* writing a single line of application code, resulting in 65 passed tests. It showed me how much my internal code quality and architectural thinking have grown.

## Honest feedback
* The task was a really good test of backend logic and handling edge cases.
* Figuring out the dynamic word splitting for the SMS segmenter was a bit tricky at first, and waiting for the provider simulated delays made the tests run a bit slow in the terminal, but it was great to see all 65 tests pass in the end.

## Running Tests
Run this in PowerShell:
```powershell
$env:PYTHONPATH="src"
python -m pytest tests/ -v