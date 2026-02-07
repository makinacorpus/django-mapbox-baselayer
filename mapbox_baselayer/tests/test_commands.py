from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from mapbox_baselayer.models import BaseLayerTile, MapBaseLayer


class InstallOpenTopoMapCommand(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command(
            "install_opentopomap_baselayer", stdout=StringIO(), stderr=StringIO()
        )

    def test_base_layer_is_present(self):
        self.assertTrue(MapBaseLayer.objects.filter(name="OpenTopoMap").exists())

    def test_tile_are_present_and_differents(self):
        tiles = BaseLayerTile.objects.all()
        self.assertEqual(len(tiles), 3)

        self.assertEqual(len(set(tiles.values_list("url", flat=True))), 3)


class InstallOSMCommand(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("install_osm_baselayer", stdout=StringIO(), stderr=StringIO())

    def test_base_layer_is_present(self):
        self.assertTrue(MapBaseLayer.objects.filter(name="OSM").exists())

    def test_tile_are_present_and_differents(self):
        tiles = BaseLayerTile.objects.all()
        self.assertEqual(len(tiles), 3)

        self.assertEqual(len(set(tiles.values_list("url", flat=True))), 3)


class InstallMapboxCommand(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("install_mapbox_baselayer", stdout=StringIO(), stderr=StringIO())

    def test_without_arguments(self):
        self.assertTrue(MapBaseLayer.objects.filter(name="Mapbox").exists())


class InstallIGNCommandDefault(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("install_ign_baselayer", stdout=StringIO(), stderr=StringIO())

    def test_default_creates_ortho(self):
        self.assertTrue(MapBaseLayer.objects.filter(name="IGN ortho").exists())

    def test_default_ortho_is_raster(self):
        layer = MapBaseLayer.objects.get(name="IGN ortho")
        self.assertEqual(layer.base_layer_type, "raster")
        self.assertEqual(layer.tile_size, 256)
        self.assertFalse(layer.is_overlay)

    def test_default_ortho_has_tile(self):
        layer = MapBaseLayer.objects.get(name="IGN ortho")
        tiles = BaseLayerTile.objects.filter(base_layer=layer)
        self.assertEqual(tiles.count(), 1)
        self.assertIn("ORTHOIMAGERY.ORTHOPHOTOS", tiles.first().url)
        self.assertNotIn("apikey", tiles.first().url)


class InstallIGNCommandMultipleLayers(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command(
            "install_ign_baselayer",
            "--layers",
            "ortho",
            "plan",
            "cadastre",
            "plan_vt",
            stdout=StringIO(),
            stderr=StringIO(),
        )

    def test_all_layers_created(self):
        for name in ["IGN ortho", "IGN plan", "IGN cadastre", "IGN plan_vt"]:
            self.assertTrue(
                MapBaseLayer.objects.filter(name=name).exists(), f"{name} missing"
            )

    def test_cadastre_is_overlay(self):
        layer = MapBaseLayer.objects.get(name="IGN cadastre")
        self.assertTrue(layer.is_overlay)

    def test_plan_vt_is_mapbox_style(self):
        layer = MapBaseLayer.objects.get(name="IGN plan_vt")
        self.assertEqual(layer.base_layer_type, "mapbox")
        self.assertEqual(layer.tile_size, 512)
        self.assertIn("vectorTiles", layer.map_box_url)


class InstallIGNCommandWithKey(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command(
            "install_ign_baselayer",
            "--key",
            "mykey",
            "--layers",
            "maps",
            "scan_25",
            stdout=StringIO(),
            stderr=StringIO(),
        )

    def test_layers_with_key_have_apikey(self):
        for name in ["IGN maps", "IGN scan_25"]:
            layer = MapBaseLayer.objects.get(name=name)
            tile = BaseLayerTile.objects.filter(base_layer=layer).first()
            self.assertIn("apikey=mykey", tile.url)


class InstallIGNCommandInvalidLayer(TestCase):
    def test_invalid_layer_raises_error(self):
        from django.core.management import CommandError

        with self.assertRaises(CommandError):
            call_command(
                "install_ign_baselayer",
                "--layers",
                "invalid_layer",
                stdout=StringIO(),
                stderr=StringIO(),
            )
