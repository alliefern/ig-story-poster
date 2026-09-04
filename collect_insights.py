#!/usr/bin/env python3
"""
Collects Instagram Story insights for the stories this repo posted and saves them
to data/insights.jsonl, so the dashboard (index.html) can chart them.

Why this exists as a separate daily job
---------------------------------------
Meta only serves insights for a Story while the Story is live, i.e. for 24 hours
after it posts. After that the numbers are gone from the API. So this runs every
day at 15:30 UTC (see .github/workflows/collect-insights.yml), half an hour before
the next post goes out, and grabs near-final numbers for whatever posted yesterday.

What it records per story
-------------------------
views, reach, replies, shares, total_interactions, profile_visits, follows, and the
navigation breakdown (tap_forward, tap_back, tap_exit, swipe_forward). Meta gives
counts, not names: the API does not expose who viewed a Story.

It also asks Meta when the access token expires (best effort, via /debug_token) and
writes that to data/status.json so the dashboard can count down to it.

Env vars
--------
  IG_ACCESS_TOKEN   - required, the same long-lived token post_story.py uses
  DATA_DIR          - default "data"
  LOOKBACK_HOURS    - default 24. Collect for posts newer than this.
  TOKEN_ISSUED      - YYYY-MM-DD the current token was generated. Meta refuses
                      debug_token on the Instagram-login path, so this is how the
                      dashboard knows when to start warning. Update it when you
                      refresh the token.
  TOKEN_LIFETIME_DAYS - default 60.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

from post_story import GRAPH_API_VERSION, graph_base, require_env

DATA_DIR = os.environ.get("DATA_DIR", "data")
POSTS_PATH = os.path.join(DATA_DIR, "posts.jsonl")
INSIGHTS_PATH = os.path.join(DATA_DIR, "insights.jsonl")
STATUS_PATH = os.path.join(DATA_DIR, "status.json")

# Metrics Meta supports for STORY media. If Meta renames or retires one, the bulk
# request fails and we fall back to asking for each metric on its own, so one bad
# name can't take the whole collection down.
STORY_METRICS = ["views", "reach", "replies", "shares", "total_interactions", "profile_visits", "follows"]
NAVIGATION_METRIC = "navigation"
NAVIGATION_BREAKDOWN = "story_navigation_action_type"


def load_jsonl(path: str) -> list:
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def append_jsonl(path: str, row: dict) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def graph_get(url: str, params: dict) -> dict:
    """GET from the Graph API and always return a dict; API errors come back under "error"."""
    try:
        resp = requests.get(url, params=params, timeout=30)
    except requests.RequestException as exc:
        return {"error": {"message": f"network error: {exc}", "code": "network"}}
    try:
        body = resp.json()
    except ValueError:
        return {"error": {"message": f"non-JSON response (HTTP {resp.status_code})", "code": resp.status_code}}
    if resp.status_code >= 400 and "error" not in body:
        body = {"error": {"message": f"HTTP {resp.status_code}", "code": resp.status_code}}
    return body


def error_text(body: dict) -> str:
    err = body.get("error") or {}
    return f"{err.get('message', 'unknown error')} (code {err.get('code')}, subcode {err.get('error_subcode')})"


def parse_value(item: dict):
    """Insights come in two shapes depending on the metric's generation:
    {"total_value": {"value": N}} for newer metrics, {"values": [{"value": N}]} for older ones."""
    total = item.get("total_value")
    if isinstance(total, dict) and "value" in total:
        return total["value"]
    values = item.get("values")
    if values:
        return values[0].get("value")
    return None


def parse_breakdown(item: dict) -> dict:
    out = {}
    total = item.get("total_value") or {}
    for breakdown in total.get("breakdowns", []):
        for result in breakdown.get("results", []):
            dims = result.get("dimension_values") or []
            if dims:
                out[dims[0]] = result.get("value")
    return out


def fetch_story_metrics(media_id: str, token: str) -> tuple[dict, list]:
    metrics: dict = {}
    errors: list = []
    url = f"{graph_base(token)}/{media_id}/insights"

    body = graph_get(url, {"metric": ",".join(STORY_METRICS), "metric_type": "total_value", "access_token": token})
    if "error" in body:
        errors.append(f"bulk request failed, retrying per metric: {error_text(body)}")
        for name in STORY_METRICS:
            single = graph_get(url, {"metric": name, "metric_type": "total_value", "access_token": token})
            if "error" in single:
                single = graph_get(url, {"metric": name, "access_token": token})
            if "error" in single:
                errors.append(f"{name}: {error_text(single)}")
                continue
            for item in single.get("data", []):
                metrics[item.get("name", name)] = parse_value(item)
    else:
        for item in body.get("data", []):
            metrics[item["name"]] = parse_value(item)

    nav = graph_get(url, {
        "metric": NAVIGATION_METRIC,
        "breakdown": NAVIGATION_BREAKDOWN,
        "metric_type": "total_value",
        "access_token": token,
    })
    if "error" in nav:
        errors.append(f"navigation: {error_text(nav)}")
    else:
        for item in nav.get("data", []):
            metrics["navigation"] = parse_breakdown(item)
            metrics["navigation_total"] = parse_value(item)

    return metrics, errors


def check_token(token: str) -> dict:
    """Best effort: ask Meta when this token expires. Works when the token belongs to a
    developer of the app (which is you). If Meta refuses, we simply don't know."""
    body = graph_get(f"{graph_base(token)}/debug_token",
                     {"input_token": token, "access_token": token})
    data = body.get("data") if isinstance(body.get("data"), dict) else None
    if not data:
        return {"token_check_error": error_text(body) if "error" in body else "no data returned"}
    return {
        "token_is_valid": data.get("is_valid"),
        "token_expires_at": data.get("expires_at"),  # unix seconds, 0 means never
        "token_data_access_expires_at": data.get("data_access_expires_at"),
        "token_scopes": data.get("scopes"),
    }


