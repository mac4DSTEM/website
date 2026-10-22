#!/usr/bin/env python3
"""Generate suite/index.html, suite/benchmarks.html and suite/releases.html from the six kits' own files.

Nothing is typed in by hand here except the one-line kit descriptions: versions and dates come from each kit's
CHANGELOG.md, parity totals from docs/parity.md, benchmark tables from docs/benchmarks.md. Run it after a kit tag:

    python3 tools/build_suite_pages.py [--kits DIR]      # DIR holds the kit checkouts (default: ..)
    python3 tools/build_suite_pages.py --fetch           # read the files from github.com at each kit's CHANGELOG tag

The output is committed; the site has no build step. Standard library only.
"""
import argparse, html, re, sys, urllib.request
from pathlib import Path

ORG = "mac4DSTEM"
PAGES = "https://mac4dstem.github.io"   # per-kit DocC sites (kit repo Pages), see macEM-suite ROADMAP
KITS = [  # name, one line (from the kit's CLAUDE.md), the Python reference
    ("FormatoKit", "File formats for electron microscopy: Velox EMD, DM3/DM4, HDF5/EMD, MRC, TIFF, MIB, EMPAD.", "RosettaSciIO"),
    ("ImagoKit", "Image numerics: FFT, profiles, filters, alignment, measurement, segmentation.", "NumPy, SciPy, scikit-image"),
    ("DiffractoKit", "Crystallography, diffraction geometry, ring and ellipse fits, indexing, orientation and ACOM.", "pymatgen, py4DSTEM, orix"),
    ("SpectroKit", "EDX quantification and EELS thickness, background and edges.", "HyperSpy, exSpy"),
    ("CuboKit", "The 4D-STEM library: virtual imaging, centre of mass, DPC, strain, Bragg disks, parallax, ptychography.", "py4DSTEM"),
    ("SimulatoKit", "Multislice TEM/STEM simulation: potentials, frozen phonons, scans, detectors, CTF.", "abTEM"),
]
E = html.escape

def read(kit, rel, a):
    if a.fetch:
        ref = "main"
        if rel != "CHANGELOG.md":
            ref = read.tags.get(kit, "main")
        url = f"https://raw.githubusercontent.com/{ORG}/{kit}/{ref}/{rel}"
        return urllib.request.urlopen(url).read().decode()
    return (Path(a.kits) / kit / rel).read_text()
read.tags = {}

def inline(s):
    s = E(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: f'{m.group(1)}' if not m.group(2).startswith("http") else f'<a class="u-link" href="{m.group(2)}">{m.group(1)}</a>', s)
    return s

def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]

def md(text):
    """Headings, paragraphs and pipe tables: all the benchmark files use."""
    out, lines, i, para = [], text.splitlines(), 0, []
    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>"); para.clear()
    while i < len(lines):
        l = lines[i]
        if l.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|?$", lines[i + 1]):
            flush()
            head = cells(l); i += 2; rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(cells(lines[i])); i += 1
            t = "<div class=\"tablewrap\"><table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
            t += "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table></div>"
            out.append(t); continue
        m = re.match(r"^(#{1,4})\s+(.*)", l)
        if m:
            flush(); n = min(len(m.group(1)) + 2, 5)   # page h1 is ours; kit headings start at h3
            out.append(f"<h{n}>{inline(m.group(2))}</h{n}>")
        elif not l.strip():
            flush()
        elif l.lstrip().startswith(("- ", "* ", "```")):
            flush(); out.append("<p>" + inline(l.lstrip("-* ")) + "</p>")
        else:
            para.append(l.strip())
        i += 1
    flush()
    return "\n".join(out)

def page(title, desc, body, path):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)} — macEM suite</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="https://mac4dstem.com/suite/{path}">
<meta name="color-scheme" content="light dark">
<link rel="icon" href="/assets/favicon.ico" sizes="any">
<link rel="icon" href="/assets/icon-512.png" type="image/png" sizes="512x512">
<link rel="stylesheet" href="/assets/site.css">
<style>
.tablewrap{{overflow-x:auto;margin:1rem 0}}
table{{border-collapse:collapse;font-size:.9rem;font-variant-numeric:tabular-nums}}
th,td{{padding:.3rem .7rem;border-bottom:1px solid color-mix(in srgb,currentColor 18%,transparent);text-align:left;white-space:nowrap}}
</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="masthead">
  <div class="wrap">
    <a class="masthead-mark" href="/"><img src="/assets/icon-512.png" alt="" width="512" height="512"><span>mac<em>4D</em>STEM</span></a>
    <nav aria-label="Sections">
      <a href="/">Home</a>
      <a href="/guide/">Guide</a>
      <a href="/suite/">Kits</a>
      <a href="/suite/benchmarks.html">Benchmarks</a>
      <a href="/suite/releases.html">Releases</a>
    </nav>
  </div>
</header>
<main id="main">
  <div class="wrap">
    <article class="doc">
{body}
    </article>
  </div>
