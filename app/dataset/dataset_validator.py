import json
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Literal

from app.core.config import settings
from app.detection.classes import DETECTION_CLASSES
from app.dataset.yolo_exporter import parse_yolo_label_line


IssueSeverity = Literal["error", "warning"]


@dataclass
class DatasetIssue:
    severity: IssueSeverity
    code: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "path": self.path,
        }


@dataclass
class DatasetValidationResult:
    image_count: int
    label_count: int
    split_counts: dict[str, dict[str, int]]
    errors: list[DatasetIssue]
    warnings: list[DatasetIssue]
    report_path: Path
    html_report_path: Path

    def to_dict(self) -> dict:
        return {
            "image_count": self.image_count,
            "label_count": self.label_count,
            "split_counts": self.split_counts,
            "errors": [issue.to_dict() for issue in self.errors],
            "warnings": [issue.to_dict() for issue in self.warnings],
            "report_path": str(self.report_path),
            "html_report_path": str(self.html_report_path),
        }


class DatasetValidator:
    """Validates a YOLO TXT dataset without assuming every image is annotated yet."""

    split_names = ("train", "val", "test")

    def __init__(
        self,
        dataset_dir: Path = settings.dataset_dir,
        exports_dir: Path = settings.dataset_exports_dir,
        previews_dir: Path = settings.dataset_previews_dir,
        class_names: list[str] | tuple[str, ...] = DETECTION_CLASSES,
        supported_extensions: tuple[str, ...] = settings.supported_image_extensions,
    ) -> None:
        self.dataset_dir = Path(dataset_dir)
        self.exports_dir = Path(exports_dir)
        self.previews_dir = Path(previews_dir)
        self.class_names = list(class_names)
        self.supported_extensions = supported_extensions

    def validate(self) -> DatasetValidationResult:
        images_by_split = self._collect_images()
        labels_by_split = self._collect_labels()
        errors: list[DatasetIssue] = []
        warnings: list[DatasetIssue] = []

        self._validate_duplicate_names(images_by_split, "image", errors)
        self._validate_duplicate_names(labels_by_split, "label", errors)
        self._validate_image_label_pairs(images_by_split, labels_by_split, errors, warnings)
        self._validate_label_contents(labels_by_split, errors, warnings)
        self._validate_images_readable(images_by_split, warnings)

        split_counts = {
            split_name: {
                "images": len(images_by_split[split_name]),
                "labels": len(labels_by_split[split_name]),
            }
            for split_name in self.split_names
        }
        image_count = sum(counts["images"] for counts in split_counts.values())
        label_count = sum(counts["labels"] for counts in split_counts.values())

        report_path = self.dataset_dir / "validation_report.json"
        html_report_path = self.exports_dir / "dataset_report.html"
        result = DatasetValidationResult(
            image_count=image_count,
            label_count=label_count,
            split_counts=split_counts,
            errors=errors,
            warnings=warnings,
            report_path=report_path,
            html_report_path=html_report_path,
        )
        self._write_json_report(result)
        self._write_html_report(result)
        return result

    def _collect_images(self) -> dict[str, list[Path]]:
        return {
            split_name: sorted(
                path
                for path in (self.dataset_dir / "images" / split_name).iterdir()
                if path.is_file() and path.suffix.lower() in self.supported_extensions
            )
            if (self.dataset_dir / "images" / split_name).exists()
            else []
            for split_name in self.split_names
        }

    def _collect_labels(self) -> dict[str, list[Path]]:
        return {
            split_name: sorted(
                path
                for path in (self.dataset_dir / "labels" / split_name).iterdir()
                if path.is_file() and path.suffix.lower() == ".txt"
            )
            if (self.dataset_dir / "labels" / split_name).exists()
            else []
            for split_name in self.split_names
        }

    def _validate_duplicate_names(
        self,
        paths_by_split: dict[str, list[Path]],
        kind: str,
        errors: list[DatasetIssue],
    ) -> None:
        seen: dict[str, str] = {}
        for split_name, paths in paths_by_split.items():
            for path in paths:
                normalized = path.name.lower()
                if normalized in seen:
                    errors.append(
                        DatasetIssue(
                            severity="error",
                            code=f"duplicate_{kind}_name",
                            message=f"Duplicate {kind} name in {seen[normalized]} and {split_name}: {path.name}",
                            path=str(path),
                        )
                    )
                seen[normalized] = split_name

    def _validate_image_label_pairs(
        self,
        images_by_split: dict[str, list[Path]],
        labels_by_split: dict[str, list[Path]],
        errors: list[DatasetIssue],
        warnings: list[DatasetIssue],
    ) -> None:
        for split_name in self.split_names:
            image_stems = {path.stem for path in images_by_split[split_name]}
            label_stems = {path.stem for path in labels_by_split[split_name]}

            for label_path in labels_by_split[split_name]:
                if label_path.stem not in image_stems:
                    errors.append(
                        DatasetIssue(
                            severity="error",
                            code="label_without_image",
                            message=f"Label has no matching image in split '{split_name}'.",
                            path=str(label_path),
                        )
                    )

            for image_path in images_by_split[split_name]:
                if image_path.stem not in label_stems:
                    warnings.append(
                        DatasetIssue(
                            severity="warning",
                            code="image_without_label",
                            message=f"Image has no matching YOLO label in split '{split_name}'.",
                            path=str(image_path),
                        )
                    )

    def _validate_label_contents(
        self,
        labels_by_split: dict[str, list[Path]],
        errors: list[DatasetIssue],
        warnings: list[DatasetIssue],
    ) -> None:
        for labels in labels_by_split.values():
            for label_path in labels:
                lines = [
                    line.strip()
                    for line in label_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                if not lines:
                    warnings.append(
                        DatasetIssue(
                            severity="warning",
                            code="empty_label",
                            message="Label file is empty.",
                            path=str(label_path),
                        )
                    )
                    continue

                for line_number, line in enumerate(lines, start=1):
                    try:
                        parse_yolo_label_line(line, class_count=len(self.class_names))
                    except ValueError as exc:
                        errors.append(
                            DatasetIssue(
                                severity="error",
                                code="invalid_yolo_label",
                                message=f"Line {line_number}: {exc}",
                                path=str(label_path),
                            )
                        )

    def _validate_images_readable(
        self,
        images_by_split: dict[str, list[Path]],
        warnings: list[DatasetIssue],
    ) -> None:
        try:
            from PIL import Image
        except ImportError:
            return

        for images in images_by_split.values():
            for image_path in images:
                try:
                    with Image.open(image_path) as image:
                        image.verify()
                except Exception as exc:  # noqa: BLE001
                    warnings.append(
                        DatasetIssue(
                            severity="warning",
                            code="unreadable_image",
                            message=f"Image could not be opened: {exc}",
                            path=str(image_path),
                        )
                    )

    def _write_json_report(self, result: DatasetValidationResult) -> None:
        result.report_path.parent.mkdir(parents=True, exist_ok=True)
        report = result.to_dict()
        report["classes"] = {index: name for index, name in enumerate(self.class_names)}
        result.report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write_html_report(self, result: DatasetValidationResult) -> None:
        result.html_report_path.parent.mkdir(parents=True, exist_ok=True)
        previews = self._preview_html()
        classes = "".join(f"<li>{index}: {escape(name)}</li>" for index, name in enumerate(self.class_names))
        split_rows = "".join(
            "<tr>"
            f"<td>{escape(split_name)}</td>"
            f"<td>{counts['images']}</td>"
            f"<td>{counts['labels']}</td>"
            "</tr>"
            for split_name, counts in result.split_counts.items()
        )
        issue_rows = "".join(
            "<tr>"
            f"<td>{escape(issue.severity)}</td>"
            f"<td>{escape(issue.code)}</td>"
            f"<td>{escape(issue.message)}</td>"
            f"<td>{escape(issue.path or '')}</td>"
            "</tr>"
            for issue in result.errors + result.warnings
        ) or "<tr><td colspan=\"4\">Brak bledow i ostrzezen.</td></tr>"

        html = f"""<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <title>Street Vision - dataset report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 40px; color: #1f2933; }}
    table {{ border-collapse: collapse; margin-bottom: 20px; }}
    th, td {{ border: 1px solid #d9e2ec; padding: 8px 12px; text-align: left; }}
    th {{ background: #f0f4f8; }}
    .thumbs {{ display: flex; gap: 12px; flex-wrap: wrap; }}
    .thumbs img {{ width: 180px; border: 1px solid #d9e2ec; }}
  </style>
</head>
<body>
  <h1>Dataset preparation report</h1>
  <table>
    <tr><th>Metryka</th><th>Wartosc</th></tr>
    <tr><td>Liczba obrazow</td><td>{result.image_count}</td></tr>
    <tr><td>Liczba labeli</td><td>{result.label_count}</td></tr>
    <tr><td>Liczba bledow</td><td>{len(result.errors)}</td></tr>
    <tr><td>Liczba ostrzezen</td><td>{len(result.warnings)}</td></tr>
  </table>
  <h2>Train / val / test</h2>
  <table><tr><th>Split</th><th>Obrazy</th><th>Labele</th></tr>{split_rows}</table>
  <h2>Klasy datasetu</h2>
  <ol>{classes}</ol>
  <h2>Bledy i ostrzezenia</h2>
  <table><tr><th>Typ</th><th>Kod</th><th>Opis</th><th>Plik</th></tr>{issue_rows}</table>
  <h2>Przykladowe miniaturki</h2>
  {previews}
</body>
</html>
"""
        result.html_report_path.write_text(html, encoding="utf-8")

    def _preview_html(self) -> str:
        preview_dir = self.previews_dir
        if not preview_dir.exists():
            return "<p>Brak miniaturek.</p>"

        preview_paths = sorted(path for path in preview_dir.iterdir() if path.is_file())[:8]
        if not preview_paths:
            return "<p>Brak miniaturek.</p>"

        items = []
        for preview_path in preview_paths:
            try:
                relative_path = preview_path.relative_to(self.exports_dir)
            except ValueError:
                relative_path = Path("..") / "previews" / preview_path.name
            path_text = escape(str(relative_path).replace("\\", "/"))
            items.append(f"<a href=\"{path_text}\"><img src=\"{path_text}\" alt=\"{escape(preview_path.name)}\"></a>")
        return f"<div class=\"thumbs\">{''.join(items)}</div>"


def main() -> None:
    result = DatasetValidator().validate()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
