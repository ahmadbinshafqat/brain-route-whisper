from django.db import models


class Trip(models.Model):
    title = models.CharField(max_length=160)
    created_at = models.DateTimeField(auto_now_add=True)
    origin_optional = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.title


class Stop(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='stops')
    label = models.CharField(max_length=255)
    address = models.CharField(max_length=500)
    lat = models.FloatField()
    lng = models.FloatField()
    order_index = models.PositiveIntegerField(default=0)
    notes_optional = models.TextField(blank=True)

    class Meta:
        ordering = ['order_index', 'id']

    def __str__(self):
        return f'{self.order_index + 1}. {self.label}'


class RouteRun(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='route_runs')
    optimization_method = models.CharField(max_length=100)
    total_distance_optional = models.FloatField(null=True, blank=True, help_text='Kilometers')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.trip.title} - {self.optimization_method}'
