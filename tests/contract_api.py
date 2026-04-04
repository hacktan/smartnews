"""
SmartNews API Contract Checks
============================
Validates response shape/key contracts for critical endpoints.

Usage:
  python tests/contract_api.py [base_url]

Exit codes:
  0 = pass
  1 = fail
"""
from __future__ import annotations

import json
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
TIMEOUT = 30
RETRIES = 3

failures: list[str] = []


def fetch(path: str, params: dict | None = None):
    url = BASE_URL + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    last_error: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                body = resp.read().decode("utf-8")
                return resp.status, json.loads(body)
        except (urllib.error.URLError, TimeoutError, socket.timeout) as err:
            last_error = err
            if attempt < RETRIES:
                time.sleep(2 * attempt)
                continue
            raise
        except Exception as err:
            last_error = err
            if attempt < RETRIES:
                time.sleep(2 * attempt)
                continue
            raise
    raise RuntimeError(f"fetch failed after retries: {last_error}")


def expect(condition: bool, message: str):
    if not condition:
        failures.append(message)


def has_keys(obj: dict, keys: list[str], endpoint: str):
    for key in keys:
        expect(key in obj, f"{endpoint}: missing key '{key}'")


def run():
    discovered: dict[str, str] = {}

    status, health = fetch("/health")
    expect(status == 200, "/health: status != 200")
    expect(health.get("status") == "ok", "/health: status field is not 'ok'")

    status, home = fetch("/api/home")
    expect(status == 200, "/api/home: status != 200")
    has_keys(home, ["top_stories", "trending_topics", "category_rows"], "/api/home")
    expect(isinstance(home.get("top_stories"), list), "/api/home: top_stories is not list")
    if home.get("top_stories"):
        top = home["top_stories"][0]
        has_keys(
            top,
            ["entry_id", "title", "source_name", "published_at", "hype_score", "credibility_score", "importance_score"],
            "/api/home.top_stories[0]",
        )
        discovered["entry_id"] = top.get("entry_id", "")

    status, categories = fetch("/api/categories")
    expect(status == 200, "/api/categories: status != 200")
    has_keys(categories, ["categories"], "/api/categories")
    expect(isinstance(categories.get("categories"), list), "/api/categories: categories is not list")
    if categories.get("categories"):
        c0 = categories["categories"][0]
        has_keys(c0, ["slug", "label", "article_count"], "/api/categories.categories[0]")
        discovered["category_slug"] = c0.get("slug", "")

    status, search = fetch("/api/search", {"q": "ai"})
    expect(status == 200, "/api/search: status != 200")
    has_keys(search, ["total", "items"], "/api/search")
    expect(isinstance(search.get("items"), list), "/api/search: items is not list")

    status, sources = fetch("/api/sources/leaderboard")
    expect(status == 200, "/api/sources/leaderboard: status != 200")
    has_keys(sources, ["sources"], "/api/sources/leaderboard")

    status, clusters = fetch("/api/clusters")
    expect(status == 200, "/api/clusters: status != 200")
    expect(isinstance(clusters, list), "/api/clusters: response is not list")
    if clusters:
        discovered["cluster_id"] = str(clusters[0].get("cluster_id", ""))

    status, entities = fetch("/api/entities", {"limit": 5})
    expect(status == 200, "/api/entities: status != 200")
    has_keys(entities, ["entities"], "/api/entities")
    if entities.get("entities"):
        discovered["entity_name"] = entities["entities"][0].get("entity_name", "")

    status, narratives = fetch("/api/narratives", {"limit": 5})
    expect(status == 200, "/api/narratives: status != 200")
    has_keys(narratives, ["items"], "/api/narratives")
    if narratives.get("items"):
        discovered["arc_id"] = narratives["items"][0].get("arc_id", "")

    status, stories = fetch("/api/stories", {"limit": 5})
    expect(status == 200, "/api/stories: status != 200")
    has_keys(stories, ["items"], "/api/stories")
    if stories.get("items"):
        s0 = stories["items"][0]
        has_keys(s0, ["story_id", "compiled_title", "source_count", "first_published", "last_published"], "/api/stories.items[0]")
        discovered["story_id"] = s0.get("story_id", "")

    if discovered.get("entry_id"):
        status, article = fetch(f"/api/article/{urllib.parse.quote(discovered['entry_id'], safe='')}")
        expect(status == 200, "/api/article/{id}: status != 200")
        has_keys(article, ["entry_id", "title", "source_name", "link"], "/api/article/{id}")

    if discovered.get("category_slug"):
        status, category_feed = fetch(f"/api/category/{urllib.parse.quote(discovered['category_slug'], safe='')}")
        expect(status == 200, "/api/category/{slug}: status != 200")
        has_keys(category_feed, ["total", "items", "page", "page_size"], "/api/category/{slug}")

    if discovered.get("cluster_id"):
        status, cluster = fetch(f"/api/clusters/{urllib.parse.quote(discovered['cluster_id'], safe='')}")
        expect(status == 200, "/api/clusters/{id}: status != 200")
        has_keys(cluster, ["cluster_id", "label", "article_count", "articles"], "/api/clusters/{id}")

    if discovered.get("entity_name"):
        status, entity = fetch(f"/api/entity/{urllib.parse.quote(discovered['entity_name'], safe='')}")
        expect(status == 200, "/api/entity/{name}: status != 200")
        has_keys(entity, ["entity_name", "article_count", "articles"], "/api/entity/{name}")

    if discovered.get("arc_id"):
        status, narrative = fetch(f"/api/narratives/{urllib.parse.quote(discovered['arc_id'], safe='')}")
        expect(status == 200, "/api/narratives/{arc_id}: status != 200")
        has_keys(narrative, ["arc_id", "subtopic", "article_count", "articles"], "/api/narratives/{arc_id}")

    if discovered.get("story_id"):
        sid = urllib.parse.quote(discovered["story_id"], safe="")
        status, story = fetch(f"/api/story/{sid}")
        expect(status == 200, "/api/story/{id}: status != 200")
        has_keys(story, ["story_id", "compiled_title", "compiled_body", "source_count", "source_articles"], "/api/story/{id}")

        status, claims = fetch(f"/api/story/{sid}/claims")
        expect(status == 200, "/api/story/{id}/claims: status != 200")
        has_keys(claims, ["story_id", "items"], "/api/story/{id}/claims")


if __name__ == "__main__":
    t0 = time.time()
    try:
        run()
    except urllib.error.HTTPError as err:
        failures.append(f"HTTPError: {err.code} {err.reason}")
    except Exception as err:
        failures.append(f"Unhandled: {err}")

    elapsed = int((time.time() - t0) * 1000)
    if failures:
        print("\nAPI Contract Check: FAILED")
        for item in failures:
            print(f" - {item}")
        print(f"Elapsed: {elapsed}ms")
        sys.exit(1)

    print("\nAPI Contract Check: PASSED")
    print(f"Elapsed: {elapsed}ms")
    sys.exit(0)
