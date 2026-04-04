# Gold Layer — Cross-Source Story Matching
# Identifies when multiple articles from different sources cover the same story.
# Uses a 3-tier matching algorithm: title similarity + embedding cosine + entity overlap.
# Runs after 03_gold_aggregation and before 04_ai_enrichment.

import hashlib
import json
import math
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import duckdb
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", str(Path(__file__).parent.parent / "smartnews.duckdb"))

WINDOW_DAYS = int(os.getenv("STORY_MATCH_WINDOW_DAYS", "14"))
MAX_TIME_DIFF_HOURS = int(os.getenv("STORY_MATCH_MAX_TIME_DIFF_HOURS", "96"))
TITLE_JACCARD_THRESHOLD = float(os.getenv("STORY_MATCH_TITLE_JACCARD", "0.24"))
EMBEDDING_COSINE_THRESHOLD = float(os.getenv("STORY_MATCH_EMBEDDING_COSINE", "0.72"))
ENTITY_OVERLAP_THRESHOLD = float(os.getenv("STORY_MATCH_ENTITY_OVERLAP", "0.30"))
MIN_TIERS_AGREE = int(os.getenv("STORY_MATCH_MIN_TIERS", "1"))
MIN_ARTICLES_PER_GROUP = int(os.getenv("STORY_MATCH_MIN_ARTICLES_PER_GROUP", "2"))

STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for",
    "of", "and", "or", "but", "with", "by", "from", "as", "it", "its", "this",
    "that", "has", "have", "had", "be", "been", "will", "would", "can", "could",
    "not", "no", "do", "does", "did", "how", "what", "when", "where", "who", "why",
    "new", "says", "said", "report", "reports", "according",
}


def normalize_title(title: str) -> set:
    if not title:
        return set()
    words = re.sub(r"[^\w\s]", "", title.lower()).split()
    return {w for w in words if w not in STOP_WORDS and len(w) > 2}


def jaccard_similarity(set_a: set, set_b: set) -> float:
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def cosine_similarity(vec_a: list, vec_b: list) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def entity_overlap(ent_a: list, ent_b: list) -> float:
    if not ent_a or not ent_b:
        return 0.0
    names_a = {e.get("name", "").lower() for e in ent_a if e.get("name")}
    names_b = {e.get("name", "").lower() for e in ent_b if e.get("name")}
    if not names_a or not names_b:
        return 0.0
    return len(names_a & names_b) / min(len(names_a), len(names_b))


