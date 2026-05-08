import hashlib
from pathlib import Path

from app.core.schemas import DetectionResult, ImageRecord
from app.detection.classes import DETECTION_CLASSES


class PoleDetector:
    """Mock detector prepared for a later YOLO implementation."""

    allowed_modes = {"mock", "yolo"}

    def __init__(
        self,
        mode: str = "mock",
        model_path: str | Path | None = None,
        confidence_threshold: float = 0.5,
    ) -> None:
        self.requested_mode = mode
        self.model_path = Path(model_path) if model_path else None
        self.confidence_threshold = confidence_threshold
        self.warnings: list[str] = []
        self.mode = self._resolve_mode(mode)

    def detect_batch(self, images: list[ImageRecord]) -> list[DetectionResult]:
        detections: list[DetectionResult] = []
        for image in images:
            detections.extend(self._filter_by_confidence(self.detect(image)))
        return detections

    def detect(self, image: ImageRecord) -> list[DetectionResult]:
        if self.mode == "yolo":
            return self._detect_yolo(image)
        return self._mock_detect(image)

    def _resolve_mode(self, mode: str) -> str:
        normalized_mode = (mode or "mock").lower().strip()
        if normalized_mode not in self.allowed_modes:
            self.warnings.append(f"Unknown detector mode '{mode}'. Falling back to mock mode.")
            return "mock"

        if normalized_mode == "yolo":
            if self.model_path is None or not self.model_path.exists():
                self.warnings.append(
                    f"YOLO model not found at {self.model_path}. Falling back to mock mode."
                )
                return "mock"

            # Stage 2 prepares the integration point. Real inference will be added later.
            self.warnings.append(
                "YOLO model file exists, but YOLO inference is not implemented yet. Using mock detections."
            )
            return "mock"

        return normalized_mode

    def _detect_yolo(self, image: ImageRecord) -> list[DetectionResult]:
        # Future Stage: load the model from self.model_path and return DetectionResult objects.
        self.warnings.append(f"YOLO detection requested for {image.image_name}, using mock placeholder.")
        return self._mock_detect(image)

    def _mock_detect(self, image: ImageRecord) -> list[DetectionResult]:
        seed = self._seed(image.image_name)
        name = image.image_name.lower()

        if "double" in name:
            pole_class = "double_pole"
        elif "a_frame" in name or "aframe" in name:
            pole_class = "a_frame_pole"
        else:
            pole_class = "pole"

        detections = [
            DetectionResult(
                image_name=image.image_name,
                detected_class=pole_class,
                confidence=round(0.72 + (seed % 23) / 100, 2),
                bbox_x1=410,
                bbox_y1=60,
                bbox_x2=520,
                bbox_y2=720,
            )
        ]

        optional_objects = [
            ("street_lamp", seed % 2 == 0, 0.78, (500, 120, 650, 230)),
            ("telecom_box", seed % 3 == 0, 0.74, (430, 430, 510, 520)),
            ("cable_loop", seed % 5 == 0, 0.68, (390, 300, 455, 370)),
            ("support_stay", seed % 7 == 0, 0.71, (260, 460, 430, 720)),
            ("pole_number_plate", self._has_plate(name, seed), 0.83, (435, 255, 500, 292)),
            ("overhead_wire", True, 0.81, (120, 80, 900, 125)),
            ("fiber_cable", seed % 4 == 0, 0.66, (160, 145, 890, 172)),
        ]

        for detected_class, should_add, confidence, bbox in optional_objects:
            if should_add:
                detections.append(
                    DetectionResult(
                        image_name=image.image_name,
                        detected_class=detected_class,
                        confidence=confidence,
                        bbox_x1=bbox[0],
                        bbox_y1=bbox[1],
                        bbox_x2=bbox[2],
                        bbox_y2=bbox[3],
                    )
                )

        return detections

    def _filter_by_confidence(self, detections: list[DetectionResult]) -> list[DetectionResult]:
        return [
            detection
            for detection in detections
            if detection.confidence >= self.confidence_threshold
        ]

    def _has_plate(self, image_name: str, seed: int) -> bool:
        return "001" in image_name or "plate" in image_name or seed % 4 == 0

    def _seed(self, value: str) -> int:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return int(digest[:8], 16)

    @property
    def supported_classes(self) -> list[str]:
        return DETECTION_CLASSES
