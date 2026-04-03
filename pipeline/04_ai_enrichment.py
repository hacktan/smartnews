# AI Enrichment Layer
# Enriches gold.news_articles with OpenAI-generated fields:
#   ai_summary, hype_score, credibility_score, importance_score,
#   freshness_score, entities, subtopic, language, why_it_matters,
#   dehyped_title, embedding
#
# Processing is incremental: only articles where enriched_at IS NULL are processed.
#
# Required env vars:
#   OPENAI_API_KEY           — OpenAI API key
#   OPENAI_MODEL             — model to use (default: gpt-4o-mini)
#   OPENAI_EMBEDDING_MODEL   — embedding model (default: text-embedding-3-small)
#   ENRICHMENT_BATCH_LIMIT   — max articles per run (default: 50)

import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DB_PATH = os.getenv("DB_PATH", str(Path(__file__).parent.parent / "smartnews.duckdb"))
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
BATCH_LIMIT = int(os.getenv("ENRICHMENT_BATCH_LIMIT", "50"))
EMBEDDING_BATCH_LIMIT = 100
RATE_LIMIT_SLEEP = 0.3

SYSTEM_PROMPT = """You are a news analysis AI. Given a news article title and summary,
return a JSON object with exactly these fields:

{
  "ai_summary": "A clear, neutral 2-3 sentence summary of the article.",
  "why_it_matters": "1-2 sentences explaining why this story is significant for readers in this tech/news category.",
  "dehyped_title": "If hype_score > 0.6, rewrite the title as a calm, factual, accurate headline that preserves the core information but removes sensationalism, clickbait language, and exaggeration. If hype_score <= 0.6, return an empty string.",
  "hype_score": 0.0,
  "credibility_score": 0.0,
  "importance_score": 0.0,
  "entities": [{"name": "EntityName", "type": "PERSON|ORG|PLACE|PRODUCT|EVENT"}],
  "subtopic": "specific subtopic string",
  "language": "en"
}

Scoring rules:
- hype_score (0.0-1.0): how exaggerated, clickbait-like, or sensationalized the article is.
  0.0 = completely measured and factual, 1.0 = pure clickbait or extreme exaggeration.
- credibility_score (0.0-1.0): how trustworthy the content appears based on specificity,
  evidence signals, and journalistic quality. 0.0 = vague/unverifiable, 1.0 = highly specific and sourced.
- importance_score (0.0-1.0): how significant or impactful this story is likely to be.
  0.0 = trivial, 1.0 = major world event or breakthrough.
- why_it_matters: a concise, reader-focused explanation of the broader significance or real-world impact.
  Focus on what changes, who is affected, or what trend this signals. Do not repeat the summary.
- dehyped_title: Rewrite only if the original headline uses ALL CAPS, excessive punctuation (!!!),
  hyperbolic language ('destroy', 'revolutionary', 'mind-blowing'), or unsubstantiated superlatives.
  Keep the factual core intact. Max 15 words.
- subtopic: a specific sub-area within the category (e.g. "LLM Safety", "Chip Export Policy", "Series B Funding").
- language: ISO 639-1 code of the article language.
- entities: list the most important named entities only (max 5).

Return ONLY the JSON object. No markdown, no explanation."""


def compute_freshness(published_at) -> float:
    if published_at is None:
        return 0.1
    now = datetime.now(timezone.utc)
    pub = published_at
    if hasattr(pub, "tzinfo") and pub.tzinfo is None:
        pub = pub.replace(tzinfo=timezone.utc)
    hours_old = max(0, (now - pub).total_seconds() / 3600)
    return round(math.exp(-hours_old / 72.0), 4)


def clamp(v, default=0.5) -> float:
    try:
        return round(max(0.0, min(1.0, float(v))), 3)
    except Exception:
        return default


