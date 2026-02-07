from urllib.parse import urlencode

from django.core.management import BaseCommand, CommandError

from mapbox_baselayer.models import BaseLayerTile, MapBaseLayer


class Command(BaseCommand):
    help = "Install an IGN base layer"
    raster_layers = {
        "plan": {
            "label": "Plan IGN",
            "name": "GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2",
            "format": "png",
            "need_key": False,
        },
        "ortho": {
            "label": "Orthophoto IGN",
            "name": "ORTHOIMAGERY.ORTHOPHOTOS",
            "format": "jpeg",
            "need_key": False,
        },
        "maps": {
            "label": "Cartes IGN",
            "name": "GEOGRAPHICALGRIDSYSTEMS.MAPS",
            "format": "jpeg",
            "need_key": True,
        },
        "scan_25": {
            "label": "Scan IGN",
            "name": "GEOGRAPHICALGRIDSYSTEMS.MAPS.SCAN25TOUR",
            "format": "jpeg",
            "need_key": True,
        },
        "cadastre": {
            "label": "Cadastre IGN",
            "name": "CADASTRALPARCELS.PARCELS",
            "format": "png",
            "need_key": False,
        },
    }
    mapbox_style_layers = {
        "plan_vt": {
            "label": "Plan IGN VT",
            "url": "//data.geopf.fr/annexes/ressources/vectorTiles/styles/PLAN.IGN/standard.json",
        },
        "scan_25_vt": {
            "label": "Scan IGN VT",
            "url": "//data.geopf.fr/annexes/ressources/vectorTiles/styles/PLAN.IGN/classique.json",
        },
        "gris_vt": {
            "label": "Gris IGN VT",
            "url": "//data.geopf.fr/annexes/ressources/vectorTiles/styles/PLAN.IGN/gris.json",
        },
        "cadastre_vt": {
            "label": "Cadastre IGN VT",
            "url": "https://data.geopf.fr/annexes/ressources/vectorTiles/styles/PCI/pci.json",
        },
    }

    def add_arguments(self, parser):
        parser.add_argument("--key", type=str, default="ign_scan_ws")
        parser.add_argument(
            "--overlay",
            action="store_true",
            help="Install layers as overlay",
            default=False,
        )
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
        overlay = options.get("overlay")

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
                base_url = f"//data.geopf.fr/{'private/' if self.raster_layers[layer]['need_key'] else ''}wmts"

                # Build URL with unencoded placeholders
                query_string = urlencode(params)
                final_url = f"{base_url}?{query_string}&TILEMATRIX={{z}}&TILEROW={{y}}&TILECOL={{x}}"

                base_layer = MapBaseLayer.objects.create(
                    name=self.raster_layers[layer]["label"],
                    base_layer_type="raster",
                    tile_size=256,
                    is_overlay=overlay,
                    min_zoom=0,
                    max_zoom=19,
                    attribution="© IGN - GeoPortail",
                )
                BaseLayerTile.objects.bulk_create(
                    [
                        BaseLayerTile(base_layer=base_layer, url=final_url),
                    ]
                )

            elif layer in self.mapbox_style_layers:
                style = self.mapbox_style_layers[layer]
                MapBaseLayer.objects.create(
                    name=style["label"],
                    base_layer_type="mapbox",
                    tile_size=512,
                    is_overlay=overlay,
                    attribution="© IGN - GeoPortail",
                    map_box_url=style["url"],
                )
        self.stdout.write(self.style.SUCCESS("IGN layer(s) created."))
