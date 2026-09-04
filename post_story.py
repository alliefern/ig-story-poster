#!/usr/bin/env python3
"""
Posts a day's worth of images to an Instagram Story, every day, following a fixed
12-day loop:

  Day 1   SET_ONE, SET_ONE_A              Day 7   SET_FOUR, SET_FOUR_A
  Day 2   QUIZ_ONE ... QUIZ_FOUR          Day 8   QUIZ_STANDALONE
  Day 3   SET_TWO, SET_TWO_A              Day 9   SET_FIVE, SET_FIVE_A
  Day 4   QUIZ_STANDALONE                 Day 10  QUIZ_ONE ... QUIZ_FOUR
  Day 5   SET_THREE, SET_THREE_A          Day 11  SET_SIX, SET_SIX_A
  Day 6   QUIZ_ONE ... QUIZ_FOUR          Day 12  QUIZ_STANDALONE

Day 13 is Day 1 again. Slides post in the order listed, a few seconds apart, so
they appear in that order in the Story. The loop is edited in CYCLE below.

Which day is which
------------------
Day 1 is CYCLE_START_DATE (an env var, set in the GitHub Actions workflow). The
script counts days from there and takes the remainder after dividing by 12. If
the workflow first runs after that date, it simply joins the loop part-way
through, which is fine. Before that date it posts nothing.

What Meta can and can't do here
-------------------------------
Stories posted through the API are plain images. No quiz sticker, poll, slider,
link or mention can be attached. A "quiz" here is an image that looks like one;
people answer by replying or by tapping through to the next slide.

Requirements
------------
- An Instagram Business or Creator account linked to a Facebook Page (required by Meta
  for any API posting; there is no way around this for personal accounts).
- A Meta access token with instagram_basic + instagram_content_publish permissions,
  exchanged for a long-lived token (lasts ~60 days, must be refreshed, see README).
- Images hosted at a public URL Meta's servers can fetch. This script assumes they live
  in THIS repo (under images/) and are referenced via raw.githubusercontent.com, which
  means the repo needs to be public. See README for alternatives.

Env vars required (set as GitHub repo secrets, see README):
  IG_USER_ID       - your Instagram Business Account ID (numeric)
  IG_ACCESS_TOKEN  - long-lived Meta access token
  IMAGE_BASE_URL   - public base URL where images/ is served from
                      e.g. https://raw.githubusercontent.com/<you>/<repo>/main/images
Optional:
  GRAPH_HOST         - "auto" (default) picks the right Meta host from the token's
                       own prefix. Force it with graph.instagram.com or graph.facebook.com.
  GRAPH_API_VERSION  - defaults to v21.0.
  CYCLE_START_DATE   - YYYY-MM-DD that counts as Day 1. Defaults to 2026-09-05.
  CYCLE_DAY_OVERRIDE - 1 to 12. Post that day's slides regardless of the date. For testing.
  FORCE_REPOST       - "true" to post again even though today is already in the post log.
  DATA_DIR           - where to write the post log (default: data/). Each published slide
                       is appended to data/posts.jsonl so collect_insights.py and the
                       dashboard (index.html) know what went live and when.
"""

import json
import os
import sys
import time
from datetime import date, datetime, timezone
import requests

GRAPH_API_VERSION = os.environ.get("GRAPH_API_VERSION", "v21.0")

# Meta has two Instagram publishing paths and they use different hosts:
#   graph.instagram.com  - "Instagram API with Instagram login". Scopes are named
#                          instagram_business_*, and no Facebook Page is involved.
#   graph.facebook.com   - "Instagram API with Facebook login". Scopes are named
#                          instagram_basic, instagram_content_publish, pages_*.
# Which one you need depends on how the Meta app's use case was set up. Getting it
# wrong produces a confusing permission error naming a scope your app cannot have,
# so it is an env var rather than something to go editing in here.
# Tokens are self-identifying: Instagram-login tokens start "IGAA", Facebook-login
# tokens start "EAA". Each host only accepts its own kind, and sending one to the
# other gets you "Cannot parse access token", which reads like a corrupted paste
# rather than a mismatch. So work it out from the token instead of guessing. Set
# GRAPH_HOST to a hostname to override.
GRAPH_HOST = os.environ.get("GRAPH_HOST", "auto").strip() or "auto"


