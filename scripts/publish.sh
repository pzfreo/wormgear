#!/bin/bash
# Publish script for wormgear package
# Works with protected main branches (requires PR workflow)
#
# Usage:
#   ./scripts/publish.sh [version]    # Create release PR
#   ./scripts/publish.sh --tag        # Tag current main (after PR merged)
#
# Examples:
#   ./scripts/publish.sh              # Auto-increment patch, create PR
#   ./scripts/publish.sh 0.1.0        # Specify version, create PR
#   ./scripts/publish.sh --tag        # Tag main with version from pyproject.toml

set -e

# Get current version from pyproject.toml
CURRENT_VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
echo "Current version: $CURRENT_VERSION"

# Handle --tag flag (run after PR is merged)
if [ "$1" = "--tag" ]; then
    echo "Tagging main with v$CURRENT_VERSION..."

    # Make sure we're on main and up to date
    git checkout main
    git pull origin main

    # Create and push tag
    git tag "v$CURRENT_VERSION"
    git push origin "v$CURRENT_VERSION"

    echo ""
    echo "Tagged v$CURRENT_VERSION!"
    echo "GitHub Action will build and upload to PyPI."
    echo "Check: https://github.com/pzfreo/wormgear/actions"
    exit 0
fi

# Calculate new version
if [ -n "$1" ]; then
    NEW_VERSION="$1"
else
    # Auto-increment patch version
    IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"
    PATCH=$((PATCH + 1))
    NEW_VERSION="$MAJOR.$MINOR.$PATCH"
fi

echo "New version: $NEW_VERSION"

# Confirm
read -p "Create release PR for v$NEW_VERSION? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Create release branch
BRANCH="release/v$NEW_VERSION"
git checkout main
git pull origin main
git checkout -b "$BRANCH"

# Update version in pyproject.toml
sed -i.bak "s/^version = \".*\"/version = \"$NEW_VERSION\"/" pyproject.toml
rm -f pyproject.toml.bak

# Commit version bump
git add pyproject.toml
git commit -m "chore: Bump version to $NEW_VERSION"

# Push branch
git push -u origin "$BRANCH"

# Create PR using gh CLI if available
if command -v gh &> /dev/null; then
    gh pr create --title "Release v$NEW_VERSION" --body "Bump version to $NEW_VERSION for PyPI release.

After merging, run:
\`\`\`
./scripts/publish.sh --tag
\`\`\`
to trigger the PyPI publish."
    echo ""
    echo "PR created! After merging, run: ./scripts/publish.sh --tag"
else
    echo ""
    echo "Branch pushed. Create PR at:"
    echo "https://github.com/pzfreo/wormgear/pull/new/$BRANCH"
    echo ""
    echo "After merging, run: ./scripts/publish.sh --tag"
fi
