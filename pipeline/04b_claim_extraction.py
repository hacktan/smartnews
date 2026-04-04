"""
Gold Layer - Claim Extraction
Extracts atomic factual claims from article full text for matched multi-source stories.

Reads:
  - gold.story_matches
  - gold.news_articles

Writes:
  - gold.article_claims
  - gold.news_articles.claims_extracted / claims_extracted_at

Run after:
  03b_story_matching.py
"""

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DB_PATH = os.getenv("DB_PATH", str(Path(__file__).parent.parent / "smartnews.duckdb"))
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
CLAIM_BATCH_LIMIT = int(os.getenv("CLAIM_BATCH_LIMIT", "40"))
RATE_LIMIT_SLEEP = 0.25

SYSTEM_PROMPT = """You extract verifiable factual claims from a news article.
Return JSON only, with this schema:
{
  "claims": [
    {
      "claim": "atomic factual statement",
      "type": "STATISTIC|QUOTE|EVENT|DATE|ATTRIBUTION|OTHER",
      "confidence": 0.0
    }
  ]
}

Rules:
- Extract 3 to 10 claims when possible.
- Claims must be specific and verifiable.
- No opinions, speculation, or rhetorical language.
- Keep each claim under 220 characters.
- confidence must be between 0.0 and 1.0.
- Return only JSON, no markdown."""


def clamp_confidence(value: object) -> float:
    try:
        num = float(value)
    except Exception:
        return 0.5
    return round(max(0.0, min(1.0, num)), 3)


def normalize_claim(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"\s+", " ", lowered).strip()
    lowered = re.sub(r"[^\w\s]", "", lowered)
    return lowered[:280]


def ensure_claim_columns(con: duckdb.DuckDBPyConnection) -> None:
    existing = {
        row[0]
        for row in con.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'gold'
              AND table_name = 'news_articles'
            """
        ).fetchall()
    }

    if "claims_extracted" not in existing:
        con.execute("ALTER TABLE gold.news_articles ADD COLUMN claims_extracted BOOLEAN")
    if "claims_extracted_at" not in existing:
        con.execute("ALTER TABLE gold.news_articles ADD COLUMN claims_extracted_at TIMESTAMPTZ")


def ensure_claim_table(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("CREATE SCHEMA IF NOT EXISTS gold")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS gold.article_claims (
            claim_id          VARCHAR PRIMARY KEY,
            story_id          VARCHAR,
            entry_id          VARCHAR,
            source_name       VARCHAR,
            claim_idx         INTEGER,
            claim_text        VARCHAR,
            claim_normalized  VARCHAR,
            claim_type        VARCHAR,
            confidence        DOUBLE,
            extracted_at      TIMESTAMPTZ,
            model_used        VARCHAR
        )
        """
    )


def fetch_story_members(con: duckdb.DuckDBPyConnection) -> list[tuple[str, str]]:
    story_rows = con.execute(
        """
        SELECT story_id, entry_ids
        FROM gold.story_matches
        WHERE source_count >= 2
        """
    ).fetchall()

    members: list[tuple[str, str]] = []
    for story_id, entry_ids_raw in story_rows:
        try:
            entry_ids = json.loads(entry_ids_raw or "[]")
        except Exception:
            continue
        for entry_id in entry_ids:
            if entry_id:
                members.append((str(entry_id), str(story_id)))
    return members


def extract_claims(
    client: OpenAI,
    *,
    title: str,
    category: str,
    source_name: str,
    full_text: str,
) -> list[dict]:
    text = (full_text or "")[:5000]
    user_content = (
        f"Category: {category or ''}\n"
        f"Source: {source_name or ''}\n"
        f"Title: {title or ''}\n\n"
        f"Article text:\n{text}"
    )

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.0,
        max_tokens=700,
        response_format={"type": "json_object"},
    )

    payload = json.loads(response.choices[0].message.content or "{}")
    raw_claims = payload.get("claims", [])
    if not isinstance(raw_claims, list):
        return []

    cleaned: list[dict] = []
    seen: set[str] = set()
    for item in raw_claims:
        if not isinstance(item, dict):
            continue
        claim_text = str(item.get("claim", "")).strip()
        if len(claim_text) < 15:
            continue
        normalized = normalize_claim(claim_text)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        claim_type = str(item.get("type", "OTHER")).upper().strip()
        if claim_type not in {"STATISTIC", "QUOTE", "EVENT", "DATE", "ATTRIBUTION", "OTHER"}:
            claim_type = "OTHER"
        cleaned.append(
            {
                "claim_text": claim_text[:280],
                "claim_normalized": normalized,
                "claim_type": claim_type,
                "confidence": clamp_confidence(item.get("confidence")),
            }
        )
        if len(cleaned) >= 12:
            break
    return cleaned


