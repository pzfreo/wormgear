#!/bin/bash
# Build script: web/ + src/ → dist/
set -e

echo "🔧 Building wormgear web interface..."

# Ensure we're in project root
cd "$(dirname "$0")/.."
PROJECT_ROOT="$(pwd)"

# Clean old build (preserve directory for running server)
echo "🧹 Cleaning old build..."
mkdir -p dist/
rm -rf dist/*

# Copy web source files to dist/
echo "📄 Copying web files..."
cp -r web/*.html web/*.js web/*.css web/*.svg web/*.md dist/ 2>/dev/null || true
cp -r web/modules dist/
cp -r web/tests dist/ 2>/dev/null || true
cp web/CNAME dist/ 2>/dev/null || true

# Copy Python package to dist/
echo "📦 Copying wormgear package..."
mkdir -p dist/wormgear
cp -r src/wormgear/* dist/wormgear/

# Clean Python cache files
echo "🧹 Cleaning Python cache..."
find dist/wormgear -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find dist/wormgear -name "*.pyc" -delete 2>/dev/null || true

# Generate Python file manifest for Pyodide dynamic loading
echo "📋 Generating Python file manifest..."
(cd dist && find wormgear -name '*.py' | sort | python3 -c "
import sys, json
files = [line.strip() for line in sys.stdin]
json.dump(files, sys.stdout, indent=2)
print()
" > wormgear-manifest.json)
echo "✓ Manifest: $(python3 -c "import json; print(len(json.load(open('dist/wormgear-manifest.json'))))" ) Python files"

# Verify critical files
echo "🔍 Verifying build..."
REQUIRED=(
    "dist/index.html"
    "dist/app.js"
    "dist/wormgear/__init__.py"
    "dist/wormgear/calculator/core.py"
    "dist/wormgear/core/bore_sizing.py"
    "dist/wormgear/calculator/js_bridge.py"
    "dist/wormgear/enums.py"
    "dist/wormgear/io/loaders.py"
)

for file in "${REQUIRED[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Missing: $file"
        exit 1
    fi
done

echo "✓ All required files present"
echo ""
echo "✅ Build complete!"
echo "📍 Output: $PROJECT_ROOT/dist/"
echo "🌐 Run: python web/serve.py"
