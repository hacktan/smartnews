# SmartNews — Quick Start Guide

> **For AI agents**: Read `AGENT_HANDOFF.md` first — it has all credentials and resources.
> This guide is the human-readable setup walkthrough for a **brand-new Azure environment**.

---

## What You're Setting Up

```
RSS Feeds → Databricks (Bronze→Silver→Gold→Serve) → FastAPI → Next.js
               Azure OpenAI enrichment ↗
```

Full setup takes about 30-45 minutes (most of it is waiting for Azure to provision).

---

## Prerequisites

| Tool | How to install |
|------|---------------|
| Azure CLI | [aka.ms/installazurecli](https://aka.ms/installazurecli) |
| Python 3.11+ | `winget install Python.Python.3.11` |
| uv (Python mgr) | `pip install uv` |
| Git | Already installed |

---

## Phase 0 — One-Time Manual Setup (new Azure account only)

These steps require human interaction and cannot be automated.

### 0.1 Create a Service Principal

```powershell
az login
az ad sp create-for-rbac `
  --name "smartnews-sp" `
  --role Contributor `
  --scopes "/subscriptions/YOUR-SUBSCRIPTION-ID" `
  --sdk-auth
```

Save the output JSON — it gives you `clientId`, `clientSecret`, `tenantId`, `subscriptionId`.

### 0.2 Create Databricks Workspace

```powershell
az databricks workspace create `
  --name "smartnews-databricks" `
  --resource-group "rg_FutureNews" `
  --location "eastus" `
  --sku premium
```

> **Premium SKU required** for Unity Catalog.

### 0.3 Set Up Unity Catalog (Databricks account admin)

1. Go to [accounts.azuredatabricks.net](https://accounts.azuredatabricks.net)
2. Create a metastore for East US (if none exists)
3. Attach the metastore to your workspace
4. Create catalog: `dbc_mcp_projects`
5. Create schemas: `bronze`, `silver`, `gold`, `serve`
6. Grant the Service Principal `ALL PRIVILEGES` on the catalog

### 0.4 Create Databricks PAT

1. Open Databricks workspace
2. Top-right → User settings → Access Tokens → Generate token
3. Save the token (starts with `dapi...`)

### 0.5 Create SQL Warehouse

1. In Databricks: SQL tab → SQL Warehouses → Create Starter Warehouse
2. Note the Warehouse ID from the URL or settings

### 0.6 Add Service Principal to Workspace (SCIM)

1. Databricks workspace: Settings → Identity & access → Service principals → Add
2. Add the SP by client ID
3. Give `CAN_MANAGE` and SQL access permissions

---

## Phase 1 — Configure Your Environment

```powershell
# Clone the repo
git clone https://github.com/hacktan/SmartNews-Pipeline.git
cd SmartNews-Pipeline

# Install Python dependencies
C:\Users\haktan\.local\bin\uv.exe sync

# Create .env from template
copy .env.example .env
```

Edit `.env` with your values:
```env
DATABRICKS_HOST=https://adb-XXXXXXXXXXXX.azuredatabricks.net/
DATABRICKS_TOKEN=dapiXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

SQL_WAREHOUSE_ID=XXXXXXXXXXXXXXXX

AZURE_TENANT_ID=YOUR-TENANT-ID
AZURE_SP_CLIENT_ID=YOUR-SP-CLIENT-ID
AZURE_SP_CLIENT_SECRET=YOUR-SP-CLIENT-SECRET

AZURE_OPENAI_ENDPOINT=https://YOUR-RESOURCE.openai.azure.com/
AZURE_OPENAI_KEY=YOUR-OPENAI-KEY
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
```

---

## Phase 2 — Automated Bootstrap (everything else)

Run the bootstrap script — it handles OpenAI, ACR, Container Apps, and Databricks job:

```powershell
# Login to Azure first
az login

# Run full bootstrap (uses values from .env automatically)
.\scripts\bootstrap.ps1

# For a brand-new environment with different resource names:
.\scripts\bootstrap.ps1 `
  -SubscriptionId "YOUR-SUBSCRIPTION-ID" `
  -TenantId "YOUR-TENANT-ID" `
  -ResourceGroup "rg_YourProject" `
  -AcrName "yourprojectacr" `
  -SpClientId "YOUR-SP-CLIENT-ID" `
  -SpClientSecret "YOUR-SP-SECRET" `
  -DatabricksHost "https://adb-XXXX.azuredatabricks.net/" `
  -DatabricksToken "dapiXXXXXX" `
  -SqlWarehouseId "XXXXXXXX" `
  -TriggerRun   # optionally run the pipeline immediately
```

The script will:
1. Create Resource Group
2. Create Azure OpenAI + gpt-4o-mini deployment (10K TPM)
3. Create Azure Container Registry
4. Build & push Docker image (cloud build, no local Docker needed)
5. Create Container Apps environment + app
6. Deploy Databricks notebooks + create job (every 4h schedule)

---

## Phase 3 — Verify Everything Works

```powershell
# Quick health check
C:\Users\haktan\.local\bin\uv.exe run python -c "
import httpx
r = httpx.get('https://YOUR-APP-URL/health', timeout=20)
print(r.status_code, r.text)
"

# Full smoke test (edit BASE in test_api.py to your URL)
C:\Users\haktan\.local\bin\uv.exe run python test_api.py
```

Expected result: all endpoints return `200 OK`.

---

## Phase 4 — Set Up GitHub Actions (CI/CD)

After first deploy, enable auto-deploy on every push to `main`:

### 4.1 Add GitHub Secrets

Go to GitHub repo → Settings → Secrets → Actions → New repository secret:

| Secret | Value |
|--------|-------|
| `AZURE_CREDENTIALS` | The JSON from `az ad sp create-for-rbac --sdk-auth` (Step 0.1) |
| `DATABRICKS_HOST` | Your Databricks workspace URL |
| `DATABRICKS_TOKEN` | Your PAT token |
| `AZURE_TENANT_ID` | Your tenant ID |
| `AZURE_SP_CLIENT_ID` | SP client ID |
| `AZURE_SP_CLIENT_SECRET` | SP client secret |
| `AZURE_OPENAI_ENDPOINT` | OpenAI endpoint |
| `AZURE_OPENAI_KEY` | OpenAI API key |
| `SQL_WAREHOUSE_ID` | SQL warehouse ID |

### 4.2 What triggers CI/CD

- **Auto**: any push to `main` that changes `api/**` or `Dockerfile` → rebuilds image + deploys
- **Auto**: any push to `main` that changes `notebooks/**` → also redeploys Databricks job
- **Manual**: GitHub → Actions → "Deploy API to Azure Container Apps" → Run workflow

---

## Redeploying API Only (quick)

After changing API code:

```powershell
.\scripts\deploy_api.ps1
```

Or push to GitHub — CI/CD handles it automatically.

---

## Redeploying Databricks Pipeline Only

After changing notebooks:

```powershell
C:\Users\haktan\.local\bin\uv.exe run python deploy_to_databricks.py
```

---

## Existing Environment Reference

The current deployed environment (no changes needed):

| Resource | Value |
|----------|-------|
| API URL | `https://smartnews-api.victorioussea-ab137c42.eastus.azurecontainerapps.io` |
| Databricks | `https://adb-7405617617055328.8.azuredatabricks.net/` |
| Resource Group | `rg_FutureNews` (East US) |
| ACR | `smartnewsacr.azurecr.io` |
| Job ID | `375934533722180` |

All credentials in `AGENT_HANDOFF.md` Section 4.

---

## Troubleshooting

| Problem | Solution |
|---------|---------|
| Container App crashes with `ModuleNotFoundError: No module named 'httpx'` | `httpx` missing from Dockerfile pip install — check `Dockerfile` |
| SQL Warehouse auth fails (error 403 / SCIM inactive) | Use SP OAuth, not PAT — see `api/db.py` auth flow |
| `az acr build` crashes with `UnicodeEncodeError: 'charmap'` | Run `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` first |
| Container App stays on old revision after `az containerapp update` | Must use `--revision-suffix <unique>` to force new revision pull |
| Databricks job fails with `active: False` | User SCIM issue — job must run as Service Principal, not personal account |
| OpenAI rate limit | Increase capacity with `.\increase_capacity.ps1` or reduce `ENRICHMENT_BATCH_LIMIT` |