def main() -> None:
    token = require_env("IG_ACCESS_TOKEN")
    lookback_hours = float(os.environ.get("LOOKBACK_HOURS", "24"))
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=lookback_hours)

    posts = load_jsonl(POSTS_PATH)
    already_recorded = {row["media_id"] for row in load_jsonl(INSIGHTS_PATH)}

    due, expired = [], []
    for post in posts:
        posted_at = datetime.fromisoformat(post["posted_at"])
        if posted_at >= cutoff:
            due.append(post)
        elif post["media_id"] not in already_recorded:
            expired.append(post)

    print(f"{len(posts)} posts logged, {len(due)} within the last {lookback_hours:g}h, "
          f"{len(expired)} expired before we could collect.")

    collected, failed = 0, 0
    for post in due:
        posted_at = datetime.fromisoformat(post["posted_at"])
        hours_after = round((now - posted_at).total_seconds() / 3600, 2)
        print(f"Collecting {post['media_id']} ({post['group']} slide {post['slide']} of {post['slides_total']}, "
              f"{hours_after}h after posting)...")
        metrics, errors = fetch_story_metrics(post["media_id"], token)
        if metrics:
            collected += 1
            print(f"  got {', '.join(f'{k}={v}' for k, v in metrics.items() if k != 'navigation')}")
        else:
            failed += 1
        for err in errors:
            print(f"  warning: {err}")
        append_jsonl(INSIGHTS_PATH, {
            "media_id": post["media_id"],
            "collected_at": now.isoformat(timespec="seconds"),
            "hours_after_post": hours_after,
            "metrics": metrics,
            "errors": errors,
        })

    for post in expired:
        print(f"Marking {post['media_id']} ({post['date']} {post['group']} slide {post['slide']}) as missed: "
              f"the story expired before insights were collected.")
        append_jsonl(INSIGHTS_PATH, {
            "media_id": post["media_id"],
            "collected_at": now.isoformat(timespec="seconds"),
            "hours_after_post": None,
            "metrics": {},
            "errors": ["expired before insights were collected"],
        })

    status = {
        "last_collect_at": now.isoformat(timespec="seconds"),
        "last_collect_ok": failed == 0,
        "stories_collected": collected,
        "stories_failed": failed,
        "api_version": GRAPH_API_VERSION,
        "token_checked_at": now.isoformat(timespec="seconds"),
    }
    status.update(check_token(token))

    # If Meta would not tell us the expiry, fall back to counting from the date the
    # token was issued, so the dashboard can still show a countdown rather than a shrug.
    issued = os.environ.get("TOKEN_ISSUED", "").strip()
    if issued and not status.get("token_expires_at"):
        lifetime = int(os.environ.get("TOKEN_LIFETIME_DAYS", "60"))
        issued_at = datetime.strptime(issued, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        expires_at = issued_at + timedelta(days=lifetime)
        status["token_issued"] = issued
        status["token_expires_at"] = int(expires_at.timestamp())
        status["token_expiry_is_estimated"] = True
        print(f"Meta would not report an expiry; estimating {expires_at.date()} "
              f"({lifetime} days from {issued}).")
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2)
        f.write("\n")

    if status.get("token_is_valid") is False:
        print("ERROR: Meta says the access token is no longer valid. Refresh IG_ACCESS_TOKEN.", file=sys.stderr)
        sys.exit(1)
    if due and collected == 0:
        print("ERROR: every insights request failed. See warnings above.", file=sys.stderr)
        sys.exit(1)
    print("Done.")


if __name__ == "__main__":
    main()
