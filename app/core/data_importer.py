import csv
from pathlib import Path

from app.core.config import settings
from app.core.schemas import ImageRecord, ImportResult, ValidationIssue


class MetadataValidationError(ValueError):
    def __init__(
        self,
        message: str,
        validation_errors: list[ValidationIssue],
        metadata_rows: int = 0,
        missing_images_count: int = 0,
    ) -> None:
        super().__init__(message)
        self.validation_errors = validation_errors
        self.metadata_rows = metadata_rows
        self.missing_images_count = missing_images_count


class MetadataImporter:
    """Loads local images and joins them with GPS coordinates from metadata.csv."""

    required_columns = {"image_name", "lat", "lon"}

    def load(
        self,
        images_dir: Path = settings.images_dir,
        metadata_path: Path = settings.metadata_csv,
    ) -> ImportResult:
        images_dir = Path(images_dir)
        metadata_path = self._resolve_metadata_path(images_dir, Path(metadata_path))
        validation_errors: list[ValidationIssue] = []

        if not images_dir.exists():
            validation_errors.append(ValidationIssue(f"Images directory does not exist: {images_dir}"))
            raise MetadataValidationError("Images directory does not exist.", validation_errors)
        if not metadata_path.exists():
            validation_errors.append(ValidationIssue(f"metadata.csv does not exist: {metadata_path}"))
            raise MetadataValidationError("metadata.csv does not exist.", validation_errors)

        image_paths = self._find_images(images_dir)
        images: list[ImageRecord] = []
        warnings: list[str] = []
        seen_in_metadata: set[str] = set()
        metadata_rows = 0
        missing_images_count = 0
        invalid_rows_count = 0

        with metadata_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            missing_columns = self.required_columns - set(reader.fieldnames or [])
            if missing_columns:
                missing = ", ".join(sorted(missing_columns))
                validation_errors.append(
                    ValidationIssue(f"metadata.csv is missing required columns: {missing}")
                )
                raise MetadataValidationError(
                    "metadata.csv is missing required columns.",
                    validation_errors,
                )

            for row_number, row in enumerate(reader, start=2):
                metadata_rows += 1
                image_name = (row.get("image_name") or "").strip()
                seen_in_metadata.add(image_name)

                if not image_name:
                    invalid_rows_count += 1
                    validation_errors.append(ValidationIssue("Missing image_name.", row_number=row_number))
                    continue
                if image_name not in image_paths:
                    missing_images_count += 1
                    validation_errors.append(
                        ValidationIssue(
                            f"Image not found in {images_dir}.",
                            row_number=row_number,
                            image_name=image_name,
                        )
                    )
                    continue

                lat = self._parse_coordinate(row.get("lat"), "lat", row_number, image_name, validation_errors)
                lon = self._parse_coordinate(row.get("lon"), "lon", row_number, image_name, validation_errors)
                if lat is None or lon is None:
                    invalid_rows_count += 1
                    continue
                if not (-90 <= lat <= 90):
                    invalid_rows_count += 1
                    validation_errors.append(
                        ValidationIssue(
                            f"Latitude out of range: {lat}",
                            row_number=row_number,
                            image_name=image_name,
                        )
                    )
                    continue
                if not (-180 <= lon <= 180):
                    invalid_rows_count += 1
                    validation_errors.append(
                        ValidationIssue(
                            f"Longitude out of range: {lon}",
                            row_number=row_number,
                            image_name=image_name,
                        )
                    )
                    continue

                images.append(
                    ImageRecord(
                        image_name=image_name,
                        image_path=image_paths[image_name],
                        lat=lat,
                        lon=lon,
                        captured_at=(row.get("captured_at") or "").strip() or None,
                        notes=(row.get("notes") or "").strip() or None,
                    )
                )

        for file_name in sorted(image_paths):
            if file_name not in seen_in_metadata:
                validation_errors.append(
                    ValidationIssue(
                        "Image exists but is missing in metadata.csv.",
                        severity="warning",
                        image_name=file_name,
                    )
                )

        if not images:
            validation_errors.append(ValidationIssue("No valid images were loaded from metadata.csv."))
            raise MetadataValidationError(
                "No valid images were loaded from metadata.csv.",
                validation_errors,
                metadata_rows=metadata_rows,
                missing_images_count=missing_images_count,
            )

        warnings = [issue.format() for issue in validation_errors]
        return ImportResult(
            images=images,
            warnings=warnings,
            validation_errors=validation_errors,
            metadata_rows=metadata_rows,
            missing_images_count=missing_images_count,
            invalid_rows_count=invalid_rows_count,
        )

    def _find_images(self, images_dir: Path) -> dict[str, Path]:
        return {
            path.name: path
            for path in images_dir.iterdir()
            if path.is_file() and path.suffix.lower() in settings.supported_image_extensions
        }

    def _resolve_metadata_path(self, images_dir: Path, metadata_path: Path) -> Path:
        if metadata_path.exists():
            return metadata_path

        local_metadata = images_dir / "metadata.csv"
        if local_metadata.exists():
            return local_metadata

        return metadata_path

    def _parse_coordinate(
        self,
        value: str | None,
        field_name: str,
        row_number: int,
        image_name: str,
        validation_errors: list[ValidationIssue],
    ) -> float | None:
        try:
            return float((value or "").replace(",", "."))
        except ValueError:
            validation_errors.append(
                ValidationIssue(
                    f"Invalid {field_name}: {value}",
                    row_number=row_number,
                    image_name=image_name,
                )
            )
            return None
