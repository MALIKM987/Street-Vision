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

## Testy

Po instalacji zaleznosci:

```powershell
python -m pytest
```

Albo:

```powershell
py -3 -m pytest
```

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
```

Opis pol:

- `detector_mode` - `mock` albo `yolo`.
- `confidence_threshold` - minimalna pewnosc detekcji.
- `max_segment_distance_m` - limit odleglosci miedzy slupami.
- `input_images_dir` - folder ze zdjeciami.
- `metadata_path` - sciezka do CSV z lokalizacjami GPS.
- `output_dir` - folder wynikow.
- `model_path` - przyszla sciezka do modelu YOLO.

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
