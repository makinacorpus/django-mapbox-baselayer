from django.test import TestCase
from django.urls import reverse

from mapbox_baselayer.models import MapBaseLayer
from mapbox_baselayer.utils import get_map_base_layers


class GetMapBaseLayersTestCase(TestCase):
    def test_no_enabled_layers_returns_default_osm(self):
        """Test that when there are no enabled layers, the default OSM layer is returned."""
        # Create a disabled layer to ensure it's not included
        MapBaseLayer.objects.create(
            name="Disabled layer",
            base_layer_type="raster",
            enabled=False,
        )

        data = get_map_base_layers()

        self.assertIn("base_layers", data)
        self.assertIn("overlay_layers", data)
        self.assertEqual(len(data["base_layers"]), 1)
        self.assertEqual(len(data["overlay_layers"]), 0)

        # Check default OSM layer is returned
        osm_entry = data["base_layers"][0]
        self.assertEqual(osm_entry["name"], "OSM")
        self.assertEqual(osm_entry["slug"], "osm")
        self.assertEqual(
            osm_entry["url"], reverse("mapbox_baselayer:default-osm-tilejson")
        )

    def test_only_base_layers(self):
        """Test that only base layers are returned when no overlay layers exist."""
        MapBaseLayer.objects.create(
            name="Base layer 1",
            base_layer_type="mapbox",
            map_box_url="mapbox://style1",
            enabled=True,
            is_overlay=False,
        )
        MapBaseLayer.objects.create(
            name="Base layer 2",
            base_layer_type="mapbox",
            map_box_url="mapbox://style2",
            enabled=True,
            is_overlay=False,
        )

        data = get_map_base_layers()

        self.assertIn("base_layers", data)
        self.assertIn("overlay_layers", data)
        self.assertEqual(len(data["base_layers"]), 2)
        self.assertEqual(len(data["overlay_layers"]), 0)

        # Verify base layer data
        base_layer_names = [bl["name"] for bl in data["base_layers"]]
        self.assertIn("Base layer 1", base_layer_names)
        self.assertIn("Base layer 2", base_layer_names)

        # Verify structure of returned layers
        for bl in data["base_layers"]:
            self.assertIn("name", bl)
            self.assertIn("slug", bl)
            self.assertIn("url", bl)

    def test_only_overlay_layers(self):
        """Test that only overlay layers are returned and default OSM is used for base."""
        MapBaseLayer.objects.create(
            name="Overlay layer 1",
            base_layer_type="raster",
            enabled=True,
            is_overlay=True,
        )
        MapBaseLayer.objects.create(
            name="Overlay layer 2",
            base_layer_type="raster",
            enabled=True,
            is_overlay=True,
        )

        data = get_map_base_layers()

        self.assertIn("base_layers", data)
        self.assertIn("overlay_layers", data)
        # Should return default OSM when no base layers exist
        self.assertEqual(len(data["base_layers"]), 1)
        self.assertEqual(len(data["overlay_layers"]), 2)

        # Check default OSM layer is returned
        osm_entry = data["base_layers"][0]
        self.assertEqual(osm_entry["name"], "OSM")

        # Verify overlay layer data
        overlay_layer_names = [ol["name"] for ol in data["overlay_layers"]]
        self.assertIn("Overlay layer 1", overlay_layer_names)
        self.assertIn("Overlay layer 2", overlay_layer_names)

        # Verify structure of returned layers
        for ol in data["overlay_layers"]:
            self.assertIn("name", ol)
            self.assertIn("slug", ol)
            self.assertIn("url", ol)

    def test_mix_of_base_and_overlay_layers(self):
        """Test that both base and overlay layers are correctly separated and returned."""
        base_layer = MapBaseLayer.objects.create(
            name="Base layer",
            base_layer_type="mapbox",
            map_box_url="mapbox://base",
            enabled=True,
            is_overlay=False,
        )
        overlay_layer = MapBaseLayer.objects.create(
            name="Overlay layer",
            base_layer_type="raster",
            enabled=True,
            is_overlay=True,
        )

        data = get_map_base_layers()

        self.assertIn("base_layers", data)
        self.assertIn("overlay_layers", data)
        self.assertEqual(len(data["base_layers"]), 1)
        self.assertEqual(len(data["overlay_layers"]), 1)

        # Verify base layer
        self.assertEqual(data["base_layers"][0]["name"], "Base layer")
        self.assertEqual(data["base_layers"][0]["slug"], base_layer.slug)
        self.assertEqual(data["base_layers"][0]["url"], base_layer.url)

        # Verify overlay layer
        self.assertEqual(data["overlay_layers"][0]["name"], "Overlay layer")
        self.assertEqual(data["overlay_layers"][0]["slug"], overlay_layer.slug)
        self.assertEqual(data["overlay_layers"][0]["url"], overlay_layer.url)

    def test_disabled_layers_are_excluded(self):
        """Test that disabled layers are not included in the results."""
        MapBaseLayer.objects.create(
            name="Enabled base",
            base_layer_type="mapbox",
            map_box_url="mapbox://enabled",
            enabled=True,
            is_overlay=False,
        )
        MapBaseLayer.objects.create(
            name="Disabled base",
            base_layer_type="mapbox",
            map_box_url="mapbox://disabled",
            enabled=False,
            is_overlay=False,
        )
        MapBaseLayer.objects.create(
            name="Enabled overlay",
            base_layer_type="raster",
            enabled=True,
            is_overlay=True,
        )
        MapBaseLayer.objects.create(
            name="Disabled overlay",
            base_layer_type="raster",
            enabled=False,
            is_overlay=True,
        )

        data = get_map_base_layers()

        # Only enabled layers should be present
        self.assertEqual(len(data["base_layers"]), 1)
        self.assertEqual(len(data["overlay_layers"]), 1)

        self.assertEqual(data["base_layers"][0]["name"], "Enabled base")
        self.assertEqual(data["overlay_layers"][0]["name"], "Enabled overlay")

    def test_empty_database_returns_default_osm(self):
        """Test that an empty database returns the default OSM layer."""
        data = get_map_base_layers()

        self.assertIn("base_layers", data)
        self.assertIn("overlay_layers", data)
        self.assertEqual(len(data["base_layers"]), 1)
        self.assertEqual(len(data["overlay_layers"]), 0)

        # Check default OSM layer
        osm_entry = data["base_layers"][0]
        self.assertEqual(osm_entry["name"], "OSM")
        self.assertEqual(osm_entry["slug"], "osm")
        self.assertEqual(
            osm_entry["url"], reverse("mapbox_baselayer:default-osm-tilejson")
        )
