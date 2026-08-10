import hashlib
import math
import os
import re
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

import requests

COORD_RE = re.compile(r'(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)')
FALLBACK_CENTER = (40.7580, -73.9855)  # Midtown Manhattan, convenient for demo walking routes


@dataclass
class ParsedStop:
    label: str
    address: str
    lat: float
    lng: float


def haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    lat1, lon1 = a
    lat2, lon2 = b
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    x = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(x), math.sqrt(1 - x))


def total_distance_km(points: List[Tuple[float, float]]) -> float:
    return sum(haversine_km(points[i], points[i + 1]) for i in range(len(points) - 1))


def split_label_address(line: str) -> Tuple[str, str]:
    if '|' in line:
        label, address = [part.strip() for part in line.split('|', 1)]
        return label or address, address
    return line.strip(), line.strip()


def parse_coordinates(text: str) -> Optional[Tuple[float, float]]:
    match = COORD_RE.search(text)
    if not match:
        return None
    lat = float(match.group(1))
    lng = float(match.group(2))
    if -90 <= lat <= 90 and -180 <= lng <= 180:
        return lat, lng
    return None


def fallback_geocode(address: str, index: int) -> Tuple[float, float]:
    digest = hashlib.sha256(address.encode('utf-8')).hexdigest()
    angle_seed = int(digest[:8], 16) / 0xFFFFFFFF
    radius_seed = int(digest[8:16], 16) / 0xFFFFFFFF
    angle = 2 * math.pi * angle_seed
    radius_km = 0.35 + radius_seed * 3.0 + (index % 4) * 0.08
    lat_offset = (radius_km / 111.0) * math.cos(angle)
    lng_offset = (radius_km / (111.0 * math.cos(math.radians(FALLBACK_CENTER[0])))) * math.sin(angle)
    return FALLBACK_CENTER[0] + lat_offset, FALLBACK_CENTER[1] + lng_offset


def online_geocode(address: str) -> Optional[Tuple[float, float]]:
    if os.getenv('ROUTE_WHISPER_ENABLE_ONLINE_GEOCODING', '1') != '1':
        return None
    try:
        response = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={'q': address, 'format': 'json', 'limit': 1},
            headers={'User-Agent': os.getenv('NOMINATIM_USER_AGENT', 'route-whisper-mvp')},
            timeout=4,
        )
        response.raise_for_status()
        data = response.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except requests.RequestException:
        return None
    return None


def geocode_line(line: str, index: int) -> ParsedStop:
    label, address = split_label_address(line)
    coords = parse_coordinates(address) or parse_coordinates(label)
    if coords is None:
        coords = online_geocode(address)
        if coords is not None:
            time.sleep(1.0)  # be polite to public Nominatim
    if coords is None:
        coords = fallback_geocode(address, index)
    return ParsedStop(label=label, address=address, lat=round(coords[0], 6), lng=round(coords[1], 6))


def optimize_order(stops: List[ParsedStop], origin: Optional[Tuple[float, float]] = None) -> List[ParsedStop]:
    if not stops:
        return []
    remaining = stops[:]
    ordered: List[ParsedStop] = []
    current = origin or (remaining[0].lat, remaining[0].lng)
    while remaining:
        nearest = min(remaining, key=lambda s: haversine_km(current, (s.lat, s.lng)))
        ordered.append(nearest)
        remaining.remove(nearest)
        current = (nearest.lat, nearest.lng)
    return two_opt(ordered, origin)


def route_length_for_order(stops: List[ParsedStop], origin: Optional[Tuple[float, float]] = None) -> float:
    points = [(s.lat, s.lng) for s in stops]
    if origin:
        points = [origin] + points
    return total_distance_km(points)


def two_opt(stops: List[ParsedStop], origin: Optional[Tuple[float, float]] = None) -> List[ParsedStop]:
    best = stops[:]
    improved = True
    while improved:
        improved = False
        for i in range(0, len(best) - 2):
            for j in range(i + 2, len(best)):
                if i == 0 and origin is not None:
                    candidate = best[:i] + list(reversed(best[i:j + 1])) + best[j + 1:]
                else:
                    candidate = best[:i] + list(reversed(best[i:j + 1])) + best[j + 1:]
                if route_length_for_order(candidate, origin) + 0.0001 < route_length_for_order(best, origin):
                    best = candidate
                    improved = True
        
    return best


def build_route(lines: Iterable[str], origin_text: str = '') -> Tuple[List[ParsedStop], Optional[Tuple[float, float]], float]:
    parsed = [geocode_line(line, idx) for idx, line in enumerate(lines)]
    origin = None
    if origin_text.strip():
        origin = parse_coordinates(origin_text) or online_geocode(origin_text) or fallback_geocode(origin_text, 99)
    ordered = optimize_order(parsed, origin)
    distance = route_length_for_order(ordered, origin)
    return ordered, origin, distance
