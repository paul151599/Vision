"""Morphological features: Circularity, Aspect Ratio, Solidity (3 features)."""
import numpy as np
import cv2
from typing import Dict, List, Any
from features.base import FeatureExtractor
from config.settings import ANOMALY_MIN_AREA_PX, MORPH_SIGMA


class MorphologicalExtractor(FeatureExtractor):
    """Shape analysis of anomaly regions from 3σ mask."""

    def feature_ids(self) -> List[str]:
        return ["morph_circularity", "morph_aspect_ratio", "morph_solidity"]

    def extract(self, image_data: Dict[str, np.ndarray], cache: Dict[str, Any]) -> Dict[str, float]:
        # Get or create anomaly mask
        mask = cache.get("anomaly_mask_3sigma")
        if mask is None:
            gray = image_data["gray"].astype(np.float64)
            mean_val = np.mean(gray)
            std_val = np.std(gray, ddof=0)
            mask = (np.abs(gray - mean_val) > MORPH_SIGMA * std_val).astype(np.uint8)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        circularities = []
        aspect_ratios = []
        solidities = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < ANOMALY_MIN_AREA_PX:
                continue

            perimeter = cv2.arcLength(cnt, True)
            if perimeter > 0:
                circ = 4 * np.pi * area / (perimeter ** 2)
                circularities.append(circ)

            # Bounding rect aspect ratio
            x, y, w, h = cv2.boundingRect(cnt)
            if h > 0:
                aspect_ratios.append(w / h)

            # Solidity = area / convex_hull_area
            hull = cv2.convexHull(cnt)
            hull_area = cv2.contourArea(hull)
            if hull_area > 0:
                solidities.append(area / hull_area)

        return {
            "morph_circularity": float(np.mean(circularities)) if circularities else 0.0,
            "morph_aspect_ratio": float(np.mean(aspect_ratios)) if aspect_ratios else 0.0,
            "morph_solidity": float(np.mean(solidities)) if solidities else 0.0,
        }
