"""CLI entry point for EUV Pellicle Vision Inspection System."""
import argparse
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.camera import CameraConfig
from config.settings import BASELINE_DIR, OUTPUT_DIR
from core.data_models import ProcessType
from core.baseline import BaselineManager
from core.feature_engine import FeatureEngine
from core.judgment import JudgmentEngine
from batch.processor import BatchProcessor
from reporting.excel_report import generate_report
from reporting.csv_report import generate_csv


def print_progress(current: int, total: int, name: str):
    bar_len = 30
    filled = int(bar_len * current / total)
    bar = "\u2588" * filled + "\u2591" * (bar_len - filled)
    print(f"\r  [{bar}] {current}/{total} {name}", end="", flush=True)
    if current == total:
        print()


def cmd_extract(args):
    """Extract features from a single image."""
    engine = FeatureEngine(CameraConfig())
    print(f"Extracting features from: {args.image}")
    t0 = time.time()
    values = engine.extract_values(args.image)
    elapsed = time.time() - t0
    print(f"  Extracted {len(values)} features in {elapsed:.1f}s\n")

    for fid, val in sorted(values.items()):
        print(f"  {fid:40s} = {val:.6f}")


def cmd_baseline(args):
    """Create baseline from images."""
    process_type = ProcessType(args.process_type)

    folder = Path(args.folder)
    images = sorted(folder.glob(args.pattern))

    if not images:
        print(f"No images found matching '{args.pattern}' in {folder}")
        sys.exit(1)

    print(f"Creating baseline from {len(images)} images ({process_type.value})")
    manager = BaselineManager(CameraConfig())
    baseline = manager.create_from_images(images, args.sample_id, process_type)

    out_path = manager.save(baseline)
    print(f"Baseline saved: {out_path}")
    print(f"  Features: {len(baseline.stats)}")
    print(f"  Samples: {baseline.n_samples}")


def cmd_inspect(args):
    """Inspect images against baseline."""
    process_type = ProcessType(args.process_type)

    # Load baseline
    baseline_path = Path(args.baseline)
    if not baseline_path.exists():
        # Try baselines/ directory
        baseline_path = BASELINE_DIR / args.baseline

    manager = BaselineManager(CameraConfig())
    baseline = manager.load(baseline_path)

    # Process images
    folder = Path(args.folder)
    processor = BatchProcessor(CameraConfig(), sigma_multiplier=args.sigma)

    print(f"Inspecting images in: {folder}")
    results = processor.process_folder(
        folder, baseline, process_type,
        sample_id=args.sample_id,
        pattern=args.pattern,
        progress_callback=print_progress,
    )

    # Generate reports
    if args.excel:
        excel_path = generate_report(results, baseline)
        print(f"Excel report: {excel_path}")

    if args.csv:
        csv_path = generate_csv(results)
        print(f"CSV report: {csv_path}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"Inspection Summary: {len(results)} images")
    print(f"{'='*60}")
    for res in results:
        name = Path(res.image_path).stem
        status = "\u2713 PASS" if res.overall_judgment.value == "PASS" else "\u2717 FAIL"
        fail_count = sum(1 for j in res.judgments.values() if j.judgment.value == "FAIL")
        elapsed = res.metadata.get("processing_time_sec", "?")
        print(f"  {name:50s} {status}  (fails: {fail_count}, {elapsed}s)")
        if res.fail_reasons:
            for reason in res.fail_reasons[:5]:
                print(f"    \u2192 {reason}")


def cmd_import_excel(args):
    """Import baseline from existing Excel file."""
    process_type = ProcessType(args.process_type)
    manager = BaselineManager(CameraConfig())
    baseline = manager.import_from_excel(args.excel, args.sample_id, process_type)
    out_path = manager.save(baseline)
    print(f"Imported baseline: {out_path}")
    print(f"  Features: {len(baseline.stats)}")


def main():
    parser = argparse.ArgumentParser(
        description="EUV Pellicle Surface Vision Inspection System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # extract
    p_extract = sub.add_parser("extract", help="Extract features from a single image")
    p_extract.add_argument("image", help="Path to BMP image")

    # baseline
    p_baseline = sub.add_parser("baseline", help="Create baseline from images")
    p_baseline.add_argument("folder", help="Folder with reference images")
    p_baseline.add_argument("--sample-id", required=True, help="Sample identifier")
    p_baseline.add_argument("--process-type", required=True, choices=["Reactor", "Densification"])
    p_baseline.add_argument("--pattern", default="*.bmp", help="File pattern")

    # inspect
    p_inspect = sub.add_parser("inspect", help="Inspect images against baseline")
    p_inspect.add_argument("folder", help="Folder with images to inspect")
    p_inspect.add_argument("--baseline", required=True, help="Baseline JSON path")
    p_inspect.add_argument("--sample-id", default="", help="Sample identifier")
    p_inspect.add_argument("--process-type", required=True, choices=["Reactor", "Densification"])
    p_inspect.add_argument("--pattern", default="*.bmp", help="File pattern")
    p_inspect.add_argument("--sigma", type=float, default=2.0, help="Sigma multiplier for spec")
    p_inspect.add_argument("--excel", action="store_true", help="Generate Excel report")
    p_inspect.add_argument("--csv", action="store_true", help="Generate CSV report")

    # import-excel
    p_import = sub.add_parser("import-excel", help="Import baseline from Excel")
    p_import.add_argument("excel", help="Path to Excel file")
    p_import.add_argument("--sample-id", required=True, help="Sample identifier")
    p_import.add_argument("--process-type", required=True, choices=["Reactor", "Densification"])

    args = parser.parse_args()

    if args.command == "extract":
        cmd_extract(args)
    elif args.command == "baseline":
        cmd_baseline(args)
    elif args.command == "inspect":
        cmd_inspect(args)
    elif args.command == "import-excel":
        cmd_import_excel(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
