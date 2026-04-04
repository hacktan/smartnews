# MCP Skill: SmartNews Platform

> **Last updated:** 2026-03-08 — Layer 5 in progress (Why It Matters ✅, TF-IDF Related Stories ✅)
> **AGENT_HANDOFF.md** is the authoritative single source of truth — read it first before touching any code.

## 1. Project Mission

SmartNews is a platform that enriches news from RSS feeds with AI (generating hype, credibility, importance scores) to provide users with a "high-signal, low-noise" news discovery experience. The core goal is to focus on quality and signal over volume.

## 2. Layer Status (2026-03-08)

| Layer | Name | Status |
|---|---|---|
| 0 | Data Foundation (Bronze→Silver→Gold) | ✅ COMPLETE |
| 1 | AI Enrichment | ✅ COMPLETE |
| 2 | Serving Projection | ✅ COMPLETE |
| 3 | API Layer (FastAPI) | ✅ COMPLETE + DEPLOYED |
| 4 | Web Frontend (Next.js) | ✅ COMPLETE + DEPLOYED |
| 5 | Product Intelligence | 🔶 IN PROGRESS |
| 6–8 | Personalization / Agentic / iOS | ⬜ NOT STARTED |

### Layer 5 — Done
- `why_it_matters` field: AI enrichment → gold → serve → API → frontend (amber banner on article detail)
- **TF-IDF related stories**: Spark MLlib cosine similarity replaces same-category self-join; cross-category semantic matches verified

### Layer 5 — Next
- Topic clustering (KMeans on TF-IDF vectors already computed in notebook 05)
- Trending clusters, Semantic search (Azure AI Search), Source comparison

## 3. Live URLs

| Service | URL |
|---|---|
| Frontend | `https://smartnews-frontend.victorioussea-ab137c42.eastus.azurecontainerapps.io` |
| API | `https://smartnews-api.victorioussea-ab137c42.eastus.azurecontainerapps.io` |
| API Docs | `https://smartnews-api.victorioussea-ab137c42.eastus.azurecontainerapps.io/docs` |

## 4. Tech Stack

- **Data Pipeline:** Azure Databricks, Delta Lake, Unity Catalog (`dbc_mcp_projects`)
- **AI Enrichment:** Azure OpenAI (gpt-4o-mini) — hype / credibility / importance / why_it_matters
- **Related Stories:** Spark MLlib TF-IDF cosine similarity (HashingTF 8192 + IDF + StopWordsRemover)
- **API:** FastAPI (Python 3.11), Pydantic v2, cachetools TTLCache
- **Frontend:** Next.js 16 (App Router), TypeScript, Tailwind CSS
- **Hosting:** Azure Container Apps (2x apps: `smartnews-api`, `smartnews-frontend`)
- **Registry:** ACR `smartnewsacr.azurecr.io`
- **CI/CD:** GitHub Actions (`deploy.yml`, `deploy-frontend.yml`)
- **DB Auth:** Service Principal OAuth (PAT does NOT work for SQL Warehouse — SCIM issue)

## 5. Architecture Flow

```
RSS Feeds
  → Bronze (raw, MERGE on entry_id)
  → Silver (cleaned, categorized)
  → Gold (AI-enriched: scores, summaries, why_it_matters, entities)
  → Serve (UI-ready: article_cards, category_feeds, trending_topics, article_detail)
  → FastAPI (Azure Container App)
  → Next.js (Azure Container App)
```

## 6. Key Files

| Path | Purpose |
|---|---|
| `AGENT_HANDOFF.md` | **Start here** — full credentials, gotchas, deploy commands |
| `PRODUCT_GOALS.md` | Product vision + layer checklist |
| `SETUP.md` | Full setup guide for a new Azure environment |
| `notebooks/01-05_*.py` | Databricks pipeline notebooks |
| `notebooks/05_serving_projection.py` | TF-IDF related stories logic lives here |
| `api/routers/` | FastAPI endpoint implementations |
| `frontend/app/` | Next.js pages (homepage, category, article, search) |
| `frontend/components/` | ArticleCard, ScoreBadge, ClickTracker |
| `infra/provision-azure.ps1` | Idempotent Azure provisioner |
| `deploy_to_databricks.py` | Upload notebooks + create/update Databricks job |

## 7. Critical Rules (never violate)

1. **Never query Gold directly** — always Serve → API → frontend
2. **PAT token fails for SQL Warehouse** — use Service Principal OAuth (see AGENT_HANDOFF.md §4)
3. **After editing a notebook, run `deploy_to_databricks.py`** — job reads from workspace, not GitHub
4. **All task timeouts: 1800s** — cold cluster startup takes 7-8 min
5. **VM: Standard_D4s_v3** — DS3_v2 not available in this region
6. **Container Apps ignores `:latest` re-tag** — always use `--revision-suffix` on update
7. **az CLI Unicode crash on Windows** — set `[Console]::OutputEncoding = UTF8` first

## 8. Local Development

### API
```powershell
cd C:\Users\haktan\Documents\Mcp_SmartNews
C:\Users\haktan\.local\bin\uv.exe run uvicorn api.main:app --reload
# Docs: http://localhost:8000/docs
```

### Frontend
```powershell
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
# Open: http://localhost:3000
```

## 9. Databricks Pipeline

- **Job name:** `SmartNews_Daily_Pipeline`
- **Job ID:** `545305541944595` (updated 2026-03-08)
- **Status:** Every 4 hours UTC (trigger manually to control cost)
- **Trigger via SP OAuth:**

```python
import httpx, os
from dotenv import load_dotenv
load_dotenv()
tenant, client_id, client_secret = os.getenv("AZURE_TENANT_ID"), os.getenv("AZURE_SP_CLIENT_ID"), os.getenv("AZURE_SP_CLIENT_SECRET")
host = os.getenv("DATABRICKS_HOST", "").rstrip("/")
token = httpx.post(f"https://login.microsoftonline.com/{tenant}/oauth2/token",
    data={"grant_type": "client_credentials", "client_id": client_id,
          "client_secret": client_secret, "resource": "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d"}, timeout=15).json()["access_token"]
r = httpx.post(f"{host}/api/2.1/jobs/run-now", headers={"Authorization": f"Bearer {token}"},
    json={"job_id": 545305541944595}, timeout=15)
print("Run ID:", r.json().get("run_id"))
```

## 10. Cost Management

### Stop services overnight
```powershell
$env:PATH = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin;$env:PATH"
$apiRev = az containerapp revision list --name smartnews-api --resource-group rg_FutureNews --query "[?properties.active].name" -o tsv
az containerapp revision deactivate --name smartnews-api --resource-group rg_FutureNews --revision $apiRev
$feRev = az containerapp revision list --name smartnews-frontend --resource-group rg_FutureNews --query "[?properties.active].name" -o tsv
az containerapp revision deactivate --name smartnews-frontend --resource-group rg_FutureNews --revision $feRev
```

### Restart (trigger GitHub Actions)
```powershell
$h = @{ Authorization = "token ghp_YOUR_TOKEN" }
Invoke-RestMethod "https://api.github.com/repos/hacktan/SmartNews-Pipeline/actions/workflows/deploy.yml/dispatches" -Method POST -Headers $h -Body '{"ref":"main"}' -ContentType "application/json"
Invoke-RestMethod "https://api.github.com/repos/hacktan/SmartNews-Pipeline/actions/workflows/deploy-frontend.yml/dispatches" -Method POST -Headers $h -Body '{"ref":"main"}' -ContentType "application/json"
```

### Expected monthly cost (idle)
~$8–15/month (Container Apps mostly). Databricks pipeline: $0 when paused.
