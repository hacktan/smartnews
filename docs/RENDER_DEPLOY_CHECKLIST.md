# Render Deploy Checklist (API)

1. Render dashboard -> `New` -> `Blueprint`.
2. Select repository: `hacktan/smartnews`.
3. Confirm `render.yaml` is detected.
4. In service env vars:
   - `DB_PATH=smartnews.duckdb`
   - `GITHUB_REPOSITORY=hacktan/smartnews`
   - `GITHUB_RELEASE_TAG=db-latest`
   - `GITHUB_DB_ASSET_NAME=smartnews.duckdb`
   - `CORS_ORIGINS=*`
   - `GITHUB_TOKEN` optional (recommended for private repos or rate limits)
5. Deploy.
6. After first boot, test:
   - `GET /health` -> `{"status":"ok"}`
7. Smoke test endpoints:
   - `GET /api/home`
   - `GET /api/categories`
   - `GET /api/stories?limit=5`

If boot fails:
- Check logs for release tag/asset mismatch (`db-latest` + `smartnews.duckdb`).
- Verify repository visibility and token permissions.
