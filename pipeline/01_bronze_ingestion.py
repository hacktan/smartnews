# Bronze Layer — RSS Feed Ingestion
# Fetches raw data from RSS feeds and upserts into bronze.rss_raw (DuckDB).

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import feedparser
import httpx
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", str(Path(__file__).parent.parent / "smartnews.duckdb"))

RSS_FEEDS = [
    "http://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    "https://www.theverge.com/rss/index.xml",
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://www.engadget.com/rss.xml",
    "https://venturebeat.com/feed/",
    "https://techcrunch.com/feed/",
    "https://www.wired.com/feed/rss",
    "https://www.technologyreview.com/feed/",
    "https://www.zdnet.com/news/rss.xml",
    "https://www.cnet.com/rss/news/",
    "https://www.theguardian.com/uk/technology/rss",
    "https://mashable.com/feeds/rss/tech",
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "http://feeds.bbci.co.uk/news/business/rss.xml",
    "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",
    "https://www.theguardian.com/world/rss",
    "https://www.theguardian.com/uk/business/rss",
    "https://www.theguardian.com/science/rss",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://www.nature.com/nature.rss",
    "https://www.economist.com/latest/rss.xml",
    "https://feeds.npr.org/1001/rss.xml",
    "https://www.sciencedaily.com/rss/top.xml",
    "https://www.sciencedaily.com/rss/health_medicine.xml",
    "https://www.who.int/rss-feeds/news-english.xml",
    "https://news.un.org/feed/subscribe/en/news/all/rss.xml",
    "https://www.ft.com/world?format=rss",
    "https://feeds.bloomberg.com/markets/news.rss",
    "https://thehill.com/feed/",
    "https://www.pbs.org/newshour/feeds/rss/headlines",
    "https://feeds.washingtonpost.com/rss/world",
]

SOURCE_NAME_OVERRIDES = {
    "http://feeds.bbci.co.uk/news/technology/rss.xml":              "BBC News",
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml":  "NYT Technology",
    "https://www.theverge.com/rss/index.xml":                       "The Verge",
    "https://feeds.arstechnica.com/arstechnica/index":              "Ars Technica",
    "https://www.engadget.com/rss.xml":                             "Engadget",
    "https://venturebeat.com/feed/":                                "VentureBeat",
    "https://techcrunch.com/feed/":                                 "TechCrunch",
    "https://www.wired.com/feed/rss":                               "WIRED",
    "https://www.technologyreview.com/feed/":                       "MIT Technology Review",
    "https://www.zdnet.com/news/rss.xml":                           "ZDNet",
    "https://www.cnet.com/rss/news/":                               "CNET",
    "https://www.theguardian.com/uk/technology/rss":                "The Guardian Tech",
    "https://mashable.com/feeds/rss/tech":                          "Mashable Tech",
    "http://feeds.bbci.co.uk/news/world/rss.xml":                   "BBC World",
    "http://feeds.bbci.co.uk/news/business/rss.xml":                "BBC Business",
    "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml": "BBC Science",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml":       "NYT World",
    "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml":    "NYT Business",
    "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml":     "NYT Science",
    "https://www.theguardian.com/world/rss":                        "The Guardian World",
    "https://www.theguardian.com/uk/business/rss":                  "The Guardian Business",
    "https://www.theguardian.com/science/rss":                      "The Guardian Science",
    "https://www.aljazeera.com/xml/rss/all.xml":                    "Al Jazeera",
    "https://www.nature.com/nature.rss":                            "Nature",
    "https://www.economist.com/latest/rss.xml":                     "The Economist",
    "https://feeds.npr.org/1001/rss.xml":                           "NPR News",
    "https://www.sciencedaily.com/rss/top.xml":                     "ScienceDaily",
    "https://www.sciencedaily.com/rss/health_medicine.xml":         "ScienceDaily Health",
    "https://www.who.int/rss-feeds/news-english.xml":               "WHO News",
    "https://news.un.org/feed/subscribe/en/news/all/rss.xml":       "UN News",
    "https://www.ft.com/world?format=rss":                          "Financial Times World",
    "https://feeds.bloomberg.com/markets/news.rss":                 "Bloomberg Markets",
    "https://thehill.com/feed/":                                    "The Hill",
    "https://www.pbs.org/newshour/feeds/rss/headlines":             "PBS NewsHour",
    "https://feeds.washingtonpost.com/rss/world":                   "Washington Post World",
}


