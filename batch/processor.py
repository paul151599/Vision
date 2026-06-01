"""Batch processing: folder-level inspection with progress tracking."""
from pathlib import Path
from typing import List, Optional, Callable
import time

from config.camera import CameraConfig
from core.data_models import InspectionResult, ProcessType, BaselineSpec
from core.feature_engine import FeatureEngine
from core.judgment import JudgmentEngine


class BatchProcessor:
    """Process multiple images in a folder."""

    def __init__(
        self,
        camera_config: Optional[CameraConfig] = None,
        sigma_multiplier: float = 2.0,
    ):
        self.engine = FeatureEngine(camera_config)
        self.judge = JudgmentEngine(sigma_multiplier)

    def process_folder(
        self,
        folder: str | Path,
        baseline: BaselineSpec,
        process_type: ProcessType,
        sample_id: str = "",
        pattern: str = "*.bmp",
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> List[InspectionResult]:
        """Process all matching images in a folder.

        Args:
            folder: Directory containing images
            baseline: Baseline spec for judgment
            process_type: Reactor or Densification
            sample_id: Sample identifier
            pattern: Glob pattern for image files
            progress_callback: Optional callback(current, total, filename)

        Returns:
            List of InspectionResult
        """
        folder = Path(folder)
        images = sorted(folder.glob(pattern))
        results = []

        for i, img_path in enumerate(images):
            if progress_callback:
                progress_callback(i + 1, len(images), img_path.name)

            t0 = time.time()
            features = self.engine.extract(img_path)
            result = self.judge.judge_all(
                features, baseline,
                image_path=str(img_path),
                process_type=process_type,
                sample_id=sample_id,
            )
            elapsed = time.time() - t0
            result.metadata["processing_time_sec"] = round(elapsed, 2)
            results.append(result)

        return results

    def create_baseline(
        self,
        folder: str | Path,
        sample_id: str,
        process_type: ProcessType,
        pattern: str = "*.bmp",
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> "BaselineSpec":
        """Create baseline from all images in a folder."""
        from core.baseline import BaselineManager

        folder = Path(folder)
        images = sorted(folder.glob(pattern))

        manager = BaselineManager(self.engine.loader.camera_config)

        if progress_callback:
            for i, img in enumerate(images):
                progress_callback(i + 1, len(images), img.name)

        return manager.create_from_images(images, sample_id, process_type)
