from pathlib import Path

from app.dataset.dataset_splitter import DatasetSplitter
from app.dataset.dataset_validator import DatasetValidator
from app.dataset.yolo_exporter import YoloExporter, parse_yolo_label_line


def _write_image(path: Path) -> None:
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 64), "#f5f7fb").save(path)


def _write_label(path: Path, line: str = "0 0.500000 0.500000 0.250000 0.250000") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{line}\n", encoding="utf-8")


def test_dataset_split_uses_configured_ratios(tmp_path) -> None:
    source_dir = tmp_path / "processed"
    dataset_dir = tmp_path / "dataset"

    for index in range(10):
        image_path = source_dir / f"image_{index}.jpg"
        _write_image(image_path)
        _write_label(source_dir / f"image_{index}.txt")

    result = DatasetSplitter(
        dataset_dir=dataset_dir,
        source_images_dir=source_dir,
        source_labels_dir=source_dir,
        raw_dir=tmp_path / "raw",
        exports_dir=tmp_path / "exports",
        random_seed=42,
    ).split()

    assert result.train == 7
    assert result.val == 2
    assert result.test == 1
    assert len(list((dataset_dir / "labels" / "train").glob("*.txt"))) == 7


def test_dataset_yaml_generation(tmp_path) -> None:
    dataset_dir = tmp_path / "dataset"
    output_path = YoloExporter(dataset_dir=dataset_dir).export_dataset_yaml()

    content = output_path.read_text(encoding="utf-8")

    assert "path: dataset" in content
    assert "train: images/train" in content
    assert "0: pole" in content
    assert "11: fiber_cable" in content


def test_dataset_validator_accepts_valid_yolo_dataset(tmp_path) -> None:
    dataset_dir = tmp_path / "dataset"
    _write_image(dataset_dir / "images" / "train" / "image_001.jpg")
    _write_label(dataset_dir / "labels" / "train" / "image_001.txt")

    result = DatasetValidator(
        dataset_dir=dataset_dir,
        exports_dir=tmp_path / "exports",
        previews_dir=tmp_path / "previews",
    ).validate()

    assert result.image_count == 1
    assert result.label_count == 1
    assert result.errors == []
    assert result.report_path.exists()


def test_yolo_label_parser_validates_values() -> None:
    label = parse_yolo_label_line("0 0.5 0.5 0.25 0.25")

    assert label.class_id == 0
    assert label.x_center == 0.5

    try:
        parse_yolo_label_line("99 0.5 0.5 0.25 0.25", class_count=12)
    except ValueError as exc:
        assert "Invalid class_id" in str(exc)
    else:
        raise AssertionError("Invalid class id should raise ValueError.")


def test_missing_label_is_reported_without_crashing(tmp_path) -> None:
    source_dir = tmp_path / "processed"
    dataset_dir = tmp_path / "dataset"
    _write_image(source_dir / "with_label.jpg")
    _write_label(source_dir / "with_label.txt")
    _write_image(source_dir / "without_label.jpg")

    split_result = DatasetSplitter(
        dataset_dir=dataset_dir,
        source_images_dir=source_dir,
        source_labels_dir=source_dir,
        raw_dir=tmp_path / "raw",
        exports_dir=tmp_path / "exports",
        train_ratio=1.0,
        val_ratio=0.0,
        test_ratio=0.0,
    ).split()

    validation_result = DatasetValidator(
        dataset_dir=dataset_dir,
        exports_dir=tmp_path / "exports",
        previews_dir=tmp_path / "previews",
    ).validate()

    assert "without_label.jpg" in split_result.missing_labels
    assert any(issue.code == "image_without_label" for issue in validation_result.warnings)
