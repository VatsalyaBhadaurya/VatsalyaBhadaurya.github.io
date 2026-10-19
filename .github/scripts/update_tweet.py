#!/usr/bin/env python3
"""Refresh the featured X/Twitter tweet in index.html from an RSS feed.

Reads the RSS feed URL from the X_RSS_FEED env var (set it as the repo secret
of the same name), finds the newest tweet, and rewrites the embed between the
<!-- X_TWEET:START --> / <!-- X_TWEET:END --> markers in index.html.

Fails safe: if the feed is missing, unreachable, or has no tweet, it exits 0
without touching the file, so the live site never breaks.
"""
import os
import re
import sys
import urllib.request

INDEX = "index.html"
FEED = os.environ.get("X_RSS_FEED", "").strip()
HANDLE = os.environ.get("X_HANDLE", "_Vaastavikata").strip()

MARKER = re.compile(r"(<!-- X_TWEET:START.*?-->)(.*?)(<!-- X_TWEET:END -->)", re.S)
STATUS = re.compile(r"(?:twitter\.com|x\.com)/[^/\"<>\s]+/status/(\d+)")
INDENT = " " * 24


def fail_safe(msg: str) -> None:
    print(msg)
    sys.exit(0)


def main() -> None:
    if not FEED:
        fail_safe("X_RSS_FEED not set; skipping (nothing changed).")

    req = urllib.request.Request(
        FEED, headers={"User-Agent": "Mozilla/5.0 (GitHub Actions; x-tweet updater)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            feed = resp.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001 - never break the site on a feed error
        fail_safe(f"Feed fetch failed ({exc.__class__.__name__}); leaving file unchanged.")

    match = STATUS.search(feed)
    if not match:
        fail_safe("No tweet id found in feed; leaving file unchanged.")
    tweet_id = match.group(1)

    with open(INDEX, encoding="utf-8") as fh:
        src = fh.read()

    block = MARKER.search(src)
    if not block:
        print("ERROR: X_TWEET markers not found in index.html.")
        sys.exit(1)

    if f"/status/{tweet_id}" in block.group(2):
        fail_safe(f"Already featuring tweet {tweet_id}; no change.")

    embed = (
        '<blockquote class="twitter-tweet" data-theme="dark" data-dnt="true" '
        f'data-width="100%"><a href="https://twitter.com/{HANDLE}/status/{tweet_id}"></a>'
        "</blockquote>"
    )
    replacement = f"\\1\n{INDENT}{embed}\n{INDENT}\\3"
    updated = MARKER.sub(replacement, src, count=1)

    with open(INDEX, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(updated)
    print(f"Updated featured tweet to {tweet_id}.")


if __name__ == "__main__":
    main()
