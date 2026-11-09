#!/usr/bin/env bash
# Reads existing tags from stdin, ignores anything not in vX.Y.Z format, and prints the next tag.
# Usage: next_version.sh major|minor|patch
set -euo pipefail

bump="${1:-patch}"
highest="$(grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sed 's/^v//' | sort -t. -k1,1n -k2,2n -k3,3n | tail -n 1 || true)"
IFS=. read -r major minor patch <<< "${highest:-0.0.0}"

case "$bump" in
  major) major=$((major + 1)); minor=0; patch=0 ;;
  minor) minor=$((minor + 1)); patch=0 ;;
  patch) patch=$((patch + 1)) ;;
  *) echo "Unknown bump: $bump" >&2; exit 1 ;;
esac

echo "v${major}.${minor}.${patch}"