def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY must be set for claim extraction.")

    con = duckdb.connect(DB_PATH)
    ensure_claim_columns(con)
    ensure_claim_table(con)

    story_members = fetch_story_members(con)
    if not story_members:
        print("No story members found in gold.story_matches. Skipping.")
        con.close()
        return

    con.execute("DROP TABLE IF EXISTS temp_story_members")
    con.execute("CREATE TEMP TABLE temp_story_members (entry_id VARCHAR, story_id VARCHAR)")
    con.executemany("INSERT INTO temp_story_members VALUES (?, ?)", story_members)

    pending = con.execute(
        f"""
        SELECT
            g.entry_id,
            t.story_id,
            g.title,
            g.full_text,
            g.feed_source,
            g.category
        FROM gold.news_articles g
        JOIN temp_story_members t ON t.entry_id = g.entry_id
        WHERE COALESCE(LENGTH(g.full_text), 0) >= 300
          AND COALESCE(g.claims_extracted, FALSE) = FALSE
        ORDER BY g.published_at DESC
        LIMIT {CLAIM_BATCH_LIMIT}
        """
    ).fetchall()

    print(f"Claim extraction pending: {len(pending)}")
    if not pending:
        con.close()
        return

    client = OpenAI()
    now = datetime.now(timezone.utc)

    inserted_rows: list[tuple] = []
    processed_entry_ids: list[str] = []
    failed_entry_ids: list[str] = []

    for idx, row in enumerate(pending, start=1):
        entry_id, story_id, title, full_text, source_name, category = row
        try:
            claims = extract_claims(
                client,
                title=title or "",
                category=category or "",
                source_name=source_name or "",
                full_text=full_text or "",
            )

            con.execute("DELETE FROM gold.article_claims WHERE entry_id = ?", [entry_id])
            for claim_idx, claim in enumerate(claims, start=1):
                claim_id = hashlib.md5(
                    f"{entry_id}|{claim_idx}|{claim['claim_normalized']}".encode("utf-8")
                ).hexdigest()
                inserted_rows.append(
                    (
                        claim_id,
                        story_id,
                        entry_id,
                        source_name or "",
                        claim_idx,
                        claim["claim_text"],
                        claim["claim_normalized"],
                        claim["claim_type"],
                        claim["confidence"],
                        now,
                        OPENAI_MODEL,
                    )
                )

            processed_entry_ids.append(entry_id)
            print(f"  [{idx}/{len(pending)}] {entry_id[:10]}... claims={len(claims)}")
        except Exception as err:
            failed_entry_ids.append(entry_id)
            print(f"  [{idx}/{len(pending)}] ERROR {entry_id[:10]}... {err}")
        time.sleep(RATE_LIMIT_SLEEP)

    if inserted_rows:
        con.executemany(
            """
            INSERT INTO gold.article_claims
                (claim_id, story_id, entry_id, source_name, claim_idx, claim_text,
                 claim_normalized, claim_type, confidence, extracted_at, model_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (claim_id) DO UPDATE SET
                story_id         = excluded.story_id,
                source_name      = excluded.source_name,
                claim_text       = excluded.claim_text,
                claim_normalized = excluded.claim_normalized,
                claim_type       = excluded.claim_type,
                confidence       = excluded.confidence,
                extracted_at     = excluded.extracted_at,
                model_used       = excluded.model_used
            """,
            inserted_rows,
        )

    if processed_entry_ids:
        placeholders = ",".join("?" for _ in processed_entry_ids)
        con.execute(
            f"""
            UPDATE gold.news_articles
            SET
                claims_extracted = TRUE,
                claims_extracted_at = ?
            WHERE entry_id IN ({placeholders})
            """,
            [now, *processed_entry_ids],
        )

    total_claims = con.execute("SELECT COUNT(*) FROM gold.article_claims").fetchone()[0]
    print("\n=== Claim Extraction Summary ===")
    print(f"Processed articles : {len(processed_entry_ids)}")
    print(f"Failed articles    : {len(failed_entry_ids)}")
    print(f"Claims upserted    : {len(inserted_rows)}")
    print(f"Claims total       : {total_claims}")

    con.close()


if __name__ == "__main__":
    main()
