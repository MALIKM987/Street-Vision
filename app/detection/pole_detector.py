import hashlib
from pathlib import Path
from typing import Any

from app.core.schemas import DetectionResult, DetectorRunInfo, ImageRecord
from app.detection.classes import DETECTION_CLASSES


GENERIC_COCO_WARNING = (
    "Fallback YOLO model is generic COCO model and does not detect dedicated power pole classes. "
    "Use it only to test inference pipeline."
)


class PoleDetector:
    """Runs mock detections or optional YOLO inference on local images."""

    allowed_modes = {"mock", "yolo"}

    def __init__(
        self,
        mode: str = "mock",
        model_path: str | Path | None = None,
        yolo_model_path: str | Path | None = None,
        yolo_fallback_model: str = "yolo11n.pt",
        yolo_allowed_classes: list[str] | tuple[str, ...] | None = None,
        confidence_threshold: float = 0.5,
    ) -> None:
        self.requested_mode = mode
        self.model_path = Path(yolo_model_path or model_path) if (yolo_model_path or model_path) else None
        self.yolo_fallback_model = yolo_fallback_model
        self.yolo_allowed_classes = set(yolo_allowed_classes or DETECTION_CLASSES)
        self.confidence_threshold = confidence_threshold
        self.warnings: list[str] = []
        self.model: Any | None = None
        self.model_path_used: str | None = None
        self.number_of_yolo_detections = 0
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
            return self._try_load_yolo()

        return normalized_mode

    def _try_load_yolo(self) -> str:
        model_source = self._select_yolo_model_source()

        try:
            # Keep ultralytics optional: mock mode must work without this package.
            from ultralytics import YOLO
        except Exception as exc:  # noqa: BLE001 - optional dependency.
            self.warnings.append(f"Could not import ultralytics YOLO: {exc}. Falling back to mock mode.")
            return "mock"

        try:
            self.model = YOLO(str(model_source))
            self.model_path_used = str(model_source)
            return "yolo"
        except Exception as exc:  # noqa: BLE001 - loading can fail for many local reasons.
            self.warnings.append(f"Could not load YOLO model '{model_source}': {exc}. Falling back to mock mode.")
            self.model = None
            self.model_path_used = None
            return "mock"

    def _select_yolo_model_source(self) -> str | Path:
        if self.model_path and self.model_path.exists():
            return self.model_path

        if self.model_path:
            self.warnings.append(
                f"Custom YOLO model not found at {self.model_path}. Trying fallback model {self.yolo_fallback_model}."
            )
        else:
            self.warnings.append(f"No custom YOLO model path configured. Trying fallback model {self.yolo_fallback_model}.")

        self.warnings.append(GENERIC_COCO_WARNING)
        return self.yolo_fallback_model

    def _detect_yolo(self, image: ImageRecord) -> list[DetectionResult]:
        if self.model is None:
            self.warnings.append(f"YOLO model is unavailable for {image.image_name}. Using mock detections.")
            return self._mock_detect(image)

        try:
            results = self.model.predict(
                source=str(image.image_path),
                conf=self.confidence_threshold,
                verbose=False,
            )
        except Exception as exc:  # noqa: BLE001 - inference must not stop the local pipeline.
            self.warnings.append(f"YOLO inference failed for {image.image_name}: {exc}. Using mock detections.")
            return self._mock_detect(image)

        detections: list[DetectionResult] = []
        for result in results:
            names = getattr(result, "names", {}) or {}
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue

            for box in boxes:
                class_id = self._to_int(box.cls)
                confidence = self._to_float(box.conf)
                class_name = str(names.get(class_id, class_id))

                if class_name not in self.yolo_allowed_classes and self._using_custom_model():
                    continue
                if confidence < self.confidence_threshold:
                    continue

                x1, y1, x2, y2 = self._extract_xyxy(box)
                detections.append(
                    DetectionResult(
                        image_name=image.image_name,
                        detected_class=class_name,
                        confidence=round(confidence, 4),
                        bbox_x1=x1,
                        bbox_y1=y1,
                        bbox_x2=x2,
                        bbox_y2=y2,
                        class_id=class_id,
                        model_path=self.model_path_used,
                        source="yolo",
                    )
                )

        self.number_of_yolo_detections += len(detections)
        return detections

    def _using_custom_model(self) -> bool:
        return bool(self.model_path and self.model_path.exists() and self.model_path_used == str(self.model_path))

    def _extract_xyxy(self, box: Any) -> tuple[int, int, int, int]:
        xyxy = box.xyxy[0]
        values = xyxy.tolist() if hasattr(xyxy, "tolist") else list(xyxy)
        return tuple(round(float(value)) for value in values[:4])  # type: ignore[return-value]

    def _to_int(self, value: Any) -> int:
        if hasattr(value, "item"):
            return int(value.item())
        if hasattr(value, "tolist"):
            listed = value.tolist()
            if isinstance(listed, list):
                return int(listed[0])
            return int(listed)
        if isinstance(value, list):
            return int(value[0])
        return int(value)

    def _to_float(self, value: Any) -> float:
        if hasattr(value, "item"):
            return float(value.item())
        if hasattr(value, "tolist"):
            listed = value.tolist()
            if isinstance(listed, list):
                return float(listed[0])
            return float(listed)
        if isinstance(value, list):
            return float(value[0])
        return float(value)

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

    def get_run_info(self) -> DetectorRunInfo:
        return DetectorRunInfo(
            detector_mode_requested=self.requested_mode,
            detector_mode_used=self.mode,
            model_path_used=self.model_path_used,
            number_of_yolo_detections=self.number_of_yolo_detections,
            warnings=list(dict.fromkeys(self.warnings)),
        )
