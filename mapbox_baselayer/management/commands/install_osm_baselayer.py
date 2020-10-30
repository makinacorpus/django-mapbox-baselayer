from django.core.management import BaseCommand
from django.utils.translation import gettext_lazy as _
from mapbox_baselayer.models import MapBaseLayer, BaseLayerTile


class Command(BaseCommand):
    help = _("Install an OSM base layer")

    def handle(self, *args, **options):
        base_layer = MapBaseLayer.objects.create(
            name="OSM",
            base_layer_type="raster",
            tile_size=256,
            min_zoom=0,
            max_zoom=19,
            attribution='<a href="https://www.openstreetmap.org/copyright">OSM Contributors</a>'
        )
        BaseLayerTile.objects.bulk_create([
            BaseLayerTile(base_layer=base_layer, url="//a.tile.openstreetmap.org/{z}/{x}/{y}.png"),
            BaseLayerTile(base_layer=base_layer, url="//b.tile.openstreetmap.org/{z}/{x}/{y}.png"),
            BaseLayerTile(base_layer=base_layer, url="//c.tile.openstreetmap.org/{z}/{x}/{y}.png"),
        ])
        self.stdout.write(self.style.SUCCESS(_("OSM base layer has been created.")))
