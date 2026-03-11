#!/bin/bash
# One-shot setup: push playlists to GitHub Gist + print iPlayTV URLs.
# Run: bash ~/Documents/tv/setup-iplaytv.sh

set -euo pipefail
TV="$HOME/Documents/tv"
OUTPUT="$TV/output"

# --- Check prerequisites ---
if ! command -v gh &>/dev/null; then
  echo "❌ GitHub CLI not found. Installing via Homebrew..."
  if command -v brew &>/dev/null; then
    brew install gh
  else
    echo "❌ Homebrew not found either. Install gh manually:"
    echo "   https://cli.github.com"
    exit 1
  fi
fi

if ! gh auth status &>/dev/null 2>&1; then
  echo "🔑 Need to log in to GitHub first..."
  gh auth login
fi

# --- Rebuild playlists fresh ---
echo "🔨 Rebuilding playlists..."
python3 "$TV/build.py"

# --- Create or update gist ---
GIST_FILE="$TV/.gist-id"

if [ -f "$GIST_FILE" ]; then
  GIST_ID=$(cat "$GIST_FILE")
  echo "📡 Updating existing gist $GIST_ID ..."
  gh gist edit "$GIST_ID" \
    "$OUTPUT/post-soviet-tv.m3u" \
    "$OUTPUT/us-tv.m3u"
else
  echo "📡 Creating new gist..."
  GIST_URL=$(gh gist create \
    "$OUTPUT/post-soviet-tv.m3u" \
    "$OUTPUT/us-tv.m3u" \
    --desc "IPTV playlists — post-Soviet & US TV" \
    --public 2>&1 | grep 'https://gist.github.com')
  GIST_ID=$(basename "$GIST_URL")
  echo "$GIST_ID" > "$GIST_FILE"
  echo "  Saved gist ID to $GIST_FILE"
fi

# --- Get raw URLs ---
echo ""
echo "✅ Done! Add these URLs in iPlayTV → Add Playlist:"
echo ""
GIST_USER=$(gh api user --jq '.login' 2>/dev/null || echo "YOUR_USERNAME")
echo "  📺 Post-Soviet TV:"
echo "  https://gist.githubusercontent.com/$GIST_USER/$GIST_ID/raw/post-soviet-tv.m3u"
echo ""
echo "  📺 US TV:"
echo "  https://gist.githubusercontent.com/$GIST_USER/$GIST_ID/raw/us-tv.m3u"
echo ""
echo "  (These URLs are stable — they always serve the latest version)"
echo ""
echo "  To update channels later, just run:  ./tv rebuild"
