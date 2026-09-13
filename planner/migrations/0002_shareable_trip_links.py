# Generated for Route Whisper shareable trip links

import uuid

from django.db import migrations, models


def populate_share_ids(apps, schema_editor):
    Trip = apps.get_model("planner", "Trip")
    for trip in Trip.objects.all():
        if not getattr(trip, "share_id", None):
            trip.share_id = uuid.uuid4()
            trip.save(update_fields=["share_id"])


def backfill_map_view(apps, schema_editor):
    Trip = apps.get_model("planner", "Trip")
    Stop = apps.get_model("planner", "Stop")
    for trip in Trip.objects.all():
        stops = list(Stop.objects.filter(trip=trip).order_by("order"))
        if not stops:
            continue
        trip.map_center_lat = sum(stop.latitude for stop in stops) / len(stops)
        trip.map_center_lng = sum(stop.longitude for stop in stops) / len(stops)
        trip.map_zoom = 13
        trip.save(update_fields=["map_center_lat", "map_center_lng", "map_zoom"])


class Migration(migrations.Migration):
    dependencies = [
        ("planner", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="trip",
            name="share_id",
            field=models.UUIDField(default=uuid.uuid4, editable=False, db_index=True, unique=True),
        ),
        migrations.AddField(
            model_name="trip",
            name="map_center_lat",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="trip",
            name="map_center_lng",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="trip",
            name="map_zoom",
            field=models.PositiveSmallIntegerField(default=13),
        ),
        migrations.RunPython(populate_share_ids, migrations.RunPython.noop),
        migrations.RunPython(backfill_map_view, migrations.RunPython.noop),
    ]
