from django.core.management import BaseCommand

from mapbox_baselayer.models import BaseLayerTile, MapBaseLayer


class Command(BaseCommand):
    help = "Install an OpenTopoMap base layer"

    def handle(self, *args, **options):
        base_layer = MapBaseLayer.objects.create(
            name="OpenTopoMap",
            base_layer_type="raster",
            tile_size=256,
            min_zoom=2,
            max_zoom=17,
            attribution='map data: © <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> contributors,'
            '<a href="http://viewfinderpanoramas.org">SRTM</a> | map style: © '
            '<a href="https://opentopomap.org">OpenTopoMap</a> '
            '(<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)',
        )
        BaseLayerTile.objects.bulk_create(
            [
                BaseLayerTile(
                    base_layer=base_layer,
                    url="https://a.tile.opentopomap.org/{z}/{x}/{y}.png",
                ),
                BaseLayerTile(
                    base_layer=base_layer,
                    url="https://b.tile.opentopomap.org/{z}/{x}/{y}.png",
                ),
                BaseLayerTile(
                    base_layer=base_layer,
                    url="https://c.tile.opentopomap.org/{z}/{x}/{y}.png",
                ),
            ]
        )
        self.stdout.write(
            self.style.SUCCESS("OpenTopoMap base layer has been created.")
        )
