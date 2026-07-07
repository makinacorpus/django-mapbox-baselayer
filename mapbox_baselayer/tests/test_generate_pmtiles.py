import os
import shutil
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase, override_settings

from mapbox_baselayer.models import MapBaseLayer, PMTile

TEMP_MEDIA_ROOT = TemporaryDirectory()

@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT.name)
class GeneratePMTilesCommandTestCase(TestCase):
    def setUp(self):
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
