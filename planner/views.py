import json
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import TripCreateForm
from .models import RouteRun, Stop, Trip
from .services import build_route


@require_http_methods(['GET', 'POST'])
def home(request):
    if request.method == 'POST':
        form = TripCreateForm(request.POST)
        if form.is_valid():
            lines = form.cleaned_data['stops_text'].splitlines()
            ordered, origin, distance = build_route(lines, form.cleaned_data.get('origin_optional', ''))
            trip = Trip.objects.create(
                title=form.cleaned_data['title'],
                origin_optional=form.cleaned_data.get('origin_optional', ''),
            )
            for idx, stop in enumerate(ordered):
                Stop.objects.create(
                    trip=trip,
                    label=stop.label,
                    address=stop.address,
                    lat=stop.lat,
                    lng=stop.lng,
                    order_index=idx,
                )
            RouteRun.objects.create(
                trip=trip,
                optimization_method='nearest-neighbor + 2-opt',
                total_distance_optional=round(distance, 2),
            )
            return redirect('trip_detail', trip_id=trip.id)
    else:
        form = TripCreateForm(initial={
            'stops_text': 'Times Square | 40.7580,-73.9855\nBryant Park | 40.7536,-73.9832\nGrand Central Terminal | 40.7527,-73.9772\nEmpire State Building | 40.7484,-73.9857\nFlatiron Building | 40.7411,-73.9897\nWashington Square Park | 40.7308,-73.9973'
        })
    recent_trips = Trip.objects.order_by('-created_at')[:5]
    return render(request, 'planner/home.html', {'form': form, 'recent_trips': recent_trips})


def trip_detail(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    stops = list(trip.stops.all())
    route_run = trip.route_runs.order_by('-created_at').first()
    map_points = [{'label': s.label, 'lat': s.lat, 'lng': s.lng, 'order': s.order_index + 1} for s in stops]
    return render(request, 'planner/trip_detail.html', {
        'trip': trip,
        'stops': stops,
        'route_run': route_run,
        'map_points_json': json.dumps(map_points),
    })
