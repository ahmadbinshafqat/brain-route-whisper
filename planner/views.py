import json
from typing import Any, Dict, Optional

from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import TripForm
from .models import Trip
from .services import plan_trip


def _field_names() -> set:
    return {field.name for field in Trip._meta.fields}


def _set_if_field(trip: Trip, field_names: set, name: str, value: Any) -> None:
    if name in field_names:
        setattr(trip, name, value)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def _first_existing_attr(obj: Any, names, default=None):
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value not in (None, ""):
                return value
    return default


def _trip_detail_url(trip: Trip) -> str:
    for url_name in ("planner:trip_detail", "trip_detail"):
        try:
            if hasattr(trip, "share_token") and trip.share_token:
                return reverse(url_name, kwargs={"share_token": trip.share_token})
            if hasattr(trip, "slug") and trip.slug:
                return reverse(url_name, kwargs={"slug": trip.slug})
            return reverse(url_name, kwargs={"pk": trip.pk})
        except Exception:
            continue
    return f"/trips/{trip.pk}/"


def _create_trip(raw_stops: str, route: Dict[str, Any]) -> Trip:
    field_names = _field_names()
    trip = Trip()

    _set_if_field(trip, field_names, "title", route["stops"][0]["name"] if route.get("stops") else "Untitled trip")
    _set_if_field(trip, field_names, "raw_stops", raw_stops)
    _set_if_field(trip, field_names, "raw_input", raw_stops)
    _set_if_field(trip, field_names, "input_text", raw_stops)
    _set_if_field(trip, field_names, "stops_text", raw_stops)

    payload = {
        "stops": route["stops"],
        "total_distance_km": route["total_distance_km"],
        "preferences": route["preferences"],
        "preference_labels": route["preference_labels"],
        "map_points": route["map_points"],
    }
    payload_json = _json_dumps(payload)
    stops_json = _json_dumps(route["stops"])

    for name in ("route_json", "plan_json", "data", "payload"):
        _set_if_field(trip, field_names, name, payload_json)
    for name in ("stops_json", "ordered_stops_json", "optimized_stops"):
        _set_if_field(trip, field_names, name, stops_json)
    for name in ("total_distance_km", "distance_km"):
        _set_if_field(trip, field_names, name, route["total_distance_km"])

    trip.save()
    return trip


def _route_from_trip(trip: Trip) -> Dict[str, Any]:
    payload = _json_loads(_first_existing_attr(trip, ["route_json", "plan_json", "data", "payload"], None), {})
    stops = payload.get("stops") if isinstance(payload, dict) else None
    if not stops:
        stops = _json_loads(_first_existing_attr(trip, ["stops_json", "ordered_stops_json", "optimized_stops"], "[]"), [])

    distance = None
    if isinstance(payload, dict):
        distance = payload.get("total_distance_km")
    if distance is None:
        distance = _first_existing_attr(trip, ["total_distance_km", "distance_km"], 0)

    preferences = payload.get("preferences", {}) if isinstance(payload, dict) else {}
    preference_labels = payload.get("preference_labels", {}) if isinstance(payload, dict) else {}
    if not preference_labels:
        preference_labels = {
            "optimization_goal": "Minimize total distance" if preferences.get("optimization_goal") == "distance" else "Balanced optimization",
            "preserve_order": "Yes" if preferences.get("preserve_order") else "No",
            "anchor_stop": preferences.get("anchor_stop") or "First optimized stop",
        }

    return {
        "stops": stops or [],
        "total_distance_km": distance or 0,
        "preferences": preferences,
        "preference_labels": preference_labels,
        "map_points": [[stop.get("lat"), stop.get("lng")] for stop in (stops or []) if stop.get("lat") is not None and stop.get("lng") is not None],
    }


@require_http_methods(["GET", "POST"])
def home(request):
    if request.method == "POST":
        form = TripForm(request.POST)
        if form.is_valid():
            raw_stops = form.cleaned_data["stops"]
            route = plan_trip(raw_stops, form.get_preferences())
            trip = _create_trip(raw_stops, route)
            return redirect(_trip_detail_url(trip))
    else:
        form = TripForm()

    return render(request, "planner/home.html", {"form": form})


def trip_detail(request, pk: Optional[int] = None, share_token: Optional[str] = None, slug: Optional[str] = None):
    if share_token is not None and "share_token" in _field_names():
        trip = get_object_or_404(Trip, share_token=share_token)
    elif slug is not None and "slug" in _field_names():
        trip = get_object_or_404(Trip, slug=slug)
    else:
        trip = get_object_or_404(Trip, pk=pk)

    route = _route_from_trip(trip)
    return render(
        request,
        "planner/trip_detail.html",
        {
            "trip": trip,
            "route": route,
            "stops": route["stops"],
            "total_distance_km": route["total_distance_km"],
            "preferences": route["preferences"],
            "preference_labels": route["preference_labels"],
            "stops_json": _json_dumps(route["stops"]),
            "map_points_json": _json_dumps(route["map_points"]),
        },
    )
