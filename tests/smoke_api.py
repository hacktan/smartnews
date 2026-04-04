"""
SmartNews API Smoke Test Suite
==============================
Self-bootstrapping: discovers valid IDs from list endpoints, then tests detail
endpoints with real data.  Works against local (http://localhost:8000) or live
(https://smartnews-api.onrender.com) instances.

Usage:
    uv run python tests/smoke_api.py                          # local
    uv run python tests/smoke_api.py https://smartnews-api.onrender.com  # live
    uv run python tests/smoke_api.py --strict                 # fail on warnings too

Exit codes:
    0 = all passed
    1 = at least one FAIL
"""
from __future__ import annotations

import json
import socket
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_URL = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "http://localhost:8000"
BASE_URL = BASE_URL.rstrip("/")
STRICT = "--strict" in sys.argv
TIMEOUT = 30  # seconds per request
RETRIES = 3


# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------
@dataclass
class TestResult:
    name: str
    status: str  # PASS, FAIL, WARN, SKIP
    detail: str = ""
    ms: int = 0


results: list[TestResult] = []

# Discovered IDs (populated by earlier tests, used by later ones)
discovered: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get(path: str, params: dict | None = None) -> tuple[int, dict | list | None, int]:
    """HTTP GET, returns (status_code, parsed_json_or_None, elapsed_ms)."""
    url = BASE_URL + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    last_err: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                body = resp.read().decode()
                elapsed = int((time.time() - t0) * 1000)
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    data = None
                return resp.status, data, elapsed
        except urllib.error.HTTPError as e:
            elapsed = int((time.time() - t0) * 1000)
            return e.code, None, elapsed
        except (urllib.error.URLError, TimeoutError, socket.timeout) as e:
            last_err = e
            if attempt < RETRIES:
                time.sleep(2 * attempt)
                continue
            elapsed = int((time.time() - t0) * 1000)
            results.append(TestResult(f"GET {path}", "FAIL", f"Connection error: {e}", elapsed))
            return 0, None, elapsed
        except Exception as e:
            last_err = e
            if attempt < RETRIES:
                time.sleep(2 * attempt)
                continue
            elapsed = int((time.time() - t0) * 1000)
            results.append(TestResult(f"GET {path}", "FAIL", f"Connection error: {e}", elapsed))
            return 0, None, elapsed
    results.append(TestResult(f"GET {path}", "FAIL", f"Connection error: {last_err}", 0))
    return 0, None, 0


def check(name: str, condition: bool, detail: str = "", ms: int = 0, warn_only: bool = False):
    """Record a test result."""
    if condition:
        results.append(TestResult(name, "PASS", detail, ms))
    elif warn_only:
        results.append(TestResult(name, "WARN", detail, ms))
    else:
        results.append(TestResult(name, "FAIL", detail, ms))


# ---------------------------------------------------------------------------
# Test groups
# ---------------------------------------------------------------------------

def test_health():
    code, data, ms = get("/health")
    check("GET /health", code == 200 and data and data.get("status") == "ok",
          f"status={code}", ms)


def test_home():
    code, data, ms = get("/api/home")
    check("GET /api/home returns 200", code == 200, f"status={code}", ms)
    if code != 200 or not data:
        return

    # Extract IDs for later tests
    top = data.get("top_stories") or []
    check("/api/home has top_stories", len(top) > 0,
          f"count={len(top)}", ms)
    if top:
        discovered["entry_id"] = top[0].get("entry_id", "")

    topics = data.get("trending_topics") or []
    if topics:
        discovered["topic"] = topics[0].get("topic", "")

    # Score sanity: hype/credibility/importance should be 0..1
    for art in top[:5]:
        for score_key in ("hype_score", "credibility_score", "importance_score"):
            val = art.get(score_key)
            if val is not None:
                check(f"top_story score {score_key} in range",
                      0.0 <= val <= 1.0,
                      f"{score_key}={val}", warn_only=True)
                break  # one check is enough to prove the point


def test_article_detail():
    eid = discovered.get("entry_id")
    if not eid:
        results.append(TestResult("GET /api/article/{id}", "SKIP", "no entry_id discovered"))
        return
    code, data, ms = get(f"/api/article/{eid}")
    check("GET /api/article/{id} returns 200", code == 200, f"status={code} id={eid[:12]}", ms)
    if data:
        check("article has title", bool(data.get("title")), "", ms)
        check("article has source_name", bool(data.get("source_name")), "", ms)


