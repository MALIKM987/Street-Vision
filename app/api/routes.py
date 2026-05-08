from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.pipeline import AnalysisPipeline


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
