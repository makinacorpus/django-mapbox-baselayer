from copy import deepcopy
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.contrib.gis.geos import Polygon
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from pmtiles.tile import Compression, TileType, zxy_to_tileid
from pmtiles.writer import Writer

from mapbox_baselayer.admin import MapBaseLayerAdmin
from mapbox_baselayer.models import (
    BaseLayerTile,
    MapBaseLayer,
    PMTile,
)
from mapbox_baselayer.utils import DEFAULT_OSM_TILEJSON


def build_pmtiles_bytes(
    tiles,
    tile_type=TileType.PNG,
    tile_compression=Compression.NONE,
):
    buf = BytesIO()
    writer = Writer(buf)
    for (z, x, y), data in sorted(
        tiles.items(), key=lambda item: zxy_to_tileid(*item[0])
    ):
        writer.write_tile(zxy_to_tileid(z, x, y), data)
    writer.finalize(
        {
            "tile_type": tile_type,
            "tile_compression": tile_compression,
            "min_zoom": 0,
            "max_zoom": 2,
            "min_lon_e7": -1800000000,
            "min_lat_e7": -850000000,
            "max_lon_e7": 1800000000,
            "max_lat_e7": 850000000,
        },
        {"attribution": "Test"},
    )
    return buf.getvalue()


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
                    "tileSize": 256,
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
        self.admin = MapBaseLayerAdmin(MapBaseLayer, AdminSite())
        self.request = self.factory.get("/")
        self.request.user = User.objects.create_superuser("admin", "a@b.com", "pass")

    def test_inlines(self):
        """MapBaseLayerAdmin should have 2 inlines, one for tiles and one for pmtiles"""
        layer = MapBaseLayer.objects.create(name="R", base_layer_type="raster")
        inlines = self.admin.get_inline_instances(self.request, obj=layer)
        self.assertEqual(len(inlines), 2)


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
        pmtile = PMTile.objects.create(
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
        self.assertEqual(
            item["tiles_url"],
            f"http://testserver/pmtiles/{pmtile.pk}/tiles/{{z}}/{{x}}/{{y}}/",
        )
        self.assertEqual(item["options"]["attribution"], "My Attribution")
        self.assertEqual(item["options"]["minZoom"], 3)
        self.assertEqual(item["options"]["maxZoom"], 10)
        self.assertAlmostEqual(item["options"]["center"][0], 2.0)
        self.assertAlmostEqual(item["options"]["center"][1], 3.0)
        self.assertEqual(item["options"]["maxBounds"], [[1.0, 2.0], [3.0, 4.0]])

    def test_pmtiles_tile_endpoint_png(self):
        layer = MapBaseLayer.objects.create(
            name="PMTiles PNG Layer",
            base_layer_type="raster",
        )
        pmtiles_bytes = build_pmtiles_bytes(
            {(0, 0, 0): b"png-tile-bytes"},
            tile_type=TileType.PNG,
            tile_compression=Compression.NONE,
        )
        pmtile = PMTile.objects.create(
            name="PNG PMTile",
            layer=layer,
            pmtiles_file=SimpleUploadedFile("tiles.pmtiles", pmtiles_bytes),
            pmtiles_style=SimpleUploadedFile("style.json", b"{}"),
            bbox=Polygon.from_bbox((1.0, 2.0, 3.0, 4.0)),
        )

        response = self.client.get(
            reverse(
                "mapbox_baselayer:pmtiles-tile",
                kwargs={"pk": pmtile.pk, "z": 0, "x": 0, "y": 0},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"png-tile-bytes")
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertNotIn("Content-Encoding", response)

    def test_pmtiles_tile_endpoint_mvt_gzip(self):
        layer = MapBaseLayer.objects.create(
            name="PMTiles MVT Layer",
            base_layer_type="mapbox",
            style_url="http://mock-style",
        )
        pmtiles_bytes = build_pmtiles_bytes(
            {(0, 0, 0): b"mvt-tile-bytes"},
            tile_type=TileType.MVT,
            tile_compression=Compression.GZIP,
        )
        pmtile = PMTile.objects.create(
            name="MVT PMTile",
            layer=layer,
            pmtiles_file=SimpleUploadedFile("tiles.pmtiles", pmtiles_bytes),
            pmtiles_style=SimpleUploadedFile("style.json", b"{}"),
            bbox=Polygon.from_bbox((1.0, 2.0, 3.0, 4.0)),
        )

        response = self.client.get(
            reverse(
                "mapbox_baselayer:pmtiles-tile",
                kwargs={"pk": pmtile.pk, "z": 0, "x": 0, "y": 0},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"mvt-tile-bytes")
        self.assertEqual(response["Content-Type"], "application/vnd.mapbox-vector-tile")
        self.assertEqual(response["Content-Encoding"], "gzip")

    def test_pmtiles_tile_endpoint_missing_and_out_of_bounds_returns_204(self):
        layer = MapBaseLayer.objects.create(
            name="PMTiles 204 Layer",
            base_layer_type="raster",
        )
        pmtiles_bytes = build_pmtiles_bytes({(0, 0, 0): b"png-tile-bytes"})
        pmtile = PMTile.objects.create(
            name="204 PMTile",
            layer=layer,
            pmtiles_file=SimpleUploadedFile("tiles.pmtiles", pmtiles_bytes),
            pmtiles_style=SimpleUploadedFile("style.json", b"{}"),
            bbox=Polygon.from_bbox((1.0, 2.0, 3.0, 4.0)),
        )

        # Tile not present in archive
        response_missing = self.client.get(
            reverse(
                "mapbox_baselayer:pmtiles-tile",
                kwargs={"pk": pmtile.pk, "z": 1, "x": 0, "y": 0},
            )
        )
        self.assertEqual(response_missing.status_code, 204)

        # Tile coordinates out of bounds for zoom level (x=5 at z=0)
        response_oob = self.client.get(
            reverse(
                "mapbox_baselayer:pmtiles-tile",
                kwargs={"pk": pmtile.pk, "z": 0, "x": 5, "y": 5},
            )
        )
        self.assertEqual(response_oob.status_code, 204)

    def test_pmtiles_tile_endpoint_errors_return_404(self):
        # Non-existent PMTile pk
        response_no_pk = self.client.get(
            reverse(
                "mapbox_baselayer:pmtiles-tile",
                kwargs={"pk": 9999, "z": 0, "x": 0, "y": 0},
            )
        )
        self.assertEqual(response_no_pk.status_code, 404)

        # Invalid PMTiles file content
        layer = MapBaseLayer.objects.create(
            name="PMTiles Invalid Layer",
            base_layer_type="raster",
        )
        pmtile = PMTile.objects.create(
            name="Invalid PMTile",
            layer=layer,
            pmtiles_file=SimpleUploadedFile("invalid.pmtiles", b"not a pmtiles file"),
            pmtiles_style=SimpleUploadedFile("style.json", b"{}"),
            bbox=Polygon.from_bbox((1.0, 2.0, 3.0, 4.0)),
        )
        response_invalid = self.client.get(
            reverse(
                "mapbox_baselayer:pmtiles-tile",
                kwargs={"pk": pmtile.pk, "z": 0, "x": 0, "y": 0},
            )
        )
        self.assertEqual(response_invalid.status_code, 404)
