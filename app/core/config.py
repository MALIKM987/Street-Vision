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

    try:
        import yaml
    except ImportError:
        yaml = None

    if yaml is not None:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(loaded, dict):
            return loaded

    meaningful_lines = [
        raw_line
        for raw_line in path.read_text(encoding="utf-8").splitlines()
        if raw_line.strip() and not raw_line.strip().startswith("#")
    ]

    config: dict[str, Any] = {}
    current_top_key: str | None = None

    for index, raw_line in enumerate(meaningful_lines):
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        stripped_line = raw_line.strip()

        if stripped_line.startswith("-") and current_top_key:
            target = config.get(current_top_key)
            if not isinstance(target, list):
                target = []
                config[current_top_key] = target
            target.append(_parse_scalar(stripped_line[1:].strip()))
            continue

        if ":" not in stripped_line:
            continue

        key, value = stripped_line.split(":", 1)
        key = key.strip()
        value = value.strip()

        if indent == 0:
            if value:
                config[key] = _parse_scalar(value)
                current_top_key = key
                continue

            next_line = meaningful_lines[index + 1].strip() if index + 1 < len(meaningful_lines) else ""
            config[key] = [] if next_line.startswith("-") else {}
            current_top_key = key
            continue

        if current_top_key and isinstance(config.get(current_top_key), dict):
            config[current_top_key][key] = _parse_scalar(value)

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

dataset_config = config_values.get("dataset", {})
if not isinstance(dataset_config, dict):
    dataset_config = {}

data_sources_config = config_values.get("data_sources", {})
if not isinstance(data_sources_config, dict):
    data_sources_config = {}

mapillary_config = data_sources_config.get("mapillary", {})
if not isinstance(mapillary_config, dict):
    mapillary_config = {}

kartaview_config = data_sources_config.get("kartaview", {})
if not isinstance(kartaview_config, dict):
    kartaview_config = {}


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
    dataset_dir: Path = BASE_DIR / "dataset"
    dataset_raw_dir: Path = _resolve_path(os.getenv("DATASET_RAW_DIR", dataset_config.get("raw_dir", "dataset/raw")))
    dataset_processed_dir: Path = _resolve_path(
        os.getenv("DATASET_PROCESSED_DIR", dataset_config.get("processed_dir", "dataset/processed"))
    )
    dataset_exports_dir: Path = BASE_DIR / "dataset" / "exports"
    dataset_previews_dir: Path = BASE_DIR / "dataset" / "previews"
    dataset_images_dir: Path = BASE_DIR / "dataset" / "images"
    dataset_labels_dir: Path = BASE_DIR / "dataset" / "labels"
    dataset_train_ratio: float = float(os.getenv("DATASET_TRAIN_RATIO", str(dataset_config.get("train_ratio", 0.7))))
    dataset_val_ratio: float = float(os.getenv("DATASET_VAL_RATIO", str(dataset_config.get("val_ratio", 0.2))))
    dataset_test_ratio: float = float(os.getenv("DATASET_TEST_RATIO", str(dataset_config.get("test_ratio", 0.1))))
    dataset_image_size: int = int(os.getenv("DATASET_IMAGE_SIZE", str(dataset_config.get("image_size", 1280))))
    dataset_random_seed: int = int(os.getenv("DATASET_RANDOM_SEED", str(dataset_config.get("random_seed", 42))))
    imports_dir: Path = BASE_DIR / "dataset" / "imports"
    mapillary_enabled: bool = bool(mapillary_config.get("enabled", True))
    mapillary_access_token_env: str = str(mapillary_config.get("access_token_env", "MAPILLARY_ACCESS_TOKEN"))
    mapillary_bbox: str = str(mapillary_config.get("bbox", "21.00,52.22,21.03,52.24"))
    mapillary_limit: int = int(mapillary_config.get("limit", 50))
    mapillary_output_dir: Path = _resolve_path(mapillary_config.get("output_dir", "dataset/raw/mapillary"))
    kartaview_enabled: bool = bool(kartaview_config.get("enabled", False))
    kartaview_api_base_url: str = os.getenv(
        "KARTAVIEW_API_BASE_URL",
        str(kartaview_config.get("api_base_url", "https://api.openstreetcam.org/2.0")),
    )
    kartaview_lat: float = float(kartaview_config.get("lat", 52.2297))
    kartaview_lon: float = float(kartaview_config.get("lon", 21.0122))
    kartaview_radius_m: int = int(kartaview_config.get("radius_m", 500))
    kartaview_limit: int = int(kartaview_config.get("limit", 50))
    kartaview_output_dir: Path = _resolve_path(kartaview_config.get("output_dir", "dataset/raw/kartaview"))
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
