"""Judgment engine: per-feature and overall Pass/Fail determination."""
from typing import Dict, Optional
from config.feature_registry import (
    FEATURE_REGISTRY, FeatureSpec, Variability, SpecDirection,
    get_feature, get_critical_features,
)
from config.settings import DEFAULT_SIGMA_MULTIPLIER
from core.data_models import (
    BaselineSpec, BaselineStats, FeatureResult,
    FeatureJudgment, InspectionResult, Judgment, ProcessType,
)


def _compute_spec_bounds(
    stats: BaselineStats,
    spec: FeatureSpec,
    sigma_multiplier: float = DEFAULT_SIGMA_MULTIPLIER,
) -> tuple:
    """Compute (lower, upper) spec bounds from baseline stats.

    STABLE:   mean +/- 2*sigma (bilateral)
    MODERATE: mean +/- 2*sigma (bilateral) but wider tolerance
    VARIABLE: Upper limit only
    """
    mean = stats.mean
    std = stats.std

    if spec.direction == SpecDirection.UPPER:
        return None, mean + sigma_multiplier * std
    else:
        return mean - sigma_multiplier * std, mean + sigma_multiplier * std


class JudgmentEngine:
    """Evaluate features against baseline specification."""

    def __init__(self, sigma_multiplier: float = DEFAULT_SIGMA_MULTIPLIER):
        self.sigma_multiplier = sigma_multiplier
        self._critical_ids = {f.id for f in get_critical_features()}

    def judge_feature(
        self,
        feature_id: str,
        value: float,
        baseline: BaselineSpec,
    ) -> FeatureJudgment:
        """Judge a single feature against baseline."""
        if feature_id not in baseline.stats:
            return FeatureJudgment(
                feature_id=feature_id, value=value, judgment=Judgment.NA
            )

        stats = baseline.stats[feature_id]
        try:
            spec = get_feature(feature_id)
        except KeyError:
            return FeatureJudgment(
                feature_id=feature_id, value=value, judgment=Judgment.NA
            )

        lower, upper = _compute_spec_bounds(stats, spec, self.sigma_multiplier)

        # Determine pass/fail
        passed = True
        deviation = 0.0

        if upper is not None and value > upper:
            passed = False
            deviation = (value - upper) / stats.std if stats.std > 0 else float("inf")
        if lower is not None and value < lower:
            passed = False
            deviation = (lower - value) / stats.std if stats.std > 0 else float("inf")

        return FeatureJudgment(
            feature_id=feature_id,
            value=value,
            lower_spec=lower,
            upper_spec=upper,
            judgment=Judgment.PASS if passed else Judgment.FAIL,
            deviation=deviation,
        )

    def judge_all(
        self,
        features: Dict[str, FeatureResult],
        baseline: BaselineSpec,
        image_path: str = "",
        process_type: ProcessType = ProcessType.DENSIFICATION,
        sample_id: str = "",
    ) -> InspectionResult:
        """Judge all features and produce overall result.

        Overall FAIL if any critical feature fails.
        """
        judgments = {}
        fail_reasons = []

        for fid, fr in features.items():
            jdg = self.judge_feature(fid, fr.value, baseline)
            judgments[fid] = jdg

            if jdg.judgment == Judgment.FAIL:
                is_critical = fid in self._critical_ids
                reason = f"{'[CRITICAL] ' if is_critical else ''}{fid}: {fr.value:.4f} (spec: {jdg.lower_spec}~{jdg.upper_spec})"
                fail_reasons.append(reason)

        # Overall judgment: any critical fail -> NG
        critical_fails = [
            fid for fid, jdg in judgments.items()
            if jdg.judgment == Judgment.FAIL and fid in self._critical_ids
        ]

        if critical_fails:
            overall = Judgment.FAIL
        elif fail_reasons:
            # Non-critical failures only: still PASS but with warnings
            overall = Judgment.PASS
        else:
            overall = Judgment.PASS

        return InspectionResult(
            image_path=str(image_path),
            process_type=process_type,
            sample_id=sample_id,
            features=features,
            judgments=judgments,
            overall_judgment=overall,
            fail_reasons=fail_reasons,
        )
