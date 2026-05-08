# Street Vision GIS/AI MVP

Lokalny prototyp aplikacji GIS/AI do automatycznej inwentaryzacji slupow energetycznych oraz wstepnej oceny mozliwosci prowadzenia sieci swiatlowodowej po istniejacej infrastrukturze.

Aplikacja dziala na lokalnych danych:

- zdjecia w `data/images/`,
- metadane GPS w `data/metadata.csv`,
- wyniki w `data/output/`,
- opcjonalny model w `models/pole_detector.pt`.

Projekt nie wykonuje scrapowania Google Maps ani Google Street View. Nie wymaga zewnetrznych kluczy API.

## Etap 1

Etap 1 zawiera:

- strukture projektu Python,
- FastAPI z endpointem health check,
- upload zdjecia,
- analize folderu zdjec,
- import `metadata.csv`,
- mock detekcji,
- eksport `poles.geojson`,
- eksport `network_segments.geojson`,
- raporty CSV i HTML.

## Etap 2

Etap 2 rozbudowuje MVP o:

- `config.yaml`,
- walidacje danych wejsciowych,
- czytelne bledy w konsoli i raporcie HTML,
- tryby detektora `mock` oraz `yolo`,
- fallback z `yolo` do `mock`, gdy nie ma pliku `models/pole_detector.pt`,
- prog `confidence_threshold`,
- generowanie obrazow z naniesionymi bounding boxami w `data/output/annotated/`,
- testy podstawowych modulow.

Tryb `yolo` jest przygotowany jako punkt integracji. Trenowanie i prawdziwa inferencja YOLO nie sa jeszcze implementowane.

## Etap 3

Etap 3 dodaje opcjonalna integracje z `ultralytics` YOLO:

- `PoleDetector` dziala w trybach `mock` oraz `yolo`,
- `ultralytics.YOLO` jest importowane tylko w trybie `yolo`,
- jesli `models/pole_detector.pt` istnieje, aplikacja probuje uzyc tego modelu,
- jesli modelu brakuje, aplikacja probuje uzyc `yolo11n.pt` jako modelu testowego,
- jesli YOLO albo model nie moga zostac zaladowane, aplikacja przechodzi do trybu `mock`,
- surowe detekcje sa zapisywane do `data/output/detections_raw.csv`,
- raport HTML pokazuje tryb detektora, uzyty model, liczbe detekcji YOLO i ostrzezenia.

`yolo11n.pt` jest generycznym modelem COCO. Nie zna klas specjalistycznych takich jak slupy energetyczne, `telecom_box` albo `support_stay`. Uzywaj go tylko do sprawdzenia, czy pipeline inferencji dziala technicznie.

## Wymagania

- Windows 10/11,
- Python 3.11 lub nowszy,
- terminal PowerShell.

## Instalacja lokalna

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Jesli masz aktywny alias `python`, mozesz uzyc:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Uruchomienie analizy

```powershell
python -m app.core.pipeline
```

Alternatywnie:

```powershell
py -3 -m app.core.pipeline
```

Wyniki zostana zapisane do `data/output/`:

- `poles.geojson`,
- `network_segments.geojson`,
- `poles.csv`,
- `network_segments.csv`,
- `detections_raw.csv`,
- `report.html`,
- `annotated/*.png`.

## Uruchomienie API

```powershell
uvicorn main:app --reload
```

Po starcie API:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

Najwazniejsze endpointy:

- `GET /health`
- `POST /images/upload`
- `POST /analysis/folder`
- `GET /results/poles.geojson`
- `GET /results/network_segments.geojson`
- `POST /dataset/build`
- `POST /dataset/split`
- `GET /dataset/status`
- `GET /dataset/validation-report`

## Testy

Po instalacji zaleznosci:

```powershell
python -m pytest
```

Albo:

```powershell
py -3 -m pytest
```

## Dataset preparation

Etap 4 przygotowuje dataset YOLO do przyszlego trenowania wlasnego modelu. Nie uruchamia treningu i nie pobiera danych z internetu.

Struktura:

```text
dataset/
├── raw/
├── processed/
├── images/
│   ├── train/
│   ├── val/
│   └── test/
├── labels/
│   ├── train/
│   ├── val/
│   └── test/
├── exports/
└── previews/
```

Komendy:

```powershell
python -m app.dataset.dataset_builder
python -m app.dataset.dataset_splitter
python -m app.dataset.yolo_exporter
python -m app.dataset.dataset_validator
```

Wyniki:

- `dataset/dataset.yaml`
- `dataset/validation_report.json`
- `dataset/exports/build_report.json`
- `dataset/exports/split_report.json`
- `dataset/exports/dataset_report.html`

Format labela YOLO TXT:

```text
class_id x_center y_center width height
```

Przyklad:

```text
0 0.512000 0.486000 0.120000 0.640000
4 0.430000 0.610000 0.080000 0.120000
```

Wartosci bbox sa znormalizowane do `0..1`. Klasy sa opisane w `dataset/dataset.yaml` oraz w [docs/stage_4.md](docs/stage_4.md).

## Tryb mock

W `config.yaml` ustaw:

