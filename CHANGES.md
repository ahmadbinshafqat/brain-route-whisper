# Changes: Shareable trip links

Added shareable saved-trip URLs to Route Whisper.

## What changed

- Added stable public `share_id` identifiers to `Trip` records.
- Added optional saved map view fields (`map_center_lat`, `map_center_lng`, `map_zoom`) so reopened trips can restore the same map viewport.
- Added `/trips/<share_id>/` trip detail routes.
- Updated the planner flow so newly optimized trips redirect to their shareable URL.
- Updated trip detail UI with a copyable share link and Leaflet map-view persistence.
- Updated home page copy to explain that optimized routes can be shared and revisited.

## Integration notes

Run migrations after applying this change:

```bash
python manage.py migrate
```

Then start the app as usual. Any newly created trip will have a unique share URL. Existing trips receive a generated `share_id` during the migration.
