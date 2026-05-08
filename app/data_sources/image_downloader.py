import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.data_sources.source_models import RemoteImageCandidate, SourceImageMetadata


class ImageDownloader:
    """Downloads street-view images while avoiding duplicate local files."""

    def __init__(self, timeout_s: int = 30) -> None:
        self.timeout_s = timeout_s

    def download(self, candidate: RemoteImageCandidate, output_dir: Path) -> tuple[SourceImageMetadata | None, bool, str | None]:
        output_dir.mkdir(parents=True, exist_ok=True)
        image_name = self._image_name(candidate)
        local_path = output_dir / image_name

        if local_path.exists():
            return self._metadata(candidate, image_name, local_path), True, None

        try:
            with urllib.request.urlopen(candidate.download_url, timeout=self.timeout_s) as response:
                local_path.write_bytes(response.read())
        except (OSError, urllib.error.URLError, urllib.error.HTTPError) as exc:
            return None, False, f"Could not download {candidate.image_id}: {exc}"

        return self._metadata(candidate, image_name, local_path), False, None

    def _image_name(self, candidate: RemoteImageCandidate) -> str:
        suffix = self._suffix_from_url(candidate.download_url)
        safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "_", candidate.image_id).strip("_") or "image"
        return f"{candidate.source}_{safe_id}{suffix}"

    def _suffix_from_url(self, url: str) -> str:
        path = urllib.parse.urlparse(url).path
        suffix = Path(path).suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
            return suffix
        return ".jpg"

    def _metadata(
        self,
        candidate: RemoteImageCandidate,
        image_name: str,
        local_path: Path,
    ) -> SourceImageMetadata:
        return SourceImageMetadata(
            source=candidate.source,
            image_id=candidate.image_id,
            image_name=image_name,
            lat=candidate.lat,
            lon=candidate.lon,
            captured_at=candidate.captured_at,
            heading_deg=candidate.heading_deg,
            source_url=candidate.source_url,
            local_path=local_path,
            license_note=candidate.license_note,
        )
