import hashlib
import json
import math
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass
class Stop:
    name: str
    lat: float
    lng: float
    input_order: int
    display_name: str = ""

    def as_dict(self, route_order: int) -> Dict[str, object]:
        return {
            "name": self.name,
            "display_name": self.display_name or self.name,
            "lat": self.lat,
            "lng": self.lng,
            "input_order": self.input_order,
            "route_order": route_order,
        }


_COORD_RE = re.compile(r"^\s*(?P<lat>-?\d+(?:\.\d+)?)\s*,\s*(?P<lng>-?\d+(?:\.\d+)?)\s*$")


def parse_stop_line(line: str) -> Tuple[str, Optional[Tuple[float, float]]]:
    """Parse either 'Name' or 'Name | lat,lng' or 'lat,lng'."""
    raw = line.strip()
    if "|" in raw:
        name, coord_text = [part.strip() for part in raw.split("|", 1)]
        match = _COORD_RE.match(coord_text)
        if match:
            return name or coord_text, (float(match.group("lat")), float(match.group("lng")))
        return raw, None

    match = _COORD_RE.match(raw)
    if match:
        return raw, (float(match.group("lat")), float(match.group("lng")))
    return raw, None


def fallback_coordinates(name: str) -> Tuple[float, float]:
    """Return deterministic coordinates near Manhattan for offline/local runs."""
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()
    lat_bits = int(digest[:8], 16)
    lng_bits = int(digest[8:16], 16)
    lat = 40.730610 + ((lat_bits % 20000) - 10000) / 100000.0
    lng = -73.935242 + ((lng_bits % 20000) - 10000) / 100000.0
    return round(lat, 6), round(lng, 6)


def online_geocode(name: str) -> Optional[Tuple[float, float, str]]:
    if os.environ.get("ROUTE_WHISPER_ENABLE_ONLINE_GEOCODING", "1") in {"0", "false", "False"}:
        return None

    params = urlencode({"q": name, "format": "json", "limit": 1})
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    user_agent = os.environ.get("NOMINATIM_USER_AGENT", "route-whisper-mvp")
    try:
        request = Request(url, headers={"User-Agent": user_agent})
        with urlopen(request, timeout=4) as response:
            data = json.loads(response.read().decode("utf-8"))
        if not data:
            return None
        result = data[0]
        time.sleep(0.1)
        return float(result["lat"]), float(result["lon"]), result.get("display_name", name)
    except Exception:
        return None


def geocode_stops(raw_stops: str) -> List[Stop]:
    stops: List[Stop] = []
    for idx, line in enumerate([line.strip() for line in raw_stops.splitlines() if line.strip()], start=1):
        name, coords = parse_stop_line(line)
        display_name = name
        if coords is None:
            geocoded = online_geocode(name)
            if geocoded:
                lat, lng, display_name = geocoded
            else:
                lat, lng = fallback_coordinates(name)
        else:
            lat, lng = coords
        stops.append(Stop(name=name, lat=lat, lng=lng, input_order=idx, display_name=display_name))
    return stops


def haversine_km(a: Stop, b: Stop) -> float:
    radius_km = 6371.0
    lat1, lon1 = math.radians(a.lat), math.radians(a.lng)
    lat2, lon2 = math.radians(b.lat), math.radians(b.lng)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * radius_km * math.asin(math.sqrt(h))


def total_distance_km(stops: Sequence[Stop]) -> float:
    return sum(haversine_km(stops[i], stops[i + 1]) for i in range(len(stops) - 1))


def resolve_anchor_index(stops: Sequence[Stop], anchor_stop: str) -> int:
    anchor = (anchor_stop or "").strip().lower()
    if not anchor:
        return 0
    if anchor.isdigit():
        requested = int(anchor)
        if 1 <= requested <= len(stops):
            return requested - 1
    for idx, stop in enumerate(stops):
        if anchor == stop.name.lower() or anchor in stop.name.lower() or anchor in stop.display_name.lower():
            return idx
    return 0


def nearest_neighbor(stops: Sequence[Stop], start_index: int = 0) -> List[Stop]:
    if not stops:
        return []
    unvisited = list(stops)
    current = unvisited.pop(start_index)
    route = [current]
    while unvisited:
        next_idx, next_stop = min(enumerate(unvisited), key=lambda item: haversine_km(current, item[1]))
        route.append(next_stop)
        current = next_stop
        unvisited.pop(next_idx)
    return route


def two_opt(route: Sequence[Stop], max_passes: int = 2, lock_start: bool = True) -> List[Stop]:
    best = list(route)
    if len(best) < 4:
        return best

    start_i = 1 if lock_start else 0
    passes = 0
    improved = True
    while improved and passes < max_passes:
        improved = False
        passes += 1
        for i in range(start_i, len(best) - 2):
            for j in range(i + 2, len(best)):
                candidate = best[:i] + list(reversed(best[i:j])) + best[j:]
                if total_distance_km(candidate) + 0.000001 < total_distance_km(best):
                    best = candidate
                    improved = True
    return best


def optimize_route(stops: Sequence[Stop], preferences: Optional[Dict[str, object]] = None) -> List[Stop]:
    prefs = preferences or {}
    anchor_index = resolve_anchor_index(stops, str(prefs.get("anchor_stop", "")))

    if prefs.get("preserve_order"):
        ordered = list(stops)
        if anchor_index > 0:
            ordered = ordered[anchor_index:] + ordered[:anchor_index]
        return ordered

    route = nearest_neighbor(stops, start_index=anchor_index)
    passes = 5 if prefs.get("optimization_goal") == "distance" else 2
    return two_opt(route, max_passes=passes, lock_start=True)


def plan_trip(raw_stops: str, preferences: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    prefs = {
        "optimization_goal": "balanced",
        "preserve_order": False,
        "anchor_stop": "",
    }
    prefs.update(preferences or {})

    stops = geocode_stops(raw_stops)
    ordered = optimize_route(stops, prefs)
    distance = round(total_distance_km(ordered), 2)
    route_stops = [stop.as_dict(route_order=i) for i, stop in enumerate(ordered, start=1)]

    preference_labels = {
        "optimization_goal": "Minimize total distance" if prefs.get("optimization_goal") == "distance" else "Balanced optimization",
        "preserve_order": "Yes" if prefs.get("preserve_order") else "No",
        "anchor_stop": prefs.get("anchor_stop") or "First optimized stop",
    }

    return {
        "stops": route_stops,
        "total_distance_km": distance,
        "preferences": prefs,
        "preference_labels": preference_labels,
        "map_points": [[stop["lat"], stop["lng"]] for stop in route_stops],
    }
