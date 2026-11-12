#!/usr/bin/env python3
"""Check the site before it publishes: every internal link resolves, and the pages name the current releases.

    python3 tools/check_site.py             # links, then versions and download sizes against GitHub releases
    python3 tools/check_site.py --offline   # links only

Links: every href, src and srcset that points into the site must name a file in this repo, and every #fragment an id
on its page. Releases: each app page must give the latest release's version and its .dmg size wherever it states
them (the text and the JSON-LD), and the kits pages the latest tag of each kit and of MacEMUI. From mac4DSTEM 5.3.0 on,
the website download updates itself (Sparkle), so appcast/mac4dstem.xml must name that latest release: its version, and
its mac4DSTEM-<version>.dmg on the release with the same length. CI runs it on every push
and once a day, so a new release turns it red until the pages follow. Standard library only; GITHUB_TOKEN is used
when set.
"""
import argparse, html.parser, json, os, re, sys, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parents[1]
ORG = "mac4DSTEM"
APPS = {"mac4DSTEM": "index.html", "macTEM": "mactem/index.html"}
PACKAGES = ["FormatoKit", "ImagoKit", "DiffractoKit", "SpectroKit", "CuboKit", "SimulatoKit", "MacEMUI"]
SKIP = {".git", "datacube", "tools"}
# Apps whose website download reads an update feed, the feed's path in this repo, and the first version that reads it.
FEEDS = {"mac4DSTEM": ("appcast/mac4dstem.xml", (5, 3, 0))}
SPARKLE = "{http://www.andymatuschak.org/xml-namespaces/sparkle}"


class Page(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.refs = set(), []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a" and "name" in a:
            self.ids.add(a["name"])
        for key in ("href", "src"):
            if a.get(key):
                self.refs.append(a[key])
        if a.get("srcset"):
            self.refs += [part.split()[0] for part in a["srcset"].split(",") if part.strip()]


def pages():
    return sorted(p for p in ROOT.rglob("*.html") if not SKIP & set(p.relative_to(ROOT).parts))


def parse(path):
    p = Page()
    p.feed(path.read_text())
    return p


def target(page, ref):
    """The file a site-internal reference names, or None for an external one."""
    u = urlsplit(ref)
    if u.scheme or u.netloc or ref.startswith(("mailto:", "tel:", "data:")):
        return None
    if not u.path:
        return page, u.fragment
    base = ROOT if u.path.startswith("/") else page.parent
    f = (base / unquote(u.path).lstrip("/")).resolve()
    if u.path.endswith("/") or f.is_dir():
        f = f / "index.html"
    return f, u.fragment


def check_links():
    errors, parsed = [], {}
    for page in pages():
        parsed[page] = parse(page)
    for page, p in parsed.items():
        for ref in p.refs:
            t = target(page, ref)
            if t is None:
                continue
            f, frag = t
            name = page.relative_to(ROOT)
            if not f.is_file():
                errors.append(f"{name}: {ref} names no file")
            elif frag and f.suffix == ".html":
                ids = parsed[f].ids if f in parsed else parse(f).ids
                if frag not in ids:
                    errors.append(f"{name}: {ref} names no id on its page")
    return errors, len(parsed)


def latest(repo):
    req = urllib.request.Request(f"https://api.github.com/repos/{ORG}/{repo}/releases/latest",
                                 headers={"Accept": "application/vnd.github+json"})
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    return json.load(urllib.request.urlopen(req, timeout=30))


def check_releases():
    errors = []
    for app, rel in APPS.items():
        r = latest(app)
        ver = r["tag_name"].lstrip("v")
        dmg = next((a for a in r["assets"] if a["name"] == f"{app}.dmg"), None)
        if dmg is None:
            errors.append(f"{rel}: the latest {app} release {r['tag_name']} has no {app}.dmg, so the page's "
                          f"releases/latest/download/{app}.dmg link is a 404: build it with tools/release.sh "
                          "on that tag and attach it")
            continue
        size = f"{dmg['size'] / 1e6:.1f} MB"
        text = (ROOT / rel).read_text()
        for stated in sorted(set(re.findall(r"Version (\d+\.\d+\.\d+)", text))):
            if stated != ver:
                errors.append(f"{rel}: says Version {stated}, the latest {app} release is {ver}")
        meta = re.search(r'<p class="get-meta">(.*?)</p>', text, re.S)
        if not meta or f"Version {ver}" not in meta.group(1) or size not in meta.group(1):
            errors.append(f"{rel}: the download line must read Version {ver} and {size}")
        ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S).group(1))
        if ld.get("softwareVersion") != ver:
            errors.append(f"{rel}: JSON-LD softwareVersion {ld.get('softwareVersion')}, latest is {ver}")
        if ld.get("fileSize") != size:
            errors.append(f"{rel}: JSON-LD fileSize {ld.get('fileSize')}, the {app}.dmg of {ver} is {size}")
        if not ld.get("downloadUrl", "").endswith(f"/{app}.dmg"):
            errors.append(f"{rel}: JSON-LD downloadUrl must point at {app}.dmg")
        errors += check_feed(app, ver, r["assets"])
    releases = (ROOT / "suite/releases.html").read_text()
    for pkg in PACKAGES:
        ver = latest(pkg)["tag_name"]
        m = re.search(rf"<tr><td>{pkg}</td><td>([^<]*)</td>", releases)
        if not m or m.group(1) != ver:
            errors.append(f"suite/releases.html: {pkg} {m.group(1) if m else 'missing'}, latest tag is {ver}: "
                          "run tools/build_suite_pages.py --fetch")
    return errors


def check_feed(app, ver, assets):
    """The update feed names the latest release: its version, and its versioned DMG with the release's length."""
    if app not in FEEDS:
        return []
    path, first = FEEDS[app]
    if tuple(int(n) for n in ver.split(".")) < first:
        return []
    feed = ROOT / path
    if not feed.is_file():
        return [f"{path}: missing; the {app} {ver} download reads it to update itself. Commit the feed "
                f"tools/release.sh wrote for v{ver}"]
    try:
        item = ET.parse(feed).getroot().find("channel/item")
    except ET.ParseError as e:
        return [f"{path}: not readable XML ({e})"]
    if item is None:
        return [f"{path}: has no item"]
    errors = []
    for key in ("version", "shortVersionString"):
        stated = item.findtext(f"{SPARKLE}{key}")
        if stated != ver:
            errors.append(f"{path}: sparkle:{key} {stated}, the latest {app} release is {ver}")
    enclosure = item.find("enclosure")
    name = f"{app}-{ver}.dmg"
    url = enclosure.get("url", "") if enclosure is not None else ""
    if url != f"https://github.com/{ORG}/{app}/releases/download/v{ver}/{name}":
        errors.append(f"{path}: the enclosure must point at {name} on the v{ver} release, not {url or 'nothing'}")
    elif not (enclosure.get(f"{SPARKLE}edSignature") or "").strip():
        errors.append(f"{path}: the enclosure has no sparkle:edSignature")
    else:
        asset = next((a for a in assets if a["name"] == name), None)
        if asset is None:
            errors.append(f"{path}: the v{ver} release has no {name} for the feed to point at")
        elif str(asset["size"]) != enclosure.get("length"):
            errors.append(f"{path}: length {enclosure.get('length')}, the release's {name} is {asset['size']} bytes")
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="check links only")
    a = ap.parse_args()
    errors, n = check_links()
    print(f"links: {n} pages checked")
    if not a.offline:
        errors += check_releases()
        print(f"releases: {len(APPS)} apps and {len(PACKAGES)} packages checked")
    for e in errors:
        print("error:", e)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
