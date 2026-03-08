#!/usr/bin/env python3
"""Real Life Pokédex — point it at any image and get a Pokédex entry."""

import argparse
import base64
import sys
import urllib.request
from pathlib import Path

import anthropic

SYSTEM_PROMPT = """You are the Pokédex — a high-tech encyclopaedia that analyses real-world creatures, plants, objects, and phenomena and presents them as if they were Pokémon.

When given an image, produce a structured Pokédex entry using EXACTLY this format (fill every field):

═══════════════════════════════════════════
#XXX  <SPECIES NAME> (real name in parentheses)
═══════════════════════════════════════════
Type      : <TYPE 1> / <TYPE 2 or leave blank>
Category  : The <ADJECTIVE> Pokémon
Height    : <estimated height>
Weight    : <estimated weight>

POKÉDEX ENTRY
─────────────
<Two or three evocative flavour-text sentences written in classic Pokédex style.
Mention one surprising or poetic fact about the subject.>

ABILITIES
─────────
• <Ability 1 name>: <one-line description>
• <Ability 2 name>: <one-line description>
• Hidden Ability — <Ability name>: <one-line description>

BASE STATS
──────────
HP        ░░░░░░░░░░  <value>/255
Attack    ░░░░░░░░░░  <value>/255
Defense   ░░░░░░░░░░  <value>/255
Sp. Atk   ░░░░░░░░░░  <value>/255
Sp. Def   ░░░░░░░░░░  <value>/255
Speed     ░░░░░░░░░░  <value>/255
─────────────────────────────────
Total                 <sum>/1530
═══════════════════════════════════════════

Rules:
- Choose a creative, Latin-sounding Pokémon name that hints at the subject's nature.
- Pick types that fit thematically (e.g. a cactus → Grass/Poison, a fire truck → Fire/Steel).
- Stats should reflect the subject's real-world characteristics (a tortoise has high Defense but low Speed).
- Fill the stat bars with filled blocks (█) proportional to the value out of 255. Each bar is 10 characters wide.
- Keep flavour text poetic and concise — two to three sentences max.
- If you cannot identify the subject clearly, describe what you see and still produce a full entry."""


def load_image_as_base64(path_or_url: str) -> tuple[str, str]:
    """Return (base64_data, media_type) for a local file or URL."""
    path = Path(path_or_url)

    ext_to_mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }

    if path.exists():
        suffix = path.suffix.lower()
        media_type = ext_to_mime.get(suffix, "image/jpeg")
        data = base64.standard_b64encode(path.read_bytes()).decode()
        return data, media_type

    # Treat as URL — download and base64-encode
    if path_or_url.startswith(("http://", "https://")):
        req = urllib.request.Request(
            path_or_url,
            headers={"User-Agent": "Mozilla/5.0 (Real-Life-Pokedex/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            content_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
        data = base64.standard_b64encode(raw).decode()
        return data, content_type

    sys.exit(f"Error: '{path_or_url}' is not a valid file path or URL.")


def stat_bar(value: int, width: int = 10) -> str:
    filled = round(value / 255 * width)
    return "█" * filled + "░" * (width - filled)


def render_entry(raw_text: str) -> str:
    """Post-process the raw Claude output to fill stat bars properly.

    Claude may emit placeholder bars; we scan for lines containing a stat
    name + numeric value and redraw the bar. Everything else is passed through.
    """
    stat_names = {"HP", "Attack", "Defense", "Sp. Atk", "Sp. Def", "Speed"}
    lines = raw_text.splitlines()
    out = []
    for line in lines:
        replaced = False
        for stat in stat_names:
            if line.strip().startswith(stat):
                # Try to find the value (last integer on the line before /255)
                parts = line.replace("/255", "").split()
                for part in reversed(parts):
                    if part.isdigit():
                        val = min(int(part), 255)
                        label = f"{stat:<9}"
                        out.append(f"{label} {stat_bar(val)}  {val}/255")
                        replaced = True
                        break
        if not replaced:
            out.append(line)
    return "\n".join(out)


def scan(image_source: str, stream: bool = True) -> None:
    client = anthropic.Anthropic()

    # Decide between URL source and base64
    if image_source.startswith(("http://", "https://")):
        image_block = {
            "type": "image",
            "source": {"type": "url", "url": image_source},
        }
    else:
        b64_data, media_type = load_image_as_base64(image_source)
        image_block = {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": b64_data},
        }

    messages = [
        {
            "role": "user",
            "content": [
                image_block,
                {"type": "text", "text": "Scan this and produce a full Pokédex entry."},
            ],
        }
    ]

    print("\n🔴 Pokédex scanning...\n")

    if stream:
        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
        ) as s:
            chunks = []
            for text in s.text_stream:
                print(text, end="", flush=True)
                chunks.append(text)
            print()  # newline after stream ends
    else:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        print(render_entry(response.content[0].text))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pokedex",
        description="Real Life Pokédex — scan any image and get a Pokédex entry.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python pokedex.py photo.jpg
  python pokedex.py https://upload.wikimedia.org/wikipedia/commons/.../Lion.jpg
  python pokedex.py cat.png --no-stream
""",
    )
    parser.add_argument(
        "image",
        help="Path to a local image file or a public image URL.",
    )
    parser.add_argument(
        "--no-stream",
        dest="stream",
        action="store_false",
        default=True,
        help="Disable streaming output (wait for full response before printing).",
    )

    args = parser.parse_args()
    scan(args.image, stream=args.stream)


if __name__ == "__main__":
    main()
