from unittest.mock import Mock, patch

from django.contrib.gis.geos import Polygon
from django.test import TestCase
from django.urls import reverse

from mapbox_baselayer.models import (
    BaseLayer,
    BaseLayerTile,
    MapBaseLayer,
    OverlayLayer,
    PMTile,
    pmtile_path_handler,
)


class MapBaseLayerTEstCase(TestCase):
    def setUp(self):
        self.mapbox_base_layer = MapBaseLayer.objects.create(
            name="Base layer 1",
            order=0,
            base_layer_type="mapbox",
            style_url="mapbox://styles/mystyle",
            sprite="mapbox://mystyle",
            glyphs="mapbox://mystyle",
        )
        self.raster_base_layer = MapBaseLayer.objects.create(
            name="Raster layer",
            base_layer_type="raster",
            sprite="http://mystyle",
            glyphs="http://mystyle",
        )

    def test_str(self):
        self.assertEqual(self.mapbox_base_layer.name, str(self.mapbox_base_layer))

    def test_style_url(self):
        self.assertEqual("mapbox://styles/mystyle", self.mapbox_base_layer.style_url)

    def test_raster_url(self):
        self.assertEqual(
            self.raster_base_layer.url,
            reverse("mapbox_baselayer:tilejson", args=(self.raster_base_layer.pk,)),
        )

    def test_ordering(self):
        MapBaseLayer.objects.all().delete()
        layer_c = MapBaseLayer.objects.create(
            name="C", order=2, base_layer_type="mapbox"
        )
        layer_a2 = MapBaseLayer.objects.create(
            name="A2", order=1, base_layer_type="mapbox"
        )
        layer_a1 = MapBaseLayer.objects.create(
            name="A1", order=1, base_layer_type="mapbox"
        )
        layer_b = MapBaseLayer.objects.create(
            name="B", order=1, base_layer_type="mapbox"
        )

        layers = list(MapBaseLayer.objects.all())
        self.assertEqual(layers, [layer_a1, layer_a2, layer_b, layer_c])


class ProxyModelsTestCase(TestCase):
    def setUp(self):
        MapBaseLayer.objects.all().delete()

    def test_base_layer_proxy_sets_is_overlay_false(self):
        layer = BaseLayer.objects.create(
            name="Test Base Layer", base_layer_type="raster"
        )
        self.assertFalse(layer.is_overlay)
        # Verify it's also False in the database
        layer.refresh_from_db()
        self.assertFalse(layer.is_overlay)

    def test_overlay_layer_proxy_sets_is_overlay_true(self):
        layer = OverlayLayer.objects.create(
            name="Test Overlay Layer", base_layer_type="raster"
        )
        self.assertTrue(layer.is_overlay)
        # Verify it's also True in the database
        layer.refresh_from_db()
        self.assertTrue(layer.is_overlay)

    def test_base_layer_manager_filters_correctly(self):
        BaseLayer.objects.create(name="Base 1", base_layer_type="raster")
        BaseLayer.objects.create(name="Base 2", base_layer_type="raster")
        OverlayLayer.objects.create(name="Overlay 1", base_layer_type="raster")

        self.assertEqual(BaseLayer.objects.count(), 2)
        self.assertEqual(OverlayLayer.objects.count(), 1)
        self.assertEqual(MapBaseLayer.objects.count(), 3)

    def test_proxy_models_share_same_table(self):
        base = BaseLayer.objects.create(name="Base Layer", base_layer_type="raster")
        overlay = OverlayLayer.objects.create(
            name="Overlay Layer", base_layer_type="raster"
        )

        # Both should be accessible via MapBaseLayer
        all_layers = MapBaseLayer.objects.all()
        self.assertEqual(all_layers.count(), 2)
        self.assertIn(base.pk, all_layers.values_list("pk", flat=True))
        self.assertIn(overlay.pk, all_layers.values_list("pk", flat=True))


class RealUrlTestCase(TestCase):
    def test_real_url_raster(self):
        layer = MapBaseLayer.objects.create(name="Raster", base_layer_type="raster")
        self.assertEqual(layer.real_url, layer.url)

    def test_real_url_mapbox(self):
        layer = MapBaseLayer.objects.create(
            name="Mapbox",
            base_layer_type="mapbox",
            style_url="mapbox://styles/user/style",
        )
        self.assertEqual(
            layer.real_url,
            "https://api.mapbox.com/styles/v1/user/style",
        )

    def test_real_url_vector(self):
        layer = MapBaseLayer.objects.create(
            name="Vector",
            base_layer_type="vector",
            style_url="mapbox://styles/user/vstyle",
        )
        self.assertEqual(
            layer.real_url,
            "https://api.mapbox.com/styles/v1/user/vstyle",
        )


class BaseLayerTileStrTestCase(TestCase):
    def test_str(self):
        layer = MapBaseLayer.objects.create(name="Test", base_layer_type="raster")
        tile = BaseLayerTile.objects.create(
            base_layer=layer, url="http://example.com/{z}/{x}/{y}.png"
        )
        self.assertEqual(str(tile), "Test - http://example.com/{z}/{x}/{y}.png")


class PMTileModelTestCase(TestCase):
    def setUp(self):
        self.layer = MapBaseLayer.objects.create(
            name="Test Base Layer", base_layer_type="raster"
        )
        self.pmtile = PMTile.objects.create(
            name="Test PMTile",
            layer=self.layer,
            bbox=Polygon.from_bbox((0, 0, 10, 10)),
        )

    def test_pmtile_str(self):
        self.assertEqual(str(self.pmtile), "Test PMTile")

    def test_pmtile_path_handler_other(self):
        path = pmtile_path_handler(self.pmtile, "test.txt")
        self.assertTrue(path.endswith("-other.txt"))

    def test_save_existing_updates_slug(self):
        layer = MapBaseLayer.objects.create(
            name="Original Name", base_layer_type="raster"
        )
        layer.name = "New Name"
        layer.save()
        layer.refresh_from_db()
        self.assertEqual(layer.slug, f"new-name-{layer.pk}")

    @patch("mapbox_baselayer.models.requests.get")
    def test_tilejson_style_url_attribution(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "version": 8,
            "sources": {
                "source1": {"type": "vector", "tiles": ["http://tiles"]},
                "source2": {
                    "type": "vector",
                    "tiles": ["http://tiles"],
                    "attribution": "Existing Attribution",
                },
            },
        }
        mock_get.return_value = mock_response

        layer = MapBaseLayer.objects.create(
            name="Style Layer",
            base_layer_type="mapbox",
            style_url="http://style-url",
            attribution="Layer Attribution",
        )

        data = layer.tilejson

        self.assertEqual(data["sources"]["source1"]["attribution"], "Layer Attribution")
        self.assertEqual(
            data["sources"]["source2"]["attribution"], "Existing Attribution"
        )