def graph_base(access_token: str) -> str:
    host = GRAPH_HOST
    if host == "auto":
        host = "graph.instagram.com" if access_token.startswith("IGAA") else "graph.facebook.com"
    return f"https://{host}/{GRAPH_API_VERSION}"
DATA_DIR = os.environ.get("DATA_DIR", "data")

CYCLE_LENGTH_DAYS = 12
QUIZ = ["QUIZ_ONE", "QUIZ_TWO", "QUIZ_THREE", "QUIZ_FOUR"]
STANDALONE = ["QUIZ_STANDALONE"]

# One entry per day of the loop: a label for the day, and the slides in posting order.
# Filenames are <slide>.jpg inside images/. Uppercase matters: GitHub URLs are case-sensitive.
CYCLE = [
    ("SET_ONE", ["SET_ONE", "SET_ONE_A"]),
    ("QUIZ", QUIZ),
    ("SET_TWO", ["SET_TWO", "SET_TWO_A"]),
    ("QUIZ_STANDALONE", STANDALONE),
    ("SET_THREE", ["SET_THREE", "SET_THREE_A"]),
    ("QUIZ", QUIZ),
    ("SET_FOUR", ["SET_FOUR", "SET_FOUR_A"]),
    ("QUIZ_STANDALONE", STANDALONE),
    ("SET_FIVE", ["SET_FIVE", "SET_FIVE_A"]),
    ("QUIZ", QUIZ),
    ("SET_SIX", ["SET_SIX", "SET_SIX_A"]),
    ("QUIZ_STANDALONE", STANDALONE),
]
assert len(CYCLE) == CYCLE_LENGTH_DAYS


def cycle_day(start_date_str: str, today: date) -> int | None:
    """1-based day of the 12-day loop for `today`, or None if the loop hasn't started yet."""
    start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    delta_days = (today - start).days
    if delta_days < 0:
        return None
    return delta_days % CYCLE_LENGTH_DAYS + 1


def already_posted_today(today: date) -> bool:
    """True if data/posts.jsonl already has a slide logged for today.

    A manual test run and the daily schedule can easily land on the same day, and
    without this the day's slides go out twice. Set FORCE_REPOST=true to override.
    """
    path = os.path.join(DATA_DIR, "posts.jsonl")
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and json.loads(line).get("date") == today.isoformat():
                return True
    return False


def require_env(name: str) -> str:
    raw = os.environ.get(name)
    if not raw or not raw.strip():
        print(f"ERROR: missing required env var {name}", file=sys.stderr)
        sys.exit(1)
    # A stray newline or space pasted into a GitHub secret is invisible in the UI and
    # makes Meta reject the whole request as unparseable, so trim rather than trust.
    value = raw.strip()
    if value != raw:
        print(f"note: trimmed whitespace from {name}")
    return value


def check(resp, what: str):
    """Raise with Meta's own error message attached.

    requests' raise_for_status() only reports the status code, but every Graph API
    failure carries a JSON body naming the actual problem (bad token, wrong account
    ID, unfetchable image, missing permission). Losing that turns a five-second fix
    into a guessing game, so print it and put it in the exception.
    """
    if resp.status_code < 400:
        return resp
    try:
        err = resp.json().get("error", {})
        detail = (f"{err.get('message', resp.text)} "
                  f"(type {err.get('type')}, code {err.get('code')}, "
                  f"subcode {err.get('error_subcode')})")
    except ValueError:
        detail = resp.text[:500]
    print(f"ERROR: {what} failed with HTTP {resp.status_code}", file=sys.stderr)
    print(f"  Meta said: {detail}", file=sys.stderr)
    raise RuntimeError(f"{what}: {detail}")


def create_story_container(ig_user_id: str, access_token: str, image_url: str) -> str:
    resp = requests.post(
        f"{graph_base(access_token)}/{ig_user_id}/media",
        data={
            "image_url": image_url,
            "media_type": "STORIES",
            "access_token": access_token,
        },
        timeout=60,
    )
    check(resp, f"creating story container for {image_url}")
    container_id = resp.json()["id"]
    return container_id


