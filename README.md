# Instagram Story auto-poster

Posts a "day image" (changes by weekday) plus a "constant image" (always the same)
to your Instagram Story every other calendar day, on autopilot via GitHub Actions.

## The honest version of how this works

Instagram/Meta does not let anyone auto-post to Stories from a personal account —
full stop, no workaround. It only works for a **Business or Creator account linked
to a Facebook Page**, through Meta's official Graph API. Since your account already
meets that bar, this will work — but there are two real maintenance costs worth
knowing upfront:

1. **The access token expires.** Meta's long-lived tokens last ~60 days, then need
   manually refreshing (5 minutes, described below). This script won't silently
   fail forever — GitHub will email you if a run errors out — but it *will* stop
   posting until you refresh it.
2. **Images need a public URL.** Meta's servers fetch the image from a URL you give
   them — they don't accept file uploads directly. The simplest reliable option is
   hosting the images in this same GitHub repo and pointing at the raw file URL,
   which means the repo (or at least the `images/` folder) needs to be public.
   Google Drive/Dropbox share links technically can work, but Meta's fetcher is
   picky about them (permission prompts, redirect chains) and they're the #1 cause
   of these things silently breaking. I'd steer you away from that route.

## One-time setup

### 1. Create a Meta developer app and get credentials

1. Go to [developers.facebook.com/apps](https://developers.facebook.com/apps) and
   create an app (type: "Business").
2. Add the **Instagram Graph API** product to it.
3. In [Graph API Explorer](https://developers.facebook.com/tools/explorer/), select
   your app, and generate a User Access Token with these permissions:
   `instagram_basic`, `instagram_content_publish`, `pages_show_list`,
   `pages_read_engagement`.
4. Exchange that short-lived token for a **long-lived token** (~60 days) — Meta's
   docs call this the "long-lived access token" step; it's one API call with your
   app ID and app secret.
5. Find your **Instagram Business Account ID**: call
   `GET /me/accounts` (lists your Pages) then
   `GET /<page_id>?fields=instagram_business_account` to get the numeric IG user ID.

This part is genuinely the fiddliest step in the whole setup — if you want, send me
your Facebook Page name once you're at this point and I can walk the exact API calls
with you rather than you hunting through Meta's docs.

### 2. Create the GitHub repo

1. Create a new **public** repo (private also works if you use GitHub Pages instead
   of raw.githubusercontent.com for image hosting — ask me if you'd rather do that).
2. Add all the files from this project to it, including the `.github/workflows/`
   folder.
3. Drop your 14 images into `images/` — see `images/README.md` for exact filenames
   (each weekday gets a `SET_N.jpg` + `SET_N_A.jpg` pair).

### 3. Add your secrets

In the repo: Settings → Secrets and variables → Actions → New repository secret.
Add three:

| Secret name | Value |
|---|---|
| `IG_USER_ID` | your Instagram Business Account ID from step 1 |
| `IG_ACCESS_TOKEN` | your long-lived access token from step 1 |
| `IMAGE_BASE_URL` | `https://raw.githubusercontent.com/<your-username>/<repo-name>/main/images` |

### 4. Set your reference date

Open `post_story.py`, or just override `REFERENCE_DATE` in the workflow file
(`.github/workflows/post-story.yml`), to any date you want to count as a "posting
day." Every 2nd calendar day from that date will post; the days in between are
skipped automatically.

### 5. Test it

Go to the repo's **Actions** tab → "Post Instagram Story" → **Run workflow** to
trigger it manually and confirm it works before trusting the schedule.

## Ongoing maintenance

- **Every ~60 days:** refresh `IG_ACCESS_TOKEN` (repeat the token exchange in step 1.4)
  and update the GitHub secret.
- **To change posting time:** edit the `cron` line in `.github/workflows/post-story.yml`
  (it's in UTC).
- **To change which images post:** just replace the files in `images/` — same filenames.
  Monday is always `SET_ONE`/`SET_ONE_A`, Tuesday `SET_TWO`/`SET_TWO_A`, and so on
  through Sunday as `SET_SEVEN`/`SET_SEVEN_A` — the `_A` file is always what posts
  second for that day.
