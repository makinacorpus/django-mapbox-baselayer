from copy import deepcopy
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.contrib.gis.geos import Polygon
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from mapbox_baselayer.admin import BaseLayerRasterAdmin, BaseLayerStyleAdmin
from mapbox_baselayer.models import (
    BaseLayerRaster,
    BaseLayerStyle,
    BaseLayerTile,
    MapBaseLayer,
    PMTile,
)
from mapbox_baselayer.utils import DEFAULT_OSM_TILEJSON


class EmptyDatabaseTestCase(TestCase):
    def test_baselayer_list_returns_default_osm_entry(self):
        response = self.client.get(reverse("mapbox_baselayer:baselayer-list"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("base_layers", data)
        self.assertIn("overlay_layers", data)
        self.assertEqual(len(data["base_layers"]), 1)
        self.assertEqual(len(data["overlay_layers"]), 0)
        osm_entry = data["base_layers"][0]
        self.assertEqual(osm_entry["name"], "OSM")
        self.assertEqual(osm_entry["slug"], "osm")
        self.assertIn("default-osm/tilejson", osm_entry["url"])

    def test_default_osm_tilejson_endpoint(self):
        response = self.client.get(reverse("mapbox_baselayer:default-osm-tilejson"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        osm_tilejson = deepcopy(DEFAULT_OSM_TILEJSON)
        osm_tilejson["glyphs"] = f"http://testserver{DEFAULT_OSM_TILEJSON['glyphs']}"
        self.assertEqual(data, osm_tilejson)
        self.assertIn("osm", data["sources"])
        self.assertEqual(len(data["sources"]["osm"]["tiles"]), 3)


class MapBaseLayerViewTestCase(TestCase):
    def setUp(self) -> None:
        self.raster_base_layer = MapBaseLayer.objects.create(
            name="Raster layer",
            base_layer_type="raster",
            sprite="http://mystyle",
            glyphs="http://mystyle",
        )
        self.tile = BaseLayerTile.objects.create(
            base_layer=self.raster_base_layer, url="http://tiles/{x}/{y]/{z}"
        )
        self.mapbox_base_layer = MapBaseLayer.objects.create(
            name="Mapbox layer",
            order=0,
            base_layer_type="mapbox",
            style_url="mapbox://styles/mystyle",
        )

    def test_tilejson_raster(self):
        self.maxDiff = None
        response = self.client.get(
            reverse("mapbox_baselayer:tilejson", args=(self.raster_base_layer.pk,))
        )
        self.assertEqual(response.status_code, 200)
        slug = self.raster_base_layer.slug
        expected = {
            "layers": [
                {
                    "id": f"{slug}-background",
                    "source": slug,
                    "type": "raster",
                }
            ],
            "sources": {
                slug: {
                    "maxzoom": 22,
                    "minzoom": 0,
                    "tiles": ["http://tiles/{x}/{y]/{z}"],
                    "type": "raster",
                    "attribution": "",
                    "tileSize": 512,
                }
            },
            "version": 8,
            "sprite": "http://mystyle",
            "glyphs": "http://mystyle",
        }
        self.assertDictEqual(response.json(), expected)

    @patch("mapbox_baselayer.models.requests.get")
    def test_tilejson_mapbox(self, mock_get):
        self.maxDiff = None
        mock_response = Mock()
        mock_response.json.return_value = {
            "version": 8,
            "sources": {
                "mapbox": {"type": "vector", "url": "mapbox://mapbox.mapbox-streets-v7"}
            },
        }
        mock_get.return_value = mock_response
        response = self.client.get(
            reverse("mapbox_baselayer:tilejson", args=(self.mapbox_base_layer.pk,))
        )
        self.assertEqual(response.status_code, 200)

    def test_example_view(self):
        response = self.client.get(reverse("example"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "test_app/map_example.html")
        # Layers are now fetched via JavaScript fetch() call to the API
        self.assertContains(response, "/mapbox-baselayers/")

    def test_baselayer_list_view(self):
        # Add an overlay layer
        MapBaseLayer.objects.create(
            name="Overlay layer", base_layer_type="raster", is_overlay=True, order=1
        )
        response = self.client.get(reverse("mapbox_baselayer:baselayer-list"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("base_layers", data)
        self.assertIn("overlay_layers", data)
        self.assertEqual(len(data["base_layers"]), 2)
        self.assertEqual(len(data["overlay_layers"]), 1)
        self.assertEqual(data["overlay_layers"][0]["name"], "Overlay layer")

        # Check ordering
        self.assertEqual(data["base_layers"][0]["name"], "Mapbox layer")  # order=0
        self.assertEqual(
            data["base_layers"][1]["name"], "Raster layer"
        )  # order=0, but 'M' < 'R'


class AdminGetInlinesTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.raster_admin = BaseLayerRasterAdmin(BaseLayerRaster, AdminSite())
        self.style_admin = BaseLayerStyleAdmin(BaseLayerStyle, AdminSite())
        self.request = self.factory.get("/")
        self.request.user = User.objects.create_superuser("admin", "a@b.com", "pass")

    def test_inlines_for_raster(self):
        """Raster should have 2 inlines, one for tiles and one for pmtiles"""
        layer = MapBaseLayer.objects.create(name="R", base_layer_type="raster")
        inlines = self.raster_admin.get_inline_instances(self.request, obj=layer)
        self.assertEqual(len(inlines), 2)

    def test_for_style(self):
        """Style should have 1 inline, for pmtiles"""
        layer = MapBaseLayer.objects.create(name="M", base_layer_type="mapbox")
        inlines = self.style_admin.get_inline_instances(self.request, obj=layer)
        self.assertEqual(len(inlines), 1)


TEMP_MEDIA_ROOT = TemporaryDirectory()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT.name)
class ViewsCoverageTestCase(TestCase):
    def test_relative_glyphs_resolution(self):
        layer = MapBaseLayer.objects.create(
            name="Relative Glyphs Layer",
            base_layer_type="raster",
            glyphs="relative/glyphs/{fontstack}/{range}.pbf",
        )
        response = self.client.get(
            reverse("mapbox_baselayer:tilejson", args=(layer.pk,))
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            data["glyphs"],
            f"http://testserver/mapbox-baselayers/{layer.pk}/tilejson/relative/glyphs/{{fontstack}}/{{range}}.pbf",
        )

    def test_pmtiles_view_endpoint(self):
        layer = MapBaseLayer.objects.create(
            name="PMTiles Layer",
            base_layer_type="raster",
            attribution="My Attribution",
            min_zoom=3,
            max_zoom=10,
        )
        PMTile.objects.create(
            name="Test Offline PMTile",
            layer=layer,
            pmtiles_file=SimpleUploadedFile("test.pmtiles", b"dummy content"),
            pmtiles_style=SimpleUploadedFile("test.json", b"{}"),
            bbox=Polygon.from_bbox((1.0, 2.0, 3.0, 4.0)),
        )

        response = self.client.get(reverse("mapbox_baselayer:pmtiles-list"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        item = data[0]
        self.assertEqual(item["name"], "Test Offline PMTile")
        self.assertEqual(item["options"]["attribution"], "My Attribution")
        self.assertEqual(item["options"]["minZoom"], 3)
        self.assertEqual(item["options"]["maxZoom"], 10)
        self.assertAlmostEqual(item["options"]["center"][0], 2.0)
        self.assertAlmostEqual(item["options"]["center"][1], 3.0)
        self.assertEqual(item["options"]["maxBounds"], [[1.0, 2.0], [3.0, 4.0]])
