# mac4dstem.com

Source for the [mac4DSTEM](https://mac4dstem.com) website — the landing page for a
free, native macOS application for 4D-STEM analysis.

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
| `index.html` | Landing page. Page-specific styling lives in its `<style>` block. |
| `privacy.html` | Privacy policy. |
| `support.html` | Support, requirements, and known limitations. |
| `impressum.html` | Provider identification (§ 5 DDG). |
| `assets/site.css` | Styling shared across all pages. |
| `assets/demo.js` | The interactive virtual-imaging demo. |
| `tools/export_atlas.py` | Regenerates the demo dataset. Development only. |

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
python3 tools/export_atlas.py
```

This rewrites `assets/demo-atlas.png` and `assets/demo-manifest.json`.

## Privacy

The site sets no cookies, runs no analytics, and makes no third-party requests. It
uses the system font stack rather than a hosted webfont. See
[privacy.html](privacy.html).

## Licence

The mac4DSTEM application is released under the GNU General Public License v3.0. Its
analysis algorithms are ported from and validated against
[py4DSTEM](https://github.com/py4dstem/py4DSTEM); work published using mac4DSTEM
should cite py4DSTEM for the underlying methods.

## Contact

**mail@mac4dstem.com**
