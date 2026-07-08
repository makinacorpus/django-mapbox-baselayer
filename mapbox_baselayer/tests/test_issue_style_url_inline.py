from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from mapbox_baselayer.admin import BaseLayerTileInline, MapBaseLayerAdmin
from mapbox_baselayer.models import MapBaseLayer


class StyleURLInlineTestCase(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.factory = RequestFactory()
        self.superuser = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="password"
        )

    def test_style_url_with_tiles_not_allowed(self):
        # Normalement, si le type est STYLE_URL (mapbox), on ne devrait pas avoir besoin de BaseLayerTile.
        # Mais BaseLayerTileInline a min_num = 1.

        admin = MapBaseLayerAdmin(MapBaseLayer, self.site)

        # Simuler un objet existant avec style_url
        obj = MapBaseLayer.objects.create(
            name="Style Layer",
            base_layer_type="mapbox",
            style_url="mapbox://styles/test/123",
        )

        # On simule un changement d'objet dans l'admin
        request = self.factory.get(
            f"/admin/mapbox_baselayer/mapbaselayer/{obj.pk}/change/"
        )
        request.user = self.superuser

        # Récupérer les inlines
        inlines = admin.get_inline_instances(request, obj)
        tile_inline = next(
            (i for i in inlines if isinstance(i, BaseLayerTileInline)), None
        )
        self.assertIsNotNone(tile_inline)

        # On vérifie que si le type est mapbox, BaseLayerTileInline n'est pas requis (min_num=0)
        formsets = list(admin.get_formsets_with_inlines(request, obj))
        tile_formset = next(
            fs for fs, inline in formsets if isinstance(inline, BaseLayerTileInline)
        )
        self.assertEqual(tile_formset.min_num, 0)

        # Testons ce qui se passe si on essaie de valider le formset avec 0 formulaires
        formset_data = {
            "tiles-TOTAL_FORMS": "0",
            "tiles-INITIAL_FORMS": "0",
            "tiles-MIN_NUM_FORMS": "0",
            "tiles-MAX_NUM_FORMS": "1000",
        }
        formset = tile_formset(data=formset_data, instance=obj, prefix="tiles")
        self.assertTrue(formset.is_valid(), formset.errors)
