import os

from django.contrib.gis.geos import Polygon
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from mapbox_baselayer.models import MapBaseLayer, PMTile


class PMTileDeleteTestCase(TestCase):
    def setUp(self):
        self.layer = MapBaseLayer.objects.create(
            name="Test Layer Delete", base_layer_type="raster"
        )
        self.pmtile = PMTile.objects.create(
            name="Test PMTile Delete",
            layer=self.layer,
            pmtiles_file=SimpleUploadedFile("test_delete.pmtiles", b"pmtiles content"),
            pmtiles_style=SimpleUploadedFile("test_delete.json", b"{}"),
            bbox=Polygon(((0, 0), (0, 1), (1, 1), (1, 0), (0, 0))),
        )
        self.pmtiles_file_path = self.pmtile.pmtiles_file.path
        self.pmtiles_style_path = self.pmtile.pmtiles_style.path

    def test_files_deleted_on_instance_deletion(self):
        # Vérifie que les fichiers existent avant la suppression
        self.assertTrue(os.path.exists(self.pmtiles_file_path))
        self.assertTrue(os.path.exists(self.pmtiles_style_path))

        # Supprime l'instance
        self.pmtile.delete()

        # Vérifie si les fichiers sont supprimés
        # Si le comportement par défaut de Django (ne pas supprimer) est en place,
        # ce test échouera ici si on s'attend à ce qu'ils soient supprimés.
        self.assertFalse(
            os.path.exists(self.pmtiles_file_path),
            f"Le fichier PMTiles {self.pmtiles_file_path} n'a pas été supprimé",
        )
        self.assertFalse(
            os.path.exists(self.pmtiles_style_path),
            f"Le fichier de style {self.pmtiles_style_path} n'a pas été supprimé",
        )
