# Etap 3

Etap 3 dodaje opcjonalna integracje z Ultralytics YOLO.

Zakres:

1. `ultralytics` w `requirements.txt`.
2. Leniwy import `YOLO` tylko w trybie `yolo`.
3. Uzycie `models/pole_detector.pt`, jesli istnieje.
4. Fallback do `yolo11n.pt`, jesli model lokalny nie istnieje.
5. Fallback do mock, jesli YOLO albo model nie moga zostac zaladowane.
6. Zapisywanie `data/output/detections_raw.csv`.
7. Sekcja detektora w `report.html`.
8. Testy trybu mock, fallbacku YOLO i eksportu raw detections.

`yolo11n.pt` jest generycznym modelem COCO i sluzy tylko do sprawdzenia pipeline inferencji.
