from pathlib import Path
from shutil import copyfile

from app.core.schemas import DetectionResult, ImageRecord


FALLBACK_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x04\x00\x00\x00\xb5\x1c\x0c\x02\x00\x00\x00\x0bIDATx\xdac\xfc\xff"
    b"\x1f\x00\x03\x03\x02\x00\xef\xbf\xa7\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
)


class ImageAnnotator:
    """Creates local preview images with detection bounding boxes."""

    def annotate_batch(
        self,
        images: list[ImageRecord],
        detections: list[DetectionResult],
        output_dir: Path,
    ) -> tuple[list[Path], list[str]]:
        output_dir.mkdir(parents=True, exist_ok=True)
        detections_by_image: dict[str, list[DetectionResult]] = {}
        for detection in detections:
            detections_by_image.setdefault(detection.image_name, []).append(detection)

        annotated_paths: list[Path] = []
        warnings: list[str] = []

        for image in images:
            image_detections = detections_by_image.get(image.image_name, [])
            if not image_detections:
                continue

            target_path = output_dir / f"{Path(image.image_name).stem}_annotated.png"
            try:
                self.annotate_image(image.image_path, image_detections, target_path)
                annotated_paths.append(target_path)
            except Exception as exc:  # noqa: BLE001 - annotation must not stop analysis.
                warnings.append(f"Could not annotate {image.image_name}: {exc}")
                self._write_fallback_image(image.image_path, target_path)
                if target_path.exists():
                    annotated_paths.append(target_path)

        return annotated_paths, warnings

    def annotate_image(
        self,
        image_path: Path,
        detections: list[DetectionResult],
        output_path: Path,
    ) -> Path:
        try:
            from PIL import Image, ImageDraw, ImageFont, ImageOps
        except ImportError as exc:
            self._write_fallback_image(image_path, output_path)
            raise RuntimeError("Pillow is not installed; copied fallback image without drawn boxes.") from exc

        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            image = ImageOps.exif_transpose(Image.open(image_path)).convert("RGB")
        except Exception:
            image = Image.new("RGB", (1024, 768), "#f5f7fb")

        # The bundled sample images are tiny placeholders, so make a readable canvas.
        if image.width < 100 or image.height < 100:
            image = Image.new("RGB", (1024, 768), "#f5f7fb")

        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()

        for detection in detections:
            x1, y1, x2, y2 = self._clamp_bbox(detection, image.width, image.height)
            label = f"{detection.detected_class} {detection.confidence:.2f}"

            draw.rectangle((x1, y1, x2, y2), outline="#ff2d55", width=3)
            text_bbox = draw.textbbox((x1, y1), label, font=font)
            label_y = max(0, y1 - (text_bbox[3] - text_bbox[1]) - 6)
            label_bbox = (x1, label_y, x1 + (text_bbox[2] - text_bbox[0]) + 8, y1)
            draw.rectangle(label_bbox, fill="#ff2d55")
            draw.text((x1 + 4, label_y + 2), label, fill="white", font=font)

        image.save(output_path)
        return output_path

    def _clamp_bbox(self, detection: DetectionResult, width: int, height: int) -> tuple[int, int, int, int]:
        x1 = max(0, min(width - 1, detection.bbox_x1))
        y1 = max(0, min(height - 1, detection.bbox_y1))
        x2 = max(0, min(width - 1, detection.bbox_x2))
        y2 = max(0, min(height - 1, detection.bbox_y2))

        if x2 <= x1:
            x2 = min(width - 1, x1 + 1)
        if y2 <= y1:
            y2 = min(height - 1, y1 + 1)

        return x1, y1, x2, y2

    def _write_fallback_image(self, image_path: Path, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            copyfile(image_path, output_path)
        except Exception:
            output_path.write_bytes(FALLBACK_PNG)
