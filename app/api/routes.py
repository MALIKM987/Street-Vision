from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.pipeline import AnalysisPipeline
from app.dataset.dataset_builder import DatasetBuilder
from app.dataset.dataset_splitter import DatasetSplitter
from app.dataset.dataset_validator import DatasetValidator
from app.dataset.yolo_exporter import YoloExporter


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.project_name}


@router.post("/images/upload")
async def upload_image(file: UploadFile = File(...)) -> dict[str, str]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename.")

    filename = Path(file.filename).name
    suffix = Path(filename).suffix.lower()
    if suffix not in settings.supported_image_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported image extension: {suffix}")

    settings.images_dir.mkdir(parents=True, exist_ok=True)
    target_path = settings.images_dir / filename
    target_path.write_bytes(await file.read())

    return {"filename": filename, "saved_to": str(target_path)}


@router.post("/analysis/folder")
def analyze_image_folder(
    images_dir: str | None = None,
    metadata_csv: str | None = None,
    max_span_m: float | None = None,
) -> dict:
    pipeline = AnalysisPipeline()

    try:
        result = pipeline.run(
            images_dir=Path(images_dir) if images_dir else settings.images_dir,
            metadata_path=Path(metadata_csv) if metadata_csv else settings.metadata_csv,
            max_span_m=max_span_m if max_span_m is not None else settings.max_segment_distance_m,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result.to_api_response()


@router.get("/results/poles.geojson")
def download_poles_geojson() -> FileResponse:
    path = settings.output_dir / "poles.geojson"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Run analysis first.")
    return FileResponse(path, media_type="application/geo+json", filename=path.name)


@router.get("/results/network_segments.geojson")
def download_network_segments_geojson() -> FileResponse:
    path = settings.output_dir / "network_segments.geojson"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Run analysis first.")
    return FileResponse(path, media_type="application/geo+json", filename=path.name)


@router.post("/dataset/build")
def build_dataset() -> dict:
    result = DatasetBuilder().build()
    dataset_yaml = YoloExporter().export_dataset_yaml()
    return {
        "build": result.to_dict(),
        "dataset_yaml": str(dataset_yaml),
    }


@router.post("/dataset/split")
def split_dataset() -> dict:
    result = DatasetSplitter().split()
    dataset_yaml = YoloExporter().export_dataset_yaml()
    validation = DatasetValidator().validate()
    return {
        "split": result.to_dict(),
        "dataset_yaml": str(dataset_yaml),
        "validation": validation.to_dict(),
    }


@router.get("/dataset/status")
def dataset_status() -> dict:
    validation_report = settings.dataset_dir / "validation_report.json"
    dataset_yaml = settings.dataset_dir / "dataset.yaml"

    split_counts = {}
    for split_name in ("train", "val", "test"):
        image_dir = settings.dataset_images_dir / split_name
        label_dir = settings.dataset_labels_dir / split_name
        split_counts[split_name] = {
            "images": len([path for path in image_dir.iterdir() if path.is_file()]) if image_dir.exists() else 0,
            "labels": len([path for path in label_dir.iterdir() if path.is_file()]) if label_dir.exists() else 0,
        }

    return {
        "dataset_dir": str(settings.dataset_dir),
        "dataset_yaml_exists": dataset_yaml.exists(),
        "validation_report_exists": validation_report.exists(),
        "split_counts": split_counts,
    }


@router.get("/dataset/validation-report")
def dataset_validation_report() -> FileResponse:
    result = DatasetValidator().validate()
    return FileResponse(result.report_path, media_type="application/json", filename=result.report_path.name)
