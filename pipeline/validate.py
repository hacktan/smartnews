# Pipeline Validation
# Checks that all pipeline stages produced expected data.
# Exits with code 1 if any critical check fails â€” used by GitHub Actions.
#
# Usage: uv run python pipeline/validate.py

import os
import sys
from pathlib import Path

import duckdb
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", str(Path(__file__).parent.parent / "smartnews.duckdb"))

# â”€â”€ Thresholds â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
MIN_BRONZE_ROWS = 10        # at least 10 articles ingested
MIN_SILVER_ROWS = 5         # at least 5 cleaned articles
MIN_GOLD_ROWS = 5           # at least 5 gold articles
MIN_SERVE_CARDS = 5         # at least 5 article cards
MIN_ENRICHED_FRACTION = 0.0 # enrichment is optional (might be 0 on first run)

WARNINGS: list[str] = []
ERRORS: list[str] = []


def check(label: str, actual: int | float, minimum: int | float, critical: bool = True) -> bool:
    ok = actual >= minimum
    symbol = " OK " if ok else ("FAIL" if critical else "WARN")
    print(f"  {symbol}  {label}: {actual} (min {minimum})")
    if not ok:
        if critical:
            ERRORS.append(f"{label}: got {actual}, need >= {minimum}")
        else:
            WARNINGS.append(f"{label}: got {actual}, need >= {minimum}")
    return ok


