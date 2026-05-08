from app.core.config import settings
from app.core.data_importer import MetadataImporter


def test_importer_loads_sample_metadata() -> None:
    result = MetadataImporter().load(settings.images_dir, settings.metadata_csv)

    assert len(result.images) == 3
    assert result.images[0].image_name == "sample_pole_001.png"
    assert result.images[0].lat == 52.229675


def test_importer_reports_missing_image(tmp_path) -> None:
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    (images_dir / "existing.png").write_bytes(b"image-placeholder")

    metadata_path = tmp_path / "metadata.csv"
    metadata_path.write_text(
        "image_name,lat,lon\n"
        "existing.png,52.0,21.0\n"
        "missing.png,52.1,21.1\n",
        encoding="utf-8",
    )

    result = MetadataImporter().load(images_dir, metadata_path)

    assert len(result.images) == 1
    assert result.missing_images_count == 1
    assert any("missing.png" in issue.format() for issue in result.validation_errors)
