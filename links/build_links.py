#!/usr/bin/env python3
"""Build click-through badges and images for a GitHub profile README.

When a README image is not wrapped in a link, GitHub makes it open the image
file itself in a new tab. Each SVG built here uses that:

  * inside the README it looks exactly like your badge or screenshot;
  * opened in the new tab, it becomes a "Continue to ..." page whose button
    goes to the destination in that same tab, while GitHub stays open.

Usage (needs internet access for the badges):

    python3 build_links.py               # badges + screenshots
    python3 build_links.py --images-only # screenshots only (used by the Action)

It writes links/<name>.svg and prints the README markup to paste.
No third-party packages are needed.
"""

import base64
import html
import re
import struct
import subprocess
import sys
import urllib.request
from pathlib import Path
from string import Template

REPO = "AmjadKudsi/AmjadKudsi"
BRANCH = "main"
FOLDER = "links"
NOTE = "Your GitHub tab is still open."

# The repo root: works whether this file sits in the root or in links/.
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent if HERE.name == FOLDER else HERE

SOCIALS = [
    {
        "file": "portfolio",
        "alt": "Portfolio",
        "badge": "https://img.shields.io/badge/Portfolio-2563EB?logo=data:image/svg%2Bxml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxNiAxNiI%2BPGcgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjZmZmIiBzdHJva2Utd2lkdGg9IjEuNiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cmVjdCB4PSIxLjUiIHk9IjQuOCIgd2lkdGg9IjEzIiBoZWlnaHQ9IjkuNSIgcng9IjEuNSIvPjxwYXRoIGQ9Ik01LjMgNC44VjNhMSAxIDAgMCAxIDEtMWgzLjRhMSAxIDAgMCAxIDEgMXYxLjhNMS41IDguNXE2LjUgNC4yIDEzIDAiLz48L2c%2BPC9zdmc%2B",
        "url": "https://amjadkudsi.com/",
        "title": "Amjad Kudsi — Portfolio",
        "button": "Continue to portfolio",
    },
    {
        "file": "linkedin",
        "alt": "LinkedIn",
        "badge": "https://img.shields.io/badge/LinkedIn-0077B5?logo=data:image/svg%2Bxml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxNiAxNiI%2BPHBhdGggZmlsbD0iI2ZmZiIgZD0iTTAgMS4xNDZDMCAuNTEzLjUyNiAwIDEuMTc1IDBoMTMuNjVDMTUuNDc0IDAgMTYgLjUxMyAxNiAxLjE0NnYxMy43MDhjMCAuNjMzLS41MjYgMS4xNDYtMS4xNzUgMS4xNDZIMS4xNzVDLjUyNiAxNiAwIDE1LjQ4NyAwIDE0Ljg1NFYxLjE0NnptNC45NDMgMTIuMjQ4VjYuMTY5SDIuNTQydjcuMjI1aDIuNDAxem0tMS4yLTguMjEyYy44MzcgMCAxLjM1OC0uNTU0IDEuMzU4LTEuMjQ4LS4wMTUtLjcwOS0uNTItMS4yNDgtMS4zNDItMS4yNDgtLjgyMiAwLTEuMzU5LjU0LTEuMzU5IDEuMjQ4IDAgLjY5NC41MjEgMS4yNDggMS4zMjcgMS4yNDhoLjAxNnptNC45MDggOC4yMTJWOS4zNTljMC0uMjE2LjAxNi0uNDMyLjA4LS41ODYuMTczLS40MzEuNTY4LS44NzggMS4yMzItLjg3OC44NjkgMCAxLjIxNi42NjIgMS4yMTYgMS42MzR2My44NjVoMi40MDFWOS4yNWMwLTIuMjItMS4xODQtMy4yNTItMi43NjQtMy4yNTItMS4yNzQgMC0xLjg0NS43LTIuMTY1IDEuMTkzdi4wMjVoLS4wMTZhNS41NCA1LjU0IDAgMCAxIC4wMTYtLjAyNVY2LjE2OWgtMi40Yy4wMy42NzggMCA3LjIyNSAwIDcuMjI1aDIuNHoiLz48L3N2Zz4%3D",
        "url": "https://linkedin.com/in/amjadkudsi",
        "title": "Amjad Kudsi on LinkedIn",
        "button": "Continue to LinkedIn",
    },
    {
        "file": "medium",
        "alt": "Medium",
        "badge": "https://img.shields.io/badge/Medium-12100E?logo=medium&logoColor=white",
        "url": "https://medium.com/@amjadkudsi",
        "title": "Amjad Kudsi on Medium",
        "button": "Continue to Medium",
    },
    {
        "file": "x",
        "alt": "X",
        "badge": "https://img.shields.io/badge/X-000000?logo=x&logoColor=white",
        "url": "https://x.com/amjadkudsi",
        "title": "Amjad Kudsi on X",
        "button": "Continue to X",
    },
    {
        "file": "youtube",
        "alt": "YouTube",
        "badge": "https://img.shields.io/badge/YouTube-FF0000?logo=youtube&logoColor=white",
        "url": "https://www.youtube.com/@thelumenodyssey",
        "title": "The Lumen Odyssey on YouTube",
        "button": "Continue to YouTube",
    },
]

