from django.contrib import admin

from . import models


class TileInLine(admin.StackedInline):
    model = models.BaseLayerTile
    extra = 0


class BaseMapLayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'base_layer_type', 'order')
    list_filter = ('base_layer_type',)
    search_fields = ('name', 'slug')
    exclude = ('is_overlay',)

    def get_inlines(self, request, obj=None):
        if not obj.pk or (obj and obj.base_layer_type == obj.LayerType.RASTER):
            return [TileInLine]
        return []


@admin.register(models.BaseLayer)
class BaseLayerAdmin(BaseMapLayerAdmin):
    pass


@admin.register(models.OverlayLayer)
class OverlayLayerAdmin(BaseMapLayerAdmin):
    pass
