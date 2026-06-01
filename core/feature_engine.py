"""Feature extraction orchestrator: manages 16 extractors and shared cache."""
from typing import Dict, List, Any, Optional
from pathlib import Path
import numpy as np
import time

from config.camera import CameraConfig
from core.image_loader import ImageLoader
from core.data_models import FeatureResult
from features.base import FeatureExtractor
from features.intensity import IntensityExtractor
from features.color import ColorExtractor
from features.glcm import GLCMExtractor
from features.lbp import LBPExtractor
from features.fft import FFTExtractor
from features.anomaly import AnomalyExtractor
from features.uniformity import UniformityExtractor
from features.entropy import EntropyExtractor
from features.local_contrast import LocalContrastExtractor
from features.channel_texture import ChannelTextureExtractor
from features.spectral_ratio import SpectralRatioExtractor
from features.cross_channel import CrossChannelExtractor
from features.channel_fft import ChannelFFTExtractor
from features.channel_anomaly import ChannelAnomalyExtractor
from features.cielab import CIELABExtractor
from features.morphological import MorphologicalExtractor


# Ordered for optimal cache sharing:
# 1. GLCM first (caches glcm matrix)
# 2. Color (caches R/G/B)
# 3. Local Contrast (caches local_contrast_map)
# 4. Anomaly (caches anomaly mask, labels, stats)
# 5. Spectral Ratio (caches rb_ratio_map, gb_ratio_map)
# 6. Everything else
DEFAULT_EXTRACTORS: List[FeatureExtractor] = [
    GLCMExtractor(),
    LBPExtractor(),
    IntensityExtractor(),
    ColorExtractor(),
    FFTExtractor(),
    LocalContrastExtractor(),
    AnomalyExtractor(),
    UniformityExtractor(),
    EntropyExtractor(),
    # Group B
    ChannelTextureExtractor(),
    SpectralRatioExtractor(),
    CrossChannelExtractor(),
    ChannelFFTExtractor(),
    ChannelAnomalyExtractor(),
    CIELABExtractor(),
    # Group C
    MorphologicalExtractor(),
]


class FeatureEngine:
    """Orchestrates feature extraction from a single image."""

    def __init__(
        self,
        camera_config: Optional[CameraConfig] = None,
        extractors: Optional[List[FeatureExtractor]] = None,
    ):
        self.loader = ImageLoader(camera_config)
        self.extractors = extractors or DEFAULT_EXTRACTORS

    def extract(self, image_path: str | Path) -> Dict[str, FeatureResult]:
        """Extract all features from an image.

        Returns:
            Dict mapping feature_id to FeatureResult
        """
        image_data = self.loader.prepare(image_path)
        cache: Dict[str, Any] = {}
        results: Dict[str, FeatureResult] = {}

        for extractor in self.extractors:
            raw = extractor.extract(image_data, cache)
            for fid, value in raw.items():
                results[fid] = FeatureResult(feature_id=fid, value=value)

        return results

    def extract_values(self, image_path: str | Path) -> Dict[str, float]:
        """Extract features and return simple id->value dict."""
        results = self.extract(image_path)
        return {fid: fr.value for fid, fr in results.items()}
