from django.core.management import call_command
from django.test import TestCase

from mapbox_baselayer.models import BaseLayerTile, MapBaseLayer


class InstallOpenTopoMapCommand(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("install_opentopomap_baselayer")

    def test_base_layer_is_present(self):
        self.assertTrue(MapBaseLayer.objects.filter(name="OpenTopoMap").exists())

    def test_tile_are_present_and_differents(self):
        tiles = BaseLayerTile.objects.all()
        self.assertEqual(len(tiles), 3)

        self.assertEqual(len(set(tiles.values_list("url", flat=True))), 3)


class InstallOSMCommand(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("install_osm_baselayer")

    def test_base_layer_is_present(self):
        self.assertTrue(MapBaseLayer.objects.filter(name="OSM").exists())

    def test_tile_are_present_and_differents(self):
        tiles = BaseLayerTile.objects.all()
        self.assertEqual(len(tiles), 3)

        self.assertEqual(len(set(tiles.values_list("url", flat=True))), 3)


class InstallMapboxCommand(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("install_mapbox_baselayer")

    def test_without_arguments(self):
        self.assertTrue(MapBaseLayer.objects.filter(name="Mapbox").exists())


class InstallIGNCommand(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("install_ign_baselayer", "mykey", "--layers", "ortho")

    def test_base_layer_is_present(self):
        self.assertTrue(MapBaseLayer.objects.filter(name="IGN ortho").exists())
