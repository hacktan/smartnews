# Gold Layer — Business Aggregations (Incremental)
# Builds daily aggregations from silver.rss_cleaned.
# Each run overwrites today's partition while preserving historical data.
#
# Tables:
#   gold.daily_category_summary — daily category-level summary
#   gold.daily_source_summary   — daily source-level summary
#   gold.news_articles          — all-time articles (analysis-ready gold view)

import os
from datetime import datetime, timezone
from pathlib import Path

import duckdb
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", str(Path(__file__).parent.parent / "smartnews.duckdb"))


def main():
    con = duckdb.connect(DB_PATH)

    con.execute("CREATE SCHEMA IF NOT EXISTS gold")

    con.execute("""
        CREATE TABLE IF NOT EXISTS gold.daily_category_summary (
            report_date    DATE,
            category       VARCHAR,
            article_count  BIGINT,
            avg_word_count DOUBLE,
            total_words    BIGINT,
            unique_sources BIGINT,
            avg_read_time  DOUBLE,
            updated_at     TIMESTAMPTZ,
            PRIMARY KEY (report_date, category)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS gold.daily_source_summary (
            report_date        DATE,
            feed_source        VARCHAR,
            article_count      BIGINT,
            categories_covered BIGINT,
            avg_word_count     DOUBLE,
            unique_authors     BIGINT,
            updated_at         TIMESTAMPTZ,
            PRIMARY KEY (report_date, feed_source)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS gold.news_articles (
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
            estimated_read_time_min INTEGER,
            image_url               VARCHAR,
            publish_date            DATE,
            updated_at              TIMESTAMPTZ,
            -- AI enrichment fields (populated by 04_ai_enrichment)
            ai_summary              VARCHAR,
            why_it_matters          VARCHAR,
            dehyped_title           VARCHAR,
            hype_score              DOUBLE,
            credibility_score       DOUBLE,
            importance_score        DOUBLE,
            freshness_score         DOUBLE,
            entities                VARCHAR,
            subtopic                VARCHAR,
            language                VARCHAR,
            embedding               VARCHAR,
            enriched_at             TIMESTAMPTZ
        )
    """)

    print("Gold tables ready.")

    report_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"Processing report_date: {report_date}")

    # Load silver records for today (by published_at or ingested_at)
    today_count = con.execute(f"""
        SELECT COUNT(*) FROM silver.rss_cleaned
        WHERE DATE(published_at) = '{report_date}'
           OR DATE(ingested_at)  = '{report_date}'
    """).fetchone()[0]

    if today_count == 0:
        print(f"No data for {report_date}. Using latest available data...")
        latest_date = con.execute(
            "SELECT MAX(DATE(ingested_at)) FROM silver.rss_cleaned"
        ).fetchone()[0]
        if latest_date is None:
            print("Silver table is empty. Nothing to aggregate.")
            con.close()
            return
        report_date = str(latest_date)
        today_count = con.execute(f"""
            SELECT COUNT(*) FROM silver.rss_cleaned
            WHERE DATE(ingested_at) = '{report_date}'
        """).fetchone()[0]
        print(f"Using latest available data ({report_date}): {today_count} records")

    updated_at = datetime.now(timezone.utc)

    # 1. Daily Category Summary — delete + reinsert today's partition
    con.execute(f"DELETE FROM gold.daily_category_summary WHERE report_date = '{report_date}'")
    con.execute(f"""
        INSERT INTO gold.daily_category_summary
        SELECT
            CAST('{report_date}' AS DATE)   AS report_date,
            category,
            COUNT(entry_id)                 AS article_count,
            ROUND(AVG(word_count), 1)       AS avg_word_count,
            SUM(word_count)                 AS total_words,
            COUNT(DISTINCT feed_source)     AS unique_sources,
            ROUND(AVG(estimated_read_time_min), 1) AS avg_read_time,
            TIMESTAMPTZ '{updated_at.isoformat()}' AS updated_at
        FROM silver.rss_cleaned
        WHERE DATE(published_at) = '{report_date}'
           OR DATE(ingested_at)  = '{report_date}'
        GROUP BY category
        ORDER BY article_count DESC
    """)
    cat_count = con.execute(
        f"SELECT COUNT(*) FROM gold.daily_category_summary WHERE report_date = '{report_date}'"
    ).fetchone()[0]
    print(f"Category summary written: {cat_count} categories")

    # 2. Daily Source Summary — delete + reinsert today's partition
    con.execute(f"DELETE FROM gold.daily_source_summary WHERE report_date = '{report_date}'")
    con.execute(f"""
        INSERT INTO gold.daily_source_summary
        SELECT
            CAST('{report_date}' AS DATE)   AS report_date,
            feed_source,
            COUNT(entry_id)                 AS article_count,
            COUNT(DISTINCT category)        AS categories_covered,
            ROUND(AVG(word_count), 1)       AS avg_word_count,
            COUNT(DISTINCT author)          AS unique_authors,
            TIMESTAMPTZ '{updated_at.isoformat()}' AS updated_at
        FROM silver.rss_cleaned
        WHERE DATE(published_at) = '{report_date}'
           OR DATE(ingested_at)  = '{report_date}'
        GROUP BY feed_source
        ORDER BY article_count DESC
    """)
    src_count = con.execute(
        f"SELECT COUNT(*) FROM gold.daily_source_summary WHERE report_date = '{report_date}'"
    ).fetchone()[0]
    print(f"Source summary written: {src_count} sources")

    # 3. Gold Articles — incremental insert (new silver rows only)
    #    AI enrichment columns are left NULL; 04_ai_enrichment.py fills them in.
    con.execute(f"""
        INSERT INTO gold.news_articles
            (entry_id, title, clean_summary, full_text, has_full_text,
             link, published_at, author, category, tags, feed_source,
             word_count, estimated_read_time_min, image_url,
             publish_date, updated_at)
        SELECT
            s.entry_id, s.title, s.clean_summary, s.full_text, s.has_full_text,
            s.link, s.published_at, s.author, s.category, s.tags, s.feed_source,
            s.word_count, s.estimated_read_time_min, s.image_url,
            DATE(s.published_at) AS publish_date,
            TIMESTAMPTZ '{updated_at.isoformat()}' AS updated_at
        FROM silver.rss_cleaned s
        WHERE (DATE(s.published_at) = '{report_date}' OR DATE(s.ingested_at) = '{report_date}')
          AND NOT EXISTS (SELECT 1 FROM gold.news_articles g WHERE g.entry_id = s.entry_id)
    """)

    # Sync mutable descriptive fields from silver for existing articles.
    # This keeps category taxonomy and summaries current when classification rules evolve.
    con.execute("""
        UPDATE gold.news_articles AS g
        SET
            title                   = s.title,
            clean_summary           = s.clean_summary,
            category                = s.category,
            tags                    = s.tags,
            author                  = s.author,
            estimated_read_time_min = s.estimated_read_time_min,
            image_url               = COALESCE(g.image_url, s.image_url),
            updated_at              = NOW()
        FROM silver.rss_cleaned s
        WHERE g.entry_id = s.entry_id
    """)

    # Full-text backfill — update gold rows that were inserted without full_text
    # but where silver now has it (e.g. scraping ran after gold ingestion).
    con.execute("""
        UPDATE gold.news_articles AS g
        SET
            full_text     = s.full_text,
            has_full_text = TRUE,
            word_count    = s.word_count
        FROM silver.rss_cleaned s
        WHERE g.entry_id = s.entry_id
          AND (g.full_text IS NULL OR g.has_full_text = FALSE)
          AND s.has_full_text = TRUE
          AND s.full_text IS NOT NULL
          AND LENGTH(s.full_text) > 100
    """)

    total_art = con.execute("SELECT COUNT(*) FROM gold.news_articles").fetchone()[0]
    distinct_days = con.execute(
        "SELECT COUNT(DISTINCT report_date) FROM gold.daily_category_summary"
    ).fetchone()[0]

    print(f"\n=== Gold Layer Summary ===")
    print(f"daily_category_summary : {cat_count} categories ({distinct_days} days)")
    print(f"daily_source_summary   : {src_count} sources")
    print(f"news_articles (total)  : {total_art} articles")
    print(f"Report date processed  : {report_date}")

    con.close()
    print(f"Gold OK: {today_count} articles processed for {report_date}")


if __name__ == "__main__":
    main()