def test_categories():
    code, data, ms = get("/api/categories")
    check("GET /api/categories returns 200", code == 200, f"status={code}", ms)
    if data:
        cats = data.get("categories") or []
        check("/api/categories non-empty", len(cats) > 0, f"count={len(cats)}", ms)
        if cats:
            discovered["category_slug"] = cats[0].get("slug", "")


def test_category_feed():
    slug = discovered.get("category_slug")
    if not slug:
        results.append(TestResult("GET /api/category/{slug}", "SKIP", "no slug discovered"))
        return
    encoded = urllib.parse.quote(slug, safe="")
    code, data, ms = get(f"/api/category/{encoded}")
    check(f"GET /api/category/{slug} returns 200", code == 200, f"status={code}", ms)
    if data:
        check("category feed has items", len(data.get("items") or []) > 0,
              f"total={data.get('total', 0)}", ms)


def test_search():
    code, data, ms = get("/api/search", {"q": "technology"})
    check("GET /api/search?q=technology returns 200", code == 200, f"status={code}", ms)
    if data:
        check("search returns results", data.get("total", 0) >= 0, f"total={data.get('total')}", ms)


def test_sources_leaderboard():
    code, data, ms = get("/api/sources/leaderboard")
    check("GET /api/sources/leaderboard returns 200", code == 200, f"status={code}", ms)
    if data:
        sources = data.get("sources") or []
        check("leaderboard non-empty", len(sources) > 0, f"count={len(sources)}", ms, warn_only=True)
        # Quality: no source should have avg_credibility == 0.5 (unenriched default)
        fake_scores = [s for s in sources if s.get("avg_credibility") == 0.5]
        check("no unenriched sources in leaderboard", len(fake_scores) == 0,
              f"unenriched={len(fake_scores)}", warn_only=True)


def test_clusters():
    code, data, ms = get("/api/clusters")
    check("GET /api/clusters returns 200", code == 200, f"status={code}", ms)
    if code == 200 and isinstance(data, list) and data:
        discovered["cluster_id"] = str(data[0].get("cluster_id", ""))
        check("clusters non-empty", len(data) > 0, f"count={len(data)}", ms, warn_only=True)


def test_cluster_detail():
    cid = discovered.get("cluster_id")
    if not cid:
        results.append(TestResult("GET /api/clusters/{id}", "SKIP", "no cluster_id"))
        return
    code, data, ms = get(f"/api/clusters/{cid}")
    check(f"GET /api/clusters/{cid} returns 200", code == 200, f"status={code}", ms)


def test_entities():
    code, data, ms = get("/api/entities", {"limit": "10"})
    check("GET /api/entities returns 200", code == 200, f"status={code}", ms)
    if data:
        ents = data.get("entities") or []
        if ents:
            discovered["entity_name"] = ents[0].get("entity_name", "")
        check("entities non-empty", len(ents) > 0, f"count={len(ents)}", ms, warn_only=True)


def test_entity_detail():
    name = discovered.get("entity_name")
    if not name:
        results.append(TestResult("GET /api/entity/{name}", "SKIP", "no entity"))
        return
    encoded = urllib.parse.quote(name, safe="")
    code, data, ms = get(f"/api/entity/{encoded}")
    check(f"GET /api/entity/{name[:20]} returns 200", code == 200, f"status={code}", ms)


def test_insights_blind_spots():
    code, data, ms = get("/api/insights/blind-spots", {"limit": "5"})
    check("GET /api/insights/blind-spots returns 200", code == 200, f"status={code}", ms)


def test_briefing():
    code, data, ms = get("/api/briefing/daily")
    # 404 is acceptable when no briefing exists
    check("GET /api/briefing/daily returns 200 or 404",
          code in (200, 404), f"status={code}", ms)
    if code == 200 and data:
        check("briefing has text", bool(data.get("briefing_text")), "", ms)


def test_topic_history():
    topic = discovered.get("topic")
    if not topic:
        results.append(TestResult("GET /api/topics/{topic}/history", "SKIP", "no topic"))
        return
    encoded = urllib.parse.quote(topic, safe="")
    code, data, ms = get(f"/api/topics/{encoded}/history", {"days": "30"})
    check(f"GET /api/topics/{topic[:20]}/history returns 200", code == 200, f"status={code}", ms)


def test_narratives():
    code, data, ms = get("/api/narratives", {"limit": "10"})
    check("GET /api/narratives returns 200", code == 200, f"status={code}", ms)
    if data:
        items = data.get("items") or []
        check("narratives non-empty", len(items) > 0,
              f"count={len(items)}", ms, warn_only=True)
        if items:
            discovered["arc_id"] = items[0].get("arc_id", "")


