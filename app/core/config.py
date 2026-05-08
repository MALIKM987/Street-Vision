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
    current_list_key: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped_line = raw_line.strip()
        if not stripped_line or stripped_line.startswith("#"):
            continue

        if stripped_line.startswith("-") and current_list_key:
            config[current_list_key].append(_parse_scalar(stripped_line[1:].strip()))
            continue

        if ":" not in stripped_line:
            current_list_key = None
            continue

        key, value = stripped_line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value:
            config[key] = _parse_scalar(value)
            current_list_key = None
        else:
            config[key] = []
            current_list_key = key

    return config


def _resolve_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return BASE_DIR / path


config_values = load_config_file()


DEFAULT_YOLO_ALLOWED_CLASSES = [
    "pole",
    "double_pole",
    "a_frame_pole",
    "street_lamp",
    "telecom_box",
    "cable_loop",
    "support_stay",
    "pole_number_plate",
    "house_number",
    "transformer",
    "overhead_wire",
    "fiber_cable",
]


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
    yolo_model_path: Path = _resolve_path(
        os.getenv("YOLO_MODEL_PATH", config_values.get("yolo_model_path", config_values.get("model_path", "models/pole_detector.pt")))
    )
    yolo_fallback_model: str = os.getenv("YOLO_FALLBACK_MODEL", str(config_values.get("yolo_fallback_model", "yolo11n.pt")))
    yolo_allowed_classes: tuple[str, ...] = tuple(config_values.get("yolo_allowed_classes", DEFAULT_YOLO_ALLOWED_CLASSES))
    detector_mode: str = os.getenv("DETECTOR_MODE", str(config_values.get("detector_mode", "mock")))
    confidence_threshold: float = float(os.getenv("CONFIDENCE_THRESHOLD", str(config_values.get("confidence_threshold", 0.5))))
    max_segment_distance_m: float = float(
        os.getenv("MAX_SEGMENT_DISTANCE_M", str(config_values.get("max_segment_distance_m", 70)))
    )
    max_span_m: float = float(os.getenv("MAX_SPAN_METERS", str(config_values.get("max_segment_distance_m", 70))))
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'output' / 'street_vision.db'}")
    supported_image_extensions: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".tif", ".tiff")


settings = Settings()
