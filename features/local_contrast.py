"""Local Contrast features: Local Contrast Mean/Std (2 features)."""
import numpy as np
import cv2
from typing import Dict, List, Any
from features.base import FeatureExtractor
from config.settings import LOCAL_CONTRAST_KERNEL


class LocalContrastExtractor(FeatureExtractor):
    def feature_ids(self) -> List[str]:
        return ["local_contrast_mean", "local_contrast_std"]

    def extract(self, image_data: Dict[str, np.ndarray], cache: Dict[str, Any]) -> Dict[str, float]:
        gray = image_data["gray"].astype(np.float64)
        ksize = LOCAL_CONTRAST_KERNEL

        # Local mean using box filter
        local_mean = cv2.blur(gray, (ksize, ksize))
        # Local std = sqrt(E[X^2] - (E[X])^2)
        local_sq_mean = cv2.blur(gray ** 2, (ksize, ksize))
        local_var = np.maximum(local_sq_mean - local_mean ** 2, 0)
        local_std_map = np.sqrt(local_var)

        # Cache for reuse by morphological extractor
        cache["local_contrast_map"] = local_std_map

        return {
            "local_contrast_mean": float(np.mean(local_std_map)),
            "local_contrast_std": float(np.std(local_std_map, ddof=0)),
        }
