from django.urls import reverse

from mapbox_baselayer.models import MapBaseLayer

DEFAULT_OSM_TILEJSON = {
    "version": 8,
    "sources": {
        "osm": {
            "type": "raster",
            "tiles": [
                "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
                "https://b.tile.openstreetmap.org/{z}/{x}/{y}.png",
                "https://c.tile.openstreetmap.org/{z}/{x}/{y}.png",
            ],
            "minzoom": 0,
            "maxzoom": 19,
            "tileSize": 256,
            "attribution": '<a href="https://www.openstreetmap.org/copyright">OSM Contributors</a>',
        }
    },
    "layers": [
        {
            "id": "osm-background",
            "type": "raster",
            "source": "osm",
        }
    ],
    "glyphs": "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
}


def get_map_base_layers():
    layers = list(MapBaseLayer.objects.filter(enabled=True))
    base_layers = [layer for layer in layers if not layer.is_overlay]
    overlay_layers = [layer for layer in layers if layer.is_overlay]

    data = {
        "base_layers": [
            {"name": bl.name, "slug": bl.slug, "url": bl.url} for bl in base_layers
        ]
        if base_layers
        else [
            {
                "name": "OSM",
                "slug": "osm",
                "url": reverse("mapbox_baselayer:default-osm-tilejson"),
            }
        ],
        "overlay_layers": [
            {"name": ol.name, "slug": ol.slug, "url": ol.url} for ol in overlay_layers
        ],
    }
    return data
