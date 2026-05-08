from pathlib import Path

from app.data_sources.mapillary_client import MapillaryClient
from app.data_sources.metadata_writer import IMPORT_CSV_COLUMNS, MetadataWriter
from app.data_sources.source_models import RemoteImageCandidate, SourceImageMetadata


class FakeDownloader:
    def download(
        self,
        candidate: RemoteImageCandidate,
        output_dir: Path,
    ) -> tuple[SourceImageMetadata | None, bool, str | None]:
        output_dir.mkdir(parents=True, exist_ok=True)
        image_name = f"{candidate.source}_{candidate.image_id}.jpg"
        local_path = output_dir / image_name
        duplicate = local_path.exists()
        if not duplicate:
            local_path.write_bytes(b"fake-image")

        return (
            SourceImageMetadata(
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
            ),
            duplicate,
            None,
        )


def _mapillary_payload() -> dict:
    return {
        "data": [
            {
                "id": "123",
                "geometry": {"type": "Point", "coordinates": [21.0122, 52.2297]},
                "captured_at": "2024-01-01T10:00:00Z",
                "compass_angle": 91.5,
                "thumb_2048_url": "https://images.example/123.jpg",
                "sequence": {"id": "seq-1"},
            }
        ]
    }


def test_mapillary_import_uses_mocked_api_and_writes_csv(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TEST_MAPILLARY_TOKEN", "token")

    client = MapillaryClient(
        token_env="TEST_MAPILLARY_TOKEN",
        bbox="21.00,52.22,21.03,52.24",
        output_dir=tmp_path / "dataset" / "raw" / "mapillary",
        imports_dir=tmp_path / "dataset" / "imports",
        downloader=FakeDownloader(),
        http_get_json=lambda _url, _params: _mapillary_payload(),
        enabled=True,
    )

    result = client.import_images()
    csv_text = result.metadata_csv.read_text(encoding="utf-8")

    assert result.downloaded == 1
    assert result.skipped_duplicates == 0
    assert "mapillary_123.jpg" in csv_text
    assert ",".join(IMPORT_CSV_COLUMNS) in csv_text


def test_mapillary_missing_token_returns_clear_warning(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TEST_MAPILLARY_TOKEN", raising=False)

    client = MapillaryClient(
        token_env="TEST_MAPILLARY_TOKEN",
        output_dir=tmp_path / "dataset" / "raw" / "mapillary",
        imports_dir=tmp_path / "dataset" / "imports",
        downloader=FakeDownloader(),
        http_get_json=lambda _url, _params: _mapillary_payload(),
        enabled=True,
    )

    result = client.import_images()

    assert result.downloaded == 0
    assert any("Missing Mapillary token" in warning for warning in result.warnings)
    assert result.metadata_csv.exists()


def test_metadata_writer_uses_expected_columns(tmp_path) -> None:
    record = SourceImageMetadata(
        source="mapillary",
        image_id="abc",
        image_name="mapillary_abc.jpg",
        lat=52.0,
        lon=21.0,
        captured_at=None,
        heading_deg=None,
        source_url="https://www.mapillary.com/app/?pKey=abc",
        local_path=tmp_path / "mapillary_abc.jpg",
        license_note="license",
    )

    output_path = MetadataWriter().write([record], tmp_path / "imports" / "mapillary_import.csv")
    lines = output_path.read_text(encoding="utf-8").splitlines()

    assert lines[0] == ",".join(IMPORT_CSV_COLUMNS)
    assert "mapillary_abc.jpg" in lines[1]


def test_mapillary_import_skips_duplicate_downloads(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TEST_MAPILLARY_TOKEN", "token")
    downloader = FakeDownloader()
    client = MapillaryClient(
        token_env="TEST_MAPILLARY_TOKEN",
        output_dir=tmp_path / "dataset" / "raw" / "mapillary",
        imports_dir=tmp_path / "dataset" / "imports",
        downloader=downloader,
        http_get_json=lambda _url, _params: _mapillary_payload(),
        enabled=True,
    )

    first = client.import_images()
    second = client.import_images()

    assert first.downloaded == 1
    assert second.downloaded == 0
    assert second.skipped_duplicates == 1


def test_import_folder_structure_is_created(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TEST_MAPILLARY_TOKEN", "token")
    output_dir = tmp_path / "dataset" / "raw" / "mapillary"
    imports_dir = tmp_path / "dataset" / "imports"

    result = MapillaryClient(
        token_env="TEST_MAPILLARY_TOKEN",
        output_dir=output_dir,
        imports_dir=imports_dir,
        downloader=FakeDownloader(),
        http_get_json=lambda _url, _params: _mapillary_payload(),
        enabled=True,
    ).import_images()

    assert output_dir.exists()
    assert imports_dir.exists()
    assert result.metadata_csv == imports_dir / "mapillary_import.csv"
