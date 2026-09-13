import hashlib
import math
import re

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import TripForm
from .models import Stop, Trip

_COORD_RE = re.compile(r"^\s*(?P<label>.*?)\s*(?:\||,)?\s*(?P<lat>-?\d+(?:\.\d+)?)\s*,\s*(?P<lng>-?\d+(?:\.\d+)?)\s*$")


def home(request):
    if request.method == "POST":
        form = TripForm(request.POST)
        if form.is_valid():
            raw_stops = _first_text_value(form.cleaned_data)
            trip = _create_trip(raw_stops)
            return redirect(trip.get_absolute_url())
    else:
        form = TripForm()

    recent_trips = Trip.objects.prefetch_related("stops")[:5]
    return render(request, "planner/home.html", {"form": form, "recent_trips": recent_trips})


def trip_detail(request, share_id):
    trip = get_object_or_404(Trip.objects.prefetch_related("stops"), share_id=share_id)
    stops = list(trip.stops.order_by("order"))
    share_url = request.build_absolute_uri(trip.get_absolute_url())
    return render(
        request,
        "planner/trip_detail.html",
        {
            "trip": trip,
            "stops": stops,
            "share_url": share_url,
        },
    )


@require_POST
def update_map_view(request, share_id):
    trip = get_object_or_404(Trip, share_id=share_id)
    try:
        trip.map_center_lat = float(request.POST.get("lat"))
        trip.map_center_lng = float(request.POST.get("lng"))
        trip.map_zoom = max(1, min(20, int(float(request.POST.get("zoom", 13)))))
        trip.save(update_fields=["map_center_lat", "map_center_lng", "map_zoom"])
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "Invalid map view."}, status=400)
    return JsonResponse({"ok": True})


def _first_text_value(cleaned_data):
    for value in cleaned_data.values():
        if isinstance(value, str):
            return value.strip()
    return ""


def _create_trip(raw_stops):
    parsed = [_parse_stop(line) for line in raw_stops.splitlines() if line.strip()]
    optimized = _nearest_neighbor(parsed)
    total_distance_km = _route_distance(optimized)

    title = optimized[0]["name"] if optimized else "Shared trip"
    trip = Trip.objects.create(
        title=title,
        raw_stops=raw_stops,
        total_distance_km=total_distance_km,
    )

    for index, stop in enumerate(optimized):
        Stop.objects.create(
            trip=trip,
            name=stop["name"],
            query=stop["query"],
            latitude=stop["latitude"],
            longitude=stop["longitude"],
            order=index,
        )

    if optimized:
        trip.map_center_lat = sum(stop["latitude"] for stop in optimized) / len(optimized)
        trip.map_center_lng = sum(stop["longitude"] for stop in optimized) / len(optimized)
        trip.map_zoom = 13
        trip.save(update_fields=["map_center_lat", "map_center_lng", "map_zoom"])

    return trip


def _parse_stop(line):
    match = _COORD_RE.match(line)
    if match:
        label = (match.group("label") or "Stop").strip(" |,") or "Stop"
        return {
            "name": label,
            "query": line.strip(),
            "latitude": float(match.group("lat")),
            "longitude": float(match.group("lng")),
        }

    digest = hashlib.sha256(line.strip().lower().encode("utf-8")).hexdigest()
    lat_offset = (int(digest[:8], 16) / 0xFFFFFFFF - 0.5) * 0.08
    lng_offset = (int(digest[8:16], 16) / 0xFFFFFFFF - 0.5) * 0.08
    return {
        "name": line.strip(),
        "query": line.strip(),
        "latitude": 40.7580 + lat_offset,
        "longitude": -73.9855 + lng_offset,
    }


def _nearest_neighbor(stops):
    if len(stops) <= 2:
        return stops

    remaining = stops[:]
    route = [remaining.pop(0)]
    while remaining:
        current = route[-1]
        nearest_index = min(
            range(len(remaining)),
            key=lambda idx: _haversine_km(current, remaining[idx]),
        )
        route.append(remaining.pop(nearest_index))
    return _two_opt(route)


def _two_opt(route):
    improved = True
    best = route[:]
    while improved:
        improved = False
        for i in range(1, len(best) - 2):
            for j in range(i + 1, len(best)):
                if j - i == 1:
                    continue
                candidate = best[:]
                candidate[i:j] = reversed(candidate[i:j])
                if _route_distance(candidate) < _route_distance(best):
                    best = candidate
                    improved = True
    return best


def _route_distance(stops):
    return sum(_haversine_km(a, b) for a, b in zip(stops, stops[1:]))


def _haversine_km(a, b):
    radius_km = 6371.0
    lat1 = math.radians(a["latitude"])
    lat2 = math.radians(b["latitude"])
    dlat = lat2 - lat1
    dlng = math.radians(b["longitude"] - a["longitude"])
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * radius_km * math.asin(math.sqrt(h))
