from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.detection.classes import DETECTION_CLASSES


@dataclass
class YoloLabel:
    class_id: int
    x_center: float
    y_center: float
    width: float
    height: float

    def to_line(self) -> str:
        return (
            f"{self.class_id} "
            f"{self.x_center:.6f} "
            f"{self.y_center:.6f} "
            f"{self.width:.6f} "
            f"{self.height:.6f}"
        )


def parse_yolo_label_line(line: str, class_count: int = len(DETECTION_CLASSES)) -> YoloLabel:
    parts = line.strip().split()
    if len(parts) != 5:
        raise ValueError("YOLO label line must contain 5 values: class_id x_center y_center width height.")

    try:
        class_id = int(parts[0])
        x_center, y_center, width, height = [float(value) for value in parts[1:]]
    except ValueError as exc:
        raise ValueError(f"Invalid numeric value in YOLO label: {line}") from exc

    if class_id < 0 or class_id >= class_count:
        raise ValueError(f"Invalid class_id {class_id}; expected 0..{class_count - 1}.")

    for name, value in {
        "x_center": x_center,
        "y_center": y_center,
        "width": width,
        "height": height,
    }.items():
        if value < 0 or value > 1:
            raise ValueError(f"{name} must be normalized to 0..1, got {value}.")

    if width <= 0 or height <= 0:
        raise ValueError("width and height must be greater than 0.")

    if x_center - width / 2 < 0 or x_center + width / 2 > 1:
        raise ValueError("bbox x range must stay inside 0..1.")
    if y_center - height / 2 < 0 or y_center + height / 2 > 1:
        raise ValueError("bbox y range must stay inside 0..1.")

    return YoloLabel(
        class_id=class_id,
        x_center=x_center,
        y_center=y_center,
        width=width,
        height=height,
    )


class YoloExporter:
    """Writes dataset.yaml for Ultralytics YOLO training/inference tooling."""

    def __init__(
        self,
        dataset_dir: Path = settings.dataset_dir,
        class_names: list[str] | tuple[str, ...] = DETECTION_CLASSES,
    ) -> None:
        self.dataset_dir = Path(dataset_dir)
        self.class_names = list(class_names)

    def export_dataset_yaml(self, output_path: Path | None = None) -> Path:
        output_path = output_path or self.dataset_dir / "dataset.yaml"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        names = "\n".join(f"  {index}: {name}" for index, name in enumerate(self.class_names))
        content = (
            "path: dataset\n"
            "train: images/train\n"
            "val: images/val\n"
            "test: images/test\n\n"
            "names:\n"
            f"{names}\n"
        )
        output_path.write_text(content, encoding="utf-8")
        return output_path


def main() -> None:
    path = YoloExporter().export_dataset_yaml()
    print(f"dataset.yaml written to: {path}")


if __name__ == "__main__":
    main()
