#!/usr/bin/env python
"""Run all tests and capture output to file."""
import subprocess
import sys

# Run pytest and capture all output
result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
    capture_output=True,
    text=True
)

# Write output to file
with open("pytest_output.log", "w") as f:
    f.write("STDOUT:\n")
    f.write(result.stdout)
    f.write("\n\nSTDERR:\n")
    f.write(result.stderr)
    f.write("\n\nReturn Code: " + str(result.returncode))

print("Pytest output written to pytest_output.log")
sys.exit(result.returncode)
