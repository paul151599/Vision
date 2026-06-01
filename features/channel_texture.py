"""Per-channel GLCM features: R/G/B Contrast and Homogeneity (6 features)."""
import numpy as np
from typing import Dict, List, Any
from skimage.feature import graycomatrix, graycoprops
from features.base import FeatureExtractor
from config.settings import GLCM_DISTANCES, GLCM_ANGLES, GLCM_LEVELS


class ChannelTextureExtractor(FeatureExtractor):
    """GLCM Contrast & Homogeneity per gain-corrected R/G/B channel."""

    def feature_ids(self) -> List[str]:
        return [
            "chtex_r_contrast", "chtex_r_homogeneity",
            "chtex_g_contrast", "chtex_g_homogeneity",
            "chtex_b_contrast", "chtex_b_homogeneity",
        ]

    def _compute_glcm(self, ch_float: np.ndarray) -> dict:
        ch_uint8 = np.clip(ch_float, 0, 255).astype(np.uint8)
        glcm = graycomatrix(
            ch_uint8, distances=GLCM_DISTANCES, angles=GLCM_ANGLES,
            levels=GLCM_LEVELS, symmetric=True, normed=True,
        )
        return {
            "contrast": float(graycoprops(glcm, "contrast")[0, 0]),
            "homogeneity": float(graycoprops(glcm, "homogeneity")[0, 0]),
        }

    def extract(self, image_data: Dict[str, np.ndarray], cache: Dict[str, Any]) -> Dict[str, float]:
        results = {}
        for ch_name in ("r", "g", "b"):
            ch = image_data[f"{ch_name.upper()}_corr"]
            props = self._compute_glcm(ch)
            results[f"chtex_{ch_name}_contrast"] = props["contrast"]
            results[f"chtex_{ch_name}_homogeneity"] = props["homogeneity"]
        return results
