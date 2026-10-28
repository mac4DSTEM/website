# mac4dstem.com

Source for [mac4dstem.com](https://mac4dstem.com), the website of the macEM suite: two free,
native macOS applications for electron microscopy, [mac4DSTEM](https://github.com/mac4DSTEM/mac4DSTEM)
(4D-STEM) and [macTEM](https://github.com/mac4DSTEM/macTEM) (TEM images, spectra and diffraction),
and the six Swift kits they are built on.

The site is static: **plain HTML, CSS, and vanilla JavaScript, with no build step,
no dependencies, and no framework.** Pushing to `main` publishes through GitHub
Pages within about a minute.

## Running it locally

Any static file server will do. From the repository root:

```bash
python3 -m http.server 4173
```

Then open <http://localhost:4173>. Pages reference assets by absolute path, so
opening `index.html` directly from the filesystem will not load the stylesheet.

## Structure

| Path | Purpose |
|---|---|
| `index.html` | The mac4DSTEM page and landing page. Page-specific styling lives in its `<style>` block. |
| `mactem/index.html` | The macTEM page, in the landing page's style (its own `<style>` block, the demo left out). |
| `privacy.html` | Privacy policy for both applications and the site. |
| `support.html` | Support, requirements, and known limitations of both applications. |
| `impressum.html` | Provider identification (§ 5 DDG). |
| `404.html` | The page GitHub Pages serves for an unknown address. |
| `assets/site.css` | Styling shared across all pages. |
| `assets/demo.js` | The interactive virtual-imaging demo. |
| `suite/` | Kits overview, benchmarks and releases pages for the macEM suite. Generated, do not edit. |
| `tools/build_suite_pages.py` | Generates `suite/` from the kits' and MacEMUI's CHANGELOG, `docs/parity.md` and `docs/benchmarks.md`. Run `python3 tools/build_suite_pages.py --fetch` after a kit or MacEMUI release. |
| `tools/check_site.py` | The CI check: internal links, and versions and download sizes against the GitHub releases. |
| `tools/export_atlas.py` | Regenerates the demo dataset. Development only. |

## Checks and releases

CI (`.github/workflows/ci.yml`) runs on every push to `main`, on pull requests, and once a day. It scans for
references to private material and runs `tools/check_site.py`: every internal link and `#fragment` must resolve, each
app page must state the latest release's version and `.dmg` size (in the text and in the JSON-LD), and
`suite/releases.html` must name each kit's and MacEMUI's latest tag. Run it locally with
`python3 tools/check_site.py` (or `--offline` for links only).

After an app release, update the version and size on its page. After a kit or MacEMUI release, regenerate `suite/`.

Everything else in `assets/` is a generated artefact — images, icons, the social
card, and the demo data. None of it is edited by hand.

## The interactive demo

The landing page includes a working 4D-STEM virtual-imaging demo running entirely
in the browser, on a real experimental scan of a NiCu alloy.

A 4D-STEM dataset records a full diffraction pattern at every probe position, so
real space and diffraction space each produce the other. Placing a mask on the
detector integrates it into a virtual image; selecting a region of the scan
integrates it into a diffraction pattern. Both directions recompute in a few
milliseconds, so the masks respond as you drag them.

### How the data is shipped

The full datacube is far too large to serve, so `tools/export_atlas.py` reduces it
to a single sprite atlas:

- The scan is binned 2×2 to 100×100 positions, keeping the atlas at 3200×3200 —
  below Safari's canvas area limit.
- Each 32×32 diffraction pattern becomes one tile, at pixel `(rx*32, ry*32)`.
- Intensities are **log-companded** to 8 bits. Eight bits cannot hold the linear
  range between the direct beam and the dark-field signal, so the page rebuilds a
  256-entry lookup table from `demo-manifest.json` and decompands before summing.
  Integrals therefore stay linear in the units the microscope recorded.

The atlas is stored losslessly. Lossy compression was measured introducing up to 9%
error in dark-field sums even at high quality, because adjacent tiles are unrelated
patterns and the codec bleeds signal across tile boundaries.

The atlas is only fetched when the demo is approached, and never on metered or slow
connections, where a load button appears instead.

### Regenerating it

Place the source `.h5` datacube in `datacube/` (gitignored — it is far above
GitHub's file size limit) and run:

```bash
pip install h5py numpy pillow
```

```bash
python3 tools/export_atlas.py [--src FILE.h5] [--previews DIR]
```

This rewrites `assets/demo-atlas.png` and `assets/demo-manifest.json`; `--previews` also writes mean-pattern,
bright-field and dark-field check images to `DIR`.

## Privacy

The site sets no cookies, runs no analytics, and makes no third-party requests. It
uses the system font stack rather than a hosted webfont. See
[privacy.html](privacy.html).

## Licence

The site is released under the GNU General Public License v3.0 ([`LICENSE`](LICENSE)), as are
both applications and the kits. mac4DSTEM's analysis algorithms are ported from and validated
against [py4DSTEM](https://github.com/py4dstem/py4DSTEM); work published using mac4DSTEM should
cite py4DSTEM for the underlying methods.

## Contact

**mail@mac4dstem.com**
