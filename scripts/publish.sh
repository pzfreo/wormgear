#!/bin/bash
# Publish script for wormgear package.
#
# Two-phase release: the script never bypasses branch protection. The human
# reviews and merges the release PR, then re-runs with --tag to create the
# tag + GitHub Release, which triggers the PyPI workflow.
#
# Usage:
#   ./scripts/publish.sh [version]                # Phase A: create release PR
#   ./scripts/publish.sh [version] --tag          # Phase B: tag + release (after PR is merged)
#
# Examples:
#   ./scripts/publish.sh                          # Auto-increment patch (0.0.51 -> 0.0.52)
#   ./scripts/publish.sh 0.1.0                    # Create release PR for 0.1.0
#   ./scripts/publish.sh 0.1.0 --tag              # Tag + GH Release for 0.1.0 (after PR merged)

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: gh CLI is required but not installed.${NC}"
    echo "Install from: https://cli.github.com/"
    exit 1
fi

# Parse args. Order-insensitive: version + optional --tag.
NEW_VERSION=""
PHASE_TAG=false
for arg in "$@"; do
    case "$arg" in
        --tag) PHASE_TAG=true ;;
        *) NEW_VERSION="$arg" ;;
    esac
done

# Always operate on a fresh main.
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${YELLOW}Switching to main branch...${NC}"
    git checkout main
fi
echo "Pulling latest main..."
git pull origin main

CURRENT_VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
echo "Current version (pyproject.toml on main): $CURRENT_VERSION"

# Defaulting rules differ by phase:
#   Phase A (no --tag): create a release PR. Default version = auto-increment
#     patch (most common case).
#   Phase B (--tag):    tag whatever's on main. Default version = CURRENT_VERSION.
if [ -z "$NEW_VERSION" ]; then
    if $PHASE_TAG; then
        NEW_VERSION="$CURRENT_VERSION"
    else
        IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"
        PATCH=$((PATCH + 1))
        NEW_VERSION="$MAJOR.$MINOR.$PATCH"
    fi
fi
echo -e "Target version: ${GREEN}$NEW_VERSION${NC}"

# Tag must not already exist for either phase.
if git rev-parse "v$NEW_VERSION" >/dev/null 2>&1; then
    echo -e "${RED}Error: Tag v$NEW_VERSION already exists locally!${NC}"
    exit 1
fi