```yaml
detector_mode: mock
confidence_threshold: 0.5
max_segment_distance_m: 70
input_images_dir: data/images
metadata_path: data/metadata.csv
output_dir: data/output
model_path: models/pole_detector.pt
yolo_model_path: models/pole_detector.pt
yolo_fallback_model: yolo11n.pt
yolo_allowed_classes:
  - pole
  - double_pole
  - a_frame_pole
  - street_lamp
  - telecom_box
  - cable_loop
  - support_stay
  - pole_number_plate
  - house_number
  - transformer
  - overhead_wire
  - fiber_cable
dataset:
  raw_dir: dataset/raw
  processed_dir: dataset/processed
  train_ratio: 0.7
  val_ratio: 0.2
  test_ratio: 0.1
  image_size: 1280
  random_seed: 42
```

Uruchom:

```powershell
python -m app.core.pipeline
```

## Tryb yolo

Zainstaluj zaleznosci:

```powershell
python -m pip install -r requirements.txt
```

Umiesc wlasny wytrenowany model tutaj:

```text
models/pole_detector.pt
```

Nastepnie ustaw w `config.yaml`:

```yaml
detector_mode: yolo
confidence_threshold: 0.5
max_segment_distance_m: 70
input_images_dir: data/images
metadata_path: data/metadata.csv
output_dir: data/output
model_path: models/pole_detector.pt
yolo_model_path: models/pole_detector.pt
yolo_fallback_model: yolo11n.pt
yolo_allowed_classes:
  - pole
  - double_pole
  - a_frame_pole
  - street_lamp
  - telecom_box
  - cable_loop
  - support_stay
  - pole_number_plate
  - house_number
  - transformer
  - overhead_wire
  - fiber_cable
```

Jesli `models/pole_detector.pt` nie istnieje, aplikacja sprobuje uzyc `yolo11n.pt`. To jest tylko model testowy COCO, nie profesjonalny detektor slupow.
Jesli `yolo11n.pt` nie jest dostepny lokalnie, biblioteka Ultralytics moze probowac go pobrac; w srodowisku offline lub bez `ultralytics` aplikacja zapisze ostrzezenie i przejdzie do mock.

## config.yaml

Przykladowy plik konfiguracyjny:

```yaml
detector_mode: mock
confidence_threshold: 0.5
max_segment_distance_m: 70
input_images_dir: data/images
metadata_path: data/metadata.csv
output_dir: data/output
model_path: models/pole_detector.pt
yolo_model_path: models/pole_detector.pt
yolo_fallback_model: yolo11n.pt
yolo_allowed_classes:
  - pole
  - double_pole
  - a_frame_pole
  - street_lamp
  - telecom_box
  - cable_loop
  - support_stay
  - pole_number_plate
  - house_number
  - transformer
  - overhead_wire
  - fiber_cable
```

Opis pol:

- `detector_mode` - `mock` albo `yolo`.
- `confidence_threshold` - minimalna pewnosc detekcji.
- `max_segment_distance_m` - limit odleglosci miedzy slupami.
- `input_images_dir` - folder ze zdjeciami.
- `metadata_path` - sciezka do CSV z lokalizacjami GPS.
- `output_dir` - folder wynikow.
- `model_path` - przyszla sciezka do modelu YOLO.
- `yolo_model_path` - sciezka do wlasnego modelu YOLO.
- `yolo_fallback_model` - testowy model awaryjny, domyslnie `yolo11n.pt`.
- `yolo_allowed_classes` - klasy akceptowane dla wlasnego modelu slupow.
- `dataset.raw_dir` - kopie oryginalnych obrazow.
- `dataset.processed_dir` - obrazy przygotowane do anotacji.
- `dataset.train_ratio`, `dataset.val_ratio`, `dataset.test_ratio` - podzial datasetu.
- `dataset.image_size` - maksymalny rozmiar boku obrazu w `processed`.
- `dataset.random_seed` - seed powtarzalnego splitu.

## metadata.csv

Wymagane kolumny:

- `image_name`
- `lat`
- `lon`

Przyklad:

```csv
image_name,lat,lon,captured_at,notes
sample_pole_001.png,52.229675,21.012230,2026-05-01T10:00:00,Przykladowy slup przy ulicy
sample_pole_002.png,52.230020,21.012720,2026-05-01T10:02:00,Przykladowy slup z osprzetem
sample_pole_003.png,52.230500,21.013050,2026-05-01T10:04:00,Przykladowy slup do weryfikacji
```

Walidacja sprawdza:

- czy `metadata.csv` istnieje,
- czy ma wymagane kolumny,
- czy zdjecia istnieja w `data/images/`,
- czy `lat` i `lon` sa liczbami,
- czy wspolrzedne sa w poprawnym zakresie.

## Obrazy annotated

Po analizie pipeline tworzy folder:

```text
data/output/annotated/
```

Dla kazdego zdjecia z detekcja powstaje plik, np.:

```text
data/output/annotated/sample_pole_001_annotated.png
```

Na obrazie sa rysowane bounding boxy, nazwa klasy oraz confidence. Dla bardzo malych lub uszkodzonych obrazow funkcja tworzy bezpieczny podglad i nie przerywa analizy.

## Kolejne etapy

1. Integracja prawdziwego YOLO.
2. Integracja OCR, np. EasyOCR albo PaddleOCR.
3. Zapis wynikow do SQLite/PostgreSQL.
4. Frontend React + Leaflet.
5. Reczna korekta i status `confirmed`.
