from django.core.management.base import BaseCommand
from planner.models import RouteRun, Stop, Trip
from planner.services import build_route


class Command(BaseCommand):
    help = 'Create a demo trip if the database has no trips.'

    def handle(self, *args, **options):
        if Trip.objects.exists():
            self.stdout.write(self.style.SUCCESS('Demo seed skipped; trips already exist.'))
            return
        lines = [
            'Times Square | 40.7580,-73.9855',
            'Bryant Park | 40.7536,-73.9832',
            'Grand Central Terminal | 40.7527,-73.9772',
            'Empire State Building | 40.7484,-73.9857',
            'Flatiron Building | 40.7411,-73.9897',
            'Washington Square Park | 40.7308,-73.9973',
        ]
        ordered, origin, distance = build_route(lines)
        trip = Trip.objects.create(title='Demo: Midtown to Downtown Walk')
        for idx, stop in enumerate(ordered):
            Stop.objects.create(trip=trip, label=stop.label, address=stop.address, lat=stop.lat, lng=stop.lng, order_index=idx)
        RouteRun.objects.create(trip=trip, optimization_method='nearest-neighbor + 2-opt', total_distance_optional=round(distance, 2))
        self.stdout.write(self.style.SUCCESS(f'Created demo trip #{trip.id}.'))
