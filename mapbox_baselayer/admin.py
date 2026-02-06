from django.contrib import admin

from . import models


class TileInLine(admin.StackedInline):
    model = models.BaseLayerTile
    extra = 0


class BaseMapLayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'order')
    search_fields = ('name', 'slug')
    inlines = [TileInLine, ]
    exclude = ('is_overlay',)


@admin.register(models.BaseLayer)
class BaseLayerAdmin(BaseMapLayerAdmin):
    pass


@admin.register(models.OverlayLayer)
class OverlayLayerAdmin(BaseMapLayerAdmin):
    pass
