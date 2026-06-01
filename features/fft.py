"""FFT features: Low/Mid/High frequency ratio (3 features)."""
import numpy as np
from typing import Dict, List, Any
from features.base import FeatureExtractor


class FFTExtractor(FeatureExtractor):
    def feature_ids(self) -> List[str]:
        return ["fft_low_freq_ratio", "fft_mid_freq_ratio", "fft_high_freq_ratio"]

    def extract(self, image_data: Dict[str, np.ndarray], cache: Dict[str, Any]) -> Dict[str, float]:
        gray = image_data["gray"].astype(np.float64)
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        magnitude = np.abs(fshift)

        h, w = gray.shape
        cy, cx = h // 2, w // 2
        max_r = min(cy, cx)

        # Create radial distance map
        y, x = np.ogrid[:h, :w]
        r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)

        # Equal-area radial bands at 1/3 and 2/3 of max radius
        low_mask = r <= max_r / 3
        mid_mask = (r > max_r / 3) & (r <= max_r * 2 / 3)
        high_mask = r > max_r * 2 / 3

        total_energy = np.sum(magnitude ** 2)
        if total_energy == 0:
            return {"fft_low_freq_ratio": 0.0, "fft_mid_freq_ratio": 0.0, "fft_high_freq_ratio": 0.0}

        low_e = np.sum(magnitude[low_mask] ** 2)
        mid_e = np.sum(magnitude[mid_mask] ** 2)
        high_e = np.sum(magnitude[high_mask] ** 2)

        # Cache for channel FFT reuse
        cache["fft_radial_r"] = r
        cache["fft_max_r"] = max_r

        return {
            "fft_low_freq_ratio": float(low_e / total_energy),
            "fft_mid_freq_ratio": float(mid_e / total_energy),
            "fft_high_freq_ratio": float(high_e / total_energy),
        }