# Screenshots kept in the repo root. Replace the PNG as usual; rebuild after.
IMAGES = [
    {
        "file": "tools",
        "image": "techstack.png",
        "alt": "Tools I use, from my CodeSignal profile",
        "url": "https://codesignal.com/learn/profile/cmahs9glz000kim04b674tjcu#:~:text=August%2021%2C%202025-,Tools,-Amazon%20Bedrock%20Models",
        "shown": "codesignal.com/learn/profile",
        "label": "TOOLS",
        "title": "Amjad Kudsi on CodeSignal",
        "button": "Continue to CodeSignal",
    },
    {
        "file": "kaggle-writeup",
        "image": "kaggle_writeup.png",
        "alt": "StatGuard Agent: hackathon writeup on Kaggle",
        "url": "https://www.kaggle.com/competitions/agents-intensive-capstone-project/writeups/statguard-agent",
        "shown": "kaggle.com/…/writeups/statguard-agent",
        "label": "HACKATHON WRITEUP",
        "title": "StatGuard Agent on Kaggle",
        "button": "Continue to Kaggle",
    },
]

FONT = '-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",Helvetica,Arial,sans-serif'
MONO = 'ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace'

# One page for everything: what the README shows ($readme_view), and a
# GitHub-style card shown instead when "$card_when" matches, i.e. when the
# file is open in its own tab. Plain SVG + CSS, so it works under GitHub's
# image servers, which block scripts and outside files but allow styles and links.
PAGE = Template("""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"$root_size>
<title>$tab</title>
<style>
.lp-page{display:none}
@media $card_when{.lp-readme{display:none}.lp-page{display:inline}:root{width:100%;height:100%}}
.lp-bg{fill:#f6f8fa}
.lp-card{fill:#fff;stroke:#d1d9e0}
.lp-over{fill:#59636e;font-family:$font;font-size:12px;font-weight:600;letter-spacing:.06em}
.lp-title{fill:#1f2328;font-family:$font;font-size:20px;font-weight:600}
.lp-url{fill:#59636e;font-family:$mono;font-size:13px}
.lp-icon{fill:none;stroke:#59636e;stroke-width:1.4;stroke-linecap:round;stroke-linejoin:round}
.lp-btn{fill:#1f2328;transition:fill .15s ease}
.lp-btn-text{fill:#fff;font-family:$font;font-size:14px;font-weight:600}
.lp-note{fill:#59636e;font-family:$font;font-size:12px}
.lp-link{cursor:pointer;outline:none;-webkit-tap-highlight-color:transparent}
.lp-link:hover .lp-btn{fill:#393f46}
.lp-link:focus-visible .lp-card{stroke:#0969da;stroke-width:2}
.lp-enter{animation:lp-in .32s cubic-bezier(.2,.7,.2,1) both}
@keyframes lp-in{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
@media (max-width:460px){.lp-fit{transform:scale(.9)}}
@media (max-width:400px){.lp-fit{transform:scale(.84)}}
@media (max-width:360px){.lp-fit{transform:scale(.78)}}
@media (max-width:330px),(max-height:300px){.lp-fit{transform:scale(.72)}}
@media (max-device-width:500px) and (min-width:700px) and (orientation:portrait){.lp-fit{transform:scale(2.2)}}
@media (prefers-color-scheme:dark){
.lp-bg{fill:#010409}
.lp-card{fill:#0d1117;stroke:#3d444d;filter:none}
.lp-title{fill:#f0f6fc}
.lp-over,.lp-url,.lp-note{fill:#9198a1}
.lp-icon{stroke:#9198a1}
.lp-btn{fill:#f0f6fc}
.lp-btn-text{fill:#0d1117}
.lp-link:hover .lp-btn{fill:#d1d9e0}
.lp-link:focus-visible .lp-card{stroke:#4493f8}
}
@media (prefers-reduced-motion:reduce){.lp-enter{animation:none}}
</style>
<defs>$defs
<filter id="lp-lift" x="-20%" y="-20%" width="140%" height="160%">
<feGaussianBlur in="SourceAlpha" stdDeviation="12"/>
<feOffset dy="8" result="blur"/>
<feFlood flood-color="#1f2328" flood-opacity=".09"/>
<feComposite in2="blur" operator="in"/>
<feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
</defs>
$readme_view
<g class="lp-page">
<rect class="lp-bg" width="100%" height="100%"/>
<svg x="50%" y="50%" overflow="visible">
<g class="lp-fit"><g class="lp-enter">
<a class="lp-link" href="$url" xlink:href="$url" aria-label="$button: $shown">
<g transform="translate(-200 -$half)">
<rect class="lp-card" x=".5" y=".5" width="399" height="$card" rx="12" filter="url(#lp-lift)"/>
$header
<text class="lp-title" x="28" y="$y_title">$title</text>
<path class="lp-icon" transform="translate(28 $y_icon)" d="M5 1.5H2.5a1 1 0 0 0-1 1v7a1 1 0 0 0 1 1h7a1 1 0 0 0 1-1V7M7.5 1.5h3v3M10.5 1.5 5.5 6.5"/>
<text class="lp-url" x="47" y="$y_url">$shown</text>
<rect class="lp-btn" x="28" y="$y_btn" width="344" height="40" rx="6"/>
<text class="lp-btn-text" x="200" y="$y_btn_text" text-anchor="middle">$button</text>
<text class="lp-note" x="200" y="$y_note" text-anchor="middle">$note</text>
</g>
</a>
</g></g>
</svg>
</g>
</svg>
""")


