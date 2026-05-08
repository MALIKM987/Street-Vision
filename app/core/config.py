import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = BASE_DIR / "config.yaml"


def _parse_scalar(value: str) -> Any:
    value = value.strip().strip('"').strip("'")
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def load_config_file(path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Reads the simple flat config.yaml used by this MVP.

    The file intentionally stays simple, so the project does not need PyYAML
    just to load basic key-value settings.
    """

    if not path.exists():
        return {}

    config: dict[str, Any] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue

        key, value = line.split(":", 1)
        config[key.strip()] = _parse_scalar(value)

    return config


def _resolve_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return BASE_DIR / path


config_values = load_config_file()


@dataclass(frozen=True)
class Settings:
    project_name: str = "Street Vision GIS/AI MVP"
    base_dir: Path = BASE_DIR
    data_dir: Path = BASE_DIR / "data"
    images_dir: Path = _resolve_path(os.getenv("INPUT_IMAGES_DIR", config_values.get("input_images_dir", "data/images")))
    videos_dir: Path = BASE_DIR / "data" / "videos"
    gis_dir: Path = BASE_DIR / "data" / "gis"
    output_dir: Path = _resolve_path(os.getenv("OUTPUT_DIR", config_values.get("output_dir", "data/output")))
    models_dir: Path = BASE_DIR / "models"
    metadata_csv: Path = _resolve_path(os.getenv("METADATA_PATH", config_values.get("metadata_path", "data/metadata.csv")))
    model_path: Path = _resolve_path(os.getenv("MODEL_PATH", config_values.get("model_path", "models/pole_detector.pt")))
    detector_mode: str = os.getenv("DETECTOR_MODE", str(config_values.get("detector_mode", "mock")))
    confidence_threshold: float = float(os.getenv("CONFIDENCE_THRESHOLD", str(config_values.get("confidence_threshold", 0.5))))
    max_segment_distance_m: float = float(
        os.getenv("MAX_SEGMENT_DISTANCE_M", str(config_values.get("max_segment_distance_m", 70)))
    )
    max_span_m: float = float(os.getenv("MAX_SPAN_METERS", str(config_values.get("max_segment_distance_m", 70))))
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'output' / 'street_vision.db'}")
    supported_image_extensions: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".tif", ".tiff")


settings = Settings()
