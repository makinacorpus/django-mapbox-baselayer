from django.contrib import admin

from . import models


class TileInLine(admin.StackedInline):
    model = models.BaseLayerTile
    extra = 0


@admin.register(models.MapBaseLayer)
class MapBaseLayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_overlay', 'order')
    list_filter = ('is_overlay',)
    search_fields = ('name', 'slug')
    inlines = [TileInLine, ]
