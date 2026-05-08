import json
import math
from pathlib import Path

from app.core.schemas import NetworkSegment, PolePoint


class NetworkAnalyzer:
    def build_segments(self, poles: list[PolePoint], max_distance_m: float = 70) -> list[NetworkSegment]:
        ordered_poles = sorted(poles, key=lambda pole: pole.id)
        segments: list[NetworkSegment] = []

        for pole_a, pole_b in zip(ordered_poles, ordered_poles[1:]):
            distance_m = round(self.haversine_m(pole_a.lat, pole_a.lon, pole_b.lat, pole_b.lon), 2)
            status = "too_long" if distance_m > max_distance_m else "ok"
            if distance_m == 0:
                status = "needs_review"

            segments.append(
                NetworkSegment(
                    pole_a_id=pole_a.id,
                    pole_b_id=pole_b.id,
                    pole_a_lat=pole_a.lat,
                    pole_a_lon=pole_a.lon,
                    pole_b_lat=pole_b.lat,
                    pole_b_lon=pole_b.lon,
                    distance_m=distance_m,
                    status=status,
                )
            )

        return segments

    def save_segments_geojson(self, segments: list[NetworkSegment], output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.to_feature_collection(segments), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output_path

    def to_feature_collection(self, segments: list[NetworkSegment]) -> dict:
        return {
            "type": "FeatureCollection",
            "features": [self._segment_to_feature(segment) for segment in segments],
        }

    def haversine_m(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        earth_radius_m = 6_371_000
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return earth_radius_m * c

    def _segment_to_feature(self, segment: NetworkSegment) -> dict:
        return {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [segment.pole_a_lon, segment.pole_a_lat],
                    [segment.pole_b_lon, segment.pole_b_lat],
                ],
            },
            "properties": {
                "pole_a_id": segment.pole_a_id,
                "pole_b_id": segment.pole_b_id,
                "distance_m": segment.distance_m,
                "status": segment.status,
            },
        }
