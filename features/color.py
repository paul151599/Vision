"""Color features: R/G/B Mean, R-G/R-B/G-B Diff, Sat Mean/Std (8 features)."""
import numpy as np
import cv2
from typing import Dict, List, Any
from features.base import FeatureExtractor


class ColorExtractor(FeatureExtractor):
    def feature_ids(self) -> List[str]:
        return [
            "red_mean", "green_mean", "blue_mean",
            "rg_diff_mean", "rb_diff_mean", "gb_diff_mean",
            "saturation_mean", "saturation_std",
        ]

    def extract(self, image_data: Dict[str, np.ndarray], cache: Dict[str, Any]) -> Dict[str, float]:
        r = image_data["R"]
        g = image_data["G"]
        b = image_data["B"]

        # Cache channels for reuse
        cache.setdefault("R", r)
        cache.setdefault("G", g)
        cache.setdefault("B", b)

        r_mean = float(np.mean(r))
        g_mean = float(np.mean(g))
        b_mean = float(np.mean(b))

        # Saturation from HSV
        hsv = cv2.cvtColor(image_data["bgr"], cv2.COLOR_BGR2HSV)
        sat = hsv[:, :, 1].astype(np.float64)

        return {
            "red_mean": r_mean,
            "green_mean": g_mean,
            "blue_mean": b_mean,
            "rg_diff_mean": r_mean - g_mean,
            "rb_diff_mean": r_mean - b_mean,
            "gb_diff_mean": g_mean - b_mean,
            "saturation_mean": float(np.mean(sat)),
            "saturation_std": float(np.std(sat, ddof=0)),
        }
