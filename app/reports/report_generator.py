import csv
from html import escape
from pathlib import Path

from app.core.schemas import DetectionResult, DetectorRunInfo, ImageRecord, NetworkSegment, PolePoint, ValidationIssue


class ReportGenerator:
    def write_reports(
        self,
        output_dir: Path,
        images: list[ImageRecord],
        poles: list[PolePoint],
        segments: list[NetworkSegment],
        detections: list[DetectionResult] | None = None,
        validation_errors: list[ValidationIssue] | None = None,
        annotated_images: list[Path] | None = None,
        metadata_rows: int | None = None,
        missing_images_count: int = 0,
        detector_info: DetectorRunInfo | None = None,
    ) -> dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)

        poles_csv = self.write_poles_csv(poles, output_dir / "poles.csv")
        segments_csv = self.write_segments_csv(segments, output_dir / "network_segments.csv")
        detections_raw_csv = self.write_detections_raw_csv(detections or [], output_dir / "detections_raw.csv")
        report_html = self.write_html_report(
            images=images,
            poles=poles,
            segments=segments,
            output_path=output_dir / "report.html",
            detections=detections or [],
            validation_errors=validation_errors or [],
            annotated_images=annotated_images or [],
            metadata_rows=metadata_rows if metadata_rows is not None else len(images),
            missing_images_count=missing_images_count,
            output_dir=output_dir,
            detector_info=detector_info,
        )

        return {
            "poles_csv": poles_csv,
            "network_segments_csv": segments_csv,
            "detections_raw_csv": detections_raw_csv,
            "report_html": report_html,
        }

    def write_poles_csv(self, poles: list[PolePoint], output_path: Path) -> Path:
        fieldnames = [
            "id",
            "lat",
            "lon",
            "source_image",
            "pole_type",
            "has_lamp",
            "has_telecom_box",
            "has_cable_loop",
            "has_support",
            "pole_number",
            "confidence",
            "status",
        ]

        with output_path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for pole in poles:
                writer.writerow({field: getattr(pole, field) for field in fieldnames})

        return output_path

    def write_detections_raw_csv(self, detections: list[DetectionResult], output_path: Path) -> Path:
        fieldnames = [
            "image_name",
            "class_id",
            "class_name",
            "confidence",
            "bbox_x1",
            "bbox_y1",
            "bbox_x2",
            "bbox_y2",
            "model_path",
        ]

        with output_path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for detection in detections:
                writer.writerow(
                    {
                        "image_name": detection.image_name,
                        "class_id": "" if detection.class_id is None else detection.class_id,
                        "class_name": detection.detected_class,
                        "confidence": detection.confidence,
                        "bbox_x1": detection.bbox_x1,
                        "bbox_y1": detection.bbox_y1,
                        "bbox_x2": detection.bbox_x2,
                        "bbox_y2": detection.bbox_y2,
                        "model_path": detection.model_path or "",
                    }
                )

        return output_path

    def write_segments_csv(self, segments: list[NetworkSegment], output_path: Path) -> Path:
        fieldnames = ["pole_a_id", "pole_b_id", "distance_m", "status"]

        with output_path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for segment in segments:
                writer.writerow(
                    {
                        "pole_a_id": segment.pole_a_id,
                        "pole_b_id": segment.pole_b_id,
                        "distance_m": segment.distance_m,
                        "status": segment.status,
                    }
                )

        return output_path

    def write_html_report(
        self,
        images: list[ImageRecord],
        poles: list[PolePoint],
        segments: list[NetworkSegment],
        output_path: Path,
        detections: list[DetectionResult] | None = None,
        validation_errors: list[ValidationIssue] | None = None,
        annotated_images: list[Path] | None = None,
        metadata_rows: int | None = None,
        missing_images_count: int = 0,
        output_dir: Path | None = None,
        detector_info: DetectorRunInfo | None = None,
    ) -> Path:
        detections = detections or []
        validation_errors = validation_errors or []
        annotated_images = annotated_images or []
        metadata_rows = metadata_rows if metadata_rows is not None else len(images)
        output_dir = output_dir or output_path.parent
        total_route_length_m = round(sum(segment.distance_m for segment in segments), 2)
        html = f"""<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <title>Street Vision - raport Etap 3</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 40px; color: #1f2933; }}
    table {{ border-collapse: collapse; min-width: 420px; }}
    th, td {{ border: 1px solid #d9e2ec; padding: 8px 12px; text-align: left; }}
    th {{ background: #f0f4f8; }}
    .error {{ color: #b42318; }}
    .warning {{ color: #8a5a00; }}
    .thumbs {{ display: flex; flex-wrap: wrap; gap: 16px; margin-top: 12px; }}
    .thumb {{ width: 220px; }}
    .thumb img {{ max-width: 220px; border: 1px solid #d9e2ec; }}
    code {{ background: #f0f4f8; padding: 2px 5px; }}
  </style>
</head>
<body>
  <h1>Street Vision - raport Etap 3</h1>
  <table>
    <tr><th>Metryka</th><th>Wartosc</th></tr>
    <tr><td>Liczba zdjec w metadata.csv</td><td>{metadata_rows}</td></tr>
    <tr><td>Liczba poprawnych zdjec</td><td>{len(images)}</td></tr>
    <tr><td>Liczba brakujacych zdjec</td><td>{missing_images_count}</td></tr>
    <tr><td>Liczba detekcji</td><td>{len(detections)}</td></tr>
    <tr><td>Liczba wykrytych slupow</td><td>{len(poles)}</td></tr>
    <tr><td>Liczba slupow z lampa</td><td>{sum(1 for pole in poles if pole.has_lamp)}</td></tr>
    <tr><td>Liczba slupow z puszka telekomunikacyjna</td><td>{sum(1 for pole in poles if pole.has_telecom_box)}</td></tr>
    <tr><td>Liczba slupow wymagajacych weryfikacji</td><td>{sum(1 for pole in poles if pole.status == "needs_review")}</td></tr>
    <tr><td>Laczna dlugosc potencjalnej trasy</td><td>{total_route_length_m} m</td></tr>
  </table>
  <h2>Detektor</h2>
  {self._detector_table(detector_info)}
  <h2>Bledy walidacji</h2>
  {self._validation_table(validation_errors)}
  <h2>Obrazy z naniesiona detekcja</h2>
  {self._annotated_images(annotated_images, output_dir)}
  <h2>Odcinki wymagajace uwagi</h2>
  {self._segments_table(segments)}
</body>
</html>
"""
        output_path.write_text(html, encoding="utf-8")
        return output_path

    def _segments_table(self, segments: list[NetworkSegment]) -> str:
        rows = [
            segment
            for segment in segments
            if segment.status in {"too_long", "needs_review"}
        ]
        if not rows:
            return "<p>Brak odcinkow wymagajacych uwagi.</p>"

        table_rows = "\n".join(
            "<tr>"
            f"<td>{escape(segment.pole_a_id)}</td>"
            f"<td>{escape(segment.pole_b_id)}</td>"
            f"<td>{segment.distance_m}</td>"
            f"<td>{escape(segment.status)}</td>"
            "</tr>"
            for segment in rows
        )
        return (
            "<table>"
            "<tr><th>Slup A</th><th>Slup B</th><th>Dystans [m]</th><th>Status</th></tr>"
            f"{table_rows}"
            "</table>"
        )

    def _validation_table(self, validation_errors: list[ValidationIssue]) -> str:
        if not validation_errors:
            return "<p>Brak bledow walidacji.</p>"

        rows = "\n".join(
            "<tr>"
            f"<td class=\"{escape(issue.severity)}\">{escape(issue.severity)}</td>"
            f"<td>{'' if issue.row_number is None else issue.row_number}</td>"
            f"<td>{escape(issue.image_name or '')}</td>"
            f"<td>{escape(issue.message)}</td>"
            "</tr>"
            for issue in validation_errors
        )
        return (
            "<table>"
            "<tr><th>Typ</th><th>Wiersz</th><th>Zdjecie</th><th>Opis</th></tr>"
            f"{rows}"
            "</table>"
        )

    def _annotated_images(self, annotated_images: list[Path], output_dir: Path) -> str:
        if not annotated_images:
            return "<p>Brak wygenerowanych obrazow annotated.</p>"

        items = []
        for image_path in annotated_images:
            try:
                relative_path = image_path.relative_to(output_dir)
            except ValueError:
                relative_path = image_path

            relative = escape(str(relative_path).replace("\\", "/"))
            name = escape(image_path.name)
            items.append(
                "<div class=\"thumb\">"
                f"<a href=\"{relative}\"><img src=\"{relative}\" alt=\"{name}\"></a>"
                f"<div><code>{name}</code></div>"
                "</div>"
            )

        return f"<div class=\"thumbs\">{''.join(items)}</div>"

    def _detector_table(self, detector_info: DetectorRunInfo | None) -> str:
        if detector_info is None:
            return "<p>Brak informacji o detektorze.</p>"

        warnings = detector_info.warnings or []
        warnings_html = "<br>".join(escape(warning) for warning in warnings) if warnings else "Brak ostrzezen."
        return f"""
<table>
  <tr><th>Parametr</th><th>Wartosc</th></tr>
  <tr><td>detector_mode_requested</td><td>{escape(detector_info.detector_mode_requested)}</td></tr>
  <tr><td>detector_mode_used</td><td>{escape(detector_info.detector_mode_used)}</td></tr>
  <tr><td>model_path_used</td><td>{escape(detector_info.model_path_used or '')}</td></tr>
  <tr><td>number_of_yolo_detections</td><td>{detector_info.number_of_yolo_detections}</td></tr>
  <tr><td>warnings</td><td>{warnings_html}</td></tr>
</table>
"""
