"""CIELAB features: ΔE mean, Local ΔE Std (2 features)."""
import numpy as np
import cv2
from typing import Dict, List, Any
from features.base import FeatureExtractor
from config.settings import UNIFORMITY_GRID


class CIELABExtractor(FeatureExtractor):
    """CIE L*a*b* color difference features from gain-corrected image."""

    def feature_ids(self) -> List[str]:
        return ["cielab_de_mean", "cielab_local_de_std"]

    def extract(self, image_data: Dict[str, np.ndarray], cache: Dict[str, Any]) -> Dict[str, float]:
        # Reconstruct gain-corrected BGR image
        r_corr = np.clip(image_data["R_corr"], 0, 255).astype(np.uint8)
        g_corr = np.clip(image_data["G_corr"], 0, 255).astype(np.uint8)
        b_corr = np.clip(image_data["B_corr"], 0, 255).astype(np.uint8)
        bgr_corr = np.stack([b_corr, g_corr, r_corr], axis=-1)

        lab = cv2.cvtColor(bgr_corr, cv2.COLOR_BGR2LAB).astype(np.float64)
        l_ch = lab[:, :, 0]
        a_ch = lab[:, :, 1]
        b_ch = lab[:, :, 2]

        # Global mean as reference
        l_mean = np.mean(l_ch)
        a_mean = np.mean(a_ch)
        b_mean = np.mean(b_ch)

        # ΔE per pixel (CIE76)
        de = np.sqrt((l_ch - l_mean) ** 2 + (a_ch - a_mean) ** 2 + (b_ch - b_mean) ** 2)
        de_mean = float(np.mean(de))

        # Local ΔE std (grid-based)
        grid_rows, grid_cols = UNIFORMITY_GRID
        h, w = de.shape
        row_step = h // grid_rows
        col_step = w // grid_cols
        patch_de_means = []
        for ri in range(grid_rows):
            for ci in range(grid_cols):
                r_s = ri * row_step
                r_e = (ri + 1) * row_step if ri < grid_rows - 1 else h
                c_s = ci * col_step
                c_e = (ci + 1) * col_step if ci < grid_cols - 1 else w
                patch_de_means.append(np.mean(de[r_s:r_e, c_s:c_e]))

        local_de_std = float(np.std(patch_de_means, ddof=0))

        return {
            "cielab_de_mean": de_mean,
            "cielab_local_de_std": local_de_std,
        }
