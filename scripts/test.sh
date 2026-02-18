#!/bin/bash
set -e

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Running pytest with coverage ==="
cd "$PROJECT_ROOT/backend" && uv run pytest
echo "💡 Coverage report: backend/htmlcov/index.html"
echo "✅ Tests complete!"
