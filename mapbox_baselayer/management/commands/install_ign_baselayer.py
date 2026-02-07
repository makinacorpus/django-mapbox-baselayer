from urllib.parse import urlencode

from django.core.management import BaseCommand, CommandError

from mapbox_baselayer.models import BaseLayerTile, MapBaseLayer


class Command(BaseCommand):
    help = "Install an IGN base layer"
    raster_layers = {
        "plan": {
            "name": "GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2",
            "format": "png",
            "overlay": False,
            "need_key": False,
        },
        "ortho": {
            "name": "ORTHOIMAGERY.ORTHOPHOTOS",
            "format": "jpeg",
            "overlay": False,
            "need_key": False,
        },
        "maps": {
            "name": "GEOGRAPHICALGRIDSYSTEMS.MAPS",
            "format": "jpeg",
            "overlay": False,
            "need_key": True,
        },
        "scan_25": {
            "name": "GEOGRAPHICALGRIDSYSTEMS.MAPS.SCAN25TOUR",
            "format": "jpeg",
            "overlay": False,
            "need_key": True,
        },
        "cadastre": {
            "name": "CADASTRALPARCELS.PARCELS",
            "format": "png",
            "overlay": True,
            "need_key": False,
        },
    }
    mapbox_style_layers = {
        "plan_vt": {
            "url": "//data.geopf.fr/annexes/ressources/vectorTiles/styles/PLAN.IGN/standard.json"
        },
    }

    def add_arguments(self, parser):
        parser.add_argument("--key", type=str, default="ign_scan_ws")
        parser.add_argument(
            "--layers",
            nargs="+",
            type=str,
            default=[
                "ortho",
            ],
        )

    def handle(self, *args, **options):
        key = options.get("key")

        for layer in options.get("layers"):
            if (
                layer not in self.raster_layers
                and layer not in self.mapbox_style_layers
            ):
                valid_layers = list(self.raster_layers.keys()) + list(
                    self.mapbox_style_layers.keys()
                )
                msg = f"'{layer}' is not a valid value. Should be '{', '.join(valid_layers)}'"
                raise CommandError(msg)

        for layer in options.get("layers"):
            if layer in self.raster_layers:
                params = {
                    "LAYER": self.raster_layers[layer]["name"],
                    "EXCEPTIONS": "text/xml",
                    "FORMAT": f"image/{self.raster_layers[layer]['format']}",
                    "SERVICE": "WMTS",
                    "VERSION": "1.0.0",
                    "REQUEST": "GetTile",
                    "STYLE": "normal",
                    "TILEMATRIXSET": "PM",
                }
                if self.raster_layers[layer]["need_key"]:
                    params["apikey"] = key
                base_url = "//data.geopf.fr/private/wmts"

                # Build URL with unencoded placeholders
                query_string = urlencode(params)
                final_url = f"{base_url}?{query_string}&TILEMATRIX={{z}}&TILEROW={{y}}&TILECOL={{x}}"

                base_layer = MapBaseLayer.objects.create(
                    name=f"IGN {layer}",
                    base_layer_type="raster",
                    tile_size=256,
                    is_overlay=self.raster_layers[layer]["overlay"],
                    min_zoom=0,
                    max_zoom=19,
                    attribution="© IGN - GeoPortail",
                )
                BaseLayerTile.objects.bulk_create(
                    [
                        BaseLayerTile(base_layer=base_layer, url=final_url),
                    ]
                )

        for layer in options.get("layers"):
            if layer in self.mapbox_style_layers:
                style = self.mapbox_style_layers[layer]
                MapBaseLayer.objects.create(
                    name=f"IGN {layer}",
                    base_layer_type="mapbox",
                    tile_size=512,
                    is_overlay=False,
                    attribution="© IGN - GeoPortail",
                    map_box_url=style["url"],
                )
        self.stdout.write(self.style.SUCCESS("IGN layer(s) created."))
