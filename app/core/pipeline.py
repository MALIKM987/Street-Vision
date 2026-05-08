import json
from pathlib import Path

from app.core.config import settings
from app.core.data_importer import MetadataImporter, MetadataValidationError
from app.core.schemas import AnalysisRunResult, DetectorRunInfo, ValidationIssue
from app.detection.annotation import ImageAnnotator
from app.detection.pole_detector import PoleDetector
from app.gis.geojson_exporter import GeoJSONExporter
from app.gis.network_analysis import NetworkAnalyzer
from app.ocr.ocr_reader import OCRReader
from app.reports.report_generator import ReportGenerator


class AnalysisPipeline:
    """Coordinates the full local analysis flow from metadata to exported files."""

    def __init__(self) -> None:
        self.importer = MetadataImporter()
        self.detector = PoleDetector(
            mode=settings.detector_mode,
            model_path=settings.model_path,
            yolo_model_path=settings.yolo_model_path,
            yolo_fallback_model=settings.yolo_fallback_model,
            yolo_allowed_classes=settings.yolo_allowed_classes,
            confidence_threshold=settings.confidence_threshold,
        )
        self.annotator = ImageAnnotator()
        self.ocr_reader = OCRReader(mode="mock")
        self.geojson_exporter = GeoJSONExporter()
        self.network_analyzer = NetworkAnalyzer()
        self.report_generator = ReportGenerator()

    def run(
        self,
        images_dir: Path = settings.images_dir,
        metadata_path: Path = settings.metadata_csv,
        output_dir: Path = settings.output_dir,
        max_span_m: float = settings.max_segment_distance_m,
    ) -> AnalysisRunResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        annotated_dir = output_dir / "annotated"
        detector_warnings = [
            ValidationIssue(message=warning, severity="warning")
            for warning in self.detector.warnings
        ]

        try:
            import_result = self.importer.load(images_dir=images_dir, metadata_path=metadata_path)
        except MetadataValidationError as exc:
            validation_errors = detector_warnings + exc.validation_errors
            self._print_validation(validation_errors)
            output_files = self.report_generator.write_reports(
                output_dir=output_dir,
                images=[],
                poles=[],
                segments=[],
                detections=[],
                validation_errors=validation_errors,
                annotated_images=[],
                metadata_rows=exc.metadata_rows,
                missing_images_count=exc.missing_images_count,
                detector_info=self.detector.get_run_info(),
            )
            return AnalysisRunResult(
                images=[],
                detections=[],
                ocr_results=[],
                poles=[],
                segments=[],
                warnings=[issue.format() for issue in validation_errors],
                output_files=output_files,
                validation_errors=validation_errors,
                metadata_rows=exc.metadata_rows,
                missing_images_count=exc.missing_images_count,
                annotated_images=[],
                detector_info=self.detector.get_run_info(),
            )

        validation_errors = detector_warnings + import_result.validation_errors
        self._print_validation(validation_errors)

        detections = self.detector.detect_batch(import_result.images)
        detector_info = self.detector.get_run_info()
        detector_issues_after_detection = self._detector_warnings_to_issues(detector_info, validation_errors)
        validation_errors.extend(detector_issues_after_detection)
        self._print_validation(detector_issues_after_detection)

        ocr_results = self.ocr_reader.read_batch(import_result.images, detections)
        poles = self.geojson_exporter.build_poles(import_result.images, detections, ocr_results)
        segments = self.network_analyzer.build_segments(poles, max_distance_m=max_span_m)
        annotated_images, annotation_warnings = self.annotator.annotate_batch(
            import_result.images,
            detections,
            annotated_dir,
        )
        annotation_issues = [
            ValidationIssue(message=warning, severity="warning")
            for warning in annotation_warnings
        ]
        validation_errors.extend(annotation_issues)
        self._print_validation(annotation_issues)

        output_files = {
            "poles_geojson": self.geojson_exporter.save_poles_geojson(poles, output_dir / "poles.geojson"),
            "network_segments_geojson": self.network_analyzer.save_segments_geojson(
                segments,
                output_dir / "network_segments.geojson",
            ),
            "annotated_dir": annotated_dir,
        }
        output_files.update(
            self.report_generator.write_reports(
                output_dir=output_dir,
                images=import_result.images,
                poles=poles,
                segments=segments,
                detections=detections,
                validation_errors=validation_errors,
                annotated_images=annotated_images,
                metadata_rows=import_result.metadata_rows,
                missing_images_count=import_result.missing_images_count,
                detector_info=detector_info,
            )
        )

        return AnalysisRunResult(
            images=import_result.images,
            detections=detections,
            ocr_results=ocr_results,
            poles=poles,
            segments=segments,
            warnings=[issue.format() for issue in validation_errors],
            output_files=output_files,
            validation_errors=validation_errors,
            metadata_rows=import_result.metadata_rows,
            missing_images_count=import_result.missing_images_count,
            annotated_images=annotated_images,
            detector_info=detector_info,
        )

    def _print_validation(self, validation_errors: list[ValidationIssue]) -> None:
        for issue in validation_errors:
            print(f"[validation] {issue.format()}")

    def _detector_warnings_to_issues(
        self,
        detector_info: DetectorRunInfo,
        existing_issues: list[ValidationIssue],
    ) -> list[ValidationIssue]:
        existing_messages = {issue.message for issue in existing_issues}
        return [
            ValidationIssue(message=warning, severity="warning")
            for warning in detector_info.warnings
            if warning not in existing_messages
        ]


def main() -> None:
    result = AnalysisPipeline().run()
    print(json.dumps(result.to_api_response(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
