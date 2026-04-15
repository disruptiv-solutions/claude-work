#!/usr/bin/env python3
"""
LaunchBox Daily Carousel — Slide Generator
Generates 6 square PNG slides using Pillow with brand colours.
"""

import json
import os
import sys
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ── Brand Palette ──────────────────────────────────────────────────────────────
CLOUD_WHITE  = "#F7F2EC"
SIGNAL_ORANGE = "#F3701E"
LAUNCH_BLUE  = "#4B607F"
INK          = "#1A2838"

# ── Canvas ─────────────────────────────────────────────────────────────────────
SIZE = (1200, 1200)
PAD  = 72   # outer margin

# ── Font paths ──────────────────────────────────────────────────────────────
FONT_BOLD    = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def draw_rule(draw, y, color, thickness=3):
    draw.rectangle([(PAD, y), (SIZE[0] - PAD, y + thickness)], fill=hex2rgb(color))

def draw_wrapped_text(draw, text, font, color, x, y, max_width, line_spacing=1.25):
    """Draw text with word-wrap. Returns the y position after the last line."""
    rgb = hex2rgb(color)
    words = text.split()
    lines = []
    current = []
    for word in words:
        test = " ".join(current + [word])
        bbox = font.getbbox(test)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))

    line_h = int((font.getbbox("Ag")[3] - font.getbbox("Ag")[1]) * line_spacing)
    cur_y = y
    for line in lines:
        draw.text((x, cur_y), line, font=font, fill=rgb)
        cur_y += line_h
    return cur_y

def make_intro_slide(out_path, date_str, logo_path=None):
    img  = Image.new("RGB", SIZE, hex2rgb(CLOUD_WHITE))
    draw = ImageDraw.Draw(img)

    # Top rule
    draw_rule(draw, PAD, LAUNCH_BLUE, thickness=5)

    # "TODAY'S TOP AI STORIES" — big orange headline
    f_headline = load_font(FONT_BOLD, 100)
    lines_hl = ["TODAY'S TOP", "AI STORIES"]
    y = 180
    for line in lines_hl:
        draw.text((PAD, y), line, font=f_headline, fill=hex2rgb(SIGNAL_ORANGE))
        bbox = f_headline.getbbox(line)
        y += int((bbox[3] - bbox[1]) * 1.15)

    # Thin separator rule
    draw_rule(draw, y + 20, LAUNCH_BLUE)
    y += 60

    # Date line
    f_date = load_font(FONT_REGULAR, 52)
    draw.text((PAD, y), date_str, font=f_date, fill=hex2rgb(INK))
    y += 80

    # "Presented by:" label
    f_label = load_font(FONT_REGULAR, 40)
    draw.text((PAD, y + 20), "Presented by:", font=f_label, fill=hex2rgb(INK))
    y += 80

    # Logo area
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            # Scale to fit width keeping 4:1 aspect
            target_w = SIZE[0] - PAD * 2
            ratio = target_w / logo.width
            target_h = int(logo.height * ratio)
            logo = logo.resize((target_w, target_h), Image.LANCZOS)
            img.paste(logo, (PAD, y + 10), logo)
            y += target_h + 30
        except Exception as e:
            print(f"[WARN] Could not load logo: {e}", file=sys.stderr)
            _draw_logo_text(draw, y)
    else:
        _draw_logo_text(draw, y)

    # Bottom rule
    draw_rule(draw, SIZE[1] - PAD - 5, LAUNCH_BLUE, thickness=5)

    img.save(out_path, "PNG")
    print(f"[OK] {out_path}")

def _draw_logo_text(draw, y):
    """Fallback: render LAUNCHBOX in brand style when no logo file is available."""
    f_logo = load_font(FONT_BOLD, 110)
    draw.text((PAD, y), "LAUNCHBOX", font=f_logo, fill=hex2rgb(LAUNCH_BLUE))

def make_story_slide(out_path, rank, total, headline, summary, motif):
    img  = Image.new("RGB", SIZE, hex2rgb(CLOUD_WHITE))
    draw = ImageDraw.Draw(img)

    # Top rule
    draw_rule(draw, PAD, SIGNAL_ORANGE, thickness=6)

    # Rank badge top-right
    f_rank = load_font(FONT_BOLD, 42)
    badge = f"{rank}/{total}"
    bbox  = f_rank.getbbox(badge)
    bw    = bbox[2] - bbox[0]
    draw.text((SIZE[0] - PAD - bw, PAD - 50), badge, font=f_rank, fill=hex2rgb(LAUNCH_BLUE))

    # Headline (Signal Orange, bold, large)
    f_hl = load_font(FONT_BOLD, 90)
    max_w = SIZE[0] - PAD * 2
    y = PAD + 60
    y = draw_wrapped_text(draw, headline, f_hl, SIGNAL_ORANGE, PAD, y, max_w, line_spacing=1.2)
    y += 30

    # Separator rule
    draw_rule(draw, y, LAUNCH_BLUE)
    y += 40

    # Summary (Ink, regular)
    f_sum = load_font(FONT_REGULAR, 52)
    y = draw_wrapped_text(draw, summary, f_sum, INK, PAD, y, max_w, line_spacing=1.4)
    y += 60

    # Visual motif (small, italic-style — Launch Blue)
    if motif:
        f_motif = load_font(FONT_REGULAR, 36)
        draw.text((PAD, y), f"Visual: {motif}", font=f_motif, fill=hex2rgb(LAUNCH_BLUE))

    # Bottom rule
    draw_rule(draw, SIZE[1] - PAD - 40, LAUNCH_BLUE, thickness=3)

    # URL — bottom left, small, Launch Blue
    f_url = load_font(FONT_REGULAR, 32)
    draw.text((PAD, SIZE[1] - PAD), "https://launchbox.space",
              font=f_url, fill=hex2rgb(LAUNCH_BLUE))

    img.save(out_path, "PNG")
    print(f"[OK] {out_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date",      required=True)
    parser.add_argument("--headlines", required=True)
    parser.add_argument("--out",       required=True)
    parser.add_argument("--logo",      default=None)
    args = parser.parse_args()

    with open(args.headlines) as f:
        data = json.load(f)

    os.makedirs(args.out, exist_ok=True)

    # Slide 1 — intro
    date_label = args.date  # e.g. "2026-04-15"
    from datetime import datetime
    try:
        dt = datetime.strptime(date_label, "%Y-%m-%d")
        date_display = dt.strftime("%B %-d, %Y")
    except Exception:
        date_display = date_label

    make_intro_slide(
        out_path  = os.path.join(args.out, "slide_1.png"),
        date_str  = date_display,
        logo_path = args.logo,
    )

    # Slides 2-6 — stories
    stories = data["stories"]
    total   = len(stories)
    for i, story in enumerate(stories, start=1):
        make_story_slide(
            out_path = os.path.join(args.out, f"slide_{i+1}.png"),
            rank     = i,
            total    = total,
            headline = story["headline"],
            summary  = story["summary"],
            motif    = story.get("visual_motif", ""),
        )

    print(f"\nAll {total + 1} slides written to {args.out}")

if __name__ == "__main__":
    main()
