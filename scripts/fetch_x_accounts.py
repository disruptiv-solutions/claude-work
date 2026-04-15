#!/usr/bin/env python3
"""
LaunchBox — X API v2 parallel account fetcher.
Fetches tweets from the last 24h for all 17 curated accounts,
scores by engagement, and writes candidates.json.

Usage:
  python3 scripts/fetch_x_accounts.py \
    --bearer-token TOKEN \
    --out daily-carousel/YYYY-MM-DD/candidates.json \
    [--max-workers 17]
"""

import argparse
import json
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
import requests

ACCOUNTS = [
    "sama", "OfficialLoganK", "AiBreakfast", "minchoi", "heyrobinai",
    "mreflow", "techhalla", "dr_cintas", "rubenhassid", "heynavtoor",
    "r0ck3t23", "PhilKiel", "HenryCrochemore", "RoundtableSpace",
    "akshay_pachaar", "AmericanutopiaX", "AdityaJiRathore",
]

SEARCH_URL  = "https://api.twitter.com/2/tweets/search/recent"
TWEET_FIELDS = "public_metrics,created_at,author_id,entities"
MAX_RESULTS  = 20   # per account (max 100 on free tier)

def engagement_score(m: dict) -> int:
    return (
        m.get("like_count", 0)       * 3 +
        m.get("retweet_count", 0)    * 2 +
        m.get("reply_count", 0)           +
        m.get("quote_count", 0)           +
        m.get("bookmark_count", 0)   * 2
    )

def fetch_account(username: str, bearer: str, since_iso: str) -> dict:
    headers = {"Authorization": f"Bearer {bearer}"}
    params  = {
        "query":        f"from:{username} -is:retweet -is:reply",
        "start_time":   since_iso,
        "max_results":  MAX_RESULTS,
        "tweet.fields": TWEET_FIELDS,
    }
    try:
        r = requests.get(SEARCH_URL, headers=headers, params=params, timeout=15)
        if r.status_code == 401:
            return {"account": username, "error": "401_unauthorized", "tweets": []}
        if r.status_code == 429:
            return {"account": username, "error": "429_rate_limit",   "tweets": []}
        r.raise_for_status()
        data  = r.json()
        tweets = data.get("data", [])
        return {"account": username, "error": None, "tweets": tweets}
    except Exception as e:
        return {"account": username, "error": str(e), "tweets": []}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bearer-token", required=True)
    ap.add_argument("--out",          required=True)
    ap.add_argument("--max-workers",  type=int, default=17)
    args = ap.parse_args()

    since = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"Fetching tweets since {since} …", file=sys.stderr)

    all_tweets     = []
    accounts_empty = []
    errors         = []

    with ThreadPoolExecutor(max_workers=args.max_workers) as pool:
        futures = {
            pool.submit(fetch_account, acct, args.bearer_token, since): acct
            for acct in ACCOUNTS
        }
        for fut in as_completed(futures):
            res = fut.result()
            acct = res["account"]
            if res["error"]:
                errors.append({"account": acct, "error": res["error"]})
                print(f"  [WARN] @{acct}: {res['error']}", file=sys.stderr)
            if not res["tweets"]:
                accounts_empty.append(acct)
                print(f"  [EMPTY] @{acct}", file=sys.stderr)
            else:
                print(f"  [OK] @{acct}: {len(res['tweets'])} tweets", file=sys.stderr)
            for tw in res["tweets"]:
                metrics = tw.get("public_metrics", {})
                all_tweets.append({
                    "id":             tw["id"],
                    "text":           tw["text"],
                    "author":         acct,
                    "created_at":     tw.get("created_at", ""),
                    "engagement_score": engagement_score(metrics),
                    "metrics":        metrics,
                    "source_url":     f"https://x.com/{acct}/status/{tw['id']}",
                })

    all_tweets.sort(key=lambda t: t["engagement_score"], reverse=True)

    output = {
        "fetched_at":      datetime.now(timezone.utc).isoformat(),
        "since":           since,
        "accounts_empty":  accounts_empty,
        "errors":          errors,
        "tweet_count":     len(all_tweets),
        "tweets":          all_tweets,
    }

    import os
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n{len(all_tweets)} tweets → {args.out}", file=sys.stderr)
    if errors and all(e["error"].startswith("401") for e in errors):
        print("\n[ERROR] All accounts returned 401 — bearer token invalid. "
              "Regenerate at developer.twitter.com.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
