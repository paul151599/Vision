"""Uniformity features: Grid σ, Grid Range (2 features)."""
import numpy as np
from typing import Dict, List, Any
from features.base import FeatureExtractor
from config.settings import UNIFORMITY_GRID


class UniformityExtractor(FeatureExtractor):
    def feature_ids(self) -> List[str]:
        return ["grid_uniformity_std", "grid_uniformity_range"]

    def extract(self, image_data: Dict[str, np.ndarray], cache: Dict[str, Any]) -> Dict[str, float]:
        gray = image_data["gray"].astype(np.float64)
        grid_rows, grid_cols = UNIFORMITY_GRID
        h, w = gray.shape

        row_step = h // grid_rows
        col_step = w // grid_cols

        grid_means = []
        for r in range(grid_rows):
            for c in range(grid_cols):
                r_start = r * row_step
                r_end = (r + 1) * row_step if r < grid_rows - 1 else h
                c_start = c * col_step
                c_end = (c + 1) * col_step if c < grid_cols - 1 else w
                patch = gray[r_start:r_end, c_start:c_end]
                grid_means.append(np.mean(patch))

        grid_means = np.array(grid_means)

        return {
            "grid_uniformity_std": float(np.std(grid_means, ddof=0)),
            "grid_uniformity_range": float(np.max(grid_means) - np.min(grid_means)),
        }