def fetch(url):
    """Download a badge; fall back to curl if Python lacks SSL certificates."""
    request = urllib.request.Request(url, headers={"User-Agent": "build_links.py"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8")
    except Exception as error:
        result = subprocess.run(["curl", "-fsSL", url], capture_output=True, text=True)
        if result.returncode != 0:
            raise SystemExit(f"Could not download {url}\n{error}")
        return result.stdout


def attrs_of(tag_text):
    return dict(re.findall(r'([\w:.-]+)="([^"]*)"', tag_text))


def inline_logo(match):
    """Turn <image href="data:image/svg+xml;base64,..."> into a nested <svg>.

    The new-tab page may be served with a policy that blocks data: images,
    so the logo is written straight into the file instead.
    """
    tag = match.group(0)
    data = re.search(r'href="data:image/svg\+xml;base64,([^"]+)"', tag)
    if not data:
        return tag
    try:
        logo = base64.b64decode(data.group(1)).decode("utf-8")
    except Exception:
        return tag
    root = re.search(r"<svg\b([^>]*)>(.*)</svg>", logo, re.S)
    if not root:
        return tag
    logo_attrs = attrs_of(root.group(1))
    if "viewBox" not in logo_attrs and "width" in logo_attrs and "height" in logo_attrs:
        w = re.sub(r"[^\d.]", "", logo_attrs["width"])
        h = re.sub(r"[^\d.]", "", logo_attrs["height"])
        logo_attrs["viewBox"] = f"0 0 {w} {h}"
    keep = {k: v for k, v in logo_attrs.items()
            if not k.startswith("xmlns") and k not in ("width", "height", "x", "y", "role")}
    keep.update({k: v for k, v in attrs_of(tag).items() if k in ("x", "y", "width", "height")})
    body = re.sub(r"<title>.*?</title>", "", root.group(2), flags=re.S)
    return "<svg " + " ".join(f'{k}="{v}"' for k, v in keep.items()) + ">" + body + "</svg>"


def parse_badge(svg):
    match = re.search(r"<svg\b([^>]*)>(.*)</svg>\s*\Z", svg.strip(), re.S)
    if not match:
        raise ValueError("Not an SVG badge")
    root, inner = match.groups()
    width = float(re.search(r'\swidth="([\d.]+)"', root).group(1))
    height = float(re.search(r'\sheight="([\d.]+)"', root).group(1))
    inner = re.sub(r"<title>.*?</title>", "", inner, flags=re.S)
    inner = re.sub(r"<image\b[^>]*?(?:/>|>\s*</image>)", inline_logo, inner)
    # Prefix ids so the badge can never clash with the page's own ids.
    for old in set(re.findall(r'\sid="([^"]+)"', inner)):
        new = "b-" + old
        inner = re.sub(rf'(\s)id="{re.escape(old)}"', rf'\1id="{new}"', inner)
        inner = inner.replace(f"url(#{old})", f"url(#{new})")
        inner = re.sub(rf'href="#{re.escape(old)}"', f'href="#{new}"', inner)
    return width, height, inner


def png_size(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit("Screenshots must be PNG files")
    return struct.unpack(">II", data[16:24])


def number(value):
    return f"{value:g}"


def render(item, *, root_size, card_when, readme_view, defs, header, header_height):
    shown = item.get("shown") or re.sub(r"^https?://(www\.)?", "", item["url"]).split("#")[0].rstrip("/")
    y_title = 28 + header_height + 38
    y_url = y_title + 24
    y_btn = y_url + 24
    y_note = y_btn + 40 + 26
    card = y_note + 22
    return PAGE.substitute(
        root_size=root_size, card_when=card_when, readme_view=readme_view,
        defs=defs, header=header, font=FONT, mono=MONO,
        tab=html.escape(item["title"]),
        title=html.escape(item["title"]),
        button=html.escape(item["button"]),
        note=html.escape(NOTE),
        shown=html.escape(shown),
        url=html.escape(item["url"]),
        half=number(card / 2),
        card=number(card - 1),
        y_title=number(y_title),
        y_icon=number(y_url - 11),
        y_url=number(y_url),
        y_btn=number(y_btn),
        y_btn_text=number(y_btn + 25),
        y_note=number(y_note),
    )


def make_page(social, badge_svg):
    """A badge: README size comes from the <img> tag; any tall view is the tab."""
    width, height, badge = parse_badge(badge_svg)
    svg = render(
        social,
        root_size="",
        card_when="(min-height:120px)",
        readme_view='<use class="lp-readme" href="#lp-badge" xlink:href="#lp-badge" width="100%" height="100%"/>',
        defs=f'\n<symbol id="lp-badge" viewBox="0 0 {number(width)} {number(height)}">{badge}</symbol>',
        header=f'<use href="#lp-badge" xlink:href="#lp-badge" x="28" y="28" '
               f'width="{number(width)}" height="{number(height)}"/>',
        header_height=height,
    )
    return svg, width, height


def make_image_page(item, png):
    """A screenshot: the README always shows it at its own shape, so a view
    that is clearly narrower than that shape, or taller than the picture
    itself, can only be the tab."""
    width, height = png_size(png)
    ratio = width / height
    if ratio < 2:
        print(f"  note: {item['image']} is getting tall; the card may not show in very wide windows")
    threshold = max(int(ratio * 0.9 * 100), 1)
    encoded = base64.b64encode(png).decode("ascii")
    return render(
        item,
        root_size=f' width="{width}" height="{height}"',
        card_when=f"(max-aspect-ratio:{threshold}/100),(min-height:{height + 1}px)",
        readme_view=f'<image class="lp-readme" width="100%" height="100%" preserveAspectRatio="none" '
                    f'href="data:image/png;base64,{encoded}"/>',
        defs="",
        header=f'<text class="lp-over" x="28" y="42">{html.escape(item["label"])}</text>',
        header_height=20,
    )


def raw_url(name):
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{FOLDER}/{name}.svg"


def main():
    images_only = "--images-only" in sys.argv[1:]
    out = ROOT / FOLDER
    out.mkdir(exist_ok=True)

    if not images_only:
        sizes = {}
        for social in SOCIALS:
            svg, width, height = make_page(social, fetch(social["badge"]))
            (out / f"{social['file']}.svg").write_text(svg, encoding="utf-8")
            sizes[social["file"]] = (width, height)
            print(f"  wrote {FOLDER}/{social['file']}.svg")

    for item in IMAGES:
        source = ROOT / item["image"]
        if not source.exists():
            print(f"  skipped {item['image']} (not found next to README.md)")
            continue
        (out / f"{item['file']}.svg").write_text(make_image_page(item, source.read_bytes()), encoding="utf-8")
        print(f"  wrote {FOLDER}/{item['file']}.svg from {item['image']}")

    if images_only:
        return
    print("\nIn README.md, the five Socials badge lines become:\n")
    print('<p align="center">')
    for social in SOCIALS:
        width, height = sizes[social["file"]]
        print(f'  <img alt="{social["alt"]}" src="{raw_url(social["file"])}" '
              f'width="{number(width)}" height="{number(height)}">')
    print("</p>")
    print("\nand the two screenshot lines become:\n")
    print('<p align="center">')
    for item in IMAGES:
        print(f'  <img alt="{item["alt"]}" src="{raw_url(item["file"])}">')
    print("</p>")


if __name__ == "__main__":
    main()
