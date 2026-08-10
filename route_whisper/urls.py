from django.contrib import admin
from django.urls import path
from planner import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('trips/<int:trip_id>/', views.trip_detail, name='trip_detail'),
]
