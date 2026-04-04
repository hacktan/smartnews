"""
SmartNews Frontend Route Smoke Test
====================================
Checks that all frontend pages return HTTP 200 (or acceptable fallbacks).
Uses the API to discover valid IDs for dynamic routes.

Usage:
    uv run python tests/smoke_frontend.py                                          # defaults
    uv run python tests/smoke_frontend.py https://frontend-chi-brown-98.vercel.app  # custom URL
    uv run python tests/smoke_frontend.py --api https://smartnews-api.onrender.com  # custom API

Exit codes:
    0 = all passed
    1 = at least one FAIL
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
FRONTEND_URL = "https://frontend-chi-brown-98.vercel.app"
API_URL = "https://smartnews-api.onrender.com"
TIMEOUT = 30

parser = argparse.ArgumentParser(description="SmartNews frontend smoke test")
parser.add_argument(
    "frontend_url",
    nargs="?",
    default=FRONTEND_URL,
    help="Frontend base URL",
)
parser.add_argument(
    "--api",
    dest="api_url",
    default=API_URL,
    help="API base URL used for dynamic route discovery",
)
args = parser.parse_args()
FRONTEND_URL = args.frontend_url.rstrip("/")
API_URL = args.api_url.rstrip("/")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
results: list[tuple[str, str, str, int]] = []  # (name, status, detail, ms)


def fetch_json(url: str) -> dict | list | None:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def check_route(name: str, path: str, accept_codes: tuple = (200,)):
    """GET a frontend route and check the HTTP status."""
    url = FRONTEND_URL + path
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SmartNews-SmokeTest/1.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            ms = int((time.time() - t0) * 1000)
            code = resp.status
    except urllib.error.HTTPError as e:
        ms = int((time.time() - t0) * 1000)
        code = e.code
    except Exception as e:
        ms = int((time.time() - t0) * 1000)
        results.append((name, "FAIL", f"Connection error: {e}", ms))
        return

    if code in accept_codes:
        results.append((name, "PASS", f"status={code}", ms))
    else:
        results.append((name, "FAIL", f"status={code} (expected {accept_codes})", ms))


# ---------------------------------------------------------------------------
# Discover dynamic IDs from API
# ---------------------------------------------------------------------------
def discover_ids() -> dict[str, str]:
    ids: dict[str, str] = {}

    home = fetch_json(f"{API_URL}/api/home")
    if home:
        top = home.get("top_stories") or []
        if top:
            ids["entry_id"] = top[0].get("entry_id", "")
        topics = home.get("trending_topics") or []
        if topics:
            ids["topic"] = topics[0].get("topic", "")

    categories = fetch_json(f"{API_URL}/api/categories")
    if categories:
        cats = categories.get("categories") or []
        if cats:
            ids["category_slug"] = cats[0].get("slug", "")

    clusters = fetch_json(f"{API_URL}/api/clusters")
    if clusters and isinstance(clusters, list) and clusters:
        ids["cluster_id"] = str(clusters[0].get("cluster_id", ""))

    entities = fetch_json(f"{API_URL}/api/entities?limit=3")
    if entities:
        ents = entities.get("entities") or []
        if ents:
            ids["entity_name"] = ents[0].get("entity_name", "")

    narratives = fetch_json(f"{API_URL}/api/narratives?limit=3")
    if narratives:
        items = narratives.get("items") or []
        if items:
            ids["arc_id"] = items[0].get("arc_id", "")

    stories = fetch_json(f"{API_URL}/api/stories?limit=3")
    if stories:
        items = stories.get("items") or []
        if items:
            ids["story_id"] = items[0].get("story_id", "")

    return ids


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print(f"\n{'='*60}")
    print(f"  SmartNews Frontend Smoke Test")
    print(f"  Frontend: {FRONTEND_URL}")
    print(f"  API:      {API_URL}")
    print(f"{'='*60}\n")

    print("Discovering dynamic IDs from API...")
    ids = discover_ids()
    for k, v in ids.items():
        print(f"  {k} = {v[:40] if v else '(empty)'}")
    print()

    # Static routes
    check_route("Homepage /", "/")
    check_route("Briefing /briefing", "/briefing")
    check_route("Sources /sources", "/sources")
    check_route("Stories /stories", "/stories")
    check_route("Narratives /narratives", "/narratives")
    check_route("Search /search?q=ai", "/search?q=ai")

    # Dynamic routes
    if ids.get("entry_id"):
        check_route(f"Article /article/{ids['entry_id'][:12]}...",
                     f"/article/{ids['entry_id']}")
    else:
        results.append(("Article /article/{id}", "SKIP", "no entry_id", 0))

    if ids.get("category_slug"):
        check_route(f"Category /category/{ids['category_slug']}",
                     f"/category/{ids['category_slug']}")
    else:
        results.append(("Category /category/{slug}", "SKIP", "no slug", 0))

    if ids.get("cluster_id"):
        check_route(f"Cluster /clusters/{ids['cluster_id']}",
                     f"/clusters/{ids['cluster_id']}")
    else:
        results.append(("Cluster /clusters/{id}", "SKIP", "no cluster_id", 0))

    if ids.get("entity_name"):
        enc = urllib.parse.quote(ids["entity_name"], safe="")
        check_route(f"Entity /entity/{ids['entity_name'][:20]}",
                     f"/entity/{enc}")
    else:
        results.append(("Entity /entity/{name}", "SKIP", "no entity", 0))

    if ids.get("arc_id"):
        check_route(f"Narrative /narratives/{ids['arc_id'][:20]}",
                     f"/narratives/{ids['arc_id']}")
    else:
        results.append(("Narrative /narratives/{arcId}", "SKIP", "no arc_id", 0))

    if ids.get("story_id"):
        check_route(f"Story /story/{ids['story_id'][:12]}...",
                     f"/story/{ids['story_id']}")
    else:
        results.append(("Story /story/{id}", "SKIP", "no story_id", 0))

    if ids.get("topic"):
        enc = urllib.parse.quote(ids["topic"], safe="")
        check_route(f"Topic /topic/{ids['topic'][:20]}",
                     f"/topic/{enc}")
    else:
        results.append(("Topic /topic/{name}", "SKIP", "no topic", 0))

    # Print
    print(f"\n{'STATUS':<6} {'MS':>5}  {'ROUTE':<50} {'DETAIL'}")
    print("-" * 90)
    for name, status, detail, ms in results:
        icon = {"PASS": " OK ", "FAIL": "FAIL", "SKIP": "SKIP"}[status]
        ms_str = f"{ms:>4}ms" if ms else "     "
        print(f"  [{icon}] {ms_str}  {name:<50} {detail}")

    fails = sum(1 for _, s, _, _ in results if s == "FAIL")
    passes = sum(1 for _, s, _, _ in results if s == "PASS")
    skips = sum(1 for _, s, _, _ in results if s == "SKIP")

    print(f"\n{'='*60}")
    print(f"  PASS={passes}  FAIL={fails}  SKIP={skips}")
    if fails > 0:
        print(f"\n  RESULT: FAILED ({fails} failures)")
    else:
        print(f"\n  RESULT: PASSED")
    print(f"{'='*60}\n")
    return 1 if fails > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
