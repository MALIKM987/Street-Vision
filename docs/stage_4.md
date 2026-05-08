# Etap 4 - przygotowanie datasetu YOLO

Etap 4 przygotowuje projekt pod budowe profesjonalnego datasetu do trenowania wlasnego modelu YOLO. Ten etap nie trenuje modelu i nie pobiera danych z internetu.

## Struktura datasetu

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

Znaczenie katalogow:

- `raw/` - kopie oryginalnych zdjec z `data/images/`.
- `processed/` - obrazy przygotowane do anotacji, opcjonalnie przeskalowane.
- `previews/` - miniaturki do szybkiego przegladu datasetu.
- `images/train`, `images/val`, `images/test` - obrazy po podziale datasetu.
- `labels/train`, `labels/val`, `labels/test` - labele YOLO TXT zsynchronizowane z obrazami.
- `exports/` - raporty pomocnicze, np. `build_report.json`, `split_report.json`, `dataset_report.html`.

## Przygotowanie obrazow

```powershell
python -m app.dataset.dataset_builder
```

Builder:

- kopiuje obrazy z `data/images/` do `dataset/raw/`,
- tworzy stabilne unikalne nazwy plikow,
- zapisuje przygotowane obrazy do `dataset/processed/`,
- generuje miniaturki w `dataset/previews/`.

## Format YOLO TXT

Kazdy obraz powinien miec label o tej samej nazwie bazowej:

```text
dataset/images/train/example.jpg
dataset/labels/train/example.txt
```

Kazda linia pliku `.txt` opisuje jeden obiekt:

```text
class_id x_center y_center width height
```

Wartosci `x_center`, `y_center`, `width`, `height` sa znormalizowane do zakresu `0..1`.

Przyklad:

```text
0 0.512000 0.486000 0.120000 0.640000
4 0.430000 0.610000 0.080000 0.120000
```

Pierwsza linia oznacza klase `0: pole`, druga `4: telecom_box`.

## Klasy datasetu

```text
0: pole
1: double_pole
2: a_frame_pole
3: street_lamp
4: telecom_box
5: cable_loop
6: support_stay
7: pole_number_plate
8: house_number
9: transformer
10: overhead_wire
11: fiber_cable
```

## Podzial train / val / test

```powershell
python -m app.dataset.dataset_splitter
```

Domyslny podzial:

- train: 70%
- val: 20%
- test: 10%

Losowanie jest powtarzalne, bo `random_seed` ma wartosc `42`.

## dataset.yaml

```powershell
python -m app.dataset.yolo_exporter
```

Tworzy plik:

```text
dataset/dataset.yaml
```

Ten plik bedzie uzywany w przyszlym etapie treningu YOLO.

## Walidacja

```powershell
python -m app.dataset.dataset_validator
```

Validator sprawdza:

- labele bez obrazow,
- obrazy bez labeli,
- puste labele,
- bledne klasy,
- bledne bboxy,
- duplikaty nazw,
- obrazy, ktorych nie da sie odczytac.

Wyniki:

```text
dataset/validation_report.json
dataset/exports/dataset_report.html
```

## LabelImg

Praktyczny przeplyw:

1. Uruchom `python -m app.dataset.dataset_builder`.
2. Otworz w LabelImg katalog `dataset/processed/`.
3. Ustaw format zapisu na YOLO.
4. Ustaw liste klas zgodna z `dataset/dataset.yaml`.
5. Zapisuj pliki `.txt` obok obrazow w `dataset/processed/`.
6. Uruchom `python -m app.dataset.dataset_splitter`.
7. Uruchom `python -m app.dataset.dataset_validator`.

## CVAT

Praktyczny przeplyw:

1. Utworz projekt z klasami z sekcji "Klasy datasetu".
2. Wgraj obrazy z `dataset/processed/`.
3. Oznacz obiekty jako bounding boxy.
4. Wyeksportuj anotacje w formacie YOLO.
5. Umiesc obrazy i labele w strukturze `dataset/images/...` oraz `dataset/labels/...`.
6. Uruchom walidator.

## Zasady anotacji

- Oznaczaj widoczna czesc obiektu mozliwie ciasnym bounding boxem.
- Nie zgaduj obiektow zaslonietych w calosci.
- Dla slupow z osprzetem oznacz osobno slup i widoczne elementy, np. `street_lamp`, `telecom_box`, `support_stay`.
- Zachowuj jedna klase dla jednego obiektu.
- Po kazdej turze anotacji uruchamiaj walidator.
