#!/bin/bash
# Neko Futures Trader - Release Script
# Usage: ./release.sh [major|minor|patch]
# Example: ./release.sh patch

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check git
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}❌ Not a git repository${NC}"
    exit 1
fi

# Check clean working tree
if [[ -n $(git status -s) ]]; then
    echo -e "${RED}❌ Working tree not clean. Commit or stash changes first.${NC}"
    git status -s
    exit 1
fi

# Bump type
BUMP=${1:-patch}
if [[ ! "$BUMP" =~ ^(major|minor|patch)$ ]]; then
    echo -e "${RED}❌ Invalid bump type: $BUMP${NC}"
    echo "Usage: ./release.sh [major|minor|patch]"
    exit 1
fi

# Read current version
CURRENT=$(cat VERSION | tr -d '[:space:]')
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"

# Calculate new version
case $BUMP in
    major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
    minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
    patch) PATCH=$((PATCH + 1)) ;;
esac
NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}"

echo -e "${YELLOW}📦 Bumping version: ${CURRENT} → ${NEW_VERSION}${NC}"

# Update VERSION file
echo "$NEW_VERSION" > VERSION

# Generate changelog entry
DATE=$(date +%Y-%m-%d)
LOG_ENTRY="\n## [${NEW_VERSION}] - ${DATE}\n\n"

# Get commits since last tag (or all if no tags)
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
if [[ -n "$LAST_TAG" ]]; then
    RANGE="${LAST_TAG}..HEAD"
    echo -e "${GREEN}📝 Commits since ${LAST_TAG}${NC}"
else
    RANGE="HEAD"
    echo -e "${GREEN}📝 All commits (no previous tag)${NC}"
fi

# Parse conventional commits
FEATURES=""
FIXES=""
CHORES=""
OTHERS=""

while IFS= read -r line; do
    HASH=$(echo "$line" | cut -d' ' -f1)
    MSG=$(echo "$line" | cut -d' ' -f2-)
    
    if [[ "$MSG" =~ ^feat[\(:] ]]; then
        FEATURES="${FEATURES}- ${MSG} (\`${HASH}\`)\n"
    elif [[ "$MSG" =~ ^fix[\(:] ]]; then
        FIXES="${FIXES}- ${MSG} (\`${HASH}\`)\n"
    elif [[ "$MSG" =~ ^(chore|docs|style|refactor|perf|test|ci|build)[\(:] ]]; then
        CHORES="${CHORES}- ${MSG} (\`${HASH}\`)\n"
    else
        OTHERS="${OTHERS}- ${MSG} (\`${HASH}\`)\n"
    fi
done < <(git log --oneline ${RANGE} 2>/dev/null || git log --oneline)

[[ -n "$FEATURES" ]] && LOG_ENTRY="${LOG_ENTRY}### ✨ Features\n${FEATURES}\n"
[[ -n "$FIXES" ]] && LOG_ENTRY="${LOG_ENTRY}### 🐛 Bug Fixes\n${FIXES}\n"
[[ -n "$CHORES" ]] && LOG_ENTRY="${LOG_ENTRY}### 🔧 Maintenance\n${CHORES}\n"
[[ -n "$OTHERS" ]] && LOG_ENTRY="${LOG_ENTRY}### 📝 Other\n${OTHERS}\n"

# Insert into CHANGELOG.md after header
HEADER=$(head -7 CHANGELOG.md)
BODY=$(tail -n +8 CHANGELOG.md)
echo -e "${HEADER}\n${LOG_ENTRY}${BODY}" > CHANGELOG.md

echo -e "${GREEN}✅ CHANGELOG.md updated${NC}"

# Git commit + tag
git add VERSION CHANGELOG.md
git commit -m "chore(release): v${NEW_VERSION}"
git tag -a "v${NEW_VERSION}" -m "Release v${NEW_VERSION}"

echo -e "${GREEN}🏷️  Tagged: v${NEW_VERSION}${NC}"
echo -e "${YELLOW}💡 Run 'git push origin main --tags' to publish${NC}"
