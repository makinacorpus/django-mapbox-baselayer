from django.core.management import BaseCommand

from mapbox_baselayer.models import BaseLayerTile, MapBaseLayer


class Command(BaseCommand):
    help = "Install an OSM base layer"

    def handle(self, *args, **options):
        base_layer = MapBaseLayer.objects.create(
            name="OSM",
            base_layer_type="raster",
            tile_size=256,
            min_zoom=0,
            max_zoom=19,
            attribution='<a href="https://www.openstreetmap.org/copyright">OSM Contributors</a>',
        )
        BaseLayerTile.objects.bulk_create(
            [
                BaseLayerTile(
                    base_layer=base_layer,
                    url="https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
                ),
                BaseLayerTile(
                    base_layer=base_layer,
                    url="https://b.tile.openstreetmap.org/{z}/{x}/{y}.png",
                ),
                BaseLayerTile(
                    base_layer=base_layer,
                    url="https://c.tile.openstreetmap.org/{z}/{x}/{y}.png",
                ),
            ]
        )
        self.stdout.write(self.style.SUCCESS("OSM base layer has been created."))
