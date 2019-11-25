from django.test import TestCase
from django.urls import reverse

from mapbox_baselayer.models import MapBaseLayer


class MapBaseLayerTEstCase(TestCase):
    def setUp(self):
        self.mapbox_base_layer = MapBaseLayer.objects.create(
            name='Base layer 1',
            order=0,
            base_layer_type='mapbox',
            map_box_url='mapbox://mystyle',
            sprite='mapbox://mystyle',
            glyphs='mapbox://mystyle',
        )
        self.raster_base_layer = MapBaseLayer.objects.create(
            name='Raster layer',
            base_layer_type='raster',
            sprite='http://mystyle',
            glyphs='http://mystyle',
        )

    def test_str(self):
        self.assertEqual(self.mapbox_base_layer.name, str(self.mapbox_base_layer))

    def test_mapbox_url(self):
        self.assertEqual(self.mapbox_base_layer.url, self.mapbox_base_layer.map_box_url)

    def test_raster_url(self):
        self.assertEqual(self.raster_base_layer.url,
                         reverse('mapbox_baselayer:tilejson',
                                 args=(self.raster_base_layer.pk, )))