def fetch_rss_feed(url: str):
    response = httpx.get(url, timeout=30, follow_redirects=True)
    response.raise_for_status()
    return feedparser.parse(response.text)


def normalize_entry(entry: dict, feed_title: str, feed_url: str, run_id: str) -> dict:
    raw_id = entry.get("id", entry.get("link", entry.get("title", "")))
    entry_id = hashlib.md5(raw_id.encode()).hexdigest()

    published = entry.get("published_parsed") or entry.get("updated_parsed")
    if published:
        published_dt = datetime(*published[:6], tzinfo=timezone.utc)
    else:
        published_dt = datetime.now(timezone.utc)

    rss_image_url = None
    for media in entry.get("media_thumbnail", []):
        rss_image_url = media.get("url")
        break
    if not rss_image_url:
        for media in entry.get("media_content", []):
            url = media.get("url", "")
            if url and any(url.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")):
                rss_image_url = url
                break
    if not rss_image_url:
        for enc in entry.get("enclosures", []):
            if enc.get("type", "").startswith("image/"):
                rss_image_url = enc.get("href") or enc.get("url")
                break
    if not rss_image_url:
        for lnk in entry.get("links", []):
            if lnk.get("type", "").startswith("image/"):
                rss_image_url = lnk.get("href")
                break

    return {
        "entry_id":        entry_id,
        "title":           entry.get("title", ""),
        "link":            entry.get("link", ""),
        "summary":         entry.get("summary", ""),
        "published_at":    published_dt,
        "author":          entry.get("author", "unknown"),
        "tags":            ",".join(tag.get("term", "") for tag in entry.get("tags", [])),
        "feed_source":     SOURCE_NAME_OVERRIDES.get(feed_url, feed_title),
        "feed_url":        feed_url,
        "rss_image_url":   rss_image_url,
        "ingested_at":     datetime.now(timezone.utc),
        "pipeline_run_id": run_id,
    }


def main():
    con = duckdb.connect(DB_PATH)

    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    con.execute("""
        CREATE TABLE IF NOT EXISTS bronze.rss_raw (
            entry_id        VARCHAR PRIMARY KEY,
            title           VARCHAR,
            link            VARCHAR,
            summary         VARCHAR,
            published_at    TIMESTAMPTZ,
            author          VARCHAR,
            tags            VARCHAR,
            feed_source     VARCHAR,
            feed_url        VARCHAR,
            rss_image_url   VARCHAR,
            ingested_at     TIMESTAMPTZ,
            pipeline_run_id VARCHAR
        )
    """)
    print("Table bronze.rss_raw ready.")

    pipeline_run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    all_entries = []

    for url in RSS_FEEDS:
        try:
            feed = fetch_rss_feed(url)
            feed_title = feed.feed.get("title", "Unknown Feed")
            for entry in feed.entries:
                normalized = normalize_entry(entry, feed_title, url, pipeline_run_id)
                all_entries.append(normalized)
            print(f"  OK: {feed_title} — {len(feed.entries)} articles")
        except Exception as e:
            print(f"  ERROR: {url} — {e}")

    print(f"\nTotal fetched: {len(all_entries)} entries")

    if all_entries:
        rows = [
            (
                e["entry_id"], e["title"], e["link"], e["summary"],
                e["published_at"], e["author"], e["tags"],
                e["feed_source"], e["feed_url"], e["rss_image_url"],
                e["ingested_at"], e["pipeline_run_id"],
            )
            for e in all_entries
        ]
        con.executemany("""
            INSERT INTO bronze.rss_raw
                (entry_id, title, link, summary, published_at, author, tags,
                 feed_source, feed_url, rss_image_url, ingested_at, pipeline_run_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (entry_id) DO NOTHING
        """, rows)

    total_count = con.execute("SELECT COUNT(*) FROM bronze.rss_raw").fetchone()[0]
    today_count = con.execute(
        "SELECT COUNT(*) FROM bronze.rss_raw WHERE DATE(ingested_at) = current_date"
    ).fetchone()[0]

    print(f"Bronze table total rows : {total_count}")
    print(f"Ingested today          : {today_count}")
    print(f"Pipeline run ID         : {pipeline_run_id}")

    con.close()
    print(f"Bronze OK: {today_count} new entries ingested (run {pipeline_run_id})")


if __name__ == "__main__":
    main()
