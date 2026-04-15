#!/usr/bin/env python3
"""
LaunchBox Daily Carousel — Gemini Slide Generator
Generates 6 square PNG slides via Gemini 3.1 Flash Image Preview REST API.

Usage:
  python3 scripts/generate_slides.py \
    --date YYYY-MM-DD \
    --headlines path/to/headlines.json \
    --out path/to/slides/ \
    [--logo path/to/logo.png] \
    [--api-key GEMINI_KEY]
"""

import argparse
import base64
import json
import os
import sys
import time
import requests
from datetime import datetime
from pathlib import Path

# ── Brand palette (referenced verbatim in prompts) ─────────────────────────────
CLOUD_WHITE   = "#F7F2EC"
SIGNAL_ORANGE = "#F3701E"
LAUNCH_BLUE   = "#4B607F"
INK           = "#1A2838"

MODEL = "models/gemini-3.1-flash-image-preview"
API_URL = "https://generativelanguage.googleapis.com/v1beta/{model}:generateContent"


def build_intro_prompt(date_str: str, logo_b64: str | None) -> list:
    """Return the parts list for the intro slide request."""
    parts = []

    logo_instruction = (
        "Reproduce the attached LaunchBox logo EXACTLY as provided — rocket-in-a-box icon on the left, "
        "'LaunchBox' wordmark on the right in its original orange/gradient colours. Do NOT redraw, recolour, or substitute text."
        if logo_b64 else
        "Write 'LaunchBox' in bold {SIGNAL_ORANGE} as a placeholder (no logo image provided)."
    )

    parts.append({"text": f"""Create a square (1:1) social media carousel slide — editorial magazine style.

BACKGROUND: solid {CLOUD_WHITE} (warm off-white, hex {CLOUD_WHITE})

LAYOUT (top to bottom, left-aligned text, generous padding ~80px each side):
1. "TODAY'S AI LUNCH BREAK" — extra-bold condensed all-caps, very large (fills ~40% of slide height), {SIGNAL_ORANGE}, top-left, NO rule above it
2. "{date_str}" — medium weight, {INK}, directly below the headline, same left margin
3. Single thin horizontal rule in {LAUNCH_BLUE} below the date, full width
4. Generous white space
5. "Presented by:" — bold, centered, {INK}
6. {logo_instruction} — centered, large, ~50% slide width
7. Single thin horizontal rule in {LAUNCH_BLUE} near bottom

STYLE: premium editorial sans-serif (condensed bold). Clean white space. No decorative elements beyond the two horizontal rules. No watermarks. No slide number.
OUTPUT: square PNG, 1200×1200 px."""})

    # Attach logo image if available
    if logo_b64:
        parts.append({
            "inline_data": {
                "mime_type": "image/png",
                "data": logo_b64,
            }
        })

    return parts


def build_story_prompt(rank: int, total: int, headline: str, summary: str, motif: str) -> list:
    return [{"text": f"""Create a square (1:1) social media carousel slide — editorial magazine style.

BACKGROUND: solid {CLOUD_WHITE} (warm off-white)
LAYOUT:
• Top: thin horizontal rule in {SIGNAL_ORANGE} (6 px)
• Top-right corner: slide number "{rank}/{total}" — small, bold, {LAUNCH_BLUE}
• Headline: "{headline}" — bold all-caps, large, {SIGNAL_ORANGE}. Max 2 lines.
• Thin separator rule in {LAUNCH_BLUE}
• Body: "{summary}" — regular weight, {INK}, 18-24pt equivalent
• Centre area: tasteful visual motif — {motif}. Subtle, not distracting.
• Bottom-left: "https://launchbox.space" — small, {LAUNCH_BLUE}
• Bottom: thin horizontal rule in {LAUNCH_BLUE}

STYLE: bold editorial sans-serif. Clean. Premium. No clip-art. No gradients. No shadows.
OUTPUT: square PNG, 1200×1200 px."""}]


