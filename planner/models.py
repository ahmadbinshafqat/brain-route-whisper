import uuid

from django.db import models
from django.urls import reverse


class Trip(models.Model):
    title = models.CharField(max_length=200, blank=True, default="")
    raw_stops = models.TextField(blank=True, default="")
    total_distance_km = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    share_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)
    map_center_lat = models.FloatField(null=True, blank=True)
    map_center_lng = models.FloatField(null=True, blank=True)
    map_zoom = models.PositiveSmallIntegerField(default=13)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        if self.title:
            return self.title
        return f"Trip {self.created_at:%Y-%m-%d %H:%M}"

    def get_absolute_url(self):
        return reverse("planner:trip_detail", kwargs={"share_id": self.share_id})

    @property
    def ordered_stops(self):
        return self.stops.order_by("order")


class Stop(models.Model):
    trip = models.ForeignKey(Trip, related_name="stops", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    query = models.CharField(max_length=500, blank=True, default="")
    latitude = models.FloatField()
    longitude = models.FloatField()
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.order + 1}. {self.name}"
