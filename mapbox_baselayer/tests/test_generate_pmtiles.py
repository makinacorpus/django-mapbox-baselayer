import os
import shutil
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.contrib.gis.geos import Polygon
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from mapbox_baselayer.models import MapBaseLayer, PMTile

TEMP_MEDIA_ROOT = TemporaryDirectory()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT.name)
class GeneratePMTilesCommandTestCase(TestCase):
    def setUp(self):
        patcher = patch(
            "mapbox_baselayer.management.commands.generate_pmtiles.requests.get"
        )
        self.mock_get = patcher.start()
        self.addCleanup(patcher.stop)

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"dummy tile bytes"
        self.mock_get.return_value = mock_response

        self.layer = MapBaseLayer.objects.create(
            name="Test Layer",
            base_layer_type="raster",
            min_zoom=0,
            max_zoom=2,
            attribution="Test Attribution",
        )
        self.layer.tiles.create(url="https://tile.openstreetmap.org/{z}/{x}/{y}.png")

    def test_generate_pmtiles_creates_pmtile_instance(self):
        # Call the command (use low zoom levels for speed)
        call_command("generate_pmtiles", self.layer.id, minzoom=0, maxzoom=0)

        # Verify that a PMTile instance was created
        pmtile_exists = PMTile.objects.filter(layer=self.layer).exists()
        self.assertTrue(pmtile_exists, "L'instance PMTile devrait avoir été créée")

        pmtile = PMTile.objects.get(layer=self.layer)
        self.assertEqual(pmtile.min_zoom, 0)
        self.assertEqual(pmtile.max_zoom, 0)
        self.assertIsNotNone(pmtile.pmtiles_file)
        self.assertIsNotNone(pmtile.pmtiles_style)
        self.assertTrue(pmtile.name.startswith("Test Layer"))

    def test_generate_pmtiles_creates_new_instance_each_time(self):
        # Ensure folders are clean
        if os.path.exists("var/tiles/pmtiles"):
            shutil.rmtree("var/tiles/pmtiles")

        # First call
        call_command("generate_pmtiles", self.layer.id, minzoom=0, maxzoom=0)
        self.assertEqual(PMTile.objects.filter(layer=self.layer).count(), 1)

        # Second call
        call_command("generate_pmtiles", self.layer.id, minzoom=0, maxzoom=0)
        self.assertEqual(PMTile.objects.filter(layer=self.layer).count(), 2)

        # Cleanup
        if os.path.exists("var/tiles/pmtiles"):
            shutil.rmtree("var/tiles/pmtiles")
        if os.path.exists("var/tmp"):
            shutil.rmtree("var/tmp")

    def test_generate_pmtiles_creates_pmtile_instance_with_custom_name(self):
        # Call the command with a specific name
        custom_name = "Custom Region"
        call_command(
            "generate_pmtiles", self.layer.id, minzoom=0, maxzoom=0, name=custom_name
        )

        pmtile = PMTile.objects.get(layer=self.layer, name=custom_name)
        self.assertEqual(pmtile.name, custom_name)
        self.assertEqual(pmtile.min_zoom, 0)
        self.assertEqual(pmtile.max_zoom, 0)

    def test_generate_pmtiles_raises_does_not_exist(self):
        with self.assertRaises(MapBaseLayer.DoesNotExist):
            call_command("generate_pmtiles", 9999, minzoom=0, maxzoom=0)

    @patch("mapbox_baselayer.management.commands.generate_pmtiles.logger")
    def test_generate_pmtiles_out_of_bounds_zooms(self, mock_logger):
        call_command("generate_pmtiles", self.layer.id, minzoom=-1, maxzoom=5)
        self.assertTrue(mock_logger.warning.called)

    def test_generate_pmtiles_style_url_type(self):
        style_layer = MapBaseLayer.objects.create(
            name="Style Layer",
            base_layer_type="mapbox",  # STYLE_URL
            min_zoom=0,
            max_zoom=0,
            style_url="http://mock-style-url",
        )
        mock_response_style = Mock()
        mock_response_style.raise_for_status.return_value = None
        mock_response_style.json.return_value = {
            "sources": {"mysource": {"tiles": ["https://my-tiles/{z}/{x}/{y}.pbf"]}}
        }
        mock_response_tile = Mock()
        mock_response_tile.raise_for_status.return_value = None
        mock_response_tile.content = b"dummy tile bytes"

        self.mock_get.side_effect = [mock_response_style, mock_response_tile]

        call_command("generate_pmtiles", style_layer.id, minzoom=0, maxzoom=0)
        pmtile = PMTile.objects.get(layer=style_layer)
        self.assertEqual(pmtile.min_zoom, 0)
        self.assertEqual(pmtile.max_zoom, 0)

    @patch("mapbox_baselayer.management.commands.generate_pmtiles.time.sleep")
    def test_generate_pmtiles_retry_error(self, mock_sleep):
        import requests

        style_layer = MapBaseLayer.objects.create(
            name="Style Layer Retry",
            base_layer_type="mapbox",  # STYLE_URL
            style_url="http://mock-style-url",
        )
        self.mock_get.side_effect = requests.exceptions.RequestException(
            "Connection failed"
        )
        with self.assertRaises(requests.exceptions.RetryError):
            call_command("generate_pmtiles", style_layer.id, minzoom=0, maxzoom=0)

    @patch("mapbox_baselayer.management.commands.generate_pmtiles.time.sleep")
    def test_generate_pmtiles_retry_error_contains_http_status_and_message(
        self, mock_sleep
    ):
        import requests

        style_layer = MapBaseLayer.objects.create(
            name="Style Layer HTTP Error",
            base_layer_type="mapbox",
            style_url="http://mock-style-url",
        )
        mock_response = Mock(status_code=404, reason="Not Found")
        http_error = requests.exceptions.HTTPError(response=mock_response)
        self.mock_get.side_effect = http_error

        with self.assertRaises(requests.exceptions.RetryError) as ctx:
            call_command("generate_pmtiles", style_layer.id, minzoom=0, maxzoom=0)

        self.assertIn("HTTP 404: Not Found", str(ctx.exception))

    def test_generate_pmtiles_zero_tiles(self):
        call_command("generate_pmtiles", self.layer.id, minzoom=2, maxzoom=1)
        self.assertFalse(PMTile.objects.filter(layer=self.layer).exists())

    @patch("mapbox_baselayer.management.commands.generate_pmtiles.Writer")
    @patch("mapbox_baselayer.management.commands.generate_pmtiles.time.sleep")
    def test_generate_pmtiles_download_failure(self, mock_sleep, mock_writer_cls):
        import requests

        mock_response_ok = Mock()
        mock_response_ok.raise_for_status.return_value = None
        mock_response_ok.content = b"dummy tile bytes"

        mock_response_404 = Mock(status_code=404, reason="Not Found")
        mock_response_404.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response_404
        )

        self.mock_get.side_effect = [
            mock_response_ok,
            mock_response_404,
            mock_response_ok,
        ]
        call_command("generate_pmtiles", self.layer.id, minzoom=0, maxzoom=2)
        self.assertTrue(PMTile.objects.filter(layer=self.layer).exists())
        self.assertEqual(self.mock_get.call_count, 3)
        mock_sleep.assert_not_called()
        self.assertEqual(mock_writer_cls.return_value.write_tile.call_count, 2)

    @patch("mapbox_baselayer.management.commands.generate_pmtiles.time.sleep")
    @patch("mapbox_baselayer.management.commands.generate_pmtiles.logger")
    def test_download_tile_worker_logs_url_and_http_status_without_retry(
        self, mock_logger, mock_sleep
    ):
        import requests

        from mapbox_baselayer.management.commands.generate_pmtiles import Command

        command = Command()
        mock_response = Mock(status_code=503, reason="Service Unavailable")
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )
        self.mock_get.return_value = mock_response

        tile_id, content = command.download_tile_worker(1, "http://mock-tile")

        self.assertEqual(tile_id, 1)
        self.assertIsNone(content)
        self.mock_get.assert_called_once()
        mock_sleep.assert_not_called()
        mock_logger.warning.assert_called_once_with(
            "%s (%s)", "http://mock-tile", "HTTP 503"
        )
        mock_logger.error.assert_not_called()

    @patch("mapbox_baselayer.management.commands.generate_pmtiles.time.sleep")
    @patch("mapbox_baselayer.management.commands.generate_pmtiles.logger")
    def test_download_tile_worker_logs_url_and_network_error_without_retry(
        self, mock_logger, mock_sleep
    ):
        import requests

        from mapbox_baselayer.management.commands.generate_pmtiles import Command

        command = Command()
        self.mock_get.side_effect = requests.exceptions.ConnectionError(
            "Connection failed"
        )

        tile_id, content = command.download_tile_worker(1, "http://mock-tile")

        self.assertEqual(tile_id, 1)
        self.assertIsNone(content)
        self.mock_get.assert_called_once()
        mock_sleep.assert_not_called()
        mock_logger.warning.assert_called_once_with(
            "%s (%s)", "http://mock-tile", "Connection failed"
        )
        mock_logger.error.assert_not_called()

    @patch("mapbox_baselayer.management.commands.generate_pmtiles.wait")
    def test_generate_pmtiles_large_number_of_tiles(self, mock_wait):
        # We mock wait to return all futures as done immediately
        mock_wait.side_effect = lambda futures, return_when: (set(futures), set())

        from mapbox_baselayer.settings import default_config

        original_bbox = default_config["DEFAULT_BBOX"]
        default_config["DEFAULT_BBOX"] = (-180, -85, 180, 85)

        try:
            large_layer = MapBaseLayer.objects.create(
                name="Large Layer",
                base_layer_type="raster",
                min_zoom=0,
                max_zoom=4,
                attribution="Test Attribution",
            )
            large_layer.tiles.create(
                url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            )
            call_command("generate_pmtiles", large_layer.id, minzoom=0, maxzoom=4)
            pmtile = PMTile.objects.get(layer=large_layer)
            self.assertEqual(pmtile.min_zoom, 0)
            self.assertEqual(pmtile.max_zoom, 4)
        finally:
            default_config["DEFAULT_BBOX"] = original_bbox

    def test_generate_pmtiles_bbox_overrides_default(self):
        call_command(
            "generate_pmtiles",
            self.layer.id,
            minzoom=0,
            maxzoom=0,
            bbox="-10,-10,10,10",
        )
        pmtile = PMTile.objects.get(layer=self.layer)
        expected_bbox = Polygon.from_bbox((-10.0, -10.0, 10.0, 10.0))
        expected_bbox.srid = 4326
        self.assertEqual(pmtile.bbox.extent, expected_bbox.extent)

    def test_generate_pmtiles_invalid_bbox_raises_command_error(self):
        with self.assertRaises(CommandError):
            call_command(
                "generate_pmtiles",
                self.layer.id,
                minzoom=0,
                maxzoom=0,
                bbox="not,valid",
            )

    def test_get_tile_type_returns_none(self):
        from mapbox_baselayer.management.commands.generate_pmtiles import Command

        cmd = Command()
        layer = MapBaseLayer(base_layer_type="unknown")
        self.assertIsNone(cmd.get_tile_type(layer))
