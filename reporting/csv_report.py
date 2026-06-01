"""CSV report for SPC integration."""
import csv
from pathlib import Path
from typing import List
from config.settings import OUTPUT_DIR
from config.feature_registry import FEATURE_REGISTRY
from core.data_models import InspectionResult


def generate_csv(
    results: List[InspectionResult],
    output_path: Path | None = None,
) -> Path:
    """Generate CSV with feature values for SPC."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        output_path = OUTPUT_DIR / "inspection_results.csv"

    headers = ["image", "process_type", "overall_judgment"]
    headers += [f.id for f in FEATURE_REGISTRY]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for res in results:
            row = [
                Path(res.image_path).name,
                res.process_type.value,
                res.overall_judgment.value,
            ]
            for fspec in FEATURE_REGISTRY:
                if fspec.id in res.features:
                    row.append(f"{res.features[fspec.id].value:.6f}")
                else:
                    row.append("")
            writer.writerow(row)

    return output_path