</main>
</body>
</html>
"""

def info(kit, a):
    cl = read(kit, "CHANGELOG.md", a)
    m = re.search(r"^## (\d+\.\d+\.\d+)(?: \((\d{4}-\d{2}-\d{2})\))?", cl, re.M)
    ver, date = m.group(1), m.group(2) or ""
    read.tags[kit] = ver
    par = read(kit, "docs/parity.md", a)
    parity = None
    for pat, f in [
        (r"(\d+) present, (\d+) partial, (\d+) missing\*\* of (\d+)", lambda g: (g[0], g[3])),         # CuboKit
        (r"\*\*all\*\* \| (\d+) \| (\d+) \| (\d+) \| (\d+) \|", lambda g: (g[0], g[3])),         # DiffractoKit
        (r"\| present \| \d+ \| \d+ \| \d+ \| (\d+) \|.*?\| rows \| \d+ \| \d+ \| \d+ \| (\d+) \|", lambda g: g), # SpectroKit
        (r"(\d+) rows of the Python counterparts: (\d+) present", lambda g: (g[1], g[0])),               # ImagoKit
        (r"\((\d+) rows\): (\d+) present", lambda g: (g[1], g[0])),                                   # SimulatoKit
        (r"the (\d+) plugins.*?: (\d+) present", lambda g: (g[1], g[0])),                               # FormatoKit
    ]:
        m = re.search(pat, par, re.S)
        if m:
            parity = f(m.groups()); break
    return dict(ver=ver, date=date, parity=parity)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kits", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--fetch", action="store_true")
    a = ap.parse_args()
    out = Path(__file__).resolve().parents[1] / "suite"
    out.mkdir(exist_ok=True)
    data = {k: info(k, a) for k, _, _ in KITS}

    rows = ""
    for k, line, ref in KITS:
        d = data[k]
        p = f'{d["parity"][0]} of {d["parity"][1]}' if d["parity"] else "—"
        rows += (f'<tr><td><a class="u-link" href="https://github.com/{ORG}/{k}">{k}</a></td><td>{E(line)}</td><td>{E(ref)}</td>'
                 f'<td>{d["ver"]}</td><td>{p}</td>'
                 f'<td><a class="u-link" href="{PAGES}/{k}/documentation/">API</a></td></tr>\n')
    body = f"""<h1>The macEM suite</h1>
<p class="lede">Six Swift packages that port the Python electron-microscopy stack to Apple silicon, and the two Mac apps built on them. Every number is checked against the Python package it comes from, within that package's own tolerance.</p>
<div class="tablewrap"><table><thead><tr><th>Kit</th><th>What it does</th><th>Reference</th><th>Version</th><th>Parity: present of rows</th><th>Docs</th></tr></thead><tbody>
{rows}</tbody></table></div>
<p>"Parity: present of rows" counts the functions of the reference package that the kit has and has tested against it; each kit's <code>docs/parity.md</code> lists every function with its state and tolerance. See <a class="u-link" href="/suite/benchmarks.html">benchmarks</a> and <a class="u-link" href="/suite/releases.html">releases</a>.</p>
<p>Apps: <a class="u-link" href="/">mac4DSTEM</a> (4D-STEM) and macTEM (TEM images and diffraction).</p>"""
    (out / "index.html").write_text(page("Kits", "The six Swift kits of the macEM suite: what each does, its Python reference, version and parity.", body, ""))

    body = ["<h1>Benchmarks</h1>",
            "<p class=\"lede\">Each kit against the Python package it ports, same inputs, on an Apple M-series Mac. Tables are copied from each kit's <code>docs/benchmarks.md</code> at its latest tag; where the kit is slower than Python, the table says so.</p>"]
    for k, _, _ in KITS:
        d = data[k]
        t = read(k, "docs/benchmarks.md", a)
        t = re.sub(r"^# .*\n", "", t, count=1)
        body.append(f'<h2 id="{k.lower()}">{k} {d["ver"]}</h2>')
        body.append(f'<p><a class="u-link" href="https://github.com/{ORG}/{k}/blob/{d["ver"]}/docs/benchmarks.md">Full file and method</a></p>')
        body.append(md(t))
    (out / "benchmarks.html").write_text(page("Benchmarks", "Timings of the macEM suite kits against NumPy, SciPy, py4DSTEM, HyperSpy, RosettaSciIO and abTEM.", "\n".join(body), "benchmarks.html"))

    rows = ""
    for k, _, _ in KITS:
        d = data[k]
        rows += (f'<tr><td>{k}</td><td>{d["ver"]}</td><td>{d["date"] or "—"}</td>'
                 f'<td><a class="u-link" href="https://github.com/{ORG}/{k}/releases/tag/{d["ver"]}">tag</a></td>'
                 f'<td><a class="u-link" href="https://github.com/{ORG}/{k}/blob/{d["ver"]}/CHANGELOG.md">changelog</a></td></tr>\n')
    body = f"""<h1>Releases</h1>
<p class="lede">Latest version of each kit. Tags are bare versions and equal the top entry of the kit's CHANGELOG. The apps pin exact kit tags.</p>
<div class="tablewrap"><table><thead><tr><th>Kit</th><th>Version</th><th>Date</th><th>Tag</th><th>Changes</th></tr></thead><tbody>
{rows}</tbody></table></div>
<p>The mac4DSTEM app: <a class="u-link" href="https://github.com/{ORG}/mac4DSTEM/releases">releases on GitHub</a>.</p>"""
    (out / "releases.html").write_text(page("Releases", "Current versions and tags of the macEM suite kits.", body, "releases.html"))

if __name__ == "__main__":
    main()
