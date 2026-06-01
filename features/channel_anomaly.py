"""Channel anomaly: B-channel 3σ anomaly count (1 feature)."""
import numpy as np
from typing import Dict, List, Any
from features.base import FeatureExtractor
from config.settings import ANOMALY_MIN_AREA_PX
import cv2


class ChannelAnomalyExtractor(FeatureExtractor):
    """B-channel specific anomaly detection using gain-corrected image."""

    def feature_ids(self) -> List[str]:
        return ["chanom_b_3sigma_count"]

    def extract(self, image_data: Dict[str, np.ndarray], cache: Dict[str, Any]) -> Dict[str, float]:
        b = image_data["B_corr"]
        mean_b = np.mean(b)
        std_b = np.std(b, ddof=0)

        mask = (np.abs(b - mean_b) > 3 * std_b).astype(np.uint8)
        num_labels, _, stats_cc, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)

        count = 0
        for i in range(1, num_labels):
            if stats_cc[i, cv2.CC_STAT_AREA] >= ANOMALY_MIN_AREA_PX:
                count += 1

        return {"chanom_b_3sigma_count": float(count)}
