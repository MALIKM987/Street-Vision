from app.core.config import settings
from app.core.data_importer import MetadataImporter
from app.detection.pole_detector import GENERIC_COCO_WARNING, PoleDetector


def test_pole_detector_mock_returns_detections() -> None:
    image = MetadataImporter().load(settings.images_dir, settings.metadata_csv).images[0]
    detector = PoleDetector(mode="mock", confidence_threshold=0.5)

    detections = detector.detect(image)

    assert detections
    assert detections[0].image_name == image.image_name
    assert detections[0].detected_class in detector.supported_classes


def test_pole_detector_yolo_missing_model_falls_back_to_mock(tmp_path) -> None:
    detector = PoleDetector(
        mode="yolo",
        model_path=tmp_path / "missing_custom_model.pt",
        yolo_fallback_model=str(tmp_path / "missing_fallback_model.pt"),
        confidence_threshold=0.5,
    )

    assert detector.mode == "mock"
    assert any("Falling back to mock mode" in warning for warning in detector.warnings)


def test_pole_detector_yolo_fallback_records_generic_model_warning(tmp_path) -> None:
    detector = PoleDetector(
        mode="yolo",
        model_path=tmp_path / "missing_custom_model.pt",
        yolo_fallback_model=str(tmp_path / "missing_fallback_model.pt"),
        confidence_threshold=0.5,
    )

    assert GENERIC_COCO_WARNING in detector.warnings
