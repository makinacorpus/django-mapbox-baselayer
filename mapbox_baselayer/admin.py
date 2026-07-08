from django import forms
from django.contrib import admin
from django.contrib.gis.db.models import GeometryField
from django.contrib.gis.forms import OSMWidget
from django.utils.translation import gettext_lazy as _

from mapbox_baselayer.choices import LayerType
from mapbox_baselayer.models import (
    BaseLayerTile,
    MapBaseLayer,
    PMTile,
)


class PMTilesInline(admin.StackedInline):
    model = PMTile
    extra = 0

    def get_size(self, obj):
        if obj.pmtiles_file:
            return f"{obj.pmtiles_file.size / (1024 * 1024):.2f} MB"
        return "N/A"

    readonly_fields = (
        "pmtiles_file",
        "pmtiles_style",
        "min_zoom",
        "max_zoom",
        "get_size",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "notes",
                    ("min_zoom", "max_zoom"),
                    ("pmtiles_file", "get_size"),
                    "pmtiles_style",
                    "bbox",
                )
            },
        ),
    )

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


class MapBaseLayerForm(forms.ModelForm):
    class Meta:
        model = MapBaseLayer
        fields = [
            "name",
            "is_overlay",
            "order",
            "base_layer_type",
            "style_url",
            "sprite",
            "glyphs",
            "min_zoom",
            "max_zoom",
            "tile_size",
            "attribution",
            "enabled",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["base_layer_type"].disabled = True
        else:
            # When creating, only name and base_layer_type are shown
            # but we should ensure other fields don't cause validation issues
            # if they are not in the form
            pass


    def clean(self):
        cleaned_data = super().clean()
        if not self.instance or not self.instance.pk:
            # During creation, only name and base_layer_type are validated
            return cleaned_data

        layer_type = cleaned_data.get("base_layer_type")
        style_url = cleaned_data.get("style_url")

        if layer_type == LayerType.STYLE_URL and not style_url:
            self.add_error(
                "style_url", _("Style URL is required for Mapbox Style layers.")
            )

        return cleaned_data


@admin.register(MapBaseLayer)
class MapBaseLayerAdmin(admin.ModelAdmin):
    form = MapBaseLayerForm
    list_display = (
        "name",
        "is_overlay",
        "base_layer_type",
        "min_zoom",
        "max_zoom",
        "enabled",
    )
    list_filter = ("is_overlay", "base_layer_type", "enabled")
    search_fields = ("name", "slug")
    inlines = [BaseLayerTileInline, PMTilesInline]
    readonly_fields = ("slug",)

    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("name", "slug"),
                    ("is_overlay", "base_layer_type"),
                    ("enabled", "order"),
                    "attribution",
                )
            },
        ),
        (
            _("Style options"),
            {
                "fields": ("style_url", "tile_size"),
            },
        ),
        (
            _("Advanced options"),
            {
                "fields": (("min_zoom", "max_zoom"), "sprite", "glyphs"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return (
                (
                    None,
                    {
                        "fields": (
                            "name",
                            "base_layer_type",
                        )
                    },
                ),
            )
        fieldsets = super().get_fieldsets(request, obj)
        excluded_fields = set()
        if obj.base_layer_type == LayerType.RASTER:
            excluded_fields.add("style_url")
        else:
            excluded_fields.add("tile_size")

        new_fieldsets = []
        for label, options in fieldsets:
            fields = options.get("fields", ())
            new_fields = []
            for f in fields:
                if isinstance(f, (list, tuple)):
                    filtered_row = [x for x in f if x not in excluded_fields]
                    if filtered_row:
                        new_fields.append(
                            tuple(filtered_row)
                            if isinstance(f, tuple)
                            else filtered_row
                        )
                else:
                    if f not in excluded_fields:
                        new_fields.append(f)
            if new_fields:
                new_options = dict(options)
                new_options["fields"] = tuple(new_fields)
                new_fieldsets.append((label, new_options))
        return tuple(new_fieldsets)

    def get_inlines(self, request, obj=None):
        if obj is None:
            return []
        if obj.base_layer_type == LayerType.RASTER:
            return [BaseLayerTileInline, PMTilesInline]
        else:
            return [PMTilesInline]

    class Media:
        js = ("mapbox_baselayer/js/mapbaselayer_admin.js",)

    def get_queryset(self, request):
        return super().get_queryset(request)

    def has_add_permission(self, request):
        return True

    def has_delete_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return True
