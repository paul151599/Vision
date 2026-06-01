"""BMP image loading with optional gain correction and channel separation."""
import numpy as np
from pathlib import Path
from typing import Tuple, Dict, Optional
import cv2

from config.camera import CameraConfig


class ImageLoader:
    """Load BMP images with optional gain reverse-correction."""

    def __init__(self, camera_config: Optional[CameraConfig] = None):
        self.camera_config = camera_config or CameraConfig()

    def load(self, path: str | Path) -> np.ndarray:
        """Load BMP image as BGR numpy array (uint8).

        Returns:
            np.ndarray: shape (H, W, 3), dtype uint8, BGR order
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")
        # Use np.fromfile + imdecode to support non-ASCII (Korean) paths
        buf = np.fromfile(str(path), dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Failed to load image: {path}")
        return img

    def load_gray(self, path: str | Path) -> np.ndarray:
        """Load BMP as grayscale uint8."""
        img = self.load(path)
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    def split_channels(self, img_bgr: np.ndarray) -> Dict[str, np.ndarray]:
        """Split BGR image into R, G, B channel arrays (float64).

        Returns:
            Dict with keys 'R', 'G', 'B', each shape (H, W), dtype float64
        """
        b, g, r = img_bgr[:, :, 0], img_bgr[:, :, 1], img_bgr[:, :, 2]
        return {
            "R": r.astype(np.float64),
            "G": g.astype(np.float64),
            "B": b.astype(np.float64),
        }

    def gain_correct(self, channels: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """Apply gain reverse-correction: pixel / gain.

        This removes the camera's per-channel analog gain to recover
        a physically-meaningful spectral response.
        """
        gains = self.camera_config.gains
        corrected = {}
        for ch_name, ch_data in channels.items():
            gain = gains.get(ch_name, 1.0)
            corrected[ch_name] = ch_data / gain if gain != 0 else ch_data.copy()
        return corrected

    def prepare(self, path: str | Path) -> Dict[str, np.ndarray]:
        """Full pipeline: load → channels → both raw and gain-corrected.

        Returns dict with keys:
            'bgr': original BGR uint8
            'gray': grayscale uint8
            'R', 'G', 'B': raw float64 channels
            'R_corr', 'G_corr', 'B_corr': gain-corrected float64 channels
        """
        bgr = self.load(path)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        raw_channels = self.split_channels(bgr)
        corrected = self.gain_correct(raw_channels)

        return {
            "bgr": bgr,
            "gray": gray,
            "R": raw_channels["R"],
            "G": raw_channels["G"],
            "B": raw_channels["B"],
            "R_corr": corrected["R"],
            "G_corr": corrected["G"],
            "B_corr": corrected["B"],
        }
