import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

from app.core.config import settings
from app.data_sources.image_downloader import ImageDownloader
from app.data_sources.metadata_writer import MetadataWriter
from app.data_sources.source_models import DataSourceImportResult, RemoteImageCandidate, SourceImageMetadata


KARTAVIEW_LICENSE_NOTE = "KartaView import is optional. Check KartaView/OpenStreetCam terms before training or redistribution."


class KartaViewClient:
    """Best-effort importer for optional KartaView/OpenStreetCam image metadata."""

    def __init__(
        self,
        api_base_url: str = settings.kartaview_api_base_url,
        lat: float = settings.kartaview_lat,
        lon: float = settings.kartaview_lon,
        radius_m: int = settings.kartaview_radius_m,
        limit: int = settings.kartaview_limit,
        output_dir: Path = settings.kartaview_output_dir,
        imports_dir: Path = settings.imports_dir,
        enabled: bool = settings.kartaview_enabled,
        downloader: ImageDownloader | None = None,
        http_get_json: Callable[[str, dict[str, str]], dict[str, Any]] | None = None,
        metadata_writer: MetadataWriter | None = None,
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.lat = lat
        self.lon = lon
        self.radius_m = radius_m
        self.limit = limit
        self.output_dir = Path(output_dir)
        self.imports_dir = Path(imports_dir)
        self.enabled = enabled
        self.downloader = downloader or ImageDownloader()
        self.http_get_json = http_get_json or self._http_get_json
        self.metadata_writer = metadata_writer or MetadataWriter()

    def import_images(self) -> DataSourceImportResult:
        metadata_csv = self.imports_dir / "kartaview_import.csv"
        warnings: list[str] = []
        records: list[SourceImageMetadata] = []

        if not self.enabled:
            warnings.append("KartaView import is disabled in config.yaml.")
            self.metadata_writer.write(records, metadata_csv)
            return self._result(0, 0, 0, metadata_csv, warnings, records)

        if not (-90 <= self.lat <= 90 and -180 <= self.lon <= 180):
            warnings.append("Invalid KartaView lat/lon configuration.")
            self.metadata_writer.write(records, metadata_csv)
            return self._result(0, 0, 0, metadata_csv, warnings, records)

        params = {
            "lat": str(self.lat),
            "lon": str(self.lon),
            "radius": str(self.radius_m),
            "limit": str(self.limit),
        }
        url = f"{self.api_base_url}/photo/"

        try:
            payload = self.http_get_json(url, params)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"KartaView API request failed: {exc}")
            self.metadata_writer.write(records, metadata_csv)
            return self._result(0, 0, 0, metadata_csv, warnings, records)

        candidates = self._parse_candidates(payload)
        if not candidates:
            warnings.append("KartaView API returned no importable images.")

        downloaded = 0
        skipped_duplicates = 0
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

    def _parse_candidates(self, payload: dict[str, Any]) -> list[RemoteImageCandidate]:
        raw_items = payload.get("result") or payload.get("data") or payload.get("currentPageItems") or []
        if isinstance(raw_items, dict):
            raw_items = raw_items.get("data") or raw_items.get("items") or []

        candidates: list[RemoteImageCandidate] = []
        for item in raw_items:
            image_id = str(item.get("id") or item.get("photoId") or item.get("sequenceId") or "").strip()
            lat = item.get("lat") or item.get("latitude")
            lon = item.get("lon") or item.get("lng") or item.get("longitude")
            download_url = item.get("thumbName") or item.get("procImg") or item.get("image_url") or item.get("url")
            if not image_id or lat is None or lon is None or not download_url:
                continue

            candidates.append(
                RemoteImageCandidate(
                    source="kartaview",
                    image_id=image_id,
                    lat=float(lat),
                    lon=float(lon),
                    captured_at=str(item.get("dateAdded") or item.get("captured_at") or "") or None,
                    heading_deg=float(item["heading"]) if item.get("heading") is not None else None,
                    download_url=str(download_url),
                    source_url=str(item.get("url") or "https://kartaview.org/"),
                    license_note=KARTAVIEW_LICENSE_NOTE,
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
            source="kartaview",
            requested=requested,
            downloaded=downloaded,
            skipped_duplicates=skipped_duplicates,
            metadata_csv=metadata_csv,
            output_dir=self.output_dir,
            warnings=warnings,
            records=records,
        )


def main() -> None:
    result = KartaViewClient().import_images()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
