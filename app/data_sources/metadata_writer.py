import csv
from pathlib import Path

from app.data_sources.source_models import SourceImageMetadata


IMPORT_CSV_COLUMNS = [
    "source",
    "image_id",
    "image_name",
    "lat",
    "lon",
    "captured_at",
    "heading_deg",
    "source_url",
    "local_path",
    "license_note",
]


class MetadataWriter:
    """Writes imported street-image metadata in a stable CSV format."""

    def write(self, records: list[SourceImageMetadata], output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=IMPORT_CSV_COLUMNS)
            writer.writeheader()
            for record in records:
                writer.writerow(record.to_csv_row())
        return output_path
