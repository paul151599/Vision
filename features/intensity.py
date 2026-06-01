"""Intensity features: Gray Mean/Std/Skewness/Kurtosis (4 features)."""
import numpy as np
from scipy import stats
from typing import Dict, List, Any
from features.base import FeatureExtractor


class IntensityExtractor(FeatureExtractor):
    def feature_ids(self) -> List[str]:
        return [
            "gray_mean",
            "gray_std",
            "gray_skewness",
            "gray_kurtosis",
        ]

    def extract(self, image_data: Dict[str, np.ndarray], cache: Dict[str, Any]) -> Dict[str, float]:
        gray = image_data["gray"].astype(np.float64)
        flat = gray.ravel()
        return {
            "gray_mean": float(np.mean(flat)),
            "gray_std": float(np.std(flat, ddof=0)),
            "gray_skewness": float(stats.skew(flat)),
            "gray_kurtosis": float(stats.kurtosis(flat, fisher=True)),
        }
