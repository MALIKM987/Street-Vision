import json
from pathlib import Path

from app.core.schemas import DetectionResult, ImageRecord, OCRResult, PolePoint
from app.detection.classes import POLE_CLASSES


class GeoJSONExporter:
    def build_poles(
        self,
        images: list[ImageRecord],
        detections: list[DetectionResult],
        ocr_results: list[OCRResult],
    ) -> list[PolePoint]:
        detections_by_image: dict[str, list[DetectionResult]] = {}
        ocr_by_image: dict[str, list[OCRResult]] = {}

        for detection in detections:
            detections_by_image.setdefault(detection.image_name, []).append(detection)
        for ocr_result in ocr_results:
            ocr_by_image.setdefault(ocr_result.image_name, []).append(ocr_result)

        poles: list[PolePoint] = []
        for image in images:
            image_detections = detections_by_image.get(image.image_name, [])
            main_pole = self._select_main_pole(image_detections)
            if main_pole is None:
                continue

            pole_number = None
            if ocr_by_image.get(image.image_name):
                pole_number = ocr_by_image[image.image_name][0].text

            status = "auto_detected" if main_pole.confidence >= 0.8 else "needs_review"
            poles.append(
                PolePoint(
                    id=f"P{len(poles) + 1:04d}",
                    lat=image.lat,
                    lon=image.lon,
                    source_image=image.image_name,
                    pole_type=main_pole.detected_class,
                    has_lamp=self._has_detection(image_detections, "street_lamp"),
                    has_telecom_box=self._has_detection(image_detections, "telecom_box"),
                    has_cable_loop=self._has_detection(image_detections, "cable_loop"),
                    has_support=self._has_detection(image_detections, "support_stay"),
                    pole_number=pole_number,
                    confidence=main_pole.confidence,
                    status=status,
                )
            )

        return poles

    def save_poles_geojson(self, poles: list[PolePoint], output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.to_feature_collection(poles), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output_path

    def to_feature_collection(self, poles: list[PolePoint]) -> dict:
        return {
            "type": "FeatureCollection",
            "features": [self._pole_to_feature(pole) for pole in poles],
        }

    def _pole_to_feature(self, pole: PolePoint) -> dict:
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [pole.lon, pole.lat],
            },
            "properties": {
                "id": pole.id,
                "lat": pole.lat,
                "lon": pole.lon,
                "source_image": pole.source_image,
                "pole_type": pole.pole_type,
                "has_lamp": pole.has_lamp,
                "has_telecom_box": pole.has_telecom_box,
                "has_cable_loop": pole.has_cable_loop,
                "has_support": pole.has_support,
                "pole_number": pole.pole_number,
                "confidence": pole.confidence,
                "status": pole.status,
            },
        }

    def _select_main_pole(self, detections: list[DetectionResult]) -> DetectionResult | None:
        pole_detections = [detection for detection in detections if detection.detected_class in POLE_CLASSES]
        if not pole_detections:
            return None
        return max(pole_detections, key=lambda detection: detection.confidence)

    def _has_detection(self, detections: list[DetectionResult], detected_class: str) -> bool:
        return any(detection.detected_class == detected_class for detection in detections)
