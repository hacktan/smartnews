#!/usr/bin/env bash
# SmartNews — agent environment setup
# Run once after git clone on Linux.
# Usage: GITHUB_PAT=ghp_xxx OPENAI_API_KEY=sk-xxx bash setup_agent.sh

set -e

GITHUB_PAT="${GITHUB_PAT:?Set GITHUB_PAT}"
OPENAI_API_KEY="${OPENAI_API_KEY:?Set OPENAI_API_KEY}"
REPO="hacktan/smartnews"

echo "=== 1/5 Python dependencies ==="
uv sync

echo "=== 2/5 Frontend dependencies ==="
cd frontend && npm ci && cd ..

echo "=== 3/5 Download database ==="
gh release download db-latest \
  --pattern "smartnews.duckdb" \
  --repo "$REPO" \
  --clobber \
  --auth "$GITHUB_PAT" 2>/dev/null \
|| {
  echo "gh not available or failed, trying curl..."
  curl -L \
    -H "Authorization: Bearer $GITHUB_PAT" \
    -H "Accept: application/octet-stream" \
    "https://api.github.com/repos/$REPO/releases/assets/$(
      curl -s \
        -H "Authorization: Bearer $GITHUB_PAT" \
        "https://api.github.com/repos/$REPO/releases/tags/db-latest" \
      | python3 -c "import sys,json; assets=json.load(sys.stdin)['assets']; print(next(a['id'] for a in assets if a['name']=='smartnews.duckdb'))"
    )" \
    -o smartnews.duckdb
  echo "Database downloaded via curl."
}
echo "DB size: $(du -sh smartnews.duckdb | cut -f1)"

echo "=== 4/5 Write .env ==="
cat > .env <<EOF
DB_PATH=smartnews.duckdb
OPENAI_API_KEY=$OPENAI_API_KEY
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
CLAIM_LLM_PROVIDER=openai
CLAIM_MODEL=gpt-4o-mini
ENRICHMENT_BATCH_LIMIT=20
SCRAPE_BATCH_LIMIT=100
GITHUB_TOKEN=$GITHUB_PAT
GITHUB_REPOSITORY=$REPO
GITHUB_RELEASE_TAG=db-latest
GITHUB_DB_ASSET_NAME=smartnews.duckdb
DB_SYNC_ON_STARTUP=false
EOF
echo ".env written."

echo "=== 5/5 Write .mcp.json ==="
cat > .mcp.json <<EOF
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "$GITHUB_PAT"
      }
    },
    "duckdb": {
      "command": "uv",
      "args": ["run", "mcp-server-duckdb", "--db-path", "./smartnews.duckdb"]
    }
  }
}
EOF
echo ".mcp.json written."

echo ""
echo "=== Done ==="
echo "Verify with:"
echo "  uv run python pipeline/validate.py"
