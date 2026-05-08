import hashlib
from pathlib import Path

from app.core.schemas import DetectionResult, ImageRecord, OCRResult


class OCRReader:
    """Mock OCR reader prepared for EasyOCR or PaddleOCR integration."""

    def __init__(self, mode: str = "mock") -> None:
        self.mode = mode

    def read_batch(
        self,
        images: list[ImageRecord],
        detections: list[DetectionResult],
    ) -> list[OCRResult]:
        results: list[OCRResult] = []
        detections_by_image: dict[str, list[DetectionResult]] = {}
        for detection in detections:
            detections_by_image.setdefault(detection.image_name, []).append(detection)

        for image in images:
            results.extend(self.read_image(image, detections_by_image.get(image.image_name, [])))

        return results

    def read_image(self, image: ImageRecord, detections: list[DetectionResult]) -> list[OCRResult]:
        if self.mode != "mock":
            raise NotImplementedError("Only mock OCR is available in Stage 1.")

        plate_detections = [detection for detection in detections if detection.detected_class == "pole_number_plate"]
        results: list[OCRResult] = []

        for detection in plate_detections:
            results.append(
                OCRResult(
                    image_name=image.image_name,
                    text=self._mock_plate_number(image.image_name),
                    confidence=0.86,
                    bbox=detection.bbox,
                )
            )

        return results

    def _mock_plate_number(self, image_name: str) -> str:
        stem = Path(image_name).stem
        digits = "".join(character for character in stem if character.isdigit())
        if digits:
            return f"SV-{int(digits):03d}"

        seed = int(hashlib.sha256(image_name.encode("utf-8")).hexdigest()[:6], 16)
        return f"SV-{seed % 1000:03d}"
