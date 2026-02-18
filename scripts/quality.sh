#!/bin/bash
set -e

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "======================================="
echo "   Running All Quality Checks"
echo "======================================="
"$SCRIPT_DIR/format.sh"
"$SCRIPT_DIR/lint.sh"
"$SCRIPT_DIR/typecheck.sh"
"$SCRIPT_DIR/test.sh"
echo "======================================="
echo "  ✅ All Quality Checks Passed!"
echo "======================================="
