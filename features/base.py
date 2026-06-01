"""Abstract base class for feature extractors."""
from abc import ABC, abstractmethod
from typing import Dict, List, Any
import numpy as np


class FeatureExtractor(ABC):
    """Base class for all feature extractors.

    Each extractor receives:
        - image_data: dict from ImageLoader.prepare() with keys like
          'gray', 'bgr', 'R', 'G', 'B', 'R_corr', 'G_corr', 'B_corr'
        - cache: shared dict for intermediate results (cross-extractor sharing)

    Returns:
        Dict[str, float]: feature_id → value
    """

    @abstractmethod
    def feature_ids(self) -> List[str]:
        """Return list of feature IDs this extractor produces."""
        ...

    @abstractmethod
    def extract(self, image_data: Dict[str, np.ndarray], cache: Dict[str, Any]) -> Dict[str, float]:
        """Extract features from image data.

        Args:
            image_data: dict from ImageLoader.prepare()
            cache: shared cache dict for intermediate results

        Returns:
            Dict mapping feature_id to computed value
        """
        ...
