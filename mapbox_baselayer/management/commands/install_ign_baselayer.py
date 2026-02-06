from django.core.management import BaseCommand, CommandError

from mapbox_baselayer.models import BaseLayerTile, MapBaseLayer


class Command(BaseCommand):
    help = "Install an IGN base layer"
    layers = {
        "ortho": {"name": "ORTHOIMAGERY.ORTHOPHOTOS", "format": "jpeg"},
        "plan": {"name": "GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2", "format": "png"},
        "maps": {"name": "GEOGRAPHICALGRIDSYSTEMS.MAPS", "format": "jpeg"},
        "se-classique": {
            "name": "GEOGRAPHICALGRIDSYSTEMS.MAPS.SCAN-EXPRESS.CLASSIQUE",
            "format": "jpeg",
        },
        "se-standard": {
            "name": "GEOGRAPHICALGRIDSYSTEMS.MAPS.SCAN-EXPRESS.STANDARD",
            "format": "jpeg",
        },
        "cadastre": {"name": "CADASTRALPARCELS.PARCELS", "format": "png"},
    }

    def add_arguments(self, parser):
        parser.add_argument("key", type=str)
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
            if layer not in self.layers:
                msg = f"'{layer}' is not a valid value. Should be '{', '.join(self.layers.keys())}'"
                raise CommandError(msg)

        for layer in options.get("layers"):
            base_url = (
                f"//wxs.ign.fr/{key}/geoportail/wmts?LAYER={self.layers[layer]['name']}&EXCEPTIONS=text/xml&"
                f"FORMAT=image/{self.layers[layer]['format']}"
                f"&SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&STYLE=normal&TILEMATRIXSET=PM&"
                "TILEMATRIX={z}&TILEROW={y}&TILECOL={x}"
            )
            base_layer = MapBaseLayer.objects.create(
                name=f"IGN {layer}",
                base_layer_type="raster",
                tile_size=256,
                min_zoom=0,
                max_zoom=19,
                attribution="© IGN - GeoPortail",
            )
            BaseLayerTile.objects.bulk_create(
                [
                    BaseLayerTile(base_layer=base_layer, url=base_url),
                ]
            )
        self.stdout.write(self.style.SUCCESS("IGN layer(s) created."))
