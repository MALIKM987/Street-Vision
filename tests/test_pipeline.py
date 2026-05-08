import json

from app.core.pipeline import AnalysisPipeline
from app.detection.pole_detector import GENERIC_COCO_WARNING, PoleDetector


def test_pipeline_generates_stage_1_outputs(tmp_path) -> None:
    result = AnalysisPipeline().run(output_dir=tmp_path)

    assert result.summary()["images"] == 3
    assert result.summary()["poles"] == 3
    assert (tmp_path / "poles.geojson").exists()
    assert (tmp_path / "poles.csv").exists()


def test_pipeline_exports_poles_geojson(tmp_path) -> None:
    AnalysisPipeline().run(output_dir=tmp_path)
    geojson = json.loads((tmp_path / "poles.geojson").read_text(encoding="utf-8"))

    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 3
    assert geojson["features"][0]["geometry"]["type"] == "Point"


def test_pipeline_generates_report_and_annotations(tmp_path) -> None:
    result = AnalysisPipeline().run(output_dir=tmp_path)
    report_html = tmp_path / "report.html"

    assert report_html.exists()
    assert "Liczba detekcji" in report_html.read_text(encoding="utf-8")
    assert result.annotated_images
    assert result.annotated_images[0].exists()


def test_pipeline_yolo_missing_model_does_not_break_analysis(tmp_path) -> None:
    pipeline = AnalysisPipeline()
    pipeline.detector = PoleDetector(
        mode="yolo",
        model_path=tmp_path / "missing_custom_model.pt",
        yolo_fallback_model=str(tmp_path / "missing_fallback_model.pt"),
        confidence_threshold=0.5,
    )

    result = pipeline.run(output_dir=tmp_path)

    assert result.summary()["images"] == 3
    assert result.detector_info is not None
    assert result.detector_info.detector_mode_requested == "yolo"
    assert result.detector_info.detector_mode_used == "mock"
    assert GENERIC_COCO_WARNING in result.detector_info.warnings


def test_pipeline_exports_detections_raw_csv(tmp_path) -> None:
    AnalysisPipeline().run(output_dir=tmp_path)
    detections_csv = tmp_path / "detections_raw.csv"

    assert detections_csv.exists()
    text = detections_csv.read_text(encoding="utf-8")
    assert "image_name,class_id,class_name,confidence,bbox_x1,bbox_y1,bbox_x2,bbox_y2,model_path" in text
    assert "sample_pole_001.png" in text