def main() -> int:
    print(f"\n=== SmartNews Pipeline Validation ===")
    print(f"DB: {DB_PATH}\n")

    if not Path(DB_PATH).exists():
        print(f"[FAIL] CRITICAL: Database file not found: {DB_PATH}")
        return 1

    try:
        con = duckdb.connect(DB_PATH, read_only=True)
    except Exception as e:
        print(f"[FAIL] CRITICAL: Cannot open database: {e}")
        return 1

    # â”€â”€ Bronze â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("[ Bronze ]")
    try:
        bronze_total = con.execute("SELECT COUNT(*) FROM bronze.rss_raw").fetchone()[0]
        check("bronze.rss_raw total rows", bronze_total, MIN_BRONZE_ROWS)

        bronze_today = con.execute(
            "SELECT COUNT(*) FROM bronze.rss_raw WHERE DATE(ingested_at) = current_date"
        ).fetchone()[0]
        check("bronze.rss_raw ingested today", bronze_today, 0, critical=False)

        ft_total = con.execute("SELECT COUNT(*) FROM bronze.article_fulltext").fetchone()[0]
        ft_ok = con.execute(
            "SELECT COUNT(*) FROM bronze.article_fulltext WHERE extraction_ok = TRUE"
        ).fetchone()[0]
        check("bronze.article_fulltext total", ft_total, 0, critical=False)
        check("bronze.article_fulltext successes", ft_ok, 0, critical=False)
    except Exception as e:
        ERRORS.append(f"Bronze check failed: {e}")
        print(f"  âœ- Bronze check failed: {e}")

    # â”€â”€ Silver â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[ Silver ]")
    try:
        silver_total = con.execute("SELECT COUNT(*) FROM silver.rss_cleaned").fetchone()[0]
        check("silver.rss_cleaned total rows", silver_total, MIN_SILVER_ROWS)

        silver_cats = con.execute(
            "SELECT COUNT(DISTINCT category) FROM silver.rss_cleaned"
        ).fetchone()[0]
        check("silver distinct categories", silver_cats, 1, critical=False)
    except Exception as e:
        ERRORS.append(f"Silver check failed: {e}")
        print(f"  âœ- Silver check failed: {e}")

    # â”€â”€ Gold â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[ Gold ]")
    try:
        gold_total = con.execute("SELECT COUNT(*) FROM gold.news_articles").fetchone()[0]
        check("gold.news_articles total rows", gold_total, MIN_GOLD_ROWS)

        gold_enriched = con.execute(
            "SELECT COUNT(*) FROM gold.news_articles WHERE enriched_at IS NOT NULL"
        ).fetchone()[0]
        enrich_frac = gold_enriched / gold_total if gold_total > 0 else 0
        check("gold enriched fraction", enrich_frac, MIN_ENRICHED_FRACTION, critical=False)
        print(f"     â†’ {gold_enriched}/{gold_total} articles enriched ({enrich_frac:.1%})")

        gold_with_emb = con.execute(
            "SELECT COUNT(*) FROM gold.news_articles WHERE embedding IS NOT NULL"
        ).fetchone()[0]
        check("gold with embeddings", gold_with_emb, 0, critical=False)

        gold_with_ft = con.execute(
            "SELECT COUNT(*) FROM gold.news_articles WHERE has_full_text = TRUE"
        ).fetchone()[0]
        check("gold with full text", gold_with_ft, 0, critical=False)

        story_matches = 0
        try:
            story_matches = con.execute("SELECT COUNT(*) FROM gold.story_matches").fetchone()[0]
        except Exception:
            pass
        check("gold.story_matches", story_matches, 0, critical=False)

        article_claims = 0
        try:
            article_claims = con.execute("SELECT COUNT(*) FROM gold.article_claims").fetchone()[0]
        except Exception:
            pass
        check("gold.article_claims", article_claims, 0, critical=False)
    except Exception as e:
        ERRORS.append(f"Gold check failed: {e}")
        print(f"  âœ- Gold check failed: {e}")

    # â”€â”€ Serve â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[ Serve ]")
    try:
        cards = con.execute("SELECT COUNT(*) FROM serve.article_cards").fetchone()[0]
        check("serve.article_cards", cards, MIN_SERVE_CARDS)

        feeds = con.execute("SELECT COUNT(*) FROM serve.category_feeds").fetchone()[0]
        check("serve.category_feeds", feeds, MIN_SERVE_CARDS)

        topics = con.execute("SELECT COUNT(*) FROM serve.trending_topics").fetchone()[0]
        check("serve.trending_topics", topics, 1, critical=False)

        detail = con.execute("SELECT COUNT(*) FROM serve.article_detail").fetchone()[0]
        check("serve.article_detail", detail, MIN_SERVE_CARDS)

        clusters = con.execute("SELECT COUNT(*) FROM serve.story_clusters").fetchone()[0]
        check("serve.story_clusters", clusters, 1, critical=False)

        entity_rows = con.execute("SELECT COUNT(*) FROM serve.entity_index").fetchone()[0]
        entity_uniq = con.execute(
            "SELECT COUNT(DISTINCT entity_name) FROM serve.entity_index"
        ).fetchone()[0]
        check("serve.entity_index distinct entities", entity_uniq, 0, critical=False)
        print(f"     â†’ {entity_rows} mentions, {entity_uniq} distinct entities")

        arcs = con.execute("SELECT COUNT(*) FROM serve.story_arcs").fetchone()[0]
        check("serve.story_arcs", arcs, 0, critical=False)

        story_claims = 0
        try:
            story_claims = con.execute("SELECT COUNT(*) FROM serve.story_claims").fetchone()[0]
        except Exception:
            pass
        check("serve.story_claims", story_claims, 0, critical=False)

        briefing = con.execute("SELECT COUNT(*) FROM serve.daily_briefing").fetchone()[0]
        check("serve.daily_briefing", briefing, 0, critical=False)
    except Exception as e:
        ERRORS.append(f"Serve check failed: {e}")
        print(f"  âœ- Serve check failed: {e}")

    # â”€â”€ Score sanity â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[ Score Sanity ]")
    try:
        score_check = con.execute("""
            SELECT
                ROUND(AVG(hype_score), 3)        AS avg_hype,
                ROUND(AVG(credibility_score), 3) AS avg_credibility,
                ROUND(AVG(importance_score), 3)  AS avg_importance,
                MIN(hype_score)                  AS min_hype,
                MAX(hype_score)                  AS max_hype
            FROM gold.news_articles
            WHERE enriched_at IS NOT NULL
        """).fetchone()

        if score_check and score_check[0] is not None:
            avg_hype, avg_cred, avg_imp, min_hype, max_hype = score_check
            print(f"  âœ“  Avg hype={avg_hype}, credibility={avg_cred}, importance={avg_imp}")
            print(f"     hype range: [{min_hype}, {max_hype}]")

            # Scores must be in [0, 1]
            if min_hype is not None and (min_hype < 0 or max_hype > 1):
                ERRORS.append(f"hype_score out of [0,1] range: [{min_hype}, {max_hype}]")
                print(f"  âœ-  hype_score out of range!")
        else:
            print("  âš   No enriched articles yet â€” score sanity skipped")
    except Exception as e:
        WARNINGS.append(f"Score sanity check failed: {e}")
        print(f"  âš   Score sanity check failed: {e}")

    con.close()

    # â”€â”€ Summary â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n" + "â”€" * 50)
    if WARNINGS:
        print(f"[WARN] {len(WARNINGS)} warning(s):")
        for w in WARNINGS:
            print(f"   - {w}")

    if ERRORS:
        print(f"\n[FAIL] VALIDATION FAILED - {len(ERRORS)} error(s):")
        for e in ERRORS:
            print(f"   - {e}")
        print("-" * 50)
        return 1

    suffix = f" ({len(WARNINGS)} warnings)" if WARNINGS else ""
    print(f"[OK] All critical checks passed.{suffix}")
    print("-" * 50)
    return 0


if __name__ == "__main__":
    sys.exit(main())


