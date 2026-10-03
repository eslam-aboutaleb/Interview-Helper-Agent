#!/usr/bin/env bash
#
# Run the backend test suite under coverage and enforce the coverage gate.
#
# Coverage is driven by the `coverage` tool rather than pytest-cov flags in
# addopts. pytest-cov loses import tracking when pytest is handed a directory
# argument in this environment and silently reports 0% for every module, so
# the gate would always fail for the wrong reason. `coverage run` measures
# correctly and is what .coveragerc configures.
#
# Usage:
#   ./scripts/check_coverage.sh              # run tests, report, enforce 90%
#   ./scripts/check_coverage.sh --no-tests   # re-report existing .coverage
#
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-.venv/bin/python}"
COVERAGE="${COVERAGE:-.venv/bin/coverage}"

if [ ! -x "$PYTHON" ]; then
  echo "error: $PYTHON not found. Create the venv or set PYTHON=..." >&2
  exit 1
fi

rm -f .coverage

if [ "${1:-}" != "--no-tests" ]; then
  "$COVERAGE" run --source=. -m pytest tests/
fi

echo
"$COVERAGE" report
status=$?

if [ "$status" -ne 0 ]; then
  echo "coverage gate failed (see .coveragerc [report] fail_under)" >&2
fi
exit "$status"
