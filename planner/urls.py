from django.urls import path

from . import views

app_name = "planner"

urlpatterns = [
    path("", views.home, name="home"),
    path("trips/<uuid:share_id>/", views.trip_detail, name="trip_detail"),
    path("trips/<uuid:share_id>/map-view/", views.update_map_view, name="update_map_view"),
]
