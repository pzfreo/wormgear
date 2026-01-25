#!/bin/bash
# Vercel build script for wormgear web interface
# Copies Python package files to web/src for WASM access

set -e  # Exit on error

echo "🔧 Building wormgear web interface..."

# Ensure we're in the web directory
cd "$(dirname "$0")"

# Create src directory if it doesn't exist
mkdir -p src

# Copy wormgear package from parent src/ to web/src/
echo "📦 Copying wormgear package..."
if [ -d "../src/wormgear" ]; then
    # Remove old copy if exists
    rm -rf src/wormgear

    # Copy package
    cp -r ../src/wormgear src/

    # Remove Python cache files (not needed in browser)
    find src/wormgear -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find src/wormgear -name "*.pyc" -delete 2>/dev/null || true

    echo "✓ Copied wormgear package to web/src/"
else
    echo "❌ Error: ../src/wormgear not found"
    exit 1
fi

# Verify critical files exist
echo "🔍 Verifying package structure..."
REQUIRED_FILES=(
    "src/wormgear/__init__.py"
    "src/wormgear/core/__init__.py"
    "src/wormgear/core/worm.py"
    "src/wormgear/core/wheel.py"
    "src/wormgear/core/features.py"
    "src/wormgear/io/__init__.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Missing required file: $file"
        exit 1
    fi
done

echo "✓ All required files present"

# List what was copied
echo ""
echo "📋 Package contents:"
ls -lh src/wormgear/
echo ""
ls -lh src/wormgear/core/

echo ""
echo "✅ Build complete!"