def enrich_article(client: OpenAI, entry_id: str, title: str, summary: str,
                   full_text: str, category: str, source: str) -> dict | None:
    body_section = ""
    if full_text and len(full_text) > 100:
        body_section = f"\nArticle Body (excerpt):\n{full_text[:3000]}"

    user_content = (
        f"Category: {category}\nSource: {source}\n"
        f"Title: {title}\nSummary: {summary or 'No summary available.'}{body_section}"
    )

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_content},
            ],
            temperature=0.1,
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)
        return {
            "entry_id":          entry_id,
            "ai_summary":        str(data.get("ai_summary", ""))[:1000],
            "why_it_matters":    str(data.get("why_it_matters", ""))[:500],
            "dehyped_title":     str(data.get("dehyped_title", ""))[:500],
            "hype_score":        clamp(data.get("hype_score")),
            "credibility_score": clamp(data.get("credibility_score")),
            "importance_score":  clamp(data.get("importance_score")),
            "entities":          json.dumps(data.get("entities", []))[:2000],
            "subtopic":          str(data.get("subtopic", ""))[:200],
            "language":          str(data.get("language", "en"))[:10],
        }
    except Exception as e:
        print(f"  ERROR enriching {entry_id}: {e}")
        return None


def get_embedding(client: OpenAI, text: str) -> list:
    try:
        resp = client.embeddings.create(
            model=OPENAI_EMBEDDING_MODEL,
            input=text[:8000],
        )
        return resp.data[0].embedding
    except Exception as e:
        print(f"  Embedding error: {e}")
        return []


