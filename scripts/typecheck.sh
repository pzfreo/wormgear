#!/bin/bash
#
# Run type checking for both Python (mypy) and TypeScript (tsc).
#
# Usage:
#   bash scripts/typecheck.sh         # Run all type checks
#   bash scripts/typecheck.sh python  # Python only
#   bash scripts/typecheck.sh ts      # TypeScript only
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

check_python() {
    echo "=== Python Type Checking (mypy) ==="
    cd "$PROJECT_ROOT"

    if ! command -v mypy &> /dev/null; then
        echo "mypy not found. Install with: pip install mypy"
        return 1
    fi

    mypy src/wormgear --ignore-missing-imports
    echo "Python type check passed."
}

check_typescript() {
    echo "=== TypeScript Type Checking (tsc) ==="
    cd "$PROJECT_ROOT/web"

    if [ ! -f "node_modules/.bin/tsc" ]; then
        if ! command -v tsc &> /dev/null; then
            echo "TypeScript not found. Run: cd web && npm install"
            return 1
        fi
        tsc --noEmit
    else
        ./node_modules/.bin/tsc --noEmit
    fi
    echo "TypeScript type check passed."
}

case "${1:-all}" in
    python|py)
        check_python
        ;;
    typescript|ts)
        check_typescript
        ;;
    all)
        check_python
        echo ""
        check_typescript
        ;;
    *)
        echo "Usage: $0 [python|ts|all]"
        exit 1
        ;;
esac

echo ""
echo "All type checks passed."