def main():
    con = duckdb.connect(DB_PATH)

    con.execute("CREATE SCHEMA IF NOT EXISTS gold")
    con.execute("""
        CREATE TABLE IF NOT EXISTS gold.story_matches (
            story_id        VARCHAR PRIMARY KEY,
            entry_ids       VARCHAR,
            source_count    INTEGER,
            sources         VARCHAR,
            canonical_title VARCHAR,
            match_method    VARCHAR,
            match_score     DOUBLE,
            first_published TIMESTAMPTZ,
            last_published  TIMESTAMPTZ,
            category        VARCHAR,
            matched_at      TIMESTAMPTZ
        )
    """)
    print("Table gold.story_matches ready.")

    rows = con.execute(f"""
        SELECT entry_id, title, feed_source, category, published_at,
               embedding, entities, credibility_score, clean_summary
        FROM gold.news_articles
        WHERE published_at >= current_date - INTERVAL '{WINDOW_DAYS} days'
          AND title IS NOT NULL
          AND TRIM(title) != ''
          AND (
                COALESCE(LENGTH(clean_summary), 0) >= 80
                OR COALESCE(LENGTH(full_text), 0) >= 300
              )
        ORDER BY published_at DESC
    """).fetchall()

    print(f"Articles in {WINDOW_DAYS}-day window: {len(rows)}")

    if len(rows) < 2:
        print("Not enough articles for story matching.")
        con.close()
        return

    article_data = []
    for row in rows:
        entry_id, title, feed_source, category, published_at, embedding_json, entities_json, credibility_score, clean_summary = row

        embedding = None
        if embedding_json:
            try:
                embedding = json.loads(embedding_json)
            except Exception:
                pass

        entities = []
        if entities_json:
            try:
                entities = json.loads(entities_json)
            except Exception:
                pass

        article_data.append({
            "entry_id":          entry_id,
            "title":             title,
            "title_words":       normalize_title(title),
            "feed_source":       feed_source,
            "category":          category,
            "published_at":      published_at,
            "embedding":         embedding,
            "entities":          entities,
            "summary":           clean_summary or "",
            "credibility_score": credibility_score or 0.5,
        })

    print(f"Prepared {len(article_data)} articles for matching.")

    matches = []
    max_time_diff_seconds = MAX_TIME_DIFF_HOURS * 3600

    for i in range(len(article_data)):
        for j in range(i + 1, len(article_data)):
            a = article_data[i]
            b = article_data[j]

            if a["feed_source"] == b["feed_source"]:
                continue

            if a["published_at"] and b["published_at"]:
                time_diff = abs((a["published_at"] - b["published_at"]).total_seconds())
                if time_diff > max_time_diff_seconds:
                    # Rows are sorted by published_at DESC, so newer-vs-much-older can break early.
                    if b["published_at"] <= a["published_at"]:
                        break
                    continue

            tiers_matched = 0
            methods = []
            scores = []

            title_sim = jaccard_similarity(a["title_words"], b["title_words"])
            if title_sim >= TITLE_JACCARD_THRESHOLD:
                tiers_matched += 1
                methods.append("title")
                scores.append(title_sim)

            emb_sim = 0.0
            if a["embedding"] and b["embedding"]:
                emb_sim = cosine_similarity(a["embedding"], b["embedding"])
                if emb_sim >= EMBEDDING_COSINE_THRESHOLD:
                    tiers_matched += 1
                    methods.append("embedding")
                    scores.append(emb_sim)

            ent_sim = 0.0
            if a["entities"] and b["entities"]:
                ent_sim = entity_overlap(a["entities"], b["entities"])
                if ent_sim >= ENTITY_OVERLAP_THRESHOLD:
                    tiers_matched += 1
                    methods.append("entity")
                    scores.append(ent_sim)

            strong_signal = (
                title_sim >= 0.50
                or emb_sim >= 0.82
                or ent_sim >= 0.60
                or (title_sim >= 0.28 and (emb_sim >= 0.72 or ent_sim >= 0.35))
                or title_sim >= 0.62
            )

            if a.get("category") and b.get("category") and a["category"] != b["category"]:
                # Cross-category links are noisier; require a stronger lexical or semantic signal.
                strong_signal = strong_signal and (title_sim >= 0.60 or emb_sim >= 0.82)

            if tiers_matched >= MIN_TIERS_AGREE and strong_signal:
                avg_score = sum(scores) / len(scores)
                matches.append((i, j, avg_score, "+".join(methods)))

    print(f"Pairwise matches found: {len(matches)}")

    # Union-Find to group transitively connected articles
    parent = list(range(len(article_data)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for i, j, score, method in matches:
        union(i, j)

    groups: dict = defaultdict(list)
    for idx in range(len(article_data)):
        groups[find(idx)].append(idx)

    story_groups = []
    for root, member_indices in groups.items():
        if len(member_indices) < MIN_ARTICLES_PER_GROUP:
            continue
        members = [article_data[i] for i in member_indices]
        sources = set(m["feed_source"] for m in members)
        if len(sources) < 2:
            continue
        story_groups.append((member_indices, members, sources))

    print(f"Story groups formed: {len(story_groups)}")

    new_stories = []
    for member_indices, members, sources in story_groups:
        entry_ids = sorted([m["entry_id"] for m in members])
        story_id = hashlib.md5("|".join(entry_ids).encode()).hexdigest()

        best_member = max(members, key=lambda m: m["credibility_score"])

        group_methods: set = set()
        group_scores = []
        for i, j, score, method in matches:
            if find(i) == find(member_indices[0]):
                group_methods.update(method.split("+"))
                group_scores.append(score)

        timestamps = [m["published_at"] for m in members if m["published_at"]]

        new_stories.append((
            story_id,
            json.dumps(entry_ids),
            len(sources),
            json.dumps(sorted(sources)),
            best_member["title"] or "",
            "+".join(sorted(group_methods)) if group_methods else "hybrid",
            round(sum(group_scores) / max(len(group_scores), 1), 3),
            min(timestamps) if timestamps else None,
            max(timestamps) if timestamps else None,
            best_member["category"] or "",
            datetime.now(timezone.utc),
        ))

    if new_stories:
        # Full overwrite — story groups are recomputed from the current window
        con.execute("DELETE FROM gold.story_matches")
        con.executemany("""
            INSERT INTO gold.story_matches
                (story_id, entry_ids, source_count, sources, canonical_title,
                 match_method, match_score, first_published, last_published,
                 category, matched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, new_stories)
        print(f"Story matches written: {len(new_stories)}")
    else:
        print("No cross-source story matches found.")

    total_stories = con.execute("SELECT COUNT(*) FROM gold.story_matches").fetchone()[0]
    multi_source = con.execute(
        "SELECT COUNT(*) FROM gold.story_matches WHERE source_count >= 3"
    ).fetchone()[0]

    print(f"\n=== Story Matching Summary ===")
    print(f"Total story groups  : {total_stories}")
    print(f"3+ source stories   : {multi_source}")
    print(f"Articles in window  : {len(article_data)}")
    print(f"Pairwise matches    : {len(matches)}")

    con.close()
    print(f"Story Matching OK: {total_stories} stories ({multi_source} with 3+ sources)")


if __name__ == "__main__":
    main()
