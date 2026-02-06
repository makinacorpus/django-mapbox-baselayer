from django.test import TestCase
from django.urls import reverse

from mapbox_baselayer.models import MapBaseLayer, BaseLayerTile


class MapBaseLayerViewTestCase(TestCase):
    def setUp(self) -> None:
        self.raster_base_layer = MapBaseLayer.objects.create(
            name='Raster layer',
            base_layer_type='raster',
            sprite='http://mystyle',
            glyphs='http://mystyle',
        )
        self.tile = BaseLayerTile.objects.create(
            base_layer=self.raster_base_layer,
            url='http://tiles/{x}/{y]/{z}'
        )
        self.mapbox_base_layer = MapBaseLayer.objects.create(
            name='Mapbox layer',
            order=0,
            base_layer_type='mapbox',
            map_box_url='mapbox://mystyle',
        )

    def test_tilejson_raster(self):
        self.maxDiff = None
        response = self.client.get(reverse('mapbox_baselayer:tilejson', args=(self.raster_base_layer.pk,)))
        self.assertEqual(response.status_code, 200)
        expected = {
            'layers': [
                {'id': 'raster-layer-background',
                 'source': 'raster-layer',
                 'type': 'raster'}],
            'sources': {'raster-layer': {
                'maxzoom': 22,
                'minzoom': 0,
                'tiles': ['http://tiles/{x}/{y]/{z}'],
                'type': 'raster',
                'attribution': '',
                'tileSize': 512, }},
            'version': 8,
            'sprite': 'http://mystyle',
            'glyphs': 'http://mystyle',
        }
        self.assertDictEqual(response.json(), expected)

    def test_tilejson_mapbox(self):
        self.maxDiff = None
        response = self.client.get(reverse('mapbox_baselayer:tilejson', args=(self.mapbox_base_layer.pk,)))
        self.assertEqual(response.status_code, 404)

    def test_example_view(self):
        response = self.client.get(reverse('example'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'test_app/map_example.html')
        # Layers are now fetched via JavaScript fetch() call to the API
        self.assertContains(response, '/mapbox-baselayers/')

    def test_baselayer_list_view(self):
        # Add an overlay layer
        MapBaseLayer.objects.create(
            name='Overlay layer',
            base_layer_type='raster',
            is_overlay=True,
            order=1
        )
        response = self.client.get(reverse('mapbox_baselayer:baselayer-list'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('base_layers', data)
        self.assertIn('overlay_layers', data)
        self.assertEqual(len(data['base_layers']), 2)
        self.assertEqual(len(data['overlay_layers']), 1)
        self.assertEqual(data['overlay_layers'][0]['name'], 'Overlay layer')

        # Check ordering
        self.assertEqual(data['base_layers'][0]['name'], 'Mapbox layer')  # order=0
        self.assertEqual(data['base_layers'][1]['name'], 'Raster layer')  # order=0, but 'M' < 'R'
