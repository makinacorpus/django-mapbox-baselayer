import os
import shutil
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.core.management import call_command
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
        # Appel de la commande (on utilise des zooms bas pour aller vite)
        call_command("generate_pmtiles", self.layer.id, minzoom=0, maxzoom=0)

        # Vérification qu'une instance PMTile a été créée
        pmtile_exists = PMTile.objects.filter(layer=self.layer).exists()
        self.assertTrue(pmtile_exists, "L'instance PMTile devrait avoir été créée")

        pmtile = PMTile.objects.get(layer=self.layer)
        self.assertEqual(pmtile.min_zoom, 0)
        self.assertEqual(pmtile.max_zoom, 0)
        self.assertIsNotNone(pmtile.pmtiles_file)
        self.assertIsNotNone(pmtile.pmtiles_style)
        self.assertTrue(pmtile.name.startswith("Test Layer"))

    def test_generate_pmtiles_creates_new_instance_each_time(self):
        # On s'assure que les dossiers existent ou sont propres
        if os.path.exists("var/tiles/pmtiles"):
            shutil.rmtree("var/tiles/pmtiles")

        # Premier appel
        call_command("generate_pmtiles", self.layer.id, minzoom=0, maxzoom=0)
        self.assertEqual(PMTile.objects.filter(layer=self.layer).count(), 1)

        # Deuxième appel
        call_command("generate_pmtiles", self.layer.id, minzoom=0, maxzoom=0)
        self.assertEqual(PMTile.objects.filter(layer=self.layer).count(), 2)

        # Nettoyage
        if os.path.exists("var/tiles/pmtiles"):
            shutil.rmtree("var/tiles/pmtiles")
        if os.path.exists("var/tmp"):
            shutil.rmtree("var/tmp")

    def test_generate_pmtiles_creates_pmtile_instance_with_custom_name(self):
        # Appel de la commande avec un nom spécifique
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

    @patch("mapbox_baselayer.management.commands.generate_pmtiles.time.sleep")
    def test_generate_pmtiles_download_failure(self, mock_sleep):
        import requests

        mock_response_ok = Mock()
        mock_response_ok.raise_for_status.return_value = None
        mock_response_ok.content = b"dummy tile bytes"

        self.mock_get.side_effect = [
            mock_response_ok,
            requests.exceptions.RequestException("Download error"),
            requests.exceptions.RequestException("Download error"),
            requests.exceptions.RequestException("Download error"),
            requests.exceptions.RequestException("Download error"),
        ]
        call_command("generate_pmtiles", self.layer.id, minzoom=0, maxzoom=1)
        self.assertTrue(PMTile.objects.filter(layer=self.layer).exists())

    @patch("mapbox_baselayer.management.commands.generate_pmtiles.logger")
    def test_download_tile_worker_logs_http_status_and_message(self, mock_logger):
        import requests

        from mapbox_baselayer.management.commands.generate_pmtiles import Command

        command = Command()
        retry_error = requests.exceptions.RetryError(
            "Failed after 3 attempts for http://mock-tile: HTTP 503: Service Unavailable"
        )

        with patch.object(command, "get_or_retry", side_effect=retry_error):
            tile_id, content = command.download_tile_worker(1, "http://mock-tile")

        self.assertEqual(tile_id, 1)
        self.assertIsNone(content)
        mock_logger.error.assert_called_once()
        self.assertIn(
            "HTTP 503: Service Unavailable", str(mock_logger.error.call_args[0][2])
        )

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

    def test_get_tile_type_returns_none(self):
        from mapbox_baselayer.management.commands.generate_pmtiles import Command

        cmd = Command()
        layer = MapBaseLayer(base_layer_type="unknown")
        self.assertIsNone(cmd.get_tile_type(layer))
