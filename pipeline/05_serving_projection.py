# Serving Projection Layer
# Builds UI-ready serving tables from gold.news_articles for the web product.
# These tables are the ONLY data source the API layer should query — never Gold directly.
#
# Tables produced:
#   serve.article_cards     — flat, pageable, card-ready article objects
#   serve.category_feeds    — per-category feeds with ranking signals
#   serve.trending_topics   — topic-level aggregations for homepage trending section
#   serve.article_detail    — full enriched article objects for detail pages
#   serve.story_clusters    — KMeans story clusters
#   serve.entity_index      — entity → article mappings
#   serve.daily_briefing    — AI-generated daily news briefing
#   serve.hype_snapshots    — daily score snapshots by topic
#   serve.story_arcs        — narrative arcs grouped by subtopic
#   serve.compiled_stories  — AI-compiled multi-source articles
#   serve.story_claims      — per-story claim verification view
#
# Strategy: full refresh on every run (serve tables are small and fast to rebuild).

import hashlib
import json
import math
import os
import re
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

import duckdb
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", str(Path(__file__).parent.parent / "smartnews.duckdb"))
LOOKBACK_DAYS = 30


def cosine_dense(v1: list, v2: list) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    return dot / (n1 * n2) if n1 > 0 and n2 > 0 else 0.0