def wait_until_ready(container_id: str, access_token: str, max_wait_seconds: int = 60) -> None:
    """Story containers usually finish processing in a few seconds, but poll to be safe."""
    waited = 0
    interval = 3
    while waited < max_wait_seconds:
        resp = requests.get(
            f"{graph_base(access_token)}/{container_id}",
            params={"fields": "status_code", "access_token": access_token},
            timeout=30,
        )
        check(resp, f"checking container {container_id}")
        body = resp.json()
        status = body.get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Container {container_id} failed processing: "
                               f"{body.get('status', 'no detail given')}")
        time.sleep(interval)
        waited += interval
    raise TimeoutError(f"Container {container_id} did not finish processing in time")


def publish_container(ig_user_id: str, access_token: str, container_id: str) -> str:
    resp = requests.post(
        f"{graph_base(access_token)}/{ig_user_id}/media_publish",
        data={
            "creation_id": container_id,
            "access_token": access_token,
        },
        timeout=60,
    )
    check(resp, f"publishing container {container_id}")
    return resp.json()["id"]


def record_post(media_id: str, group: str, slide: int, slides_total: int, filename: str) -> None:
    """Append one line to data/posts.jsonl describing a story that just went live.

    The insights collector (collect_insights.py) reads this to know which media IDs to
    fetch numbers for before the story expires, and the dashboard reads it to show what
    posted and when. The workflow commits the file back to the repo after each run.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    now = datetime.now(timezone.utc)
    entry = {
        "media_id": media_id,
        "posted_at": now.isoformat(timespec="seconds"),
        "date": now.date().isoformat(),
        "group": group,
        "slide": slide,
        "slides_total": slides_total,
        "filename": filename,
        "run_id": os.environ.get("GITHUB_RUN_ID"),
    }
    with open(os.path.join(DATA_DIR, "posts.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def post_image_to_story(
    ig_user_id: str, access_token: str, image_url: str, label: str,
    group: str = "", slide: int = 1, slides_total: int = 1, filename: str = "",
) -> str:
    print(f"Creating story container for {label} ({image_url})...")
    container_id = create_story_container(ig_user_id, access_token, image_url)
    print(f"  container id: {container_id}, waiting for processing...")
    wait_until_ready(container_id, access_token)
    media_id = publish_container(ig_user_id, access_token, container_id)
    print(f"  posted. media id: {media_id}")
    record_post(media_id, group, slide, slides_total, filename)
    return media_id


def main() -> None:
    today = date.today()
    start_date_str = os.environ.get("CYCLE_START_DATE", "2026-09-04")

    override = os.environ.get("CYCLE_DAY_OVERRIDE", "").strip()
    if override:
        day = int(override)
        if not 1 <= day <= CYCLE_LENGTH_DAYS:
            print(f"ERROR: CYCLE_DAY_OVERRIDE must be 1 to {CYCLE_LENGTH_DAYS}, got {override}", file=sys.stderr)
            sys.exit(1)
        print(f"CYCLE_DAY_OVERRIDE set: posting Day {day} content regardless of the date.")
    else:
        day = cycle_day(start_date_str, today)
        if day is None:
            print(f"{today.isoformat()} is before CYCLE_START_DATE {start_date_str}. Nothing to post yet.")
            return

    if already_posted_today(today) and os.environ.get("FORCE_REPOST", "").lower() != "true":
        print(f"{today.isoformat()} already has slides in the post log. Not posting again. "
              f"Run with force_repost if you really want a second set today.")
        return

    ig_user_id = require_env("IG_USER_ID")
    access_token = require_env("IG_ACCESS_TOKEN")
    image_base_url = require_env("IMAGE_BASE_URL").rstrip("/")

    group, slides = CYCLE[day - 1]
    print(f"{today.isoformat()} is Day {day} of {CYCLE_LENGTH_DAYS} ({group}). "
          f"Posting {len(slides)} slide(s): {', '.join(slides)}.")
    print(f"Using {graph_base(access_token)} for account {ig_user_id} "
          f"(token starts {access_token[:4]}...).")

    for index, slide in enumerate(slides, start=1):
        filename = f"{slide}.jpg"
        post_image_to_story(
            ig_user_id, access_token, f"{image_base_url}/{filename}",
            f"slide {index} of {len(slides)} ({filename})",
            group=group, slide=index, slides_total=len(slides), filename=filename,
        )

    print("Done.")


if __name__ == "__main__":
    main()
