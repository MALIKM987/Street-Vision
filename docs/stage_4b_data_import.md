# Etap 4B - import zdjec ulicznych do datasetu

Etap 4B dodaje import zdjec z zewnetrznych zrodel ulicznych do lokalnego datasetu YOLO.

Nie wolno scrapowac Google Maps ani Google Street View. Ten modul nie uzywa Google. Nie zapisuj tokenow w repozytorium i nie commituj folderu `dataset/`.

## Mapillary

Modul korzysta z oficjalnego Mapillary Graph API:

```text
https://graph.mapillary.com/images
```

Pobierane pola:

- `id`
- `geometry`
- `captured_at`
- `compass_angle`
- `thumb_2048_url`
- `sequence`

## Token Mapillary

1. Utworz konto deweloperskie Mapillary / Meta for Developers.
2. Wygeneruj access token z dostepem do Mapillary Graph API.
3. Skopiuj `.env.example` do `.env`.
4. Ustaw token tylko lokalnie:

```text
MAPILLARY_ACCESS_TOKEN=twoj_token_tutaj
```

Plik `.env` jest ignorowany przez Git.

## bbox

`bbox` ma format:

```text
min_lon,min_lat,max_lon,max_lat
```

Przyklad dla fragmentu Warszawy:

```yaml
data_sources:
  mapillary:
    bbox: "21.00,52.22,21.03,52.24"
```

## Uruchomienie importu Mapillary

```powershell
python -m app.data_sources.mapillary_client
```

Wyniki:

```text
dataset/raw/mapillary/
dataset/imports/mapillary_import.csv
```

CSV zawiera:

```text
source,image_id,image_name,lat,lon,captured_at,heading_deg,source_url,local_path,license_note
```

## KartaView

KartaView jest opcjonalne. Domyslnie w `config.yaml` jest wylaczone:

```yaml
data_sources:
  kartaview:
    enabled: false
```

Uruchomienie:

```powershell
python -m app.data_sources.kartaview_client
```

Jesli API nie zwroci danych albo wystapi blad, program zapisze ostrzezenie i zakonczy prace bez awarii.

## Przygotowanie do anotacji

Po imporcie Mapillary mozesz przygotowac obrazy dla LabelImg/CVAT:

```powershell
python -m app.dataset.dataset_builder --source-images-dir dataset/raw/mapillary
```

Nastepnie oznaczaj dane w:

```text
dataset/processed/
```

Po zapisaniu labeli YOLO TXT uruchom:

```powershell
python -m app.dataset.dataset_splitter
python -m app.dataset.dataset_validator
```

## LabelImg

1. Otworz katalog `dataset/processed/`.
2. Ustaw format zapisu na YOLO.
3. Ustaw klasy zgodne z `dataset/dataset.yaml`.
4. Zapisuj pliki `.txt` obok obrazow.
5. Po anotacji uruchom splitter i validator.

## CVAT

1. Utworz projekt z klasami z `dataset/dataset.yaml`.
2. Wgraj obrazy z `dataset/processed/`.
3. Oznacz obiekty bounding boxami.
4. Wyeksportuj anotacje jako YOLO.
5. Umiesc obrazy i labele w strukturze `dataset/images/...` i `dataset/labels/...`.
6. Uruchom validator.

## Zasady Git

Nie commituj:

- `dataset/`
- `.env`
- pobranych zdjec
- modeli `.pt`
- wynikow w `data/output/`

Te sciezki sa ignorowane przez `.gitignore`.
