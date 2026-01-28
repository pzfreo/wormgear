#!/bin/bash
# Publish script for wormgear package
#
# Takes current main, bumps version via PR, tags, creates GitHub Release, triggers PyPI publish.
#
# Usage:
#   ./scripts/publish.sh [version]
#
# Examples:
#   ./scripts/publish.sh           # Auto-increment patch (0.0.8 -> 0.0.9)
#   ./scripts/publish.sh 0.1.0     # Specify version

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check gh CLI is available
if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: gh CLI is required but not installed.${NC}"
    echo "Install from: https://cli.github.com/"
    exit 1
fi

# Ensure we're on main and up to date
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${YELLOW}Switching to main branch...${NC}"
    git checkout main
fi

echo "Pulling latest main..."
git pull origin main

# Get current version from pyproject.toml
CURRENT_VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
echo "Current version: $CURRENT_VERSION"

# Calculate new version
if [ -n "$1" ]; then
    NEW_VERSION="$1"
else
    # Auto-increment patch version
    IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"
    PATCH=$((PATCH + 1))
    NEW_VERSION="$MAJOR.$MINOR.$PATCH"
fi

echo -e "New version: ${GREEN}$NEW_VERSION${NC}"

# Check if tag already exists
if git rev-parse "v$NEW_VERSION" >/dev/null 2>&1; then
    echo -e "${RED}Error: Tag v$NEW_VERSION already exists!${NC}"
    exit 1
fi

# Confirm
echo ""
echo "This will:"
echo "  1. Create a PR to bump version to $NEW_VERSION"
echo "  2. Auto-merge the PR"
echo "  3. Create and push tag v$NEW_VERSION"
echo "  4. Create GitHub Release with auto-generated notes"
echo "  5. Trigger PyPI publish via GitHub Actions"
echo ""
read -p "Proceed? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Create release branch
BRANCH="release/v$NEW_VERSION"
echo ""
echo "Creating branch $BRANCH..."
git checkout -b "$BRANCH"

# Update version in pyproject.toml
echo "Updating pyproject.toml..."
sed -i.bak "s/^version = \".*\"/version = \"$NEW_VERSION\"/" pyproject.toml
rm -f pyproject.toml.bak

# Commit version bump
echo "Committing version bump..."
git add pyproject.toml
git commit -m "chore: Release v$NEW_VERSION"

# Push branch
echo "Pushing branch..."
git push -u origin "$BRANCH"

# Create PR
echo "Creating PR..."
PR_URL=$(gh pr create \
    --title "Release v$NEW_VERSION" \
    --body "Automated release PR for v$NEW_VERSION" \
    --head "$BRANCH" \
    --base main)

echo "PR created: $PR_URL"

# Merge PR (squash to keep history clean)
echo "Merging PR..."
gh pr merge "$BRANCH" --squash --delete-branch --admin

# Switch back to main and pull
echo "Switching to main..."
git checkout main
git pull origin main

# Create and push tag
echo "Creating tag v$NEW_VERSION..."
git tag "v$NEW_VERSION"
git push origin "v$NEW_VERSION"

# Create GitHub Release with auto-generated notes
echo "Creating GitHub Release..."
gh release create "v$NEW_VERSION" \
    --title "v$NEW_VERSION" \
    --generate-notes

echo ""
echo -e "${GREEN}✓ Release v$NEW_VERSION published!${NC}"
echo ""
echo "GitHub Actions will now build and publish to PyPI."
echo "Check progress: https://github.com/pzfreo/wormgear/actions"
