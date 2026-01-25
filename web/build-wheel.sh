#!/bin/bash
# Build wormgear wheel for WASM deployment
# This is a better approach than copying individual Python files

set -e

echo "🔧 Building wormgear wheel for web deployment..."

# Ensure we're in the repo root
cd "$(dirname "$0")/.."

# Build wheel
echo "📦 Building wheel..."
python -m build --wheel --outdir web/wheels/

# List what was built
echo ""
echo "✅ Wheel built successfully!"
ls -lh web/wheels/
echo ""
echo "The wheel can now be installed in Pyodide with:"
echo "  await micropip.install('/wheels/wormgear-<version>-py3-none-any.whl')"
