from dataclasses import dataclass
from pathlib import Path


@dataclass
class SourceImageMetadata:
    source: str
    image_id: str
    image_name: str
    lat: float
    lon: float
    captured_at: str | None
    heading_deg: float | None
    source_url: str
    local_path: Path
    license_note: str

    def to_csv_row(self) -> dict[str, str]:
        return {
            "source": self.source,
            "image_id": self.image_id,
            "image_name": self.image_name,
            "lat": str(self.lat),
            "lon": str(self.lon),
            "captured_at": self.captured_at or "",
            "heading_deg": "" if self.heading_deg is None else str(self.heading_deg),
            "source_url": self.source_url,
            "local_path": str(self.local_path),
            "license_note": self.license_note,
        }


@dataclass
class DataSourceImportResult:
    source: str
    requested: int
    downloaded: int
    skipped_duplicates: int
    metadata_csv: Path
    output_dir: Path
    warnings: list[str]
    records: list[SourceImageMetadata]

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "requested": self.requested,
            "downloaded": self.downloaded,
            "skipped_duplicates": self.skipped_duplicates,
            "metadata_csv": str(self.metadata_csv),
            "output_dir": str(self.output_dir),
            "warnings": self.warnings,
            "records": [record.to_csv_row() for record in self.records],
        }


@dataclass
class RemoteImageCandidate:
    source: str
    image_id: str
    lat: float
    lon: float
    captured_at: str | None
    heading_deg: float | None
    download_url: str
    source_url: str
    license_note: str
    sequence_id: str | None = None
