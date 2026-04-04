# Silver Layer — Data Cleaning & Transformation
# Cleans and categorizes new records from bronze.rss_raw
# and upserts them into silver.rss_cleaned (DuckDB).

import html
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import duckdb
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", str(Path(__file__).parent.parent / "smartnews.duckdb"))

CATEGORY_KEYWORDS = {
    "World & Geopolitics": [
        "world", "war", "conflict", "ceasefire", "election", "summit", "diplomacy",
        "sanction", "nato", "un", "ukraine", "gaza", "china", "russia", "middle east",
    ],
    "Business & Markets": [
        "market", "stocks", "bond", "inflation", "interest rate", "fed", "earnings", "ipo",
        "acquisition", "merger", "revenue", "economy", "trade", "tariff", "finance",
    ],
    "Policy & Politics": [
        "policy", "congress", "senate", "parliament", "government", "minister", "president",
        "campaign", "vote", "lawmakers", "regulation", "antitrust",
    ],
    "Science & Research": [
        "science", "research", "study", "scientist", "laboratory", "physics", "biology",
        "genetics", "astronomy", "space", "experiment", "peer-reviewed", "nature journal",
    ],
    "Health & Medicine": [
        "health", "medicine", "medical", "hospital", "disease", "virus", "vaccine",
        "drug", "clinical", "cdc", "who", "mental health",
    ],
    "Climate & Environment": [
        "climate", "emissions", "carbon", "renewable", "wildfire", "storm", "hurricane",
        "drought", "flood", "environment", "pollution",
    ],
    "AI & Machine Learning": ["ai", "artificial intelligence", "machine learning", "llm", "gpt", "neural"],
    "Cloud & Infrastructure": ["cloud", "aws", "azure", "kubernetes", "docker", "serverless"],
    "Cybersecurity": ["security", "hack", "breach", "vulnerability", "cyber", "privacy"],
    "Mobile & Apps": ["iphone", "android", "app", "mobile", "ios"],
    "Data & Analytics": ["data", "analytics", "database", "sql", "pipeline", "etl"],
    "Software Development": ["developer", "programming", "code", "github", "open source", "api"],
    "Hardware & Devices": ["chip", "processor", "gpu", "hardware", "device", "sensor"],
    "Technology Business": ["startup", "funding", "saas", "platform", "software company", "tech company"],
}

SOURCE_CATEGORY_HINTS = {
    "BBC World": "World & Geopolitics",
    "NYT World": "World & Geopolitics",
    "The Guardian World": "World & Geopolitics",
    "Al Jazeera": "World & Geopolitics",
    "UN News": "World & Geopolitics",
    "Washington Post World": "World & Geopolitics",
    "BBC Business": "Business & Markets",
    "NYT Business": "Business & Markets",
    "The Guardian Business": "Business & Markets",
    "Bloomberg Markets": "Business & Markets",
    "Financial Times World": "Business & Markets",
    "The Economist": "Business & Markets",
    "BBC Science": "Science & Research",
    "NYT Science": "Science & Research",
    "The Guardian Science": "Science & Research",
    "Nature": "Science & Research",
    "ScienceDaily": "Science & Research",
    "ScienceDaily Health": "Health & Medicine",
    "WHO News": "Health & Medicine",
    "The Hill": "Policy & Politics",
    "PBS NewsHour": "Policy & Politics",
}

TECH_SIGNAL_KEYWORDS = {
    "ai", "artificial intelligence", "machine learning", "software", "app", "iphone", "android",
    "cloud", "cyber", "chip", "open source", "developer", "github", "kubernetes", "api",
}


def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = html.unescape(raw_html)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def categorize(title: str, summary: str, feed_source: str = "") -> str:
    text = f"{title or ''} {summary or ''}".lower()

    source_hint = SOURCE_CATEGORY_HINTS.get(feed_source or "")
    if source_hint and not any(kw in text for kw in TECH_SIGNAL_KEYWORDS):
        return source_hint

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category
    return source_hint or "General News"


def word_count(text: str) -> int:
    if not text:
        return 0
    return len(text.split())


