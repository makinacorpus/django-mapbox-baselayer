from django.contrib import admin
from . import models


class TileInLine(admin.StackedInline):
    model = models.BaseLayerTile
    extra = 0


class MapBaseLayerAdmin(admin.ModelAdmin):
    inlines = [TileInLine, ]
