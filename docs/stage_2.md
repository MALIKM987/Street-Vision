# Etap 2

Etap 2 rozszerza lokalny prototyp bez zmiany sposobu uruchamiania Etapu 1.

Zakres:

1. Konfiguracja w `config.yaml`.
2. Walidacja `metadata.csv` oraz lokalnych zdjec.
3. Tryby detektora `mock` i `yolo`.
4. Fallback z `yolo` do `mock`, jesli nie ma `models/pole_detector.pt`.
5. Obrazy z naniesionymi detekcjami w `data/output/annotated/`.
6. Raport HTML z licznikami, bledami walidacji i linkami do obrazow annotated.
7. Testy importu, detektora, GeoJSON i raportu.

Prawdziwe trenowanie i inferencja YOLO pozostaja poza zakresem tego etapu.
