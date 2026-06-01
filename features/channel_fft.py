"""Channel FFT features: B and R high-frequency ratio (2 features)."""
import numpy as np
from typing import Dict, List, Any
from features.base import FeatureExtractor


class ChannelFFTExtractor(FeatureExtractor):
    """High-frequency energy ratio per gain-corrected B and R channel."""

    def feature_ids(self) -> List[str]:
        return ["chfft_b_high_ratio", "chfft_r_high_ratio"]

    def _high_freq_ratio(self, ch: np.ndarray, cache: Dict[str, Any]) -> float:
        f = np.fft.fft2(ch)
        fshift = np.fft.fftshift(f)
        magnitude = np.abs(fshift)

        h, w = ch.shape
        cy, cx = h // 2, w // 2
        max_r = min(cy, cx)

        y, x = np.ogrid[:h, :w]
        r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)

        # High-frequency band: outer 1/3 of radius (matches fft.py equal-area bands)
        high_mask = r > max_r * 2 / 3
        total_energy = np.sum(magnitude ** 2)
        if total_energy == 0:
            return 0.0
        return float(np.sum(magnitude[high_mask] ** 2) / total_energy)

    def extract(self, image_data: Dict[str, np.ndarray], cache: Dict[str, Any]) -> Dict[str, float]:
        b = image_data["B_corr"]
        r = image_data["R_corr"]

        return {
            "chfft_b_high_ratio": self._high_freq_ratio(b, cache),
            "chfft_r_high_ratio": self._high_freq_ratio(r, cache),
        }
