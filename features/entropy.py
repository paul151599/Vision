"""Entropy features: Gray Entropy, Local Entropy Mean/Std (3 features)."""
import numpy as np
from typing import Dict, List, Any
from skimage.filters.rank import entropy as skimage_entropy
from skimage.morphology import disk
from features.base import FeatureExtractor
from config.settings import ENTROPY_DISK_RADIUS, LOCAL_ENTROPY_GRID


class EntropyExtractor(FeatureExtractor):
    def feature_ids(self) -> List[str]:
        return ["gray_entropy", "local_entropy_mean", "local_entropy_std"]

    def extract(self, image_data: Dict[str, np.ndarray], cache: Dict[str, Any]) -> Dict[str, float]:
        gray = image_data["gray"]

        # Global entropy from histogram
        hist, _ = np.histogram(gray.ravel(), bins=256, range=(0, 256), density=True)
        hist = hist[hist > 0]
        global_entropy = -np.sum(hist * np.log2(hist))

        # Local entropy map using skimage
        selem = disk(ENTROPY_DISK_RADIUS)
        local_ent = skimage_entropy(gray, selem)
        cache["local_entropy_map"] = local_ent

        # Grid-based local entropy stats
        grid_rows, grid_cols = LOCAL_ENTROPY_GRID
        h, w = local_ent.shape
        row_step = h // grid_rows
        col_step = w // grid_cols

        patch_means = []
        for r in range(grid_rows):
            for c in range(grid_cols):
                r_start = r * row_step
                r_end = (r + 1) * row_step if r < grid_rows - 1 else h
                c_start = c * col_step
                c_end = (c + 1) * col_step if c < grid_cols - 1 else w
                patch = local_ent[r_start:r_end, c_start:c_end]
                patch_means.append(np.mean(patch))

        patch_means = np.array(patch_means, dtype=np.float64)

        return {
            "gray_entropy": float(global_entropy),
            "local_entropy_mean": float(np.mean(patch_means)),
            "local_entropy_std": float(np.std(patch_means, ddof=0)),
        }
