import json
import random
from dataclasses import dataclass
from pathlib import Path
from shutil import copy2

from app.core.config import settings


@dataclass
class DatasetSplitResult:
    train: int
    val: int
    test: int
    missing_labels: list[str]
    report_path: Path

    def to_dict(self) -> dict:
        return {
            "train": self.train,
            "val": self.val,
            "test": self.test,
            "missing_labels": self.missing_labels,
            "report_path": str(self.report_path),
        }


class DatasetSplitter:
    """Splits prepared images and matching YOLO TXT labels into train/val/test."""

    split_names = ("train", "val", "test")

    def __init__(
        self,
        dataset_dir: Path = settings.dataset_dir,
        source_images_dir: Path = settings.dataset_processed_dir,
        source_labels_dir: Path = settings.dataset_processed_dir,
        raw_dir: Path = settings.dataset_raw_dir,
        exports_dir: Path = settings.dataset_exports_dir,
        train_ratio: float = settings.dataset_train_ratio,
        val_ratio: float = settings.dataset_val_ratio,
        test_ratio: float = settings.dataset_test_ratio,
        random_seed: int = settings.dataset_random_seed,
        supported_extensions: tuple[str, ...] = settings.supported_image_extensions,
    ) -> None:
        self.dataset_dir = Path(dataset_dir)
        self.source_images_dir = Path(source_images_dir)
        self.source_labels_dir = Path(source_labels_dir)
        self.raw_dir = Path(raw_dir)
        self.exports_dir = Path(exports_dir)
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.random_seed = random_seed
        self.supported_extensions = supported_extensions

    def split(self) -> DatasetSplitResult:
        self._ensure_split_dirs()
        images = self._find_images()
        shuffled = list(images)
        random.Random(self.random_seed).shuffle(shuffled)

        train_images, val_images, test_images = self._partition(shuffled)
        split_map = {"train": train_images, "val": val_images, "test": test_images}
        missing_labels: list[str] = []

        for split_name, split_images in split_map.items():
            for image_path in split_images:
                target_image = self.dataset_dir / "images" / split_name / image_path.name
                copy2(image_path, target_image)

                label_path = self._find_label_for_image(image_path)
                if label_path is None:
                    missing_labels.append(image_path.name)
                    continue

                target_label = self.dataset_dir / "labels" / split_name / f"{image_path.stem}.txt"
                copy2(label_path, target_label)

        report_path = self._write_report(split_map, missing_labels)
        return DatasetSplitResult(
            train=len(train_images),
            val=len(val_images),
            test=len(test_images),
            missing_labels=missing_labels,
            report_path=report_path,
        )

    def _ensure_split_dirs(self) -> None:
        for split_name in self.split_names:
            (self.dataset_dir / "images" / split_name).mkdir(parents=True, exist_ok=True)
            (self.dataset_dir / "labels" / split_name).mkdir(parents=True, exist_ok=True)

    def _find_images(self) -> list[Path]:
        if self.source_images_dir.exists():
            images = [
                path
                for path in self.source_images_dir.iterdir()
                if path.is_file() and path.suffix.lower() in self.supported_extensions
            ]
            if images:
                return sorted(images)

        if not self.raw_dir.exists():
            return []
        return sorted(
            path
            for path in self.raw_dir.iterdir()
            if path.is_file() and path.suffix.lower() in self.supported_extensions
        )

    def _find_label_for_image(self, image_path: Path) -> Path | None:
        candidates = [
            self.source_labels_dir / f"{image_path.stem}.txt",
            self.raw_dir / f"{image_path.stem}.txt",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _partition(self, images: list[Path]) -> tuple[list[Path], list[Path], list[Path]]:
        total = len(images)
        if total == 0:
            return [], [], []

        ratios = [self.train_ratio, self.val_ratio, self.test_ratio]
        raw_counts = [total * ratio for ratio in ratios]
        counts = [int(count) for count in raw_counts]
        remaining = total - sum(counts)
        fractions = sorted(
            enumerate(raw_counts),
            key=lambda item: item[1] - int(item[1]),
            reverse=True,
        )
        for index, _ in fractions[:remaining]:
            counts[index] += 1

        train_count, val_count, _ = counts

        train_images = images[:train_count]
        val_images = images[train_count : train_count + val_count]
        test_images = images[train_count + val_count :]
        return train_images, val_images, test_images

    def _write_report(self, split_map: dict[str, list[Path]], missing_labels: list[str]) -> Path:
        report_path = self.exports_dir / "split_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "seed": self.random_seed,
            "ratios": {
                "train": self.train_ratio,
                "val": self.val_ratio,
                "test": self.test_ratio,
            },
            "splits": {
                split_name: [path.name for path in split_images]
                for split_name, split_images in split_map.items()
            },
            "missing_labels": missing_labels,
        }
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report_path


def main() -> None:
    result = DatasetSplitter().split()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
