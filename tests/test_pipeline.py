import json

from app.core.pipeline import AnalysisPipeline


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
