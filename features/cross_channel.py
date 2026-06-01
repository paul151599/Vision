"""Cross-channel correlation features: Pearson(R,B), Local R/B Std, Coherence (3 features)."""
import numpy as np
from typing import Dict, List, Any
import cv2
from features.base import FeatureExtractor
from config.settings import UNIFORMITY_GRID


class CrossChannelExtractor(FeatureExtractor):
    """Inter-channel correlation and coherence features."""

    def feature_ids(self) -> List[str]:
        return ["xchan_pearson_rb", "xchan_local_rb_std", "xchan_coherence"]

    def extract(self, image_data: Dict[str, np.ndarray], cache: Dict[str, Any]) -> Dict[str, float]:
        r = image_data["R_corr"]
        g = image_data["G_corr"]
        b = image_data["B_corr"]

        # Pearson correlation between R and B (flattened)
        r_flat = r.ravel()
        b_flat = b.ravel()
        pearson_rb = float(np.corrcoef(r_flat, b_flat)[0, 1])

        # Local R/B ratio variability (grid-based std of R/B ratio)
        rb_map = cache.get("rb_ratio_map")
        if rb_map is None:
            b_safe = np.where(b > 1.0, b, 1.0)
            rb_map = r / b_safe

        grid_rows, grid_cols = UNIFORMITY_GRID
        h, w = rb_map.shape
        row_step = h // grid_rows
        col_step = w // grid_cols
        patch_means = []
        for ri in range(grid_rows):
            for ci in range(grid_cols):
                r_s = ri * row_step
                r_e = (ri + 1) * row_step if ri < grid_rows - 1 else h
                c_s = ci * col_step
                c_e = (ci + 1) * col_step if ci < grid_cols - 1 else w
                patch_means.append(np.mean(rb_map[r_s:r_e, c_s:c_e]))
        local_rb_std = float(np.std(patch_means, ddof=0))

        # Channel coherence: 1 - normalized std across channels per pixel
        stack = np.stack([r, g, b], axis=-1)
        pixel_std = np.std(stack, axis=-1, ddof=0)
        pixel_mean = np.mean(stack, axis=-1)
        pixel_mean_safe = np.where(pixel_mean > 1.0, pixel_mean, 1.0)
        cv_per_pixel = pixel_std / pixel_mean_safe
        coherence = float(1.0 - np.mean(cv_per_pixel))

        return {
            "xchan_pearson_rb": pearson_rb,
            "xchan_local_rb_std": local_rb_std,
            "xchan_coherence": coherence,
        }
