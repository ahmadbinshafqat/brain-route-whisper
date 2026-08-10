from django.contrib import admin
from .models import Trip, Stop, RouteRun


class StopInline(admin.TabularInline):
    model = Stop
    extra = 0


class RouteRunInline(admin.TabularInline):
    model = RouteRun
    extra = 0


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'origin_optional')
    inlines = [StopInline, RouteRunInline]


admin.site.register(Stop)
admin.site.register(RouteRun)
