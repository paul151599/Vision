"""Data models for inspection pipeline."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime


class Judgment(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NA = "N/A"


class ProcessType(str, Enum):
    REACTOR = "Reactor"
    DENSIFICATION = "Densification"


@dataclass
class FeatureResult:
    """Single feature extraction result."""
    feature_id: str
    value: float
    unit: str = ""


@dataclass
class FeatureJudgment:
    """Judgment result for a single feature."""
    feature_id: str
    value: float
    lower_spec: Optional[float] = None
    upper_spec: Optional[float] = None
    judgment: Judgment = Judgment.NA
    deviation: float = 0.0  # how far from nearest spec boundary, in σ units


@dataclass
class BaselineStats:
    """Statistics for a single feature from baseline samples."""
    feature_id: str
    mean: float
    std: float
    min: float
    max: float
    n_samples: int
    values: List[float] = field(default_factory=list)


@dataclass
class BaselineSpec:
    """Complete baseline specification for a process type."""
    process_type: ProcessType
    sample_id: str
    camera_config: Dict[str, float] = field(default_factory=dict)
    stats: Dict[str, BaselineStats] = field(default_factory=dict)
    created_at: str = ""
    n_samples: int = 0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class InspectionResult:
    """Complete inspection result for a single image."""
    image_path: str
    process_type: ProcessType
    sample_id: str
    features: Dict[str, FeatureResult] = field(default_factory=dict)
    judgments: Dict[str, FeatureJudgment] = field(default_factory=dict)
    overall_judgment: Judgment = Judgment.NA
    fail_reasons: List[str] = field(default_factory=list)
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
