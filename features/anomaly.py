"""Anomaly features: sigma counts, area stats, connected components (10 features)."""
import numpy as np
import cv2
from typing import Dict, List, Any
from features.base import FeatureExtractor
from config.settings import ANOMALY_SIGMA_LEVELS, ANOMALY_MIN_AREA_PX, LOCAL_CONTRAST_KERNEL


class AnomalyExtractor(FeatureExtractor):
    def feature_ids(self) -> List[str]:
        return [
            "texture_anomaly_2sigma",
            "texture_anomaly_3sigma",
            "texture_anomaly_4sigma",
            "texture_anomaly_5sigma",
            "anomaly_area_pct",
            "max_anomaly_area",
            "mean_anomaly_size",
            "std_anomaly_size",
            "anomaly_count",
            "median_anomaly_size",
        ]

    def extract(self, image_data: Dict[str, np.ndarray], cache: Dict[str, Any]) -> Dict[str, float]:
        gray = image_data["gray"].astype(np.float64)
        mean_val = np.mean(gray)
        std_val = np.std(gray, ddof=0)

        results = {}

        # Two-sided sigma counts: both bright (x > μ+nσ) and dark (x < μ-nσ) anomalies.
        # An "anomaly" here means any deviation from the membrane's typical optical
        # response, in either direction. This matches the visualization (phase_renderer),
        # the B-channel (channel_anomaly), and the morphological extractor, which all use
        # the same two-sided |x-μ| > nσ criterion — keeping feature values and the
        # on-screen Anomaly map consistent.
        for sigma in ANOMALY_SIGMA_LEVELS:
            mask = np.abs(gray - mean_val) > (sigma * std_val)
            results[f"texture_anomaly_{sigma}sigma"] = float(np.sum(mask))

        # Connected-component analysis on two-sided 3σ anomaly mask
        mask_3sigma = (np.abs(gray - mean_val) > (3 * std_val)).astype(np.uint8)

        # Cache this mask for morphological analysis
        cache["anomaly_mask_3sigma"] = mask_3sigma

        num_labels, labels, stats_cc, _ = cv2.connectedComponentsWithStats(
            mask_3sigma, connectivity=8
        )

        # Filter out background (label 0) and small components
        areas = []
        for i in range(1, num_labels):
            area = stats_cc[i, cv2.CC_STAT_AREA]
            if area >= ANOMALY_MIN_AREA_PX:
                areas.append(area)

        total_pixels = gray.shape[0] * gray.shape[1]

        if len(areas) > 0:
            areas_arr = np.array(areas, dtype=np.float64)
            results["anomaly_area_pct"] = float(np.sum(areas_arr) / total_pixels * 100)
            results["max_anomaly_area"] = float(np.max(areas_arr))
            results["mean_anomaly_size"] = float(np.mean(areas_arr))
            results["std_anomaly_size"] = float(np.std(areas_arr, ddof=0))
            results["anomaly_count"] = float(len(areas))
            results["median_anomaly_size"] = float(np.median(areas_arr))
        else:
            results["anomaly_area_pct"] = 0.0
            results["max_anomaly_area"] = 0.0
            results["mean_anomaly_size"] = 0.0
            results["std_anomaly_size"] = 0.0
            results["anomaly_count"] = 0.0
            results["median_anomaly_size"] = 0.0

        # Also cache labels and stats for morphological extractor
        cache["anomaly_labels"] = labels
        cache["anomaly_cc_stats"] = stats_cc
        cache["anomaly_num_labels"] = num_labels

        return results