def call_gemini(api_key: str, parts: list, retries: int = 3) -> bytes:
    """Call Gemini image generation; return raw PNG bytes."""
    url = API_URL.format(model=MODEL) + f"?key={api_key}"
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
    }
    for attempt in range(1, retries + 1):
        try:
            r = requests.post(url, json=payload, timeout=90)
            r.raise_for_status()
            data = r.json()

            # Extract image from response
            for candidate in data.get("candidates", []):
                for part in candidate.get("content", {}).get("parts", []):
                    if "inlineData" in part:
                        raw = base64.b64decode(part["inlineData"]["data"])
                        return raw
                    if "image_url" in part:
                        # data URL fallback
                        url_data = part["image_url"].get("url", "")
                        if "," in url_data:
                            raw = base64.b64decode(url_data.split(",", 1)[1])
                            return raw

            print(f"  [WARN] No image in response: {json.dumps(data)[:300]}", file=sys.stderr)
            return None

        except requests.HTTPError as e:
            print(f"  [WARN] Attempt {attempt}: HTTP {e.response.status_code} — {e.response.text[:200]}", file=sys.stderr)
            if attempt < retries:
                time.sleep(2 ** attempt)
        except Exception as e:
            print(f"  [WARN] Attempt {attempt}: {e}", file=sys.stderr)
            if attempt < retries:
                time.sleep(2 ** attempt)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date",      required=True)
    ap.add_argument("--headlines", required=True)
    ap.add_argument("--out",       required=True)
    ap.add_argument("--logo",      default=None)
    ap.add_argument("--api-key",   default=None)
    args = ap.parse_args()

    # Load API key
    api_key = args.api_key
    if not api_key:
        cfg_path = Path(__file__).parent.parent / "config.json"
        if cfg_path.exists():
            api_key = json.loads(cfg_path.read_text()).get("gemini_api_key")
    if not api_key:
        print("[ERROR] No Gemini API key. Pass --api-key or set in config.json", file=sys.stderr)
        sys.exit(1)

    with open(args.headlines) as f:
        data = json.load(f)

    os.makedirs(args.out, exist_ok=True)

    # Format date nicely
    try:
        dt = datetime.strptime(args.date, "%Y-%m-%d")
        date_display = dt.strftime("%B %-d, %Y")
    except Exception:
        date_display = args.date

    # Load logo if available
    logo_b64 = None
    if args.logo and os.path.exists(args.logo):
        with open(args.logo, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
        print(f"[OK] Logo loaded: {args.logo}", file=sys.stderr)
    else:
        print("[INFO] No logo file found — intro slide will omit logo image", file=sys.stderr)

    # Slide 1 — intro
    print("Generating slide_1 (intro)…", file=sys.stderr)
    parts = build_intro_prompt(date_display, logo_b64)
    img = call_gemini(api_key, parts)
    if img:
        out_path = os.path.join(args.out, "slide_1.png")
        with open(out_path, "wb") as f:
            f.write(img)
        print(f"[OK] slide_1.png  ({len(img)//1024}KB)", file=sys.stderr)
    else:
        print("[FAIL] slide_1 — skipping", file=sys.stderr)

    # Slides 2-6 — stories
    stories = data["stories"]
    total = len(stories)
    for i, story in enumerate(stories, start=1):
        slide_num = i + 1
        print(f"Generating slide_{slide_num} (story {i}/{total}: {story['headline']})…", file=sys.stderr)
        parts = build_story_prompt(
            rank    = i,
            total   = total,
            headline= story["headline"],
            summary = story["summary"],
            motif   = story.get("visual_motif", "abstract tech shapes"),
        )
        img = call_gemini(api_key, parts)
        if img:
            out_path = os.path.join(args.out, f"slide_{slide_num}.png")
            with open(out_path, "wb") as f:
                f.write(img)
            print(f"[OK] slide_{slide_num}.png  ({len(img)//1024}KB)", file=sys.stderr)
        else:
            print(f"[FAIL] slide_{slide_num} — skipping", file=sys.stderr)
        time.sleep(1)  # brief pause between calls

    print(f"\nDone. Slides written to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