def main():
    con = duckdb.connect(DB_PATH)
    con.execute("CREATE SCHEMA IF NOT EXISTS serve")

    # ── Create serve tables (idempotent) ─────────────────────────────────────
    con.execute("""
        CREATE TABLE IF NOT EXISTS serve.article_cards (
            entry_id          VARCHAR PRIMARY KEY,
            title             VARCHAR,
            dehyped_title     VARCHAR,
            source_name       VARCHAR,
            published_at      TIMESTAMPTZ,
            publish_date      DATE,
            category          VARCHAR,
            subtopic          VARCHAR,
            summary_snippet   VARCHAR,
            link              VARCHAR,
            hype_score        DOUBLE,
            credibility_score DOUBLE,
            importance_score  DOUBLE,
            freshness_score   DOUBLE,
            word_count        INTEGER,
            read_time_min     INTEGER,
            language          VARCHAR,
            cluster_id        INTEGER,
            image_url         VARCHAR,
            updated_at        TIMESTAMPTZ
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS serve.category_feeds (
            entry_id          VARCHAR,
            category          VARCHAR,
            title             VARCHAR,
            source_name       VARCHAR,
            published_at      TIMESTAMPTZ,
            publish_date      DATE,
            summary_snippet   VARCHAR,
            link              VARCHAR,
            hype_score        DOUBLE,
            credibility_score DOUBLE,
            importance_score  DOUBLE,
            freshness_score   DOUBLE,
            subtopic          VARCHAR,
            language          VARCHAR,
            image_url         VARCHAR,
            updated_at        TIMESTAMPTZ,
            PRIMARY KEY (entry_id, category)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS serve.trending_topics (
            topic         VARCHAR PRIMARY KEY,
            category      VARCHAR,
            article_count BIGINT,
            avg_importance DOUBLE,
            avg_hype      DOUBLE,
            top_source    VARCHAR,
            latest_at     TIMESTAMPTZ,
            top_entry_ids VARCHAR,
            updated_at    TIMESTAMPTZ
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS serve.article_detail (
            entry_id          VARCHAR PRIMARY KEY,
            title             VARCHAR,
            dehyped_title     VARCHAR,
            source_name       VARCHAR,
            published_at      TIMESTAMPTZ,
            publish_date      DATE,
            category          VARCHAR,
            subtopic          VARCHAR,
            link              VARCHAR,
            ai_summary        VARCHAR,
            why_it_matters    VARCHAR,
            clean_summary     VARCHAR,
            entities          VARCHAR,
            tags              VARCHAR,
            author            VARCHAR,
            hype_score        DOUBLE,
            credibility_score DOUBLE,
            importance_score  DOUBLE,
            freshness_score   DOUBLE,
            word_count        INTEGER,
            read_time_min     INTEGER,
            language          VARCHAR,
            related_entry_ids VARCHAR,
            cluster_id        INTEGER,
            image_url         VARCHAR,
            updated_at        TIMESTAMPTZ
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS serve.story_clusters (
            cluster_id      INTEGER PRIMARY KEY,
            label           VARCHAR,
            article_count   INTEGER,
            top_entry_ids   VARCHAR,
            top_categories  VARCHAR,
            avg_importance  DOUBLE,
            avg_credibility DOUBLE,
            avg_hype        DOUBLE,
            updated_at      TIMESTAMPTZ
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS serve.entity_index (
            entity_name       VARCHAR,
            entity_type       VARCHAR,
            entry_id          VARCHAR,
            title             VARCHAR,
            source_name       VARCHAR,
            category          VARCHAR,
            published_at      TIMESTAMPTZ,
            hype_score        DOUBLE,
            credibility_score DOUBLE,
            importance_score  DOUBLE,
            updated_at        TIMESTAMPTZ,
            PRIMARY KEY (entity_name, entry_id)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS serve.daily_briefing (
            briefing_date DATE PRIMARY KEY,
            briefing_text VARCHAR,
            bullet_points VARCHAR,
            article_count INTEGER,
            top_entry_ids VARCHAR,
            generated_at  TIMESTAMPTZ
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS serve.hype_snapshots (
            topic          VARCHAR,
            category       VARCHAR,
            snapshot_date  DATE,
            article_count  INTEGER,
            avg_hype       DOUBLE,
            avg_credibility DOUBLE,
            avg_importance DOUBLE,
            updated_at     TIMESTAMPTZ,
            PRIMARY KEY (topic, snapshot_date)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS serve.story_arcs (
            arc_id         VARCHAR PRIMARY KEY,
            subtopic       VARCHAR,
            category       VARCHAR,
            article_count  INTEGER,
            first_seen     TIMESTAMPTZ,
            last_seen      TIMESTAMPTZ,
            span_days      INTEGER,
            entry_ids      VARCHAR,
            titles         VARCHAR,
            hype_start     DOUBLE,
            hype_end       DOUBLE,
            hype_trend     DOUBLE,
            avg_importance DOUBLE,
            avg_hype       DOUBLE,
            avg_credibility DOUBLE,
            latest_title   VARCHAR,
            updated_at     TIMESTAMPTZ
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS serve.compiled_stories (
            story_id          VARCHAR PRIMARY KEY,
            compiled_title    VARCHAR,
            compiled_summary  VARCHAR,
            compiled_body     VARCHAR,
            source_count      INTEGER,
            sources_used      VARCHAR,
            key_claims        VARCHAR,
            consensus_points  VARCHAR,
            divergence_points VARCHAR,
            entry_ids         VARCHAR,
            category          VARCHAR,
            first_published   TIMESTAMPTZ,
            last_published    TIMESTAMPTZ,
            compiled_at       TIMESTAMPTZ,
            updated_at        TIMESTAMPTZ
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS serve.story_claims (
            story_id           VARCHAR,
            claim_group_id     VARCHAR,
            claim_text         VARCHAR,
            claim_normalized   VARCHAR,
            verdict            VARCHAR,
            confidence         DOUBLE,
            confirm_count      INTEGER,
            dispute_count      INTEGER,
            sources_confirming VARCHAR,
            sources_disputing  VARCHAR,
            entry_ids          VARCHAR,
            updated_at         TIMESTAMPTZ,
            PRIMARY KEY (story_id, claim_group_id)
        )
    """)

    print("Serve tables ready.")

    # ── Load gold articles within the lookback window ─────────────────────────
    gold_rows = con.execute(f"""
        SELECT *
        FROM gold.news_articles
        WHERE publish_date >= current_date - INTERVAL '{LOOKBACK_DAYS} days'
          AND title IS NOT NULL
          AND title != ''
    """).fetchall()

    gold_count = len(gold_rows)
    print(f"Gold articles in lookback window ({LOOKBACK_DAYS} days): {gold_count}")

    if gold_count == 0:
        print("No Gold articles found. Exiting.")
        con.close()
        return

    # Register as a DuckDB view for SQL convenience
    con.execute(f"""
        CREATE OR REPLACE VIEW gold_window AS
        SELECT *
        FROM gold.news_articles
        WHERE publish_date >= current_date - INTERVAL '{LOOKBACK_DAYS} days'
          AND title IS NOT NULL
          AND title != ''
    """)

    updated_at = datetime.now(timezone.utc)

    # ── 1. serve.article_cards ────────────────────────────────────────────────
    # cluster_id placeholder — filled in after KMeans below
    cards_data = con.execute("""
        SELECT
            entry_id,
            title,
            COALESCE(dehyped_title, '')                                 AS dehyped_title,
            feed_source                                                  AS source_name,
            published_at,
            publish_date,
            category,
            COALESCE(subtopic, '')                                       AS subtopic,
            CASE
                WHEN LENGTH(COALESCE(clean_summary, '')) > 10
                    THEN SUBSTRING(COALESCE(clean_summary, ''), 1, 200)
                WHEN LENGTH(COALESCE(ai_summary, '')) > 10
                    THEN SUBSTRING(COALESCE(ai_summary, ''), 1, 200)
                ELSE ''
            END                                                          AS summary_snippet,
            link,
            COALESCE(hype_score, 0.5)                                   AS hype_score,
            COALESCE(credibility_score, 0.5)                            AS credibility_score,
            COALESCE(importance_score, 0.5)                             AS importance_score,
            COALESCE(freshness_score, 0.1)                              AS freshness_score,
            COALESCE(word_count, 0)                                     AS word_count,
            COALESCE(estimated_read_time_min, 1)                        AS read_time_min,
            COALESCE(language, 'en')                                    AS language,
            image_url,
            embedding
        FROM gold_window
    """).fetchall()

    # ── 2. Related articles (embedding cosine, fallback: category match) ──────
    emb_rows = [(r[0], r[-1]) for r in cards_data if r[-1] and r[-1] not in ("[]", "")]
    related_map: dict[str, str] = {}

    if len(emb_rows) >= 5:
        entry_ids_emb = [r[0] for r in emb_rows]
        vectors = [json.loads(r[1]) for r in emb_rows]

        for i, eid in enumerate(entry_ids_emb):
            sims = sorted(
                ((cosine_dense(vectors[i], vectors[j]), entry_ids_emb[j])
                 for j in range(len(entry_ids_emb)) if j != i),
                reverse=True,
            )
            related_map[eid] = ",".join(e for _, e in sims[:5])

        print(f"Embedding cosine similarity computed for {len(related_map)} articles")
    else:
        print(f"Fewer than 5 embeddings — using category-based related articles")
        # Group by category; for each article, pick up to 5 from same category
        cat_groups: dict[str, list[str]] = {}
        for r in cards_data:
            entry_id, cat = r[0], r[5]
            cat_groups.setdefault(cat or "General Tech", []).append(entry_id)

        for r in cards_data:
            entry_id, cat = r[0], r[5]
            peers = [e for e in cat_groups.get(cat or "General Tech", []) if e != entry_id]
            related_map[entry_id] = ",".join(peers[:5])

    # ── 3. KMeans clustering (sklearn) ────────────────────────────────────────
    cluster_map: dict[str, int] = {}

    try:
        from sklearn.cluster import KMeans
        from sklearn.feature_extraction.text import TfidfVectorizer

        texts = [
            " ".join(filter(None, [r[1], r[7], r[5]]))  # title + subtopic + category
            for r in cards_data
        ]
        entry_ids_all = [r[0] for r in cards_data]

        k = max(2, min(12, gold_count // 5))

        if len(emb_rows) >= k:
            # Use embeddings for clustering (higher quality)
            import numpy as np
            emb_entry_ids = [r[0] for r in emb_rows]
            emb_matrix = np.array([json.loads(r[1]) for r in emb_rows])
            km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(emb_matrix)
            for eid, cid in zip(emb_entry_ids, km.labels_):
                cluster_map[eid] = int(cid)
        else:
            # TF-IDF fallback
            vectorizer = TfidfVectorizer(max_features=4096, stop_words="english")
            tfidf_matrix = vectorizer.fit_transform(texts)
            km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(tfidf_matrix)
            for eid, cid in zip(entry_ids_all, km.labels_):
                cluster_map[eid] = int(cid)

        print(f"KMeans: k={k} clusters fitted on {gold_count} articles")

    except Exception as e:
        print(f"KMeans clustering failed ({e}) — assigning clusters by category hash")
        all_cats = sorted({r[5] or "General Tech" for r in cards_data})
        cat_to_id = {c: i for i, c in enumerate(all_cats)}
        for r in cards_data:
            cluster_map[r[0]] = cat_to_id.get(r[5] or "General Tech", 0)

    # ── 4. Build serve.story_clusters ─────────────────────────────────────────
    if cluster_map:
        entry_to_cat = {r[0]: (r[5] or "General Tech") for r in cards_data}
        entry_to_imp = {r[0]: (r[13] or 0.5) for r in cards_data}
        entry_to_cred = {r[0]: (r[12] or 0.5) for r in cards_data}
        entry_to_hype = {r[0]: (r[11] or 0.5) for r in cards_data}

        cluster_members: dict[int, list[str]] = {}
        for eid, cid in cluster_map.items():
            cluster_members.setdefault(cid, []).append(eid)

        cluster_rows = []
        for cid, members in cluster_members.items():
            cats = [entry_to_cat[e] for e in members]
            top_cat = Counter(cats).most_common(1)[0][0]
            top_eids = ",".join(members[:3])
            avg_imp = round(sum(entry_to_imp[e] for e in members) / len(members), 3)
            avg_cred = round(sum(entry_to_cred[e] for e in members) / len(members), 3)
            avg_hype = round(sum(entry_to_hype[e] for e in members) / len(members), 3)
            cluster_rows.append((
                cid, f"Cluster {cid + 1} - {top_cat}", len(members),
                top_eids, top_cat, avg_imp, avg_cred, avg_hype, updated_at,
            ))

        con.execute("DELETE FROM serve.story_clusters")
        con.executemany("""
            INSERT INTO serve.story_clusters
                (cluster_id, label, article_count, top_entry_ids, top_categories,
                 avg_importance, avg_credibility, avg_hype, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, cluster_rows)
        print(f"story_clusters written: {len(cluster_rows)} clusters")

    # ── 5. Write serve.article_cards ─────────────────────────────────────────
    con.execute("DELETE FROM serve.article_cards")
    card_rows = [
        (
            r[0],   # entry_id
            r[1],   # title
            r[2],   # dehyped_title
            r[3],   # source_name
            r[4],   # published_at
            r[5],   # publish_date
            r[6],   # category
            r[7],   # subtopic
            r[8],   # summary_snippet
            r[9],   # link
            r[10],  # hype_score
            r[11],  # credibility_score
            r[12],  # importance_score
            r[13],  # freshness_score
            r[14],  # word_count
            r[15],  # read_time_min
            r[16],  # language
            cluster_map.get(r[0], -1),
            r[17],  # image_url
            updated_at,
        )
        for r in cards_data
    ]
    con.executemany("""
        INSERT INTO serve.article_cards
            (entry_id, title, dehyped_title, source_name, published_at, publish_date,
             category, subtopic, summary_snippet, link,
             hype_score, credibility_score, importance_score, freshness_score,
             word_count, read_time_min, language, cluster_id, image_url, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (entry_id) DO UPDATE SET
            title             = excluded.title,
            dehyped_title     = excluded.dehyped_title,
            cluster_id        = excluded.cluster_id,
            freshness_score   = excluded.freshness_score,
            updated_at        = excluded.updated_at
    """, card_rows)
    print(f"article_cards written: {len(card_rows)} rows")

    # ── 6. serve.category_feeds ───────────────────────────────────────────────
    con.execute("DELETE FROM serve.category_feeds")
    con.execute(f"""
        INSERT INTO serve.category_feeds
        SELECT
            entry_id, category, title,
            feed_source AS source_name,
            published_at, publish_date,
            CASE
                WHEN LENGTH(COALESCE(clean_summary, '')) > 10
                    THEN SUBSTRING(COALESCE(clean_summary, ''), 1, 200)
                WHEN LENGTH(COALESCE(ai_summary, '')) > 10
                    THEN SUBSTRING(COALESCE(ai_summary, ''), 1, 200)
                ELSE ''
            END AS summary_snippet,
            link,
            COALESCE(hype_score, 0.5),
            COALESCE(credibility_score, 0.5),
            COALESCE(importance_score, 0.5),
            COALESCE(freshness_score, 0.1),
            COALESCE(subtopic, ''),
            COALESCE(language, 'en'),
            image_url,
            TIMESTAMPTZ '{updated_at.isoformat()}'
        FROM gold_window
        WHERE category IS NOT NULL
    """)
    feeds_count = con.execute("SELECT COUNT(*) FROM serve.category_feeds").fetchone()[0]
    print(f"category_feeds written: {feeds_count} rows")

    # ── 7. serve.trending_topics ──────────────────────────────────────────────
    con.execute("DELETE FROM serve.trending_topics")
    con.execute(f"""
        INSERT INTO serve.trending_topics
        SELECT
            topic,
            MODE(category) AS category,
            COUNT(entry_id) AS article_count,
            ROUND(AVG(COALESCE(importance_score, 0.5)), 3) AS avg_importance,
            ROUND(AVG(COALESCE(hype_score, 0.5)), 3) AS avg_hype,
            FIRST(feed_source) AS top_source,
            MAX(published_at) AS latest_at,
            STRING_AGG(entry_id, ',' ORDER BY importance_score DESC NULLS LAST)
                FILTER (WHERE entry_id IS NOT NULL) AS top_entry_ids,
            TIMESTAMPTZ '{updated_at.isoformat()}' AS updated_at
        FROM (
            SELECT
                entry_id,
                feed_source,
                published_at,
                importance_score,
                hype_score,
                category,
                COALESCE(NULLIF(subtopic, ''), category) AS topic
            FROM gold_window
            WHERE publish_date >= current_date - INTERVAL '7 days'
        ) t
        GROUP BY topic
        HAVING COUNT(entry_id) >= 1
        ORDER BY article_count DESC, avg_importance DESC, topic
        LIMIT 50
    """)
    topics_count = con.execute("SELECT COUNT(*) FROM serve.trending_topics").fetchone()[0]
    print(f"trending_topics written: {topics_count} topics")

    # ── 8. serve.hype_snapshots (upsert today's snapshot) ────────────────────
    con.execute(f"""
        INSERT INTO serve.hype_snapshots
        SELECT
            COALESCE(NULLIF(subtopic, ''), category) AS topic,
            category,
            current_date                             AS snapshot_date,
            COUNT(entry_id)                          AS article_count,
            ROUND(AVG(COALESCE(hype_score, 0.5)), 3)        AS avg_hype,
            ROUND(AVG(COALESCE(credibility_score, 0.5)), 3) AS avg_credibility,
            ROUND(AVG(COALESCE(importance_score, 0.5)), 3)  AS avg_importance,
            TIMESTAMPTZ '{updated_at.isoformat()}'   AS updated_at
        FROM gold_window
        WHERE publish_date >= current_date - INTERVAL '7 days'
        GROUP BY COALESCE(NULLIF(subtopic, ''), category), category
        ON CONFLICT (topic, snapshot_date) DO UPDATE SET
            article_count   = excluded.article_count,
            avg_hype        = excluded.avg_hype,
            avg_credibility = excluded.avg_credibility,
            avg_importance  = excluded.avg_importance,
            updated_at      = excluded.updated_at
    """)
    snapshots_count = con.execute("SELECT COUNT(*) FROM serve.hype_snapshots").fetchone()[0]
    print(f"hype_snapshots upserted: {snapshots_count} total rows")

    # ── 9. serve.article_detail ───────────────────────────────────────────────
    con.execute("DELETE FROM serve.article_detail")
    detail_rows = con.execute("""
        SELECT
            entry_id, title,
            COALESCE(dehyped_title, '')        AS dehyped_title,
            feed_source                        AS source_name,
            published_at, publish_date, category,
            COALESCE(subtopic, '')             AS subtopic,
            link,
            COALESCE(ai_summary, '')           AS ai_summary,
            COALESCE(why_it_matters, '')       AS why_it_matters,
            COALESCE(clean_summary, '')        AS clean_summary,
            COALESCE(entities, '[]')           AS entities,
            COALESCE(tags, '')                 AS tags,
            COALESCE(author, '')               AS author,
            COALESCE(hype_score, 0.5)          AS hype_score,
            COALESCE(credibility_score, 0.5)   AS credibility_score,
            COALESCE(importance_score, 0.5)    AS importance_score,
            COALESCE(freshness_score, 0.1)     AS freshness_score,
            COALESCE(word_count, 0)            AS word_count,
            COALESCE(estimated_read_time_min, 1) AS read_time_min,
            COALESCE(language, 'en')           AS language,
            image_url
        FROM gold_window
    """).fetchall()

    detail_insert = [
        (
            r[0],   # entry_id
            r[1],   # title
            r[2],   # dehyped_title
            r[3],   # source_name
            r[4],   # published_at
            r[5],   # publish_date
            r[6],   # category
            r[7],   # subtopic
            r[8],   # link
            r[9],   # ai_summary
            r[10],  # why_it_matters
            r[11],  # clean_summary
            r[12],  # entities
            r[13],  # tags
            r[14],  # author
            r[15],  # hype_score
            r[16],  # credibility_score
            r[17],  # importance_score
            r[18],  # freshness_score
            r[19],  # word_count
            r[20],  # read_time_min
            r[21],  # language
            related_map.get(r[0], ""),
            cluster_map.get(r[0], -1),
            r[22],  # image_url
            updated_at,
        )
        for r in detail_rows
    ]
    con.executemany("""
        INSERT INTO serve.article_detail
            (entry_id, title, dehyped_title, source_name, published_at, publish_date,
             category, subtopic, link, ai_summary, why_it_matters, clean_summary,
             entities, tags, author, hype_score, credibility_score, importance_score,
             freshness_score, word_count, read_time_min, language,
             related_entry_ids, cluster_id, image_url, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, detail_insert)
    print(f"article_detail written: {len(detail_insert)} rows")

    # ── 10. serve.entity_index ────────────────────────────────────────────────
    entity_rows_raw = con.execute("""
        SELECT
            entry_id, title, feed_source AS source_name, category,
            published_at,
            COALESCE(hype_score, 0.5)          AS hype_score,
            COALESCE(credibility_score, 0.5)   AS credibility_score,
            COALESCE(importance_score, 0.5)    AS importance_score,
            entities
        FROM gold_window
        WHERE entities IS NOT NULL AND entities NOT IN ('[]', '')
    """).fetchall()

    entity_insert = []
    for row in entity_rows_raw:
        entry_id, title, source_name, category, published_at, hype, cred, imp, entities_json = row
        try:
            entities = json.loads(entities_json)
        except Exception:
            continue
        for ent in entities:
            name = (ent.get("name") or "").strip()
            etype = (ent.get("type") or "").strip()
            if name:
                entity_insert.append((
                    name, etype, entry_id, title, source_name,
                    category, published_at, hype, cred, imp, updated_at,
                ))

    if entity_insert:
        con.execute("DELETE FROM serve.entity_index")
        con.executemany("""
            INSERT INTO serve.entity_index
                (entity_name, entity_type, entry_id, title, source_name,
                 category, published_at, hype_score, credibility_score,
                 importance_score, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (entity_name, entry_id) DO NOTHING
        """, entity_insert)

    distinct_entities = con.execute(
        "SELECT COUNT(DISTINCT entity_name) FROM serve.entity_index"
    ).fetchone()[0]
    print(f"entity_index written: {len(entity_insert)} mentions, {distinct_entities} distinct entities")

    # ── 11. serve.story_arcs ──────────────────────────────────────────────────
    import hashlib as _hashlib

    arc_base = con.execute("""
        SELECT
            subtopic,
            COUNT(*)                                              AS article_count,
            MODE(category)                                        AS category,
            MIN(published_at)                                     AS first_seen,
            MAX(published_at)                                     AS last_seen,
            DATEDIFF('day', MIN(published_at), MAX(published_at)) AS span_days,
            ROUND(AVG(hype_score), 3)                             AS avg_hype,
            ROUND(AVG(importance_score), 3)                       AS avg_importance,
            ROUND(AVG(credibility_score), 3)                      AS avg_credibility
        FROM gold_window
        WHERE subtopic IS NOT NULL AND subtopic != ''
          AND enriched_at IS NOT NULL
        GROUP BY subtopic
        HAVING COUNT(*) >= 2
    """).fetchall()

    arc_ordered = con.execute("""
        SELECT
            subtopic, entry_id, title, published_at, hype_score,
            ROW_NUMBER() OVER (PARTITION BY subtopic ORDER BY published_at ASC)  AS rn_asc,
            ROW_NUMBER() OVER (PARTITION BY subtopic ORDER BY published_at DESC) AS rn_desc
        FROM gold_window
        WHERE subtopic IS NOT NULL AND subtopic != ''
          AND enriched_at IS NOT NULL
    """).fetchall()

    # Build per-subtopic: first hype, last hype, last title, entry_ids, titles
    arc_first_hype: dict[str, float] = {}
    arc_last_hype: dict[str, float] = {}
    arc_last_title: dict[str, str] = {}
    arc_entry_ids: dict[str, list] = {}
    arc_titles_list: dict[str, list] = {}

    for row in arc_ordered:
        subtopic, entry_id, title, pub_at, hype, rn_asc, rn_desc = row
        if rn_asc == 1:
            arc_first_hype[subtopic] = hype or 0.0
        if rn_desc == 1:
            arc_last_hype[subtopic] = hype or 0.0
            arc_last_title[subtopic] = title or ""
        arc_entry_ids.setdefault(subtopic, []).append((pub_at, entry_id))
        arc_titles_list.setdefault(subtopic, []).append((pub_at, title or ""))

    arc_insert = []
    for row in arc_base:
        subtopic, article_count, category, first_seen, last_seen, span_days, avg_hype, avg_imp, avg_cred = row
        arc_id = _hashlib.md5(subtopic.encode()).hexdigest()
        eids_sorted = [e for _, e in sorted(arc_entry_ids.get(subtopic, []))]
        titles_sorted = [t for _, t in sorted(arc_titles_list.get(subtopic, []))]
        h_start = arc_first_hype.get(subtopic, 0.0)
        h_end = arc_last_hype.get(subtopic, 0.0)
        arc_insert.append((
            arc_id, subtopic, category or "", int(article_count),
            first_seen, last_seen, int(span_days or 0),
            json.dumps(eids_sorted), json.dumps(titles_sorted),
            round(h_start, 3), round(h_end, 3), round(h_end - h_start, 3),
            avg_imp or 0.0, avg_hype or 0.0, avg_cred or 0.0,
            arc_last_title.get(subtopic, ""), updated_at,
        ))

    con.execute("DELETE FROM serve.story_arcs")
    if arc_insert:
        con.executemany("""
            INSERT INTO serve.story_arcs
                (arc_id, subtopic, category, article_count, first_seen, last_seen, span_days,
                 entry_ids, titles, hype_start, hype_end, hype_trend,
                 avg_importance, avg_hype, avg_credibility, latest_title, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, arc_insert)
    print(f"story_arcs: {len(arc_insert)} narrative arcs written")

    # ── 12. serve.compiled_stories ───────────────────────────────────────────
    cnt_compiled = 0
    try:
        con.execute("DELETE FROM serve.compiled_stories")
        con.execute(f"""
            INSERT INTO serve.compiled_stories
            SELECT
                cs.story_id,
                cs.compiled_title,
                cs.compiled_summary,
                cs.compiled_body,
                cs.source_count,
                cs.sources_used,
                cs.key_claims,
                cs.consensus_points,
                cs.divergence_points,
                sm.entry_ids,
                sm.category,
                sm.first_published,
                sm.last_published,
                cs.compiled_at,
                TIMESTAMPTZ '{updated_at.isoformat()}' AS updated_at
            FROM gold.compiled_stories cs
            JOIN gold.story_matches sm ON cs.story_id = sm.story_id
            WHERE cs.compiled_title IS NOT NULL
        """)
        cnt_compiled = con.execute("SELECT COUNT(*) FROM serve.compiled_stories").fetchone()[0]
        print(f"compiled_stories: {cnt_compiled} compiled stories written")
    except Exception as e:
        print(f"compiled_stories: skipped ({e})")

    # ── 13. serve.daily_briefing (OpenAI) ────────────────────────────────────
    cnt_story_claims = 0
    try:
        claim_rows = con.execute("""
            SELECT
                story_id,
                entry_id,
                source_name,
                claim_text,
                claim_normalized,
                confidence
            FROM gold.article_claims
            WHERE story_id IS NOT NULL
              AND claim_text IS NOT NULL
              AND claim_text != ''
        """).fetchall()

        grouped_by_story: dict[str, list[tuple]] = {}
        for row in claim_rows:
            grouped_by_story.setdefault(row[0], []).append(row)

        out_rows = []
        for story_id, items in grouped_by_story.items():
            clusters: list[dict] = []
            for item in items:
                _, entry_id, source_name, claim_text, claim_norm, confidence = item
                if not claim_norm:
                    continue

                matched_cluster = None
                for cluster in clusters:
                    sim = SequenceMatcher(None, claim_norm, cluster["rep_norm"]).ratio()
                    if sim >= 0.9:
                        matched_cluster = cluster
                        break

                if matched_cluster is None:
                    matched_cluster = {"rep_text": claim_text, "rep_norm": claim_norm, "claims": []}
                    clusters.append(matched_cluster)

                matched_cluster["claims"].append(
                    {
                        "entry_id": entry_id,
                        "source_name": source_name or "",
                        "claim_text": claim_text,
                        "confidence": float(confidence or 0.5),
                    }
                )

            for cluster in clusters:
                claim_items = cluster["claims"]
                if not claim_items:
                    continue

                confirming_sources = sorted({c["source_name"] for c in claim_items if c["source_name"]})
                entry_ids = sorted({c["entry_id"] for c in claim_items if c["entry_id"]})
                confidence = round(
                    sum(c["confidence"] for c in claim_items) / max(1, len(claim_items)),
                    3,
                )

                numeric_variants = {
                    tuple(re.findall(r"\d+(?:\.\d+)?", c["claim_text"]))
                    for c in claim_items
                }
                has_numeric_conflict = len({v for v in numeric_variants if v}) > 1

                if has_numeric_conflict and len(confirming_sources) >= 2:
                    verdict = "DISPUTED"
                    sources_disputing = confirming_sources
                elif len(confirming_sources) >= 2:
                    verdict = "CONSENSUS"
                    sources_disputing = []
                else:
                    verdict = "SINGLE_SOURCE"
                    sources_disputing = []

                representative_text = max((c["claim_text"] for c in claim_items), key=len)[:280]
                group_id = hashlib.md5(
                    f"{story_id}|{cluster['rep_norm']}".encode("utf-8")
                ).hexdigest()

                out_rows.append(
                    (
                        story_id,
                        group_id,
                        representative_text,
                        cluster["rep_norm"][:280],
                        verdict,
                        confidence,
                        len(confirming_sources),
                        len(sources_disputing),
                        json.dumps(confirming_sources),
                        json.dumps(sources_disputing),
                        json.dumps(entry_ids),
                        updated_at,
                    )
                )

        con.execute("DELETE FROM serve.story_claims")
        if out_rows:
            con.executemany("""
                INSERT INTO serve.story_claims
                    (story_id, claim_group_id, claim_text, claim_normalized, verdict,
                     confidence, confirm_count, dispute_count, sources_confirming,
                     sources_disputing, entry_ids, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, out_rows)
        cnt_story_claims = len(out_rows)
        print(f"story_claims: {cnt_story_claims} grouped claims written")
    except Exception as e:
        print(f"story_claims: skipped ({e})")

    briefing_status = "skipped"
    openai_key = os.getenv("OPENAI_API_KEY")

    if openai_key:
        try:
            from openai import OpenAI
            oai_client = OpenAI()
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

            brief_articles = con.execute("""
                SELECT
                    entry_id, title,
                    COALESCE(ai_summary, clean_summary, '') AS summary,
                    feed_source AS source_name,
                    category,
                    COALESCE(importance_score, 0.5) AS importance_score,
                    COALESCE(hype_score, 0.5)       AS hype_score
                FROM gold_window
                WHERE publish_date >= current_date - INTERVAL '2 days'
                  AND (importance_score IS NULL OR importance_score > 0.4)
                  AND (hype_score IS NULL OR hype_score < 0.7)
                  AND title IS NOT NULL
                  AND (ai_summary IS NOT NULL OR clean_summary IS NOT NULL)
                ORDER BY importance_score DESC, hype_score ASC
                LIMIT 7
            """).fetchall()

            print(f"daily_briefing: {len(brief_articles)} candidate articles found")

            if brief_articles:
                top_ids = [r[0] for r in brief_articles]
                lines = []
                for r in brief_articles:
                    entry_id, title, summary, source_name, category, imp, hype = r
                    cat = f"[{category}] " if category else ""
                    src = f" ({source_name})" if source_name else ""
                    lines.append(f"- {cat}{title}{src}: {(summary or '')[:300]}")

                prompt = (
                    "You are a sharp, concise news analyst. Based on these top stories, "
                    "write a daily briefing of exactly 5 bullet points. Each bullet must:\n"
                    "- Start with a bold key phrase in markdown (e.g. **Topic:**)\n"
                    "- Be 1-2 sentences, factual and calm — no hype\n"
                    "- Cite the source in parentheses at the end\n\n"
                    f"Stories:\n{chr(10).join(lines)}\n\n"
                    "Return ONLY the 5 bullet points, no intro or outro."
                )

                resp = oai_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=600,
                    temperature=0.3,
                )
                briefing_text = resp.choices[0].message.content.strip()

                from datetime import date as _date
                today = _date.today()
                con.execute("""
                    INSERT INTO serve.daily_briefing
                        (briefing_date, briefing_text, bullet_points,
                         article_count, top_entry_ids, generated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT (briefing_date) DO UPDATE SET
                        briefing_text = excluded.briefing_text,
                        bullet_points = excluded.bullet_points,
                        article_count = excluded.article_count,
                        top_entry_ids = excluded.top_entry_ids,
                        generated_at  = excluded.generated_at
                """, [(today, briefing_text, briefing_text, len(brief_articles),
                       ",".join(top_ids), updated_at)])

                briefing_status = "ok"
                print(f"daily_briefing written: {len(brief_articles)} source articles")
            else:
                briefing_status = "no_articles"
                print("daily_briefing: no recent articles with summaries — skipped")
        except Exception as e:
            briefing_status = f"error:{str(e)[:80]}"
            print(f"daily_briefing: generation failed ({e}) — skipped")
    else:
        print("daily_briefing: OPENAI_API_KEY not set — skipped")

    # ── Final summary ─────────────────────────────────────────────────────────
    cnt_cards_final   = con.execute("SELECT COUNT(*) FROM serve.article_cards").fetchone()[0]
    cnt_feeds_final   = con.execute("SELECT COUNT(*) FROM serve.category_feeds").fetchone()[0]
    cnt_topics_final  = con.execute("SELECT COUNT(*) FROM serve.trending_topics").fetchone()[0]
    cnt_detail_final  = con.execute("SELECT COUNT(*) FROM serve.article_detail").fetchone()[0]
    cnt_clusts_final  = con.execute("SELECT COUNT(*) FROM serve.story_clusters").fetchone()[0]
    cnt_ent_rows      = con.execute("SELECT COUNT(*) FROM serve.entity_index").fetchone()[0]
    cnt_ent_uniq      = con.execute("SELECT COUNT(DISTINCT entity_name) FROM serve.entity_index").fetchone()[0]
    cnt_snaps_final   = con.execute("SELECT COUNT(*) FROM serve.hype_snapshots").fetchone()[0]
    cnt_arcs_final    = con.execute("SELECT COUNT(*) FROM serve.story_arcs").fetchone()[0]
    cnt_claims_final  = con.execute("SELECT COUNT(*) FROM serve.story_claims").fetchone()[0]
    cat_count         = con.execute("SELECT COUNT(DISTINCT category) FROM serve.category_feeds").fetchone()[0]

    print(f"\n=== Serving Layer Summary ===")
    print(f"article_cards    : {cnt_cards_final} rows")
    print(f"category_feeds   : {cnt_feeds_final} rows ({cat_count} categories)")
    print(f"trending_topics  : {cnt_topics_final} topics")
    print(f"article_detail   : {cnt_detail_final} rows")
    print(f"story_clusters   : {cnt_clusts_final} clusters")
    print(f"entity_index     : {cnt_ent_rows} mentions ({cnt_ent_uniq} distinct entities)")
    print(f"hype_snapshots   : {cnt_snaps_final} rows")
    print(f"story_arcs       : {cnt_arcs_final} narrative arcs")
    print(f"compiled_stories : {cnt_compiled} compiled stories")
    print(f"story_claims     : {cnt_claims_final} grouped claims")
    print(f"daily_briefing   : {briefing_status}")
    print(f"Lookback window  : {LOOKBACK_DAYS} days")

    con.close()
    print(
        f"Serving OK: {cnt_cards_final} cards, {cnt_topics_final} topics, "
        f"{cnt_clusts_final} clusters, {cnt_ent_uniq} entities, "
        f"{cat_count} categories, arcs={cnt_arcs_final}, compiled={cnt_compiled}, "
        f"claims={cnt_claims_final}, "
        f"briefing={briefing_status}"
    )


if __name__ == "__main__":
    main()
