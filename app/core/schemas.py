from dataclasses import dataclass
from pathlib import Path
from typing import Literal


PoleStatus = Literal["auto_detected", "needs_review", "confirmed"]
SegmentStatus = Literal["ok", "too_long", "needs_review"]
BBox = tuple[int, int, int, int]


@dataclass
class ValidationIssue:
    message: str
    severity: Literal["warning", "error"] = "error"
    row_number: int | None = None
    image_name: str | None = None

    def format(self) -> str:
        parts = [self.severity.upper()]
        if self.row_number is not None:
            parts.append(f"row {self.row_number}")
        if self.image_name:
            parts.append(self.image_name)
        return f"{' | '.join(parts)}: {self.message}"


@dataclass
class ImageRecord:
    image_name: str
    image_path: Path
    lat: float
    lon: float
    captured_at: str | None = None
    notes: str | None = None


@dataclass
class ImportResult:
    images: list[ImageRecord]
    warnings: list[str]
    validation_errors: list[ValidationIssue]
    metadata_rows: int = 0
    missing_images_count: int = 0
    invalid_rows_count: int = 0


@dataclass
class DetectionResult:
    image_name: str
    detected_class: str
    confidence: float
    bbox_x1: int
    bbox_y1: int
    bbox_x2: int
    bbox_y2: int

    @property
    def bbox(self) -> BBox:
        return (self.bbox_x1, self.bbox_y1, self.bbox_x2, self.bbox_y2)


@dataclass
class OCRResult:
    image_name: str
    text: str
    confidence: float
    bbox: BBox


@dataclass
class PolePoint:
    id: str
    lat: float
    lon: float
    source_image: str
    pole_type: str
    has_lamp: bool
    has_telecom_box: bool
    has_cable_loop: bool
    has_support: bool
    pole_number: str | None
    confidence: float
    status: PoleStatus


@dataclass
class NetworkSegment:
    pole_a_id: str
    pole_b_id: str
    pole_a_lat: float
    pole_a_lon: float
    pole_b_lat: float
    pole_b_lon: float
    distance_m: float
    status: SegmentStatus


@dataclass
class AnalysisRunResult:
    images: list[ImageRecord]
    detections: list[DetectionResult]
    ocr_results: list[OCRResult]
    poles: list[PolePoint]
    segments: list[NetworkSegment]
    warnings: list[str]
    output_files: dict[str, Path]
    validation_errors: list[ValidationIssue]
    metadata_rows: int = 0
    missing_images_count: int = 0
    annotated_images: list[Path] | None = None

    def summary(self) -> dict[str, int | float]:
        total_length = round(sum(segment.distance_m for segment in self.segments), 2)
        return {
            "images": len(self.images),
            "metadata_rows": self.metadata_rows,
            "valid_images": len(self.images),
            "missing_images": self.missing_images_count,
            "validation_errors": len([issue for issue in self.validation_errors if issue.severity == "error"]),
            "detections": len(self.detections),
            "poles": len(self.poles),
            "poles_with_lamp": sum(1 for pole in self.poles if pole.has_lamp),
            "poles_with_telecom_box": sum(1 for pole in self.poles if pole.has_telecom_box),
            "poles_needs_review": sum(1 for pole in self.poles if pole.status == "needs_review"),
            "segments": len(self.segments),
            "annotated_images": len(self.annotated_images or []),
            "total_route_length_m": total_length,
        }

    def to_api_response(self) -> dict:
        return {
            "summary": self.summary(),
            "warnings": self.warnings,
            "validation_errors": [issue.format() for issue in self.validation_errors],
            "output_files": {name: str(path) for name, path in self.output_files.items()},
        }
