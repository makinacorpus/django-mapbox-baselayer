from django.core.management import BaseCommand

from mapbox_baselayer.models import MapBaseLayer


class Command(BaseCommand):
    help = "Install a MapBox base layer"

    def add_arguments(self, parser):
        parser.add_argument(
            "--mapbox-url",
            action="store",
            help="Mapbox url to use",
            default="mapbox://styles/mapbox/streets-v11",
        )

    def handle(self, *args, **options):
        MapBaseLayer.objects.create(
            name="Mapbox",
            base_layer_type="mapbox",
            tile_size=512,
            min_zoom=0,
            max_zoom=22,
            attribution="© Mapbox",
            map_box_url=options.get("mapbox_url"),
        )
        self.stdout.write(self.style.SUCCESS("Mapbox base layer has been created."))
