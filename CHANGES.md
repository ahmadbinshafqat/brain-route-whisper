# Changes: Editable route preferences

Added user-selectable route preferences to the trip planning flow.

## What changed

- Added route preference fields to the planner form:
  - Optimization goal: balanced route or minimize total distance
  - Preserve pasted stop order
  - Optional anchor/start stop
- Updated route optimization service to respect preferences end-to-end.
- Updated the home page to expose the new controls.
- Updated trip detail page to show the preferences used for the route.
- Added lightweight styling for preference controls and route metadata.

## Integration notes

No database migration is required. Preferences are saved into existing JSON/text route payload fields when available and are also rendered directly after planning.

Run the app with the existing project instructions:

```bash
python manage.py migrate
python manage.py runserver
```

or:

```bash
docker compose up --build
```
