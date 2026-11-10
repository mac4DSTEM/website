#!/usr/bin/env python3
"""Build the documentation pages in docs/ from the page bodies in tools/docs/.

    python3 tools/build_docs.py           # write docs/
    python3 tools/build_docs.py --check   # exit 1 if docs/ is not what the sources give (CI)

Each page is a body fragment, tools/docs/<source>.html, wrapped in the site's header, the documentation sidebar and
the footer. PAGES below is the sidebar: its order, its groups and each page's title and description. APP_VERSION is
the mac4DSTEM version the pages were written for; move it when the pages have been read against a new version.
Standard library only.
"""
import argparse, html, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tools" / "docs"
APP_VERSION = "5.2"

# (group, source file stem, output path under docs/, title, description)
PAGES = [
    ("", "index", "index.html", "Documentation",
     "How to install mac4DSTEM, open 4D-STEM data and work through an analysis, step by step."),
    ("Get started", "install", "install.html", "Install",
     "Install mac4DSTEM on an Apple silicon Mac: requirements, download, updating and removing it."),
    ("Get started", "open-data", "open-data.html", "Open your data",
     "The 4D-STEM file formats mac4DSTEM reads, opening large datasets with a crop or binning, the window, and saved sessions."),
    ("Tutorials", "virtual-imaging", "tutorials/virtual-imaging.html", "Virtual imaging",
     "Tutorial: bright-field and dark-field virtual images from a 4D-STEM scan, and diffraction from a scan region."),
    ("Tutorials", "calibration", "tutorials/calibration.html", "Calibration",
     "Tutorial: calibrate a 4D-STEM dataset in mac4DSTEM: origin, elliptical distortion, rotation and pixel sizes."),
    ("Tutorials", "bragg-disks", "tutorials/bragg-disks.html", "Bragg disks",
     "Tutorial: detect Bragg disks in every diffraction pattern of a 4D-STEM scan and judge the detection."),
    ("Help", "troubleshooting", "troubleshooting.html", "Troubleshooting",
     "Answers to common problems in mac4DSTEM: files that do not open, large datasets, calibration and disk detection."),
]

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>{title} — mac4DSTEM documentation</title>
<meta name="description" content="{description}">
<link rel="canonical" href="https://mac4dstem.com/docs/{canonical}">
<meta name="color-scheme" content="light dark">
<meta name="robots" content="index, follow">

<link rel="icon" href="/assets/favicon.ico" sizes="any">
<link rel="icon" href="/assets/icon-512.png" type="image/png" sizes="512x512">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">

<link rel="stylesheet" href="/assets/site.css">
<link rel="stylesheet" href="/assets/docs.css">
</head>

<body>
<a class="skip" href="#main">Skip to content</a>

<header class="masthead">
  <div class="wrap">
    <a class="masthead-mark" href="/"><img src="/assets/icon-512.png" alt="" width="512" height="512"><span>mac<em>4D</em>STEM</span></a>
    <nav aria-label="Sections">
      <a href="/">mac4DSTEM</a>
      <a href="/docs/" aria-current="page">Docs</a>
      <a href="/mactem/">macTEM</a>
      <a href="/suite/">Kits</a>
      <a class="nav-download" href="https://github.com/mac4DSTEM/mac4DSTEM/releases/latest/download/mac4DSTEM.dmg">Download</a>
    </nav>
  </div>
</header>

<div class="wrap docs">
  <nav class="docs-nav" aria-label="Documentation">
{sidebar}
    <p class="docs-version">Written for mac4DSTEM {version}</p>
  </nav>

  <main id="main">
    <article class="doc">
"""

FOOT = """{pager}
    </article>
  </main>
</div>

<footer class="site-footer">
  <div class="wrap">
    <span>Siegen, Germany</span>
    <nav aria-label="Legal and support">
      <a href="/support.html">Support</a>
      <a href="/privacy.html">Privacy</a>
      <a href="/impressum.html">Impressum</a>
    </nav>
  </div>
</footer>
</body>
</html>
"""


def sidebar(current):
    out, group = [], None
    for g, _, path, title, _ in PAGES:
        if g != group:
            if group is not None:
                out.append("    </ul>")
            if g:
                out.append(f'    <p class="docs-group">{html.escape(g)}</p>')
            out.append("    <ul>")
            group = g
        href = "/docs/" + ("" if path == "index.html" else path)
        mark = ' aria-current="page"' if path == current else ""
        label = "Overview" if path == "index.html" else title
        out.append(f'      <li><a href="{href}"{mark}>{html.escape(label)}</a></li>')
    out.append("    </ul>")
    return "\n".join(out)


def pager(i):
    """Previous and next page, in sidebar order."""
    def link(j, cls, word):
        _, _, path, title, _ = PAGES[j]
        href = "/docs/" + ("" if path == "index.html" else path)
        return f'<a class="{cls}" href="{href}"><span>{word}</span>{html.escape(title)}</a>'
    parts = []
    if i > 0:
        parts.append(link(i - 1, "prev", "Previous"))
    if i + 1 < len(PAGES):
        parts.append(link(i + 1, "next", "Next"))
    return '      <nav class="docs-pager" aria-label="Previous and next page">' + "".join(parts) + "</nav>"


def render(i):
    _, stem, path, title, description = PAGES[i]
    body = (SRC / f"{stem}.html").read_text().replace("{version}", APP_VERSION)
    head = HEAD.format(title=html.escape(title), description=html.escape(description, quote=True),
                       canonical="" if path == "index.html" else path, sidebar=sidebar(path), version=APP_VERSION)
    return head + body.rstrip() + "\n" + FOOT.format(pager=pager(i))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if docs/ differs from what the sources give")
    a = ap.parse_args()
    stale = []
    for i, (_, _, path, _, _) in enumerate(PAGES):
        out, text = ROOT / "docs" / path, render(i)
        if a.check:
            if not out.is_file() or out.read_text() != text:
                stale.append(f"docs/{path}")
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text)
    if a.check:
        for s in stale:
            print(f"error: {s} is not what tools/docs gives: run python3 tools/build_docs.py")
        print(f"docs: {len(PAGES)} pages checked")
        sys.exit(1 if stale else 0)
    print(f"docs: {len(PAGES)} pages written")


if __name__ == "__main__":
    main()
