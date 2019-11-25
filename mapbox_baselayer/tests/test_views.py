from django.test import TestCase
from django.urls import reverse

from mapbox_baselayer.models import MapBaseLayer, BaseLayerTile


class MapBaseLayerViewTestCase(TestCase):
    def setUp(self) -> None:
        self.map_base_layer = MapBaseLayer.objects.create(
            name='Raster test',
            base_layer_type='raster',
        )
        self.tile = BaseLayerTile.objects.create(base_layer=self.map_base_layer, url='http://tiles/{x}/{y]/{z}')

    def test_tilejson(self):
        response = self.client.get(reverse('mapbox_baselayer:tilejson', args=(self.map_base_layer.pk,)))
        self.assertEqual(response.status_code, 200)
        expected = {
            'layers': [
                {'id': 'raster-test-background',
                 'source': 'raster-test',
                 'type': 'raster'}],
            'sources': {'raster-test': {
                'maxzoom': 22,
                'minzoom': 0,
                'tiles': ['http://tiles/{x}/{y]/{z}'],
                'type': 'raster'}},
            'version': 8
        }
        self.assertDictEqual(response.json(), expected)
