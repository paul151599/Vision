"""Spectral ratio features: R/B and G/B ratio statistics (6 features)."""
import numpy as np
from scipy import stats as sp_stats
from typing import Dict, List, Any
from features.base import FeatureExtractor


class SpectralRatioExtractor(FeatureExtractor):
    """Pixel-wise spectral ratios from gain-corrected channels."""

    def feature_ids(self) -> List[str]:
        return [
            "spratio_rb_mean", "spratio_rb_std", "spratio_rb_skew",
            "spratio_gb_mean", "spratio_gb_std", "spratio_gb_skew",
        ]

    def extract(self, image_data: Dict[str, np.ndarray], cache: Dict[str, Any]) -> Dict[str, float]:
        r = image_data["R_corr"]
        g = image_data["G_corr"]
        b = image_data["B_corr"]

        # Mask out pixels where B is too low (< 1 DN) to avoid division artifacts
        valid_mask = b > 1.0
        b_safe = np.where(valid_mask, b, 1.0)

        rb_ratio_map = r / b_safe
        gb_ratio_map = g / b_safe

        # Only compute stats on valid pixels
        rb_valid = rb_ratio_map[valid_mask]
        gb_valid = gb_ratio_map[valid_mask]

        # Cache full maps for cross-channel reuse
        cache["rb_ratio_map"] = rb_ratio_map
        cache["gb_ratio_map"] = gb_ratio_map
        cache["spectral_valid_mask"] = valid_mask

        if len(rb_valid) == 0:
            return {k: 0.0 for k in self.feature_ids()}

        return {
            "spratio_rb_mean": float(np.mean(rb_valid)),
            "spratio_rb_std": float(np.std(rb_valid, ddof=0)),
            "spratio_rb_skew": float(sp_stats.skew(rb_valid)),
            "spratio_gb_mean": float(np.mean(gb_valid)),
            "spratio_gb_std": float(np.std(gb_valid, ddof=0)),
            "spratio_gb_skew": float(sp_stats.skew(gb_valid)),
        }
