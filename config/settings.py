"""Global constants, paths, algorithm parameters."""
from pathlib import Path

# ── Paths ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BASELINE_DIR = PROJECT_ROOT / "baselines"
OUTPUT_DIR = PROJECT_ROOT / "output"

# ── Image ──
DEFAULT_IMAGE_SIZE = (3000, 4096)  # expected BMP resolution (H, W) — Olympus OM/Preciv "Super High"

# ── GLCM ──
GLCM_DISTANCES = [1]
GLCM_ANGLES = [0]
GLCM_LEVELS = 256
GLCM_DOWNSAMPLE = 1024  # unused/reserved — GLCM now runs at full resolution

# ── LBP ──
LBP_RADIUS = 1
LBP_N_POINTS = 8

# ── FFT ──
# Band cutoffs now hardcoded in fft.py as equal-area 1/3, 2/3 splits.

# ── Anomaly detection ──
ANOMALY_SIGMA_LEVELS = [2, 3, 4, 5]
ANOMALY_MIN_AREA_PX = 5   # minimum connected-component area in pixels

# ── Uniformity Grid ──
UNIFORMITY_GRID = (8, 8)

# ── Entropy ──
ENTROPY_DISK_RADIUS = 5
LOCAL_ENTROPY_GRID = (8, 8)

# ── Local Contrast ──
LOCAL_CONTRAST_KERNEL = 15   # kernel size for local std filter

# ── Morphological ──
MORPH_SIGMA = 3  # sigma threshold for anomaly mask used in morphological analysis


# ── Judgment ──
DEFAULT_SIGMA_MULTIPLIER = 2.0  # default ± σ multiplier for spec bounds