def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY must be set.")

    client = OpenAI()
    con = duckdb.connect(DB_PATH)

    print(f"Model       : {OPENAI_MODEL}")
    print(f"Batch limit : {BATCH_LIMIT} articles per run")

    # Ensure AI columns exist (idempotent — DuckDB doesn't support ADD COLUMN IF NOT EXISTS
    # but we create the table with all columns in 03_gold_aggregation, so this is a safety net)

    # Fetch un-enriched articles
    pending = con.execute(f"""
        SELECT entry_id, title, clean_summary, full_text, category, feed_source, published_at
        FROM gold.news_articles
        WHERE enriched_at IS NULL
        LIMIT {BATCH_LIMIT}
    """).fetchall()

    pending_count = len(pending)
    print(f"Articles pending enrichment: {pending_count}")

    enriched = []
    failed_ids = []

    for i, row in enumerate(pending):
        entry_id, title, clean_summary, full_text, category, feed_source, published_at = row

        result = enrich_article(
            client,
            entry_id=entry_id,
            title=title or "",
            summary=clean_summary or "",
            full_text=full_text or "",
            category=category or "",
            source=feed_source or "",
        )

        if result:
            result["freshness_score"] = compute_freshness(published_at)
            enriched.append(result)
            if (i + 1) % 10 == 0:
                print(f"  Enriched {i + 1}/{pending_count}...")
        else:
            failed_ids.append(entry_id)

        time.sleep(RATE_LIMIT_SLEEP)

    print(f"\nEnrichment complete: {len(enriched)} succeeded, {len(failed_ids)} failed")

    if enriched:
        enriched_at = datetime.now(timezone.utc)
        con.executemany("""
            UPDATE gold.news_articles SET
                ai_summary        = ?,
                why_it_matters    = ?,
                dehyped_title     = ?,
                hype_score        = ?,
                credibility_score = ?,
                importance_score  = ?,
                freshness_score   = ?,
                entities          = ?,
                subtopic          = ?,
                language          = ?,
                enriched_at       = ?
            WHERE entry_id = ? AND enriched_at IS NULL
        """, [
            (
                r["ai_summary"], r["why_it_matters"], r["dehyped_title"],
                r["hype_score"], r["credibility_score"], r["importance_score"],
                r["freshness_score"], r["entities"], r["subtopic"], r["language"],
                enriched_at, r["entry_id"],
            )
            for r in enriched
        ])
        print("Enrichment updates written.")

    # Embedding pass — articles missing embedding
    emb_pending = con.execute(f"""
        SELECT entry_id, title, ai_summary
        FROM gold.news_articles
        WHERE embedding IS NULL
        LIMIT {EMBEDDING_BATCH_LIMIT}
    """).fetchall()

    print(f"\nArticles pending embedding: {len(emb_pending)}")

    if emb_pending:
        emb_results = []
        for row in emb_pending:
            entry_id, title, ai_summary = row
            text = f"{title or ''} {ai_summary or ''}".strip()
            vec = get_embedding(client, text)
            if vec:
                emb_results.append((json.dumps(vec), entry_id))
            time.sleep(0.05)

        if emb_results:
            con.executemany(
                "UPDATE gold.news_articles SET embedding = ? WHERE entry_id = ?",
                emb_results,
            )
            print(f"Embeddings written: {len(emb_results)} articles")

    # Story compilation pass
    con.execute("CREATE SCHEMA IF NOT EXISTS gold")
    con.execute("""
        CREATE TABLE IF NOT EXISTS gold.compiled_stories (
            story_id          VARCHAR PRIMARY KEY,
            compiled_title    VARCHAR,
            compiled_summary  VARCHAR,
            compiled_body     VARCHAR,
            source_count      INTEGER,
            sources_used      VARCHAR,
            key_claims        VARCHAR,
            consensus_points  VARCHAR,
            divergence_points VARCHAR,
            compiled_at       TIMESTAMPTZ,
            model_used        VARCHAR
        )
    """)

    COMPILATION_BATCH_LIMIT = 20
    COMPILATION_MAX_SOURCES = 6
    MIN_FULLTEXT_SOURCES = 2

    COMPILATION_PROMPT = """You are an expert news editor synthesizing multiple source reports about the same story into a single comprehensive, neutral article.

Return a JSON object:
{
  "compiled_title": "Clear, neutral headline (max 15 words)",
  "compiled_summary": "3-5 sentence synthesis covering key facts from all sources",
  "compiled_body": "400-700 word comprehensive article that leads with confirmed facts, attributes claims to sources, notes unique details, highlights disagreements, uses calm factual language",
  "key_claims": [{"claim": "factual claim text", "confirmed_by": ["Source1"], "disputed_by": [], "confidence": 0.0}],
  "consensus_points": ["Fact agreed on by all sources"],
  "divergence_points": ["Point where sources disagree, with both sides cited"]
}

Rules:
- NEVER invent facts not present in any source
- Use only the provided source texts
- Prefer specificity: numbers, names, dates from the most detailed source
- When sources conflict, present both versions with attribution
- Return ONLY the JSON object"""

    try:
        uncompiled = con.execute(f"""
            SELECT sm.story_id, sm.entry_ids, sm.source_count, sm.sources,
                   sm.canonical_title, sm.category, sm.last_published
            FROM gold.story_matches sm
            WHERE sm.source_count >= 2
            ORDER BY sm.last_published DESC
            LIMIT {COMPILATION_BATCH_LIMIT}
        """).fetchall()

        print(f"\nStories pending compilation: {len(uncompiled)}")
        compiled_results = []
        skipped_low_fulltext = 0

        for story_row in uncompiled:
            story_id, entry_ids_json, source_count, sources_json, canonical_title, category, last_published = story_row
            entry_ids = json.loads(entry_ids_json)

            ids_placeholder = ",".join(f"'{eid}'" for eid in entry_ids[:COMPILATION_MAX_SOURCES * 2])
            source_articles = con.execute(f"""
                SELECT entry_id, title, clean_summary, full_text, has_full_text,
                       feed_source, credibility_score, published_at
                FROM gold.news_articles
                WHERE entry_id IN ({ids_placeholder})
            """).fetchall()

            source_articles = sorted(
                source_articles,
                key=lambda a: (
                    1 if (a[3] and len(a[3]) >= 400) else 0,
                    float(a[6] or 0.0),
                    len(a[3] or ""),
                ),
                reverse=True,
            )

            fulltext_articles = [a for a in source_articles if a[3] and len(a[3]) >= 400]
            if len(fulltext_articles) < MIN_FULLTEXT_SOURCES:
                skipped_low_fulltext += 1
                print(f"  Skipping {story_id[:10]}... insufficient full-text sources ({len(fulltext_articles)})")
                continue

            selected = source_articles[:COMPILATION_MAX_SOURCES]

            source_texts = []
            for idx, art in enumerate(selected, 1):
                entry_id, title, clean_summary, full_text, has_full_text, feed_source, credibility_score, published_at = art
                body = full_text[:3000] if full_text else (clean_summary or "No text available.")
                pub_str = published_at.isoformat() if published_at else ""
                source_texts.append(
                    f"Source {idx} ({feed_source}):\nPublishedAt: {pub_str}\nTitle: {title}\nText: {body}"
                )

            user_content = f"Story covered by {len(selected)} sources:\n\n" + "\n\n".join(source_texts)

            try:
                response = client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": COMPILATION_PROMPT},
                        {"role": "user",   "content": user_content},
                    ],
                    temperature=0.0,
                    max_tokens=1500,
                    response_format={"type": "json_object"},
                )
                data = json.loads(response.choices[0].message.content)
                body_text = str(data.get("compiled_body", "")).strip()
                if len(body_text) < 600:
                    print(f"  Skipping {story_id[:10]}... compiled_body too short")
                    continue

                sources_used = json.dumps(sorted({a[5] for a in selected}))
                compiled_results.append((
                    story_id,
                    str(data.get("compiled_title", ""))[:500],
                    str(data.get("compiled_summary", ""))[:2000],
                    body_text[:5000],
                    source_count,
                    sources_used,
                    json.dumps(data.get("key_claims", []))[:5000],
                    json.dumps(data.get("consensus_points", []))[:2000],
                    json.dumps(data.get("divergence_points", []))[:2000],
                    datetime.now(timezone.utc),
                    OPENAI_MODEL,
                ))
                print(f"  Compiled story: {(canonical_title or '')[:60]}")
            except Exception as e:
                print(f"  ERROR compiling {story_id}: {e}")

            time.sleep(0.5)

        if compiled_results:
            con.executemany("""
                INSERT INTO gold.compiled_stories
                    (story_id, compiled_title, compiled_summary, compiled_body,
                     source_count, sources_used, key_claims, consensus_points,
                     divergence_points, compiled_at, model_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (story_id) DO UPDATE SET
                    compiled_title    = excluded.compiled_title,
                    compiled_summary  = excluded.compiled_summary,
                    compiled_body     = excluded.compiled_body,
                    source_count      = excluded.source_count,
                    sources_used      = excluded.sources_used,
                    key_claims        = excluded.key_claims,
                    consensus_points  = excluded.consensus_points,
                    divergence_points = excluded.divergence_points,
                    compiled_at       = excluded.compiled_at,
                    model_used        = excluded.model_used
            """, compiled_results)
            print(f"Compiled stories written: {len(compiled_results)}")

        if skipped_low_fulltext:
            print(f"Skipped stories (insufficient full-text): {skipped_low_fulltext}")

    except Exception as e:
        print(f"Compilation pass skipped (story_matches table may not exist yet): {e}")

    total = con.execute("SELECT COUNT(*) FROM gold.news_articles").fetchone()[0]
    enriched_total = con.execute(
        "SELECT COUNT(*) FROM gold.news_articles WHERE enriched_at IS NOT NULL"
    ).fetchone()[0]
    pending_remaining = total - enriched_total
    emb_total = con.execute(
        "SELECT COUNT(*) FROM gold.news_articles WHERE embedding IS NOT NULL"
    ).fetchone()[0]
    fulltext_total = con.execute(
        "SELECT COUNT(*) FROM gold.news_articles WHERE has_full_text = TRUE"
    ).fetchone()[0]

    print(f"\n=== AI Enrichment Summary ===")
    print(f"Total articles      : {total}")
    print(f"Enriched (all-time) : {enriched_total}")
    print(f"Pending             : {pending_remaining}")
    print(f"Processed this run  : {len(enriched)}")
    print(f"With embeddings     : {emb_total} / {total}")
    print(f"With full text      : {fulltext_total} / {total}")

    con.close()
    print(f"AI Enrichment OK: {len(enriched)} enriched, {pending_remaining} remaining")


if __name__ == "__main__":
    main()
