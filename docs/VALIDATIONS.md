# VALIDATIONS

This file is the operational checklist for validating SmartNews after code or pipeline changes.

## 1) Data Pipeline Validation

Run full pipeline locally in this exact order:

```bash
uv run python pipeline/01_bronze_ingestion.py
uv run python pipeline/01b_fulltext_scraping.py
uv run python pipeline/02_silver_transformation.py
uv run python pipeline/03_gold_aggregation.py
uv run python pipeline/04_ai_enrichment.py
uv run python pipeline/03b_story_matching.py
uv run python pipeline/04b_claim_extraction.py
uv run python pipeline/04_ai_enrichment.py
uv run python pipeline/05_serving_projection.py
uv run python pipeline/validate.py
```

Pass criteria:
- `pipeline/validate.py` exits with code `0`.
- Critical tables are non-empty (`bronze`, `silver`, `gold.news_articles`, `serve.article_cards`).
- Non-critical checks should not regress unexpectedly (`gold.article_claims`, `serve.story_claims`, `serve.compiled_stories`).

## 2) API Validation

Minimum smoke checks:

```bash
curl -s https://smartnews-api.onrender.com/health
curl -s https://smartnews-api.onrender.com/api/home
curl -s https://smartnews-api.onrender.com/api/stories?limit=3
curl -s https://smartnews-api.onrender.com/api/story/<story_id>
curl -s https://smartnews-api.onrender.com/api/story/<story_id>/claims
```

Pass criteria:
- `/health` returns `{"status":"ok"}`.
- Story detail returns 200 for a valid `story_id`.
- Story claims endpoint returns 200 and a valid JSON object.

## 3) Frontend Validation

Local:

```bash
cd frontend
npm run build
```

Live smoke checks:

```bash
curl -s -o NUL -w "%{http_code}" https://frontend-chi-brown-98.vercel.app/
curl -s -o NUL -w "%{http_code}" https://frontend-chi-brown-98.vercel.app/stories
curl -s -o NUL -w "%{http_code}" https://frontend-chi-brown-98.vercel.app/story/<story_id>
curl -s -o NUL -w "%{http_code}" https://frontend-chi-brown-98.vercel.app/search?q=ai
```

Pass criteria:
- All routes above return `200`.
- Story page renders claims section when `/api/story/<id>/claims` has data.

## 4) Regression Watchpoints

- Broken article pages (`/article/[id]`) must not return 500.
- Footer GitHub link must point to `https://github.com/hacktan/smartnews`.
- Workflow order in `.github/workflows/pipeline.yml` must include `04b_claim_extraction.py`.
