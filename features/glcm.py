"""GLCM features: Contrast/Homogeneity/Energy/Correlation (4 features)."""
import numpy as np
from typing import Dict, List, Any
from skimage.feature import graycomatrix, graycoprops
from features.base import FeatureExtractor
from config.settings import GLCM_DISTANCES, GLCM_ANGLES, GLCM_LEVELS


class GLCMExtractor(FeatureExtractor):
    def feature_ids(self) -> List[str]:
        return [
            "glcm_contrast",
            "glcm_homogeneity",
            "glcm_energy",
            "glcm_correlation",
        ]

    def extract(self, image_data: Dict[str, np.ndarray], cache: Dict[str, Any]) -> Dict[str, float]:
        gray = image_data["gray"]

        glcm = graycomatrix(
            gray,
            distances=GLCM_DISTANCES,
            angles=GLCM_ANGLES,
            levels=GLCM_LEVELS,
            symmetric=True,
            normed=True,
        )
        cache["glcm"] = glcm

        return {
            "glcm_contrast": float(graycoprops(glcm, "contrast")[0, 0]),
            "glcm_homogeneity": float(graycoprops(glcm, "homogeneity")[0, 0]),
            "glcm_energy": float(graycoprops(glcm, "energy")[0, 0]),
            "glcm_correlation": float(graycoprops(glcm, "correlation")[0, 0]),
        }
