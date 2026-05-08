import hashlib
import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from shutil import copy2

from app.core.config import settings


@dataclass
class DatasetBuildResult:
    source_dirs: list[Path]
    source_images_total: int
    source_images_by_dir: dict[str, int]
    source_images: int
    raw_images: int
    processed_images: int
    previews: int
    skipped_duplicates: int
    warnings: list[str]
    report_path: Path

    def to_dict(self) -> dict:
        return {
            "source_dirs": [str(path) for path in self.source_dirs],
            "source_images_total": self.source_images_total,
            "source_images_by_dir": self.source_images_by_dir,
            "source_images": self.source_images,
            "raw_images": self.raw_images,
            "processed_images": self.processed_images,
            "previews": self.previews,
            "skipped_duplicates": self.skipped_duplicates,
            "warnings": self.warnings,
            "report_path": str(self.report_path),
        }


class DatasetBuilder:
    """Copies local images into a stable dataset workspace for annotation."""

    def __init__(
        self,
        source_images_dir: Path | None = None,
        source_dirs: list[Path] | tuple[Path, ...] | None = None,
        raw_dir: Path = settings.dataset_raw_dir,
        processed_dir: Path = settings.dataset_processed_dir,
        previews_dir: Path = settings.dataset_previews_dir,
        exports_dir: Path = settings.dataset_exports_dir,
        image_size: int = settings.dataset_image_size,
        supported_extensions: tuple[str, ...] = (".jpg", ".jpeg", ".png"),
    ) -> None:
        if source_dirs is not None:
            self.source_dirs = [Path(path) for path in source_dirs]
        elif source_images_dir is not None:
            self.source_dirs = [Path(source_images_dir)]
        else:
            self.source_dirs = [Path(path) for path in settings.dataset_source_dirs]

        self.raw_dir = Path(raw_dir)
        self.processed_dir = Path(processed_dir)
        self.previews_dir = Path(previews_dir)
        self.exports_dir = Path(exports_dir)
        self.image_size = image_size
        self.supported_extensions = supported_extensions

    def build(self, resize: bool = True) -> DatasetBuildResult:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.previews_dir.mkdir(parents=True, exist_ok=True)

        warnings: list[str] = []
        source_images = self._find_source_images()
        unique_source_images, skipped_duplicates, duplicate_warnings = self._deduplicate_source_images(source_images)
        warnings.extend(duplicate_warnings)
        raw_paths: list[Path] = []
        processed_paths: list[Path] = []
        preview_paths: list[Path] = []

        for source_path in unique_source_images:
            unique_name = self._unique_name(source_path)
            raw_path = self.raw_dir / unique_name
            processed_path = self.processed_dir / unique_name
            preview_path = self.previews_dir / f"{Path(unique_name).stem}_preview.jpg"

            copy2(source_path, raw_path)
            raw_paths.append(raw_path)

            try:
                self._write_processed_image(raw_path, processed_path, resize=resize)
            except Exception as exc:  # noqa: BLE001 - a bad image should not stop dataset preparation.
                warnings.append(f"Could not process {source_path.name}: {exc}. Copied original file.")
                copy2(raw_path, processed_path)
            processed_paths.append(processed_path)

            try:
                self._write_preview(processed_path, preview_path)
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"Could not create preview for {source_path.name}: {exc}.")
            else:
                preview_paths.append(preview_path)

        source_images_by_dir = self._count_images_by_dir(source_images)
        report_path = self._write_build_report(
            source_images=source_images,
            raw_paths=raw_paths,
            processed_paths=processed_paths,
            preview_paths=preview_paths,
            skipped_duplicates=skipped_duplicates,
            source_images_by_dir=source_images_by_dir,
            warnings=warnings,
        )
        return DatasetBuildResult(
            source_dirs=self.source_dirs,
            source_images_total=len(source_images),
            source_images_by_dir=source_images_by_dir,
            source_images=len(source_images),
            raw_images=len(raw_paths),
            processed_images=len(processed_paths),
            previews=len(preview_paths),
            skipped_duplicates=skipped_duplicates,
            warnings=warnings,
            report_path=report_path,
        )

    def _find_source_images(self) -> list[Path]:
        images: list[Path] = []
        for source_dir in self.source_dirs:
            if not source_dir.exists():
                continue

            images.extend(
                path
                for path in source_dir.iterdir()
                if path.is_file() and path.suffix.lower() in self.supported_extensions
            )

        return sorted(images)

    def _deduplicate_source_images(self, source_images: list[Path]) -> tuple[list[Path], int, list[str]]:
        unique_images: list[Path] = []
        seen_names: set[str] = set()
        seen_hashes: set[str] = set()
        warnings: list[str] = []
        skipped = 0

        for source_path in source_images:
            normalized_name = source_path.name.lower()
            if normalized_name in seen_names:
                skipped += 1
                warnings.append(f"Skipped duplicate image name: {source_path}")
                continue

            content_hash = self._file_hash(source_path)
            if content_hash in seen_hashes:
                skipped += 1
                warnings.append(f"Skipped duplicate image content: {source_path}")
                continue

            seen_names.add(normalized_name)
            seen_hashes.add(content_hash)
            unique_images.append(source_path)

        return unique_images, skipped, warnings

    def _file_hash(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _count_images_by_dir(self, source_images: list[Path]) -> dict[str, int]:
        counts = {str(path): 0 for path in self.source_dirs}
        for image_path in source_images:
            source_dir = str(image_path.parent)
            counts[source_dir] = counts.get(source_dir, 0) + 1
        return counts

    def _unique_name(self, source_path: Path) -> str:
        safe_stem = re.sub(r"[^a-zA-Z0-9_-]+", "_", source_path.stem).strip("_") or "image"
        digest = hashlib.sha1(str(source_path.resolve()).encode("utf-8")).hexdigest()[:10]
        return f"{safe_stem}_{digest}{source_path.suffix.lower()}"

    def _write_processed_image(self, raw_path: Path, processed_path: Path, resize: bool) -> None:
        try:
            from PIL import Image, ImageOps
        except ImportError:
            copy2(raw_path, processed_path)
            return

        image = ImageOps.exif_transpose(Image.open(raw_path)).convert("RGB")
        if resize and self.image_size > 0:
            image.thumbnail((self.image_size, self.image_size))
        image.save(processed_path)

    def _write_preview(self, image_path: Path, preview_path: Path) -> None:
        try:
            from PIL import Image, ImageOps
        except ImportError:
            copy2(image_path, preview_path)
            return

        image = ImageOps.exif_transpose(Image.open(image_path)).convert("RGB")
        image.thumbnail((320, 320))
        image.save(preview_path, format="JPEG", quality=85)

    def _write_build_report(
        self,
        source_images: list[Path],
        raw_paths: list[Path],
        processed_paths: list[Path],
        preview_paths: list[Path],
        skipped_duplicates: int,
        source_images_by_dir: dict[str, int],
        warnings: list[str],
    ) -> Path:
        report_path = self.exports_dir / "build_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "source_dirs": [str(path) for path in self.source_dirs],
            "source_images_total": len(source_images),
            "source_images_by_dir": source_images_by_dir,
            "source_images": [str(path) for path in source_images],
            "raw_images": [str(path) for path in raw_paths],
            "processed_images": [str(path) for path in processed_paths],
            "previews": [str(path) for path in preview_paths],
            "skipped_duplicates": skipped_duplicates,
            "warnings": warnings,
        }
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare local images for YOLO annotation.")
    parser.add_argument(
        "--source-images-dir",
        action="append",
        dest="source_images_dirs",
        help="Source image folder. Can be passed multiple times. Defaults to dataset.source_dirs.",
    )
    parser.add_argument("--raw-dir", default=str(settings.dataset_raw_dir))
    parser.add_argument("--processed-dir", default=str(settings.dataset_processed_dir))
    parser.add_argument("--previews-dir", default=str(settings.dataset_previews_dir))
    parser.add_argument("--no-resize", action="store_true")
    args = parser.parse_args()

    result = DatasetBuilder(
        source_dirs=[Path(path) for path in args.source_images_dirs] if args.source_images_dirs else None,
        raw_dir=Path(args.raw_dir),
        processed_dir=Path(args.processed_dir),
        previews_dir=Path(args.previews_dir),
    ).build(resize=not args.no_resize)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
