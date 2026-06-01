"""Visualization: Radar chart, Heatmap, Channel overlay."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from typing import List, Optional, Dict

from config.settings import OUTPUT_DIR
from config.feature_registry import FEATURE_REGISTRY, FeatureGroup
from core.data_models import InspectionResult, BaselineSpec


def radar_chart(
    result: InspectionResult,
    baseline: Optional[BaselineSpec] = None,
    output_path: Optional[Path] = None,
) -> Path:
    """Generate radar chart of feature values normalized to baseline."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        output_path = OUTPUT_DIR / f"radar_{Path(result.image_path).stem}.png"

    # Select representative features (one per category)
    categories = []
    values = []
    seen_cats = set()

    for fspec in FEATURE_REGISTRY:
        if fspec.category not in seen_cats and fspec.id in result.features:
            seen_cats.add(fspec.category)
            categories.append(fspec.category)
            val = result.features[fspec.id].value
            if baseline and fspec.id in baseline.stats:
                bm = baseline.stats[fspec.id].mean
                val = val / bm if bm != 0 else 1.0
            values.append(val)

    n = len(categories)
    if n < 3:
        return output_path

    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    values += values[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    ax.plot(angles, values, "o-", linewidth=2, label=Path(result.image_path).stem)
    ax.fill(angles, values, alpha=0.15)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=8)
    ax.set_title("Feature Radar Chart", fontsize=14, pad=20)

    if baseline:
        ref_line = [1.0] * (n + 1)
        ax.plot(angles, ref_line, "--", color="gray", alpha=0.5, label="Baseline")

    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
    fig.savefig(str(output_path), dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def feature_heatmap(
    results: List[InspectionResult],
    baseline: Optional[BaselineSpec] = None,
    output_path: Optional[Path] = None,
) -> Path:
    """Generate heatmap of normalized feature values across images."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        output_path = OUTPUT_DIR / "feature_heatmap.png"

    feature_ids = [f.id for f in FEATURE_REGISTRY]
    image_names = [Path(r.image_path).stem for r in results]

    data = np.zeros((len(results), len(feature_ids)))
    for i, res in enumerate(results):
        for j, fid in enumerate(feature_ids):
            if fid in res.features:
                val = res.features[fid].value
                if baseline and fid in baseline.stats:
                    bm = baseline.stats[fid].mean
                    bs = baseline.stats[fid].std
                    val = (val - bm) / bs if bs > 0 else 0.0
                data[i, j] = val

    fig, ax = plt.subplots(figsize=(20, max(4, len(results))))
    im = ax.imshow(data, aspect="auto", cmap="RdYlGn_r", vmin=-3, vmax=3)
    ax.set_yticks(range(len(image_names)))
    ax.set_yticklabels(image_names, fontsize=8)
    ax.set_xticks(range(len(feature_ids)))
    ax.set_xticklabels(feature_ids, rotation=90, fontsize=6)
    ax.set_title("Feature Deviation Heatmap (sigma units)")
    fig.colorbar(im, ax=ax, shrink=0.6)
    fig.savefig(str(output_path), dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path
