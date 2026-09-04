#!/usr/bin/env python3
"""Diagnostic: which Instagram account does this token actually control, and what is
live on its Story right now? Run it from the Actions tab ("Check Instagram account")
when a post reports success but nothing shows up in the app.

Handles both Meta paths. On graph.facebook.com "me" is the Facebook user, so the
Instagram account is reached via /me/accounts; on graph.instagram.com "me" is the
Instagram account itself. Prints no secrets.
"""
import json
import os
import sys

import requests

from post_story import graph_base, require_env

token = require_env("IG_ACCESS_TOKEN")
configured_id = os.environ.get("IG_USER_ID", "").strip()
base = graph_base(token)
is_fb = "graph.facebook.com" in base

print(f"Host:              {base}")
print(f"Token starts:      {token[:4]}...  ({'Facebook login' if is_fb else 'Instagram login'})")
print(f"IG_USER_ID secret: {configured_id or '(not set)'}\n")


def get(path, **params):
    params["access_token"] = token
    try:
        r = requests.get(f"{base}/{path}", params=params, timeout=30)
        body = r.json()
    except Exception as exc:  # network or non-JSON
        return {"error": {"message": str(exc)}}
    return body


def err(body):
    return body.get("error", {}).get("message", "unknown error")


# --- which Instagram accounts can this token reach? ---
print("Instagram accounts this token can reach:")
reachable = []
if is_fb:
    pages = get("me/accounts", fields="name,instagram_business_account")
    if "error" in pages:
        print(f"  could not list Pages: {err(pages)}")
    else:
        for page in pages.get("data", []):
            iba = page.get("instagram_business_account")
            if iba:
                info = get(iba["id"], fields="username,name,followers_count,media_count")
                uname = info.get("username", "?")
                reachable.append(str(iba["id"]))
                print(f"  Page {page.get('name')!r} -> @{uname}  id {iba['id']}")
            else:
                print(f"  Page {page.get('name')!r} -> no Instagram account linked")
        if not pages.get("data"):
            print("  the token can see no Pages at all")
else:
    me = get("me", fields="id,username")
    if "error" in me:
        print(f"  {err(me)}")
    else:
        reachable.append(str(me.get("id")))
        print(f"  @{me.get('username')}  id {me.get('id')}")

# On the Instagram-login path "me" returns an app-scoped id that legitimately differs
# from the Instagram Business account id used for publishing, so a difference there is
# not a fault. On the Facebook path the ids should match.
if configured_id and reachable:
    if configured_id in reachable:
        print(f"\n  IG_USER_ID {configured_id} matches.")
    elif is_fb:
        print(f"\n  !! IG_USER_ID is {configured_id}, which is NOT one the token can reach.")
    else:
        print(f"\n  IG_USER_ID is {configured_id}; 'me' reports the app-scoped id above. "
              f"They differ by design on this path, so this is only a problem if "
              f"publishing fails.")

# --- what is live on the configured account's Story? ---
if configured_id:
    who = get(configured_id, fields="username,name")
    label = f"@{who.get('username')}" if "error" not in who else configured_id
    print(f"\nCurrently live on {label}'s Story:")
    stories = get(f"{configured_id}/stories", fields="id,media_type,timestamp,permalink")
    if "error" in stories:
        print(f"  could not read stories: {err(stories)}")
    else:
        items = stories.get("data", [])
        if not items:
            print("  nothing live right now")
        for s in items:
            print(f"  {s.get('timestamp')}  {s.get('id')}  {s.get('media_type')}  {s.get('permalink', '')}")

# --- the two things this repo published today ---
print("\nThe most recent slides in this repo's post log:")
recent = []
try:
    with open(os.path.join(os.environ.get("DATA_DIR", "data"), "posts.jsonl"), encoding="utf-8") as f:
        recent = [json.loads(line) for line in f if line.strip()][-6:]
except FileNotFoundError:
    print("  no post log yet")
for row in recent:
    mid = row["media_id"]
    m = get(mid, fields="id,media_type,media_product_type,timestamp,permalink,username")
    label = f"{row['filename']} ({row['date']})"
    if "error" in m:
        print(f"  {label}: {err(m)}")
    else:
        print(f"  {label}: {m.get('media_product_type')} / {m.get('media_type')} "
              f"by @{m.get('username')}  {m.get('permalink', '')}")