# ---------------------------------------------------------------------------
# Phase B — tag + release (only after the version-bump PR is merged on main)
# ---------------------------------------------------------------------------
if $PHASE_TAG; then
    if [ "$CURRENT_VERSION" != "$NEW_VERSION" ]; then
        echo -e "${RED}Error: pyproject.toml on main is at $CURRENT_VERSION,"
        echo -e "but you asked for v$NEW_VERSION.${NC}"
        echo
        echo "Did you forget to merge the release PR? Re-run Phase A first:"
        echo "  ./scripts/publish.sh $NEW_VERSION"
        echo "then merge the PR it creates, then re-run with --tag."
        exit 1
    fi

    if git ls-remote --tags origin "v$NEW_VERSION" | grep -q .; then
        echo -e "${RED}Error: Tag v$NEW_VERSION already exists on remote.${NC}"
        exit 1
    fi

    echo ""
    echo "Phase B will:"
    echo "  1. Tag main as v$NEW_VERSION"
    echo "  2. Push the tag"
    echo "  3. Create a GitHub Release (uses CHANGELOG.md if present, else auto-notes)"
    echo "  4. Trigger publish.yml → TestPyPI staging → PyPI"
    echo ""
    read -p "Proceed? [y/N] " -n 1 -r
    echo
    [[ ! $REPLY =~ ^[Yy]$ ]] && { echo "Aborted."; exit 1; }

    echo "Creating tag v$NEW_VERSION..."
    git tag "v$NEW_VERSION"
    git push origin "v$NEW_VERSION"

    echo "Creating GitHub Release..."
    if [ -f CHANGELOG.md ]; then
        # Extract just the section for this version from CHANGELOG.md
        # Lines from "## $NEW_VERSION" up to the next "## " heading.
        NOTES=$(awk -v ver="$NEW_VERSION" '
            $0 ~ "^## " ver { capture = 1; next }
            capture && $0 ~ "^## " { capture = 0 }
            capture { print }
        ' CHANGELOG.md)
        if [ -n "$NOTES" ]; then
            echo "$NOTES" > /tmp/wormgear-release-notes.md
            gh release create "v$NEW_VERSION" --title "v$NEW_VERSION" --notes-file /tmp/wormgear-release-notes.md
            rm /tmp/wormgear-release-notes.md
        else
            echo -e "${YELLOW}Warning: No '## $NEW_VERSION' section found in CHANGELOG.md.${NC}"
            echo "Falling back to auto-generated notes."
            gh release create "v$NEW_VERSION" --title "v$NEW_VERSION" --generate-notes
        fi
    else
        gh release create "v$NEW_VERSION" --title "v$NEW_VERSION" --generate-notes
    fi

    echo ""
    echo -e "${GREEN}✓ Release v$NEW_VERSION published!${NC}"
    echo ""
    echo "GitHub Actions will now:"
    echo "  1. Build the package"
    echo "  2. Publish to TestPyPI + smoke-test"
    echo "  3. Publish to PyPI (only if TestPyPI step succeeded)"
    echo ""
    echo "Watch: https://github.com/pzfreo/wormgear/actions"
    exit 0
fi

# ---------------------------------------------------------------------------
# Phase A — create release PR (default)
# ---------------------------------------------------------------------------
if [ "$CURRENT_VERSION" = "$NEW_VERSION" ]; then
    echo -e "${RED}Error: pyproject.toml is already at $NEW_VERSION on main.${NC}"
    echo "Maybe you wanted Phase B?"
    echo "  ./scripts/publish.sh $NEW_VERSION --tag"
    exit 1
fi

# Refuse on dirty tree — half-finished edits would be silently included
# in the release PR.
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo -e "${RED}Error: working tree has uncommitted changes.${NC}"
    git status --short
    exit 1
fi

echo ""
echo "Phase A will:"
echo "  1. Create release branch from main"
echo "  2. Bump pyproject.toml to $NEW_VERSION"
echo "  3. Push branch + open PR"
echo "  4. Exit. (You review the PR and merge it manually once CI is green.)"
echo ""
read -p "Proceed? [y/N] " -n 1 -r
echo
[[ ! $REPLY =~ ^[Yy]$ ]] && { echo "Aborted."; exit 1; }

BRANCH="release/v$NEW_VERSION"
echo ""
echo "Creating branch $BRANCH..."
git checkout -b "$BRANCH"

echo "Updating pyproject.toml..."
sed -i.bak "s/^version = \".*\"/version = \"$NEW_VERSION\"/" pyproject.toml
rm -f pyproject.toml.bak

echo "Committing..."
git add pyproject.toml
git commit -m "chore: release v$NEW_VERSION"

echo "Pushing..."
git push -u origin "$BRANCH"

echo "Opening PR..."
PR_URL=$(gh pr create \
    --title "chore: release v$NEW_VERSION" \
    --body "Automated release PR for v$NEW_VERSION. Review CI, then merge to main. After merging, run:

\`\`\`bash
./scripts/publish.sh $NEW_VERSION --tag
\`\`\`

to tag and trigger the PyPI publish workflow." \
    --head "$BRANCH" \
    --base main)

git checkout main

echo ""
echo -e "${GREEN}✓ Release PR created:${NC} $PR_URL"
echo ""
echo "Next steps:"
echo "  1. Wait for CI to be green on the PR."
echo "  2. Review and merge the PR (no --admin, no auto-merge — by design)."
echo "  3. Run: ./scripts/publish.sh $NEW_VERSION --tag"
