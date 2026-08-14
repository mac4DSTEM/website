"""Export a 4D-STEM datacube to a sprite atlas for the web demo.

Layout: scan positions tile a single image, each tile one diffraction pattern.
Intensities are log-companded to uint8; the page decompands via a 256-entry LUT
so virtual-image sums stay linear in the original units.
"""
import glob, json, math
import h5py
import numpy as np
from PIL import Image

SRC = glob.glob('/Users/paullobpreis/GitHub/website/datacube/*.h5')[0]
OUT = '/Users/paullobpreis/GitHub/website/assets'
SCAN_BIN = 2          # 200 -> 100, keeps the atlas at 3200x3200 (under Safari's canvas cap)

with h5py.File(SRC, 'r') as h:
    data = h['/dm_dataset_root/dm_dataset/data'][()]          # (Ry, Rx, Qy, Qx) float32
    cal = h['/dm_dataset_root/metadatabundle/calibration']
    q_size = float(cal['Q_pixel_size'][()])
    r_size = float(cal['R_pixel_size'][()])
    q_units = cal['Q_pixel_units'][()]
    r_units = cal['R_pixel_units'][()]

q_units = q_units.decode() if isinstance(q_units, bytes) else q_units
r_units = r_units.decode() if isinstance(r_units, bytes) else r_units

Ry, Rx, Qy, Qx = data.shape
print(f'source {data.shape} {data.dtype}')

# ---- bin the scan ----
data = data.reshape(Ry // SCAN_BIN, SCAN_BIN, Rx // SCAN_BIN, SCAN_BIN, Qy, Qx)
data = data.sum(axis=(1, 3))
Ry, Rx = data.shape[:2]
print(f'binned  {data.shape}  (scan step {r_size * SCAN_BIN} {r_units})')

# ---- clip and compand ----
np.clip(data, 0, None, out=data)
vmax = float(np.percentile(data, 99.999))          # ignore a few hot pixels
np.clip(data, 0, vmax, out=data)

knee = max(vmax / 5000.0, 1e-6)                    # sets how much low-signal detail survives
denom = math.log1p(vmax / knee)
companded = np.rint(255.0 * np.log1p(data / knee) / denom).astype(np.uint8)

# ---- lay out the atlas: tile (ry, rx) at pixel (rx*Qx, ry*Qy) ----
atlas = companded.transpose(0, 2, 1, 3).reshape(Ry * Qy, Rx * Qx)
print(f'atlas   {atlas.shape[1]}x{atlas.shape[0]} px')

img = Image.fromarray(atlas, mode='L')
img.save(f'{OUT}/demo-atlas.webp', lossless=True, quality=100, method=6)
img.save(f'{OUT}/demo-atlas.png', optimize=True)

manifest = {
    'scan':     {'x': Rx, 'y': Ry},
    'detector': {'x': Qx, 'y': Qy},
    'calibration': {
        'q_pixel_size': q_size, 'q_pixel_units': q_units,
        'r_pixel_size': r_size * SCAN_BIN, 'r_pixel_units': r_units,
    },
    'compand': {'knee': knee, 'vmax': vmax, 'denom': denom},
    'sample': 'NiCu alloy',
}
with open(f'{OUT}/demo-manifest.json', 'w') as f:
    json.dump(manifest, f, indent=2)

# ---- sanity previews ----
lut = knee * (np.expm1(np.arange(256) / 255.0 * denom))
decoded = lut[companded]
mean_dp = decoded.mean(axis=(0, 1))
yy, xx = np.mgrid[0:Qy, 0:Qx]
r = np.hypot(yy - (Qy - 1) / 2, xx - (Qx - 1) / 2)
bf = (decoded * (r < 4)).sum(axis=(2, 3))
adf = (decoded * ((r >= 6) & (r < 15))).sum(axis=(2, 3))

def norm(a, p=99.5):
    a = a - a.min()
    hi = np.percentile(a, p)
    return np.uint8(np.clip(a / (hi if hi else 1), 0, 1) * 255)

S = '/private/tmp/claude-501/-Users-paullobpreis-GitHub-website/4e8573a9-16bf-405d-91b9-4ab3a585b68d/scratchpad'
Image.fromarray(norm(np.log1p(mean_dp))).resize((256, 256), Image.NEAREST).save(f'{S}/chk_meandp.png')
Image.fromarray(norm(bf)).resize((300, 300), Image.NEAREST).save(f'{S}/chk_bf.png')
Image.fromarray(norm(adf)).resize((300, 300), Image.NEAREST).save(f'{S}/chk_adf.png')
print('previews written')
