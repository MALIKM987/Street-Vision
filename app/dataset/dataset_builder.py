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
    source_images: int
    raw_images: int
    processed_images: int
    previews: int
    warnings: list[str]
    report_path: Path

    def to_dict(self) -> dict:
        return {
            "source_images": self.source_images,
            "raw_images": self.raw_images,
            "processed_images": self.processed_images,
            "previews": self.previews,
            "warnings": self.warnings,
            "report_path": str(self.report_path),
        }


class DatasetBuilder:
    """Copies local images into a stable dataset workspace for annotation."""

    def __init__(
        self,
        source_images_dir: Path = settings.images_dir,
        raw_dir: Path = settings.dataset_raw_dir,
        processed_dir: Path = settings.dataset_processed_dir,
        previews_dir: Path = settings.dataset_previews_dir,
        exports_dir: Path = settings.dataset_exports_dir,
        image_size: int = settings.dataset_image_size,
        supported_extensions: tuple[str, ...] = settings.supported_image_extensions,
    ) -> None:
        self.source_images_dir = Path(source_images_dir)
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
        raw_paths: list[Path] = []
        processed_paths: list[Path] = []
        preview_paths: list[Path] = []

        for source_path in source_images:
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

        report_path = self._write_build_report(source_images, raw_paths, processed_paths, preview_paths, warnings)
        return DatasetBuildResult(
            source_images=len(source_images),
            raw_images=len(raw_paths),
            processed_images=len(processed_paths),
            previews=len(preview_paths),
            warnings=warnings,
            report_path=report_path,
        )

    def _find_source_images(self) -> list[Path]:
        if not self.source_images_dir.exists():
            return []

        return sorted(
            path
            for path in self.source_images_dir.iterdir()
            if path.is_file() and path.suffix.lower() in self.supported_extensions
        )

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
        warnings: list[str],
    ) -> Path:
        report_path = self.exports_dir / "build_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "source_images": [str(path) for path in source_images],
            "raw_images": [str(path) for path in raw_paths],
            "processed_images": [str(path) for path in processed_paths],
            "previews": [str(path) for path in preview_paths],
            "warnings": warnings,
        }
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare local images for YOLO annotation.")
    parser.add_argument("--source-images-dir", default=str(settings.images_dir))
    parser.add_argument("--raw-dir", default=str(settings.dataset_raw_dir))
    parser.add_argument("--processed-dir", default=str(settings.dataset_processed_dir))
    parser.add_argument("--previews-dir", default=str(settings.dataset_previews_dir))
    parser.add_argument("--no-resize", action="store_true")
    args = parser.parse_args()

    result = DatasetBuilder(
        source_images_dir=Path(args.source_images_dir),
        raw_dir=Path(args.raw_dir),
        processed_dir=Path(args.processed_dir),
        previews_dir=Path(args.previews_dir),
    ).build(resize=not args.no_resize)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
