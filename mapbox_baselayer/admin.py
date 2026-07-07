from django import forms
from django.contrib import admin
from django.contrib.gis.db.models import GeometryField
from django.contrib.gis.forms import OSMWidget
from django.utils.translation import gettext_lazy as _

from mapbox_baselayer.models import (
    BaseLayerRaster,
    BaseLayerStyle,
    BaseLayerTile,
    MapBaseLayer,
    OverlayRaster,
    OverlayStyle,
    PMTile,
)


class PMTilesInline(admin.StackedInline):
    model = PMTile
    extra = 0
    readonly_fields = ("pmtiles_file", "pmtiles_style", "min_zoom", "max_zoom")

    formfield_overrides = {
        GeometryField: {
            "widget": OSMWidget(
                attrs={
                    "map_width": 400,
                    "map_height": 200,
                    "display_wkt": False,
                    "disabled": True,
                }
            )
        },
    }

    def has_add_permission(self, request, obj=None):
        return False


class BaseLayerTileInline(admin.TabularInline):
    model = BaseLayerTile
    extra = 0
    min_num = 1


class RasterForm(forms.ModelForm):
    class Meta:
        model = MapBaseLayer
        exclude = ("style_url", "is_overlay", "base_layer_type")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tile_size"].initial = 256


class StyleForm(forms.ModelForm):
    class Meta:
        model = MapBaseLayer
        exclude = ("is_overlay", "base_layer_type")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["style_url"].required = True


class RasterAdminMixin:
    form = RasterForm
    inlines = [BaseLayerTileInline, PMTilesInline]
    readonly_fields = ("slug",)

    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("name", "slug"),
                    ("enabled", "order"),
                    "attribution",
                )
            },
        ),
        (
            _("Advanced options"),
            {
                "fields": (("min_zoom", "max_zoom"), "sprite", "glyphs", "tile_size"),
                "classes": ("collapse",),
            },
        ),
    )


class StyleAdminMixin:
    form = StyleForm
    inlines = [
        PMTilesInline,
    ]
    readonly_fields = ("slug",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("name", "slug"),
                    "style_url",
                    ("enabled", "order"),
                    "attribution",
                )
            },
        ),
        (
            _("Advanced options"),
            {
                "fields": (("min_zoom", "max_zoom"), "sprite", "glyphs", "tile_size"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(MapBaseLayer)
class LayerAdmin(admin.ModelAdmin):
    list_display = ("name", "is_overlay", "min_zoom", "max_zoom")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(enabled=True)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(BaseLayerRaster)
class BaseLayerRasterAdmin(RasterAdminMixin, admin.ModelAdmin):
    list_display = ("name", "order", "min_zoom", "max_zoom", "enabled")


@admin.register(BaseLayerStyle)
class BaseLayerStyleAdmin(StyleAdminMixin, admin.ModelAdmin):
    list_display = ("name", "order", "min_zoom", "max_zoom", "enabled")


@admin.register(OverlayRaster)
class OverlayRasterAdmin(RasterAdminMixin, admin.ModelAdmin):
    list_display = ("name", "order", "min_zoom", "max_zoom", "enabled")


@admin.register(OverlayStyle)
class OverlayStyleAdmin(StyleAdminMixin, admin.ModelAdmin):
    list_display = ("name", "order", "min_zoom", "max_zoom", "enabled")
