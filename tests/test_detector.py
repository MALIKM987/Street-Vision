from app.core.config import settings
from app.core.data_importer import MetadataImporter
from app.detection.pole_detector import PoleDetector


def test_pole_detector_mock_returns_detections() -> None:
    image = MetadataImporter().load(settings.images_dir, settings.metadata_csv).images[0]
    detector = PoleDetector(mode="mock", confidence_threshold=0.5)

    detections = detector.detect(image)

    assert detections
    assert detections[0].image_name == image.image_name
    assert detections[0].detected_class in detector.supported_classes
