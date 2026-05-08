# Etap 1

Etap 1 buduje lokalny przeplyw MVP:

1. Import zdjec z `data/images/`.
2. Import lokalizacji GPS z `data/metadata.csv`.
3. Mock detekcji obiektow infrastruktury.
4. Mock OCR dla tabliczek numeracyjnych.
5. Eksport punktow slupow do `data/output/poles.geojson`.
6. Analiza odleglosci miedzy kolejnymi slupami.
7. Eksport odcinkow do `data/output/network_segments.geojson`.
8. Raporty CSV i HTML.

Detekcja i OCR sa celowo zamockowane, aby prototyp byl prosty do uruchomienia lokalnie. Interfejs klas jest przygotowany tak, aby w kolejnym etapie podmienic implementacje na YOLO oraz EasyOCR/PaddleOCR.
