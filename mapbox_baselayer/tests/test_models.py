from django.test import TestCase

from mapbox_baselayer.models import MapBaseLayer


class MapBaseLayerTEstCase(TestCase):
    def setUp(self):
        self.map_base_layer = MapBaseLayer.objects.create(
            name='Base layer 1',
            order=0,
            base_layer_type='mapbox',
            map_box_url='mapbox://mystyle',
            sprite='mapbox://mystyle',
            glyphs='mapbox://mystyle',
        )

    def test_str(self):
        self.assertEqual(self.map_base_layer.name, 'Base layer 1')

    def test_clean_ok(self):
        self.assertIsNone(self.map_base_layer.clean())
