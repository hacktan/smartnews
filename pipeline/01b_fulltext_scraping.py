# Bronze Layer — Full-Text Scraping
# Fetches full article body from source URLs using trafilatura.
# Runs after 01_bronze_ingestion and stores results in bronze.article_fulltext.
# Articles that fail extraction gracefully fall back to RSS summary downstream.

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import duckdb
import httpx
import lxml_html_clean  # noqa: F401 — must import before trafilatura
import trafilatura
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", str(Path(__file__).parent.parent / "smartnews.duckdb"))

SCRAPE_BATCH_LIMIT = int(os.getenv("SCRAPE_BATCH_LIMIT", "200"))
SCRAPE_DELAY = 1.0    # seconds between requests (polite crawling)
SCRAPE_TIMEOUT = 15   # seconds per HTTP request
MAX_PER_DOMAIN = 20   # max articles per domain per run
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_html_with_fallback(url: str) -> tuple[str | None, str | None]:
    downloaded = trafilatura.fetch_url(url)
    if downloaded:
        return downloaded, None

    try:
        with httpx.Client(timeout=SCRAPE_TIMEOUT, follow_redirects=True, headers=HTTP_HEADERS) as client:
            resp = client.get(url)
            if resp.status_code >= 400:
                return None, f"http_status_{resp.status_code}"
            text = resp.text
            if not text or len(text.strip()) < 200:
                return None, "httpx body too short"
            return text, "httpx_fallback"
    except Exception as e:
        return None, f"httpx_fallback_error: {str(e)[:200]}"


def main():
    con = duckdb.connect(DB_PATH)

    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    con.execute("""
        CREATE TABLE IF NOT EXISTS bronze.article_fulltext (
            entry_id        VARCHAR PRIMARY KEY,
            full_text       VARCHAR,
            image_url       VARCHAR,
            text_length     INTEGER,
            extraction_ok   BOOLEAN,
            extraction_err  VARCHAR,
            source_domain   VARCHAR,
            robots_allowed  BOOLEAN,
            scraped_at      TIMESTAMPTZ,
            pipeline_run_id VARCHAR
        )
    """)
    print("Table bronze.article_fulltext ready.")

    pipeline_run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    pending = con.execute(f"""
        SELECT b.entry_id, b.link, b.feed_source
        FROM bronze.rss_raw b
        LEFT JOIN bronze.article_fulltext f
            ON b.entry_id = f.entry_id AND f.extraction_ok = TRUE
        WHERE f.entry_id IS NULL
        LIMIT {SCRAPE_BATCH_LIMIT}
    """).fetchall()

    pending_count = len(pending)
    print(f"Articles pending scraping: {pending_count}")

    if pending_count == 0:
        print("All articles already scraped.")
        con.close()
        return

    domain_counts: dict[str, int] = {}
    results = []
    skipped_domain = 0

    for row in pending:
        entry_id, url, feed_source = row

        if not url:
            results.append((
                entry_id, None, None, 0, False, "No URL", "", True,
                datetime.now(timezone.utc), pipeline_run_id,
            ))
            continue

        domain = urlparse(url).netloc
        domain_counts[domain] = domain_counts.get(domain, 0) + 1

        if domain_counts[domain] > MAX_PER_DOMAIN:
            skipped_domain += 1
            continue

        try:
            downloaded, fetch_note = fetch_html_with_fallback(url)

            if not downloaded:
                results.append((
                    entry_id, None, None, 0, False,
                    fetch_note or "fetch_url returned None",
                    domain, True, datetime.now(timezone.utc), pipeline_run_id,
                ))
                time.sleep(SCRAPE_DELAY)
                continue

            image_url = None
            try:
                meta = trafilatura.extract_metadata(downloaded)
                if meta and meta.image:
                    image_url = meta.image
            except Exception:
                pass

            text = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=False,
                favor_precision=True,
            )

            if text and len(text.strip()) > 50:
                results.append((
                    entry_id, text.strip(), image_url, len(text.strip()),
                    True, fetch_note, domain, True,
                    datetime.now(timezone.utc), pipeline_run_id,
                ))
            else:
                results.append((
                    entry_id, None, image_url, 0, False,
                    "Extracted text too short or empty (paywall/JS?)",
                    domain, True, datetime.now(timezone.utc), pipeline_run_id,
                ))

        except Exception as e:
            results.append((
                entry_id, None, None, 0, False, str(e)[:500],
                domain, True, datetime.now(timezone.utc), pipeline_run_id,
            ))

        time.sleep(SCRAPE_DELAY)

        if len(results) % 20 == 0:
            print(f"  Scraped {len(results)}/{pending_count}...")

    success_count = sum(1 for r in results if r[4])
    fail_count = sum(1 for r in results if not r[4])

    print(f"\nScraping complete:")
    print(f"  Success: {success_count}")
    print(f"  Failed:  {fail_count}")
    print(f"  Skipped (domain limit): {skipped_domain}")

    if results:
        con.executemany("""
            INSERT INTO bronze.article_fulltext
                (entry_id, full_text, image_url, text_length,
                 extraction_ok, extraction_err, source_domain,
                 robots_allowed, scraped_at, pipeline_run_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (entry_id) DO UPDATE SET
                full_text       = excluded.full_text,
                image_url       = excluded.image_url,
                text_length     = excluded.text_length,
                extraction_ok   = excluded.extraction_ok,
                extraction_err  = excluded.extraction_err,
                source_domain   = excluded.source_domain,
                scraped_at      = excluded.scraped_at,
                pipeline_run_id = excluded.pipeline_run_id
        """, results)

    total = con.execute("SELECT COUNT(*) FROM bronze.article_fulltext").fetchone()[0]
    total_ok = con.execute(
        "SELECT COUNT(*) FROM bronze.article_fulltext WHERE extraction_ok = TRUE"
    ).fetchone()[0]

    print(f"\n=== Fulltext Scraping Summary ===")
    print(f"Total scraped (all-time): {total}")
    print(f"Successful extractions:   {total_ok}")
    print(f"This run success:         {success_count}")

    con.close()
    print(f"Fulltext OK: {success_count} extracted, {fail_count} failed")


if __name__ == "__main__":
    main()