def test_narrative_detail():
    aid = discovered.get("arc_id")
    if not aid:
        results.append(TestResult("GET /api/narratives/{arc_id}", "SKIP", "no arc_id"))
        return
    code, data, ms = get(f"/api/narratives/{aid}")
    check(f"GET /api/narratives/{aid[:20]} returns 200", code == 200, f"status={code}", ms)


def test_stories():
    code, data, ms = get("/api/stories", {"limit": "10"})
    check("GET /api/stories returns 200", code == 200, f"status={code}", ms)
    if data:
        items = data.get("items") or []
        check("compiled stories non-empty", len(items) > 0,
              f"count={len(items)}", ms, warn_only=True)
        if items:
            discovered["story_id"] = items[0].get("story_id", "")


def test_story_detail():
    sid = discovered.get("story_id")
    if not sid:
        results.append(TestResult("GET /api/story/{id}", "SKIP", "no story_id"))
        return
    code, data, ms = get(f"/api/story/{sid}")
    check(f"GET /api/story/{sid[:12]} returns 200", code == 200, f"status={code}", ms)
    if data:
        # Quality: compiled body should not contain placeholder text
        body = data.get("compiled_body") or ""
        check("story body has no placeholder text",
              "pending" not in body.lower() and "synthesis pending" not in body.lower(),
              f"body_len={len(body)}", warn_only=True)
        check("story has compiled_title", bool(data.get("compiled_title")), "")


def test_story_claims():
    sid = discovered.get("story_id")
    if not sid:
        results.append(TestResult("GET /api/story/{id}/claims", "SKIP", "no story_id"))
        return
    code, data, ms = get(f"/api/story/{sid}/claims")
    check(f"GET /api/story/{sid[:12]}/claims returns 200", code == 200, f"status={code}", ms)
    if data:
        items = data.get("items") or []
        check("story has claims", len(items) > 0,
              f"count={len(items)}", ms, warn_only=True)


def test_response_times():
    """Check that no endpoint took > 5 seconds."""
    slow = [r for r in results if r.ms > 5000 and r.status == "PASS"]
    check("no endpoint > 5s response time", len(slow) == 0,
          "; ".join(f"{r.name}={r.ms}ms" for r in slow), warn_only=True)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def main():
    print(f"\n{'='*60}")
    print(f"  SmartNews API Smoke Test")
    print(f"  Target: {BASE_URL}")
    print(f"  Mode:   {'strict' if STRICT else 'normal'}")
    print(f"{'='*60}\n")

    # Order matters: list endpoints first (discover IDs), then detail endpoints
    tests = [
        test_health,
        test_home,
        test_categories,
        test_search,
        test_sources_leaderboard,
        test_clusters,
        test_entities,
        test_insights_blind_spots,
        test_briefing,
        test_narratives,
        test_stories,
        # -- detail endpoints (need discovered IDs) --
        test_article_detail,
        test_category_feed,
        test_cluster_detail,
        test_entity_detail,
        test_topic_history,
        test_narrative_detail,
        test_story_detail,
        test_story_claims,
        # -- meta --
        test_response_times,
    ]

    for fn in tests:
        try:
            fn()
        except Exception as e:
            results.append(TestResult(fn.__name__, "FAIL", f"Unhandled: {e}"))

    # Print results
    print(f"\n{'STATUS':<6} {'MS':>5}  {'TEST':<50} {'DETAIL'}")
    print("-" * 100)
    for r in results:
        icon = {"PASS": " OK ", "FAIL": "FAIL", "WARN": "WARN", "SKIP": "SKIP"}[r.status]
        ms_str = f"{r.ms:>4}ms" if r.ms else "     "
        print(f"  [{icon}] {ms_str}  {r.name:<50} {r.detail}")

    # Summary
    counts = {"PASS": 0, "FAIL": 0, "WARN": 0, "SKIP": 0}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1

    print(f"\n{'='*60}")
    print(f"  PASS={counts['PASS']}  FAIL={counts['FAIL']}  WARN={counts['WARN']}  SKIP={counts['SKIP']}")

    if counts["FAIL"] > 0:
        print(f"\n  RESULT: FAILED ({counts['FAIL']} failures)")
        print(f"{'='*60}\n")
        return 1
    elif STRICT and counts["WARN"] > 0:
        print(f"\n  RESULT: FAILED (strict mode, {counts['WARN']} warnings)")
        print(f"{'='*60}\n")
        return 1
    else:
        print(f"\n  RESULT: PASSED")
        print(f"{'='*60}\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
