"""LBP feature: LBP Entropy (1 feature)."""
import numpy as np
from typing import Dict, List, Any
from skimage.feature import local_binary_pattern
from features.base import FeatureExtractor
from config.settings import LBP_RADIUS, LBP_N_POINTS


class LBPExtractor(FeatureExtractor):
    def feature_ids(self) -> List[str]:
        return ["lbp_entropy"]

    def extract(self, image_data: Dict[str, np.ndarray], cache: Dict[str, Any]) -> Dict[str, float]:
        gray = image_data["gray"]

        lbp = local_binary_pattern(gray, LBP_N_POINTS, LBP_RADIUS, method="uniform")
        n_bins = LBP_N_POINTS + 2
        hist, _ = np.histogram(lbp.ravel(), bins=n_bins, range=(0, n_bins), density=True)
        hist = hist[hist > 0]
        entropy = -np.sum(hist * np.log2(hist))

        return {"lbp_entropy": float(entropy)}
