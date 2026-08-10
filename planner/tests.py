from django.test import TestCase
from .services import build_route


class RouteBuilderSmokeTest(TestCase):
    def test_build_route_orders_five_coordinate_stops(self):
        lines = [
            'A | 40.7580,-73.9855',
            'B | 40.7536,-73.9832',
            'C | 40.7527,-73.9772',
            'D | 40.7484,-73.9857',
            'E | 40.7411,-73.9897',
        ]
        ordered, origin, distance = build_route(lines)
        self.assertEqual(len(ordered), 5)
        self.assertGreater(distance, 0)
