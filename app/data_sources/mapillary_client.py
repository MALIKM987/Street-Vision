import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Any

from app.core.config import settings
from app.data_sources.image_downloader import ImageDownloader
from app.data_sources.metadata_writer import MetadataWriter
from app.data_sources.source_models import DataSourceImportResult, RemoteImageCandidate, SourceImageMetadata


MAPILLARY_GRAPH_IMAGES_URL = "https://graph.mapillary.com/images"
MAPILLARY_LICENSE_NOTE = "Mapillary image metadata and thumbnails are provided by Mapillary Graph API. Check Mapillary terms before training or redistribution."


class MapillaryClient:
    """Imports image thumbnails and metadata from the official Mapillary Graph API."""

    def __init__(
        self,
        token_env: str = settings.mapillary_access_token_env,
        bbox: str = settings.mapillary_bbox,
        limit: int = settings.mapillary_limit,
        output_dir: Path = settings.mapillary_output_dir,
        imports_dir: Path = settings.imports_dir,
        enabled: bool = settings.mapillary_enabled,
        downloader: ImageDownloader | None = None,
        http_get_json: Callable[[str, dict[str, str]], dict[str, Any]] | None = None,
        metadata_writer: MetadataWriter | None = None,
    ) -> None:
        self.token_env = token_env
        self.bbox = bbox
        self.limit = limit
        self.output_dir = Path(output_dir)
        self.imports_dir = Path(imports_dir)
        self.enabled = enabled
        self.downloader = downloader or ImageDownloader()
        self.http_get_json = http_get_json or self._http_get_json
        self.metadata_writer = metadata_writer or MetadataWriter()

    def import_images(self) -> DataSourceImportResult:
        metadata_csv = self.imports_dir / "mapillary_import.csv"
        warnings: list[str] = []
        records: list[SourceImageMetadata] = []

        if not self.enabled:
            warnings.append("Mapillary import is disabled in config.yaml.")
            self.metadata_writer.write(records, metadata_csv)
            return self._result(0, 0, 0, metadata_csv, warnings, records)

        token = os.getenv(self.token_env, "").strip()
        if not token:
            warning = f"Missing Mapillary token. Set environment variable {self.token_env}."
            warnings.append(warning)
            self.metadata_writer.write(records, metadata_csv)
            return self._result(0, 0, 0, metadata_csv, warnings, records)

        try:
            bbox_values = self._parse_bbox(self.bbox)
        except ValueError as exc:
            warnings.append(str(exc))
            self.metadata_writer.write(records, metadata_csv)
            return self._result(0, 0, 0, metadata_csv, warnings, records)

        params = {
            "access_token": token,
            "fields": "id,geometry,captured_at,compass_angle,thumb_2048_url,sequence",
            "bbox": ",".join(str(value) for value in bbox_values),
            "limit": str(self.limit),
        }

        try:
            payload = self.http_get_json(MAPILLARY_GRAPH_IMAGES_URL, params)
        except Exception as exc:  # noqa: BLE001 - API errors must not crash the app.
            warnings.append(f"Mapillary API request failed: {exc}")
            self.metadata_writer.write(records, metadata_csv)
            return self._result(0, 0, 0, metadata_csv, warnings, records)

        candidates = self._parse_candidates(payload)
        skipped_duplicates = 0
        downloaded = 0

        for candidate in candidates:
            record, was_duplicate, warning = self.downloader.download(candidate, self.output_dir)
            if warning:
                warnings.append(warning)
                continue
            if was_duplicate:
                skipped_duplicates += 1
            else:
                downloaded += 1
            if record:
                records.append(record)

        self.metadata_writer.write(records, metadata_csv)
        return self._result(len(candidates), downloaded, skipped_duplicates, metadata_csv, warnings, records)

    def _parse_bbox(self, bbox: str) -> tuple[float, float, float, float]:
        try:
            min_lon, min_lat, max_lon, max_lat = [float(value.strip()) for value in bbox.split(",")]
        except ValueError as exc:
            raise ValueError("Invalid bbox. Expected 'min_lon,min_lat,max_lon,max_lat'.") from exc

        if min_lon >= max_lon or min_lat >= max_lat:
            raise ValueError("Invalid bbox. Minimum longitude/latitude must be smaller than maximum values.")
        if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180 and -90 <= min_lat <= 90 and -90 <= max_lat <= 90):
            raise ValueError("Invalid bbox. Longitude must be -180..180 and latitude must be -90..90.")

        return min_lon, min_lat, max_lon, max_lat

    def _parse_candidates(self, payload: dict[str, Any]) -> list[RemoteImageCandidate]:
        candidates: list[RemoteImageCandidate] = []
        for item in payload.get("data", []):
            image_id = str(item.get("id", "")).strip()
            thumb_url = str(item.get("thumb_2048_url", "")).strip()
            geometry = item.get("geometry") or {}
            coordinates = geometry.get("coordinates") or []

            if not image_id or not thumb_url or len(coordinates) < 2:
                continue

            lon = float(coordinates[0])
            lat = float(coordinates[1])
            source_url = f"https://www.mapillary.com/app/?pKey={urllib.parse.quote(image_id)}"
            sequence = item.get("sequence")
            sequence_id = str(sequence.get("id")) if isinstance(sequence, dict) and sequence.get("id") else None
            candidates.append(
                RemoteImageCandidate(
                    source="mapillary",
                    image_id=image_id,
                    lat=lat,
                    lon=lon,
                    captured_at=str(item.get("captured_at")) if item.get("captured_at") else None,
                    heading_deg=float(item["compass_angle"]) if item.get("compass_angle") is not None else None,
                    download_url=thumb_url,
                    source_url=source_url,
                    license_note=MAPILLARY_LICENSE_NOTE,
                    sequence_id=sequence_id,
                )
            )
        return candidates

    def _http_get_json(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        request_url = f"{url}?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(request_url, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(exc) from exc

    def _result(
        self,
        requested: int,
        downloaded: int,
        skipped_duplicates: int,
        metadata_csv: Path,
        warnings: list[str],
        records: list[SourceImageMetadata],
    ) -> DataSourceImportResult:
        return DataSourceImportResult(
            source="mapillary",
            requested=requested,
            downloaded=downloaded,
            skipped_duplicates=skipped_duplicates,
            metadata_csv=metadata_csv,
            output_dir=self.output_dir,
            warnings=warnings,
            records=records,
        )


def main() -> None:
    result = MapillaryClient().import_images()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
