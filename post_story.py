#!/usr/bin/env python3
"""
Posts two images to an Instagram Story every other calendar day:
  1. The day's set image, which depends on which weekday it is
     (images/SET_ONE.jpg through images/SET_SEVEN.jpg, one per weekday)
  2. That set's companion image, posted second
     (images/SET_ONE_A.jpg through images/SET_SEVEN_A.jpg)

Each weekday is locked to one set (Monday = SET_ONE, Tuesday = SET_TWO, ... Sunday =
SET_SEVEN). If you want the "second image" to be visually identical every single day,
just upload the same file content as each SET_N_A.jpg — the script doesn't care, it
just posts whatever's in that slot.

How the "every other day" logic works
--------------------------------------
Meta's API has no concept of "every other day" — it just posts when you tell it to.
So this script runs every day (via the GitHub Actions cron in this repo) and, each time,
checks whether today is a "posting day" by counting days since a REFERENCE_DATE and
checking if that count is even. Change REFERENCE_DATE (below, or via env var) to shift
which specific days are "on" days — e.g. set it to a day you post, and every 2nd day after
that will post too.

Requirements
------------
- An Instagram Business or Creator account linked to a Facebook Page (required by Meta
  for any API posting — there is no way around this for personal accounts).
- A Meta access token with instagram_basic + instagram_content_publish permissions,
  exchanged for a long-lived token (lasts ~60 days, must be refreshed — see README).
- Images hosted at a public URL Meta's servers can fetch. This script assumes they live
  in THIS repo (under images/) and are referenced via raw.githubusercontent.com, which
  means the repo (or at least this folder) needs to be public. See README for alternatives
  if you'd rather not make the repo public.

Env vars required (set as GitHub repo secrets, see README):
  IG_USER_ID       - your Instagram Business Account ID (numeric)
  IG_ACCESS_TOKEN  - long-lived Meta access token
  IMAGE_BASE_URL   - public base URL where images/ is served from
                      e.g. https://raw.githubusercontent.com/<you>/<repo>/main/images
Optional:
  REFERENCE_DATE   - YYYY-MM-DD, defaults to 2026-09-01. Days-since-this-date even = post.
"""

import os
import sys
import time
from datetime import date, datetime
import requests

GRAPH_API_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

WEEKDAY_SETS = {
    0: "SET_ONE",    # Monday
    1: "SET_TWO",    # Tuesday
    2: "SET_THREE",  # Wednesday
    3: "SET_FOUR",   # Thursday
    4: "SET_FIVE",   # Friday
    5: "SET_SIX",    # Saturday
    6: "SET_SEVEN",  # Sunday
}


def is_posting_day(reference_date_str: str, today: date) -> bool:
    reference_date = datetime.strptime(reference_date_str, "%Y-%m-%d").date()
    delta_days = (today - reference_date).days
    return delta_days % 2 == 0


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"ERROR: missing required env var {name}", file=sys.stderr)
        sys.exit(1)
    return value


def create_story_container(ig_user_id: str, access_token: str, image_url: str) -> str:
    resp = requests.post(
        f"{GRAPH_BASE}/{ig_user_id}/media",
        data={
            "image_url": image_url,
            "media_type": "STORIES",
            "access_token": access_token,
        },
        timeout=60,
    )
    resp.raise_for_status()
    container_id = resp.json()["id"]
    return container_id


def wait_until_ready(container_id: str, access_token: str, max_wait_seconds: int = 60) -> None:
    """Story containers usually finish processing in a few seconds, but poll to be safe."""
    waited = 0
    interval = 3
    while waited < max_wait_seconds:
        resp = requests.get(
            f"{GRAPH_BASE}/{container_id}",
            params={"fields": "status_code", "access_token": access_token},
            timeout=30,
        )
        resp.raise_for_status()
        status = resp.json().get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Container {container_id} failed processing")
        time.sleep(interval)
        waited += interval
    raise TimeoutError(f"Container {container_id} did not finish processing in time")


def publish_container(ig_user_id: str, access_token: str, container_id: str) -> str:
    resp = requests.post(
        f"{GRAPH_BASE}/{ig_user_id}/media_publish",
        data={
            "creation_id": container_id,
            "access_token": access_token,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def post_image_to_story(ig_user_id: str, access_token: str, image_url: str, label: str) -> None:
    print(f"Creating story container for {label} ({image_url})...")
    container_id = create_story_container(ig_user_id, access_token, image_url)
    print(f"  container id: {container_id}, waiting for processing...")
    wait_until_ready(container_id, access_token)
    media_id = publish_container(ig_user_id, access_token, container_id)
    print(f"  posted. media id: {media_id}")


def main() -> None:
    today = date.today()
    reference_date_str = os.environ.get("REFERENCE_DATE", "2026-09-01")

    if not is_posting_day(reference_date_str, today):
        print(f"{today.isoformat()} is not a posting day (reference {reference_date_str}). Skipping.")
        return

    ig_user_id = require_env("IG_USER_ID")
    access_token = require_env("IG_ACCESS_TOKEN")
    image_base_url = require_env("IMAGE_BASE_URL").rstrip("/")

    set_name = WEEKDAY_SETS[today.weekday()]
    day_filename = f"{set_name}.jpg"
    companion_filename = f"{set_name}_A.jpg"
    day_image_url = f"{image_base_url}/{day_filename}"
    companion_image_url = f"{image_base_url}/{companion_filename}"

    print(f"{today.isoformat()} is a posting day. Posting {day_filename} then {companion_filename}.")

    post_image_to_story(ig_user_id, access_token, day_image_url, f"day image ({day_filename})")
    post_image_to_story(ig_user_id, access_token, companion_image_url, f"companion image ({companion_filename})")

    print("Done.")


if __name__ == "__main__":
    main()
