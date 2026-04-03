# SmartNews — Complete Setup Guide

This guide walks through standing up the entire SmartNews platform from scratch in a new Azure environment. Any developer or AI agent can follow this guide to reproduce the full stack.

> **Estimated time:** ~45–60 minutes (most is waiting for Azure provisioning)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Azure Infrastructure](#3-azure-infrastructure)
4. [Databricks Workspace](#4-databricks-workspace)
5. [Azure OpenAI](#5-azure-openai)
6. [GitHub Repository](#6-github-repository)
7. [Deploy Notebooks & Pipeline Job](#7-deploy-notebooks--pipeline-job)
8. [Deploy API & Frontend](#8-deploy-api--frontend)
9. [First Pipeline Run](#9-first-pipeline-run)
10. [Verify Everything Works](#10-verify-everything-works)
11. [Cost Management](#11-cost-management)
12. [Re-deploying / Updating](#12-re-deploying--updating)
13. [Secrets Reference](#13-secrets-reference)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Architecture Overview

```
RSS Feeds (BBC, NYT, The Verge, ...)
  → Databricks Bronze (raw, deduplicated via MERGE)
  → Databricks Silver (cleaned, categorized, word count)
  → Databricks Gold   (AI-enriched: summaries, hype/credibility/importance scores, entities)
  → Databricks Serve  (UI-ready projections: article_cards, category_feeds, trending_topics, article_detail)
  → FastAPI (Azure Container App: smartnews-api)
  → Next.js (Azure Container App: smartnews-frontend)
```

### Azure Resources

| Resource | Type | Purpose |
|---|---|---|
| `rg_SmartNews` | Resource Group | Logical container for all resources |
| `smartnewsacr` | Container Registry (Basic) | Stores Docker images for API + frontend |
| `smartnews-env` | Container Apps Environment | Shared environment for both apps |
| `smartnews-env-logs` | Log Analytics Workspace | Container Apps logs |
| `smartnews-api` | Container App | FastAPI backend (CPU 0.5, 1Gi, 1-3 replicas) |
| `smartnews-frontend` | Container App | Next.js frontend (CPU 0.5, 1Gi, 1-2 replicas) |
| `github-smartnews-deploy` | Azure AD Service Principal | Used by GitHub Actions to deploy |

### Databricks Resources

| Resource | Details |
|---|---|
| Unity Catalog | `dbc_mcp_projects` catalog |
| Schemas | `bronze`, `silver`, `gold`, `serve` |
| SQL Warehouse | Any size — serverless or small (XS is sufficient) |
| Job | `SmartNews_Daily_Pipeline` (PAUSED — trigger manually) |
| Notebooks | Uploaded to `/SmartNews/pipelines/` in the workspace |

### GitHub Actions Workflows

| Workflow | Triggers | What it does |
|---|---|---|
| `deploy.yml` | Push to `api/**`, `Dockerfile`, `notebooks/**` OR `workflow_dispatch` | Builds API Docker image → pushes to ACR → deploys new Container App revision |
| `deploy-frontend.yml` | Push to `frontend/**` OR `workflow_dispatch` | Builds Next.js Docker image → pushes to ACR → deploys new Container App revision |

---

## 2. Prerequisites

Install these tools before starting:

```powershell
# 1. Azure CLI
winget install Microsoft.AzureCLI
# or: https://aka.ms/installazurecliwindows

# 2. GitHub CLI (needed for setup-github-secrets.ps1)
winget install GitHub.cli
# or: https://cli.github.com/

# 3. Python 3.11+ (for deploy_to_databricks.py)
winget install Python.Python.3.11

# 4. uv (Python package manager, faster than pip)
pip install uv
# or: https://docs.astral.sh/uv/getting-started/installation/

# 5. Node.js 22+ (for local frontend dev, not required for deployment)
winget install OpenJS.NodeJS.LTS
```

Verify installations:
```powershell
az --version        # Azure CLI
gh --version        # GitHub CLI
python --version    # Python 3.11+
uv --version        # uv
```

Log in to Azure:
```powershell
az login
az account show     # Confirm you're on the right subscription
# If needed: az account set --subscription "My Subscription"
```

---

## 3. Azure Infrastructure

### 3.1 Run the provisioning script

```powershell
cd infra

# Minimal — uses default names
.\provision-azure.ps1 -ResourceGroup "rg_SmartNews"

# Custom names (if defaults are already taken in Azure)
.\provision-azure.ps1 `
    -ResourceGroup "rg_SmartNews_Prod" `
    -Location "westeurope" `
    -AcrName "mysmartNewsacr2025" `
    -ContainerEnv "smartnews-env" `
    -ApiApp "smartnews-api" `
    -FrontendApp "smartnews-frontend"
```

The script:
- Creates all Azure resources
- Creates a Service Principal (`github-smartnews-deploy`) for GitHub Actions
- Outputs the AZURE_CREDENTIALS JSON to paste into GitHub Secrets
- Outputs the API URL to set as GitHub Variable `SMARTNEWS_API_URL`

> **Save the output** — you'll need it in step 6.

### 3.2 If using non-default resource names

If you changed `AcrName`, `ResourceGroup`, `ApiApp`, or `FrontendApp` from defaults, update the `env:` section in both workflow files:

**`.github/workflows/deploy.yml`:**
```yaml
env:
  ACR_NAME: smartnewsacr          # ← change to your ACR name
  RESOURCE_GROUP: rg_FutureNews   # ← change to your resource group
  CONTAINER_APP: smartnews-api    # ← change to your API app name
```

**`.github/workflows/deploy-frontend.yml`:**
```yaml
env:
  ACR_NAME: smartnewsacr          # ← change to your ACR name
  RESOURCE_GROUP: rg_FutureNews   # ← change to your resource group
  CONTAINER_ENV: smartnews-env    # ← change to your container env name
  CONTAINER_APP: smartnews-frontend  # ← change to your frontend app name
```

---

## 4. Databricks Workspace

You need an existing Azure Databricks workspace with Unity Catalog enabled.

### 4.1 Get Databricks credentials

**Option A — Personal Access Token (PAT)** (simplest for dev):
1. In Databricks UI: top-right → Settings → Developer → Access tokens → Generate new token
2. Copy the token (starts with `dapi_`)
3. Your `DATABRICKS_HOST` is the workspace URL: `https://adb-XXXXXXXXX.8.azuredatabricks.net/`

**Option B — Service Principal** (recommended for production — used by the API at runtime):
1. In Azure Portal: Entra ID → App Registrations → New Registration
2. Name: `smartnews-api-sp`
3. After creation, note: Application (client) ID, Directory (tenant) ID
4. Create a client secret: Certificates & secrets → New client secret
5. In Databricks Admin Console → Service Principals → Add → assign to workspace → grant cluster creation

### 4.2 Find SQL Warehouse ID

1. In Databricks UI: SQL → SQL Warehouses → click on your warehouse
2. In the URL: `https://adb-xxx.azuredatabricks.net/sql/warehouses/WAREHOUSE_ID`
3. Or: in Connection Details tab → HTTP Path → extract the ID after `/warehouses/`

**Recommended SQL Warehouse settings:**
- Size: Small (2 DBU/h) or X-Small (1 DBU/h)
- Auto-stop: 10 minutes (already configured if you used the job setup)
- Type: Serverless (cheapest) or Pro

### 4.3 Create Unity Catalog structures

If `dbc_mcp_projects` catalog doesn't exist yet:
```sql
-- Run in Databricks SQL Editor
CREATE CATALOG IF NOT EXISTS dbc_mcp_projects;
CREATE SCHEMA IF NOT EXISTS dbc_mcp_projects.bronze;
CREATE SCHEMA IF NOT EXISTS dbc_mcp_projects.silver;
CREATE SCHEMA IF NOT EXISTS dbc_mcp_projects.gold;
CREATE SCHEMA IF NOT EXISTS dbc_mcp_projects.serve;
```

> The pipeline notebooks create tables automatically — you only need the schemas.

---

## 5. Azure OpenAI

### 5.1 Create Azure OpenAI resource

1. Azure Portal → Create resource → "Azure OpenAI"
2. Region: `East US` (best model availability)
3. Pricing tier: Standard S0
4. Create

### 5.2 Deploy a model

1. In the resource → Model Deployments → Deploy model
2. Model: `gpt-4o-mini` (very cheap, sufficient for enrichment)
3. Deployment name: `gpt-4o-mini` (or any name — set as `AZURE_OPENAI_DEPLOYMENT`)
4. Tokens per minute: 30K is enough for batch enrichment

### 5.3 Get credentials

1. Resource → Keys and Endpoint
2. Copy: Key 1 → `AZURE_OPENAI_KEY`
3. Copy: Endpoint URL → `AZURE_OPENAI_ENDPOINT`

---

## 6. GitHub Repository

### 6.1 Fork / clone

If using an existing repo, just clone it. If starting from scratch:
```powershell
git clone https://github.com/hacktan/SmartNews-Pipeline.git
cd SmartNews-Pipeline
```

### 6.2 Set GitHub Secrets (required for GitHub Actions)

Go to: `https://github.com/YOUR_REPO/settings/secrets/actions`

Set these **Secrets** (encrypted, not visible after setting):

| Secret Name | Value | Where to get it |
|---|---|---|
| `AZURE_CREDENTIALS` | JSON from `provision-azure.ps1` output | Step 3.1 output |
| `DATABRICKS_HOST` | `https://adb-xxx.azuredatabricks.net/` | Step 4.1 |
| `DATABRICKS_TOKEN` | `dapi_xxxx` | Step 4.1 |
| `SQL_WAREHOUSE_ID` | e.g. `abc123def456` | Step 4.2 |
| `AZURE_TENANT_ID` | Azure AD tenant ID | Azure Portal → Entra ID → Overview |
| `AZURE_SP_CLIENT_ID` | SP Application (client) ID | Step 4.1 Option B |
| `AZURE_SP_CLIENT_SECRET` | SP client secret | Step 4.1 Option B |
| `AZURE_OPENAI_ENDPOINT` | `https://xxx.cognitiveservices.azure.com/` | Step 5.3 |
| `AZURE_OPENAI_KEY` | OpenAI API key | Step 5.3 |

> **Note on AZURE_TENANT_ID / AZURE_SP_CLIENT_ID / AZURE_SP_CLIENT_SECRET:**
> These are used by the API at runtime to authenticate to the Databricks SQL Warehouse.
> They must match the Service Principal that has access to the Databricks workspace.
> If using PAT-only auth, you can set DATABRICKS_TOKEN and leave SP fields empty.

Set this **Variable** (visible, not encrypted):

| Variable Name | Value |
|---|---|
| `SMARTNEWS_API_URL` | `https://smartnews-api.XXXXX.azurecontainerapps.io` (from step 3.1 output) |

```powershell
# Or use the automation script:
cd infra
.\setup-github-secrets.ps1 `
    -GithubToken "ghp_xxxx" `
    -GithubRepo "hacktan/SmartNews-Pipeline" `
    -AzureCredentials '{ ... JSON from provision script ... }' `
    -SmartNewsApiUrl "https://smartnews-api.xxxx.azurecontainerapps.io" `
    -DatabricksHost "https://adb-xxxx.azuredatabricks.net/" `
    -DatabricksToken "dapi_xxxx" `
    -SqlWarehouseId "xxxx" `
    -AzureTenantId "xxxx" `
    -AzureSpClientId "xxxx" `
    -AzureSpClientSecret "xxxx" `
    -AzureOpenAiEndpoint "https://xxxx.cognitiveservices.azure.com/" `
    -AzureOpenAiKey "xxxx"
```

---

## 7. Deploy Notebooks & Pipeline Job

This uploads the 5 Databricks notebooks and creates the pipeline job.

### 7.1 Set up local .env

```powershell
cp .env.example .env
# Edit .env and fill in all values
```

Minimum required in `.env`:
```
DATABRICKS_HOST=https://adb-XXXXXXXXX.azuredatabricks.net/
DATABRICKS_TOKEN=dapi_xxxx
AZURE_TENANT_ID=xxxx
AZURE_SP_CLIENT_ID=xxxx
AZURE_SP_CLIENT_SECRET=xxxx
AZURE_OPENAI_ENDPOINT=https://xxx.cognitiveservices.azure.com/
AZURE_OPENAI_KEY=xxxx
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
DATABRICKS_WORKSPACE_FOLDER=/SmartNews/pipelines
```

### 7.2 Install Python dependencies

```powershell
uv venv
.\.venv\Scripts\activate
uv pip install -r requirements.txt
# or: uv pip install httpx python-dotenv
```

### 7.3 Run the deployment script

```powershell
python deploy_to_databricks.py
# When prompted "Trigger a run now?" → type n (run manually later after verifying)
```

This:
- Uploads notebooks to `/SmartNews/pipelines/` in Databricks workspace
- Creates job `SmartNews_Daily_Pipeline` with 1 shared cluster (SPOT pricing)
- Job is created **PAUSED** — you control when it runs

To also trigger a run immediately:
```powershell
python deploy_to_databricks.py --run
```

> **To use a custom workspace folder:**
> Set `DATABRICKS_WORKSPACE_FOLDER=/Users/your@email.com/SmartNews` in `.env`

---

## 8. Deploy API & Frontend

After GitHub Secrets are set, trigger the GitHub Actions workflows:

### Option A — Automatic (push to main)
Any push to `main` that touches `api/**` or `Dockerfile` triggers `deploy.yml`.
Any push to `main` that touches `frontend/**` triggers `deploy-frontend.yml`.

### Option B — Manual trigger (workflow_dispatch)

```powershell
# Using GitHub CLI
gh workflow run deploy.yml --repo hacktan/SmartNews-Pipeline
gh workflow run deploy-frontend.yml --repo hacktan/SmartNews-Pipeline

# Or via API
$headers = @{ Authorization = "token ghp_xxxx" }
Invoke-RestMethod "https://api.github.com/repos/hacktan/SmartNews-Pipeline/actions/workflows/deploy.yml/dispatches" `
    -Method POST -Headers $headers `
    -Body '{"ref":"main"}' -ContentType "application/json"
Invoke-RestMethod "https://api.github.com/repos/hacktan/SmartNews-Pipeline/actions/workflows/deploy-frontend.yml/dispatches" `
    -Method POST -Headers $headers `
    -Body '{"ref":"main"}' -ContentType "application/json"
```

Wait ~5-7 minutes for both workflows to complete.

### Verify deployment

```powershell
# Check API health
Invoke-WebRequest "https://YOUR-API-URL/health" -UseBasicParsing | Select-Object StatusCode

# Check frontend
Invoke-WebRequest "https://YOUR-FRONTEND-URL/" -UseBasicParsing | Select-Object StatusCode
```

---

## 9. First Pipeline Run

Before the site shows real data, you need to run the pipeline at least once.

### Option A — From Databricks UI (recommended for first run)
1. Goto: Databricks → Workflows → `SmartNews_Daily_Pipeline`
2. Click "Run now"
3. Monitor in the Run tab — expect ~10-15 minutes total
4. All 5 tasks should show green checkmarks

### Option B — Via API
```powershell
# Get the job ID first
$headers = @{ Authorization = "Bearer $env:DATABRICKS_TOKEN" }
$jobs = Invoke-RestMethod "$env:DATABRICKS_HOST/api/2.1/jobs/list" -Headers $headers
$job = $jobs.jobs | Where-Object { $_.settings.name -eq "SmartNews_Daily_Pipeline" }
$jobId = $job.job_id

# Trigger run
Invoke-RestMethod "$env:DATABRICKS_HOST/api/2.1/jobs/run-now" `
    -Method POST -Headers $headers `
    -Body "{`"job_id`": $jobId}" -ContentType "application/json"
```

### What each task does

| Task | Duration | Output |
|---|---|---|
| `bronze_ingestion` | ~2 min | `bronze.rss_raw`: raw RSS entries |
| `silver_transformation` | ~2 min | `silver.rss_cleaned`: cleaned + categorized |
| `gold_aggregation` | ~2 min | `gold.news_articles`, daily summaries |
| `ai_enrichment` | ~5-8 min | AI scores + summaries added to gold (Azure OpenAI) |
| `serving_projection` | ~2 min | `serve.*` tables: UI-ready data |

After all tasks complete, the site should show real articles.

---

## 10. Verify Everything Works

Work through this checklist:

```
[ ] API health: GET /health → 200 OK
[ ] Homepage loads: GET / → shows Top Stories, Low Hype Picks, Trending
[ ] Category page works: /category/ai-machine-learning → shows articles
[ ] Article detail works: click any article → AI summary + scores visible
[ ] Search works: /search?q=AI → returns results
[ ] Score badges: cards show "High credibility", "Low hype", etc. (soft labels)
[ ] Related articles: article detail page shows "Related Stories" section
```

Quick API smoke test:
```powershell
$API = "https://YOUR-API-URL"

# Health
Invoke-WebRequest "$API/health" -UseBasicParsing | Select StatusCode

# Home
$home = Invoke-RestMethod "$API/api/home"
Write-Host "Top stories: $($home.top_stories.Count)"
Write-Host "Category rows: $($home.category_rows.Keys -join ', ')"

# Search
$search = Invoke-RestMethod "$API/api/search?q=AI"
Write-Host "Search results: $($search.total)"
```

---

## 11. Cost Management

### Expected monthly costs (all services running)

| Service | Config | Est. Monthly |
|---|---|---|
| Container Apps (API) | 0.5 CPU, 1Gi, always-on | ~$5-8 |
| Container Apps (Frontend) | 0.5 CPU, 1Gi, scale-to-0 | ~$3-5 |
| ACR Basic | Storage only | ~$0.17 |
| Log Analytics | Low volume | ~$1-2 |
| Databricks SQL Warehouse | Auto-stop after 10 min idle | Pay per query |
| Databricks pipeline job | PAUSED — manual only | $0 unless you run it |
| Azure OpenAI | gpt-4o-mini batch enrichment | ~$0.01-0.05/run |

**Total idle cost: ~$8-15/month** (mostly Container Apps)

### Stop everything overnight

```powershell
# Add Azure CLI to PATH
$env:PATH = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin;$env:PATH"

# Deactivate all active revisions (stops billing for compute)
$apiRev = az containerapp revision list --name smartnews-api --resource-group rg_FutureNews --query "[?properties.active].name" -o tsv
az containerapp revision deactivate --name smartnews-api --resource-group rg_FutureNews --revision $apiRev

$feRev = az containerapp revision list --name smartnews-frontend --resource-group rg_FutureNews --query "[?properties.active].name" -o tsv
az containerapp revision deactivate --name smartnews-frontend --resource-group rg_FutureNews --revision $feRev
```

### Restart (re-deploy via GitHub Actions)

```powershell
$headers = @{ Authorization = "token ghp_xxxx" }
Invoke-RestMethod "https://api.github.com/repos/hacktan/SmartNews-Pipeline/actions/workflows/deploy.yml/dispatches" `
    -Method POST -Headers $headers -Body '{"ref":"main"}' -ContentType "application/json"
Invoke-RestMethod "https://api.github.com/repos/hacktan/SmartNews-Pipeline/actions/workflows/deploy-frontend.yml/dispatches" `
    -Method POST -Headers $headers -Body '{"ref":"main"}' -ContentType "application/json"
```

### Databricks cost control

- Pipeline job is **PAUSED** — it only runs when you click "Run now" or trigger via API
- SQL Warehouse auto-stops after 10 minutes of no queries
- The first API call after idle takes ~30 seconds (warehouse warming up) — frontend shows a friendly message

---

## 12. Re-deploying / Updating

### Moving to a new Azure environment

1. Run `infra/provision-azure.ps1` with new resource names
2. Update GitHub Actions `env:` sections with new names (if different)
3. Update `SMARTNEWS_API_URL` GitHub Variable with new API URL
4. Run `python deploy_to_databricks.py` to re-upload notebooks (if new Databricks workspace)
5. Trigger both GitHub Actions workflows via `workflow_dispatch`

### Changing the GitHub repository owner

1. Fork or transfer the repository
2. Delete old GitHub Secrets (they don't transfer)
3. Set all secrets again in the new repo (see Section 6.2)
4. Update GitHub Token usages if you have `setup-github-secrets.ps1` saved locally

### Adding new RSS feeds

Edit `src/config.py` and `RSS_FEEDS` in `.env`:
```
RSS_FEEDS=https://feeds.bbci.co.uk/news/technology/rss.xml,https://NEW-FEED-URL/rss.xml
```
Then re-run the pipeline.

### Updating AI enrichment model

1. Deploy new model in Azure OpenAI
2. Update `AZURE_OPENAI_DEPLOYMENT` GitHub Secret
3. Trigger API deploy workflow

---

## 13. Secrets Reference

Complete list of all environment variables and GitHub Secrets:

### Required — GitHub Secrets

```
AZURE_CREDENTIALS          Service Principal JSON for GitHub Actions deployment
                           Format: {"clientId":"...","clientSecret":"...","subscriptionId":"...","tenantId":"..."}

DATABRICKS_HOST            Full workspace URL
                           Example: https://adb-7405617617055328.8.azuredatabricks.net/

DATABRICKS_TOKEN           Personal Access Token (PAT) for API runtime auth
                           Example: dapi_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

SQL_WAREHOUSE_ID           ID of the SQL Warehouse (not HTTP path, just the ID)
                           Example: abc123def456abcd

AZURE_TENANT_ID            Azure AD tenant ID (Directory ID)
                           From: Azure Portal → Entra ID → Overview

AZURE_SP_CLIENT_ID         Application (client) ID of the runtime Service Principal
                           (The SP that queries Databricks SQL Warehouse)

AZURE_SP_CLIENT_SECRET     Client secret for the runtime SP

AZURE_OPENAI_ENDPOINT      Azure OpenAI resource endpoint
                           Example: https://myaccount.openai.azure.com/

AZURE_OPENAI_KEY           Azure OpenAI API key (Key 1 or Key 2)
```

### Required — GitHub Variable

```
SMARTNEWS_API_URL          Public URL of the API Container App (no trailing slash)
                           Example: https://smartnews-api.victorioussea-ab137c42.eastus.azurecontainerapps.io
                           Used by frontend Docker build to set NEXT_PUBLIC_API_URL
```

### Optional — GitHub Secrets

```
AZURE_OPENAI_DEPLOYMENT    Model deployment name (default: gpt-4o-mini)
```

### Local Development — `.env` file

```
DATABRICKS_HOST            Same as above
DATABRICKS_TOKEN           Same as above
SQL_WAREHOUSE_ID           Same as above
AZURE_TENANT_ID            Same as above
AZURE_SP_CLIENT_ID         Same as above
AZURE_SP_CLIENT_SECRET     Same as above
AZURE_OPENAI_ENDPOINT      Same as above
AZURE_OPENAI_KEY           Same as above
AZURE_OPENAI_DEPLOYMENT    Same as above (default: gpt-4o-mini)
DATABRICKS_WORKSPACE_FOLDER  Path for notebooks (default: /SmartNews/pipelines)
CORS_ORIGINS               Allowed origins for API (default: *)
CACHE_TTL_SECONDS          API cache duration in seconds (default: 180)
```

---

## 14. Troubleshooting

### "The news pipeline is warming up"

The SQL Warehouse was idle and is restarting. Normal — wait 30 seconds and refresh.
If it persists > 2 minutes, check Databricks SQL Warehouse status.

### GitHub Actions fails at "Login to Azure"

`AZURE_CREDENTIALS` secret is wrong or expired. Re-generate:
```powershell
$rgId = az group show --name rg_FutureNews --query "id" -o tsv
az ad sp create-for-rbac --name github-smartnews-deploy --role Contributor --scopes $rgId --sdk-auth
```
Paste output as `AZURE_CREDENTIALS` secret.

### GitHub Actions fails at "Build & push image to ACR"

The SP doesn't have `AcrPush` role on the ACR:
```powershell
$acrId = az acr show --name smartnewsacr --resource-group rg_FutureNews --query "id" -o tsv
$spId  = (az ad sp show --id $(az ad sp list --display-name github-smartnews-deploy --query "[0].appId" -o tsv) --query "id" -o tsv)
az role assignment create --assignee $spId --role "AcrPush" --scope $acrId
```

### API returns 500 on /api/home

Check: are Databricks `serve.*` tables populated?
```sql
-- Run in Databricks SQL Editor
SELECT COUNT(*) FROM dbc_mcp_projects.serve.article_cards;
```
If 0 rows: run the `SmartNews_Daily_Pipeline` job (step 9).

### `deploy_to_databricks.py` fails with "Missing AZURE_TENANT_ID"

Set the required env vars in your `.env` file:
```
AZURE_TENANT_ID=xxxx
AZURE_SP_CLIENT_ID=xxxx
AZURE_SP_CLIENT_SECRET=xxxx
```

### Container App shows "Application Error"

Check logs:
```powershell
az containerapp logs show --name smartnews-api --resource-group rg_FutureNews --follow
az containerapp logs show --name smartnews-frontend --resource-group rg_FutureNews --follow
```

### The API Container App URL changed after re-deploy

The URL includes the Container Apps Environment suffix (e.g. `victorioussea-ab137c42`).
This suffix **only changes** if you delete and recreate the Container Apps Environment.
Updating a Container App within the same environment preserves the URL.

If you must recreate the environment:
1. Get new API URL: `az containerapp show --name smartnews-api --resource-group xxx --query "properties.configuration.ingress.fqdn" -o tsv`
2. Update GitHub Variable `SMARTNEWS_API_URL`
3. Re-trigger `deploy-frontend.yml` workflow (it will pick up the new URL)

---

## Quick Command Reference

```powershell
# ── Provision ────────────────────────────────────────────────────────────────
cd infra
.\provision-azure.ps1 -ResourceGroup "rg_SmartNews"

# ── Deploy notebooks + job ────────────────────────────────────────────────────
python deploy_to_databricks.py

# ── Trigger GitHub Actions ────────────────────────────────────────────────────
$h = @{ Authorization = "token ghp_xxxx" }
Invoke-RestMethod "https://api.github.com/repos/hacktan/SmartNews-Pipeline/actions/workflows/deploy.yml/dispatches" -Method POST -Headers $h -Body '{"ref":"main"}' -ContentType "application/json"
Invoke-RestMethod "https://api.github.com/repos/hacktan/SmartNews-Pipeline/actions/workflows/deploy-frontend.yml/dispatches" -Method POST -Headers $h -Body '{"ref":"main"}' -ContentType "application/json"

# ── Check platform health ──────────────────────────────────────────────────────
$API = "https://YOUR-API-URL"
Invoke-WebRequest "$API/health" -UseBasicParsing | Select StatusCode

# ── Stop container apps (overnight) ──────────────────────────────────────────
$apiRev = az containerapp revision list --name smartnews-api --resource-group rg_FutureNews --query "[?properties.active].name" -o tsv
az containerapp revision deactivate --name smartnews-api --resource-group rg_FutureNews --revision $apiRev

$feRev = az containerapp revision list --name smartnews-frontend --resource-group rg_FutureNews --query "[?properties.active].name" -o tsv
az containerapp revision deactivate --name smartnews-frontend --resource-group rg_FutureNews --revision $feRev

# ── Run Databricks pipeline manually ─────────────────────────────────────────
# From Databricks UI → Workflows → SmartNews_Daily_Pipeline → Run now
```
