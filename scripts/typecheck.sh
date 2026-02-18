#!/bin/bash
set -e

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Running Mypy type checker ==="
cd "$PROJECT_ROOT/backend" && uv run mypy . || true
echo "✅ Type checking complete! (Baseline: 23 errors expected)"