def read_time(wc: int) -> int:
    return max(1, wc // 200)


def main():
    con = duckdb.connect(DB_PATH)

    con.execute("CREATE SCHEMA IF NOT EXISTS silver")
    con.execute("""
        CREATE TABLE IF NOT EXISTS silver.rss_cleaned (
            entry_id                VARCHAR PRIMARY KEY,
            title                   VARCHAR,
            clean_summary           VARCHAR,
            full_text               VARCHAR,
            has_full_text           BOOLEAN,
            link                    VARCHAR,
            published_at            TIMESTAMPTZ,
            author                  VARCHAR,
            category                VARCHAR,
            tags                    VARCHAR,
            feed_source             VARCHAR,
            word_count              INTEGER,
            title_length            INTEGER,
            has_summary             BOOLEAN,
            estimated_read_time_min INTEGER,
            image_url               VARCHAR,
            ingested_at             TIMESTAMPTZ,
            transformed_at          TIMESTAMPTZ,
            pipeline_run_id         VARCHAR
        )
    """)
    print("Table silver.rss_cleaned ready.")

    # Fetch bronze records not yet in silver, LEFT JOIN fulltext
    new_bronze = con.execute("""
        SELECT
            b.entry_id, b.title, b.summary, b.link,
            b.published_at, b.author, b.tags, b.feed_source,
            b.ingested_at, b.pipeline_run_id,
            f.full_text       AS raw_full_text,
            f.extraction_ok   AS has_full_text,
            COALESCE(f.image_url, b.rss_image_url) AS image_url
        FROM bronze.rss_raw b
        LEFT JOIN bronze.article_fulltext f ON b.entry_id = f.entry_id
        LEFT JOIN silver.rss_cleaned s ON b.entry_id = s.entry_id
        WHERE s.entry_id IS NULL
    """).fetchall()

    new_count = len(new_bronze)
    print(f"New records to transform: {new_count}")
    transformed_at = datetime.now(timezone.utc)
    rows = []

    for row in new_bronze:
        (entry_id, raw_title, raw_summary, link,
         published_at, author, tags, feed_source,
         ingested_at, pipeline_run_id,
         raw_full_text, has_full_text_flag, image_url) = row

        title = clean_html(raw_title or "")
        clean_summary = clean_html(raw_summary or "")
        full_text = raw_full_text or None
        has_full_text = bool(has_full_text_flag)

        category = categorize(title, clean_summary, feed_source)
        body_for_count = full_text if has_full_text and full_text else clean_summary
        wc = word_count(body_for_count)
        title_len = len(title)
        has_summary = bool(clean_summary)
        read_time_min = read_time(wc)

        rows.append((
            entry_id, title, clean_summary, full_text, has_full_text,
            link, published_at, author, category, tags, feed_source,
            wc, title_len, has_summary, read_time_min,
            image_url, ingested_at, transformed_at, pipeline_run_id,
        ))

    if rows:
        con.executemany("""
            INSERT INTO silver.rss_cleaned
                (entry_id, title, clean_summary, full_text, has_full_text,
                 link, published_at, author, category, tags, feed_source,
                 word_count, title_length, has_summary, estimated_read_time_min,
                 image_url, ingested_at, transformed_at, pipeline_run_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (entry_id) DO NOTHING
        """, rows)
        print(f"Transformed and inserted: {len(rows)} records.")
    else:
        print("Nothing new to insert; running backfill and category refresh.")

    # Full-text backfill — update silver rows that were inserted without full_text
    # but where bronze.article_fulltext now has a successful extraction.
    backfill = con.execute("""
        SELECT s.entry_id, f.full_text, f.extraction_ok
        FROM silver.rss_cleaned s
        JOIN bronze.article_fulltext f ON s.entry_id = f.entry_id
        WHERE s.has_full_text = FALSE
          AND f.extraction_ok = TRUE
          AND f.full_text IS NOT NULL
          AND LENGTH(f.full_text) > 100
    """).fetchall()

    if backfill:
        con.executemany("""
            UPDATE silver.rss_cleaned
            SET full_text = ?, has_full_text = TRUE
            WHERE entry_id = ? AND has_full_text = FALSE
        """, [(r[1], r[0]) for r in backfill])
        print(f"Full-text backfill: {len(backfill)} rows updated.")

    # Image backfill — update silver rows that have no image_url
    img_backfill = con.execute("""
        SELECT s.entry_id, COALESCE(f.image_url, b.rss_image_url) AS image_url
        FROM silver.rss_cleaned s
        JOIN bronze.rss_raw b ON s.entry_id = b.entry_id
        LEFT JOIN bronze.article_fulltext f ON s.entry_id = f.entry_id
        WHERE s.image_url IS NULL
          AND COALESCE(f.image_url, b.rss_image_url) IS NOT NULL
    """).fetchall()

    if img_backfill:
        con.executemany("""
            UPDATE silver.rss_cleaned
            SET image_url = ?
            WHERE entry_id = ? AND image_url IS NULL
        """, [(r[1], r[0]) for r in img_backfill])
        print(f"Image backfill: {len(img_backfill)} rows updated.")

    # Recategorize recent records so newly added non-tech feeds are reflected immediately.
    recent_rows = con.execute("""
        SELECT entry_id, title, clean_summary, feed_source, category
        FROM silver.rss_cleaned
        WHERE published_at >= current_date - INTERVAL '30 days'
    """).fetchall()

    recat_updates = []
    for entry_id, title, clean_summary, feed_source, old_category in recent_rows:
        new_category = categorize(title or "", clean_summary or "", feed_source or "")
        if (old_category or "") != new_category:
            recat_updates.append((new_category, entry_id))

    if recat_updates:
        con.executemany(
            "UPDATE silver.rss_cleaned SET category = ? WHERE entry_id = ?",
            recat_updates,
        )
        print(f"Category refresh: {len(recat_updates)} rows recategorized.")

    total = con.execute("SELECT COUNT(*) FROM silver.rss_cleaned").fetchone()[0]
    print(f"\nSilver table total rows : {total}")
    print(f"New records added       : {new_count}")

    con.close()
    print(f"Silver OK: {new_count} new records transformed")


if __name__ == "__main__":
    main()
