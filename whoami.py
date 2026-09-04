#!/usr/bin/env python3
"""Diagnostic: says which Instagram account the token actually controls, and what
is currently live on its Story. Run it from the Actions tab ("Check Instagram
account") when a post reports success but nothing appears in the app.

Prints no secrets.
"""
import json
import os
import sys

import requests

from post_story import graph_base, require_env

token = require_env("IG_ACCESS_TOKEN")
configured_id = os.environ.get("IG_USER_ID", "").strip()
base = graph_base(token)
print(f"Host: {base}")
print(f"IG_USER_ID secret: {configured_id or '(not set)'}")
print(f"Token starts: {token[:4]}...\n")


def get(path, **params):
    params["access_token"] = token
    r = requests.get(f"{base}/{path}", params=params, timeout=30)
    try:
        body = r.json()
    except ValueError:
        return {"error": {"message": r.text[:300]}}
    return body


me = get("me", fields="id,username,account_type,media_count")
if "error" in me:
    print(f"Could not identify the token's account: {me['error'].get('message')}")
    sys.exit(1)

print("The token controls this account:")
print(f"  username     @{me.get('username')}")
print(f"  id           {me.get('id')}")
print(f"  account_type {me.get('account_type')}")
print(f"  media_count  {me.get('media_count')}")

if configured_id and me.get("id") and configured_id != str(me["id"]):
    print(f"\n  !! MISMATCH: IG_USER_ID is {configured_id} but the token belongs to {me['id']}.")
else:
    print("\n  IG_USER_ID matches the token's account.")

print("\nCurrently live on that account's Story:")
stories = get(f"{me['id']}/stories", fields="id,media_type,media_url,timestamp,permalink")
if "error" in stories:
    print(f"  could not read stories: {stories['error'].get('message')}")
else:
    items = stories.get("data", [])
    if not items:
        print("  nothing live (an empty list also means every story has expired)")
    for s in items:
        print(f"  {s.get('timestamp')}  {s.get('id')}  {s.get('media_type')}")
        if s.get("permalink"):
            print(f"      {s['permalink']}")

print("\nThe two media IDs this repo published today:")
for mid in ("18226975915323318", "18111549383121622"):
    m = get(mid, fields="id,media_type,media_product_type,timestamp,permalink,username")
    if "error" in m:
        print(f"  {mid}: {m['error'].get('message')}")
    else:
        print(f"  {mid}: {m.get('media_product_type')} {m.get('media_type')} "
              f"by @{m.get('username')} at {m.get('timestamp')}")
        if m.get("permalink"):
            print(f"      {m['permalink']}")
