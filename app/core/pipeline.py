import json
from pathlib import Path

from app.core.config import settings
from app.core.data_importer import MetadataImporter, MetadataValidationError
from app.core.schemas import AnalysisRunResult, ValidationIssue
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
            )

        validation_errors = detector_warnings + import_result.validation_errors
        self._print_validation(validation_errors)

        detections = self.detector.detect_batch(import_result.images)
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
        )

    def _print_validation(self, validation_errors: list[ValidationIssue]) -> None:
        for issue in validation_errors:
            print(f"[validation] {issue.format()}")


def main() -> None:
    result = AnalysisPipeline().run()
    print(json.dumps(result.to_api_response(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
