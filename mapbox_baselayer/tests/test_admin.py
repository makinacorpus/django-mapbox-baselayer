from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory, TestCase

from mapbox_baselayer.admin import (
    MapBaseLayerAdmin,
    MapBaseLayerForm,
)
from mapbox_baselayer.models import MapBaseLayer


class MapBaseLayerFormTestCase(TestCase):
    def test_tile_size_initial_is_256(self):
        form = MapBaseLayerForm()
        self.assertEqual(form.fields["tile_size"].initial, 256)

    def test_style_url_required_for_mapbox(self):
        layer = MapBaseLayer.objects.create(name="test", base_layer_type="mapbox")
        form = MapBaseLayerForm(
            instance=layer,
            data={"base_layer_type": "mapbox", "name": "test", "style_url": ""},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("style_url", form.errors)

    def test_clean_when_creating_no_instance(self):
        form = MapBaseLayerForm(
            data={
                "name": "new_layer",
                "base_layer_type": "raster",
                "is_overlay": False,
                "order": 0,
                "min_zoom": 0,
                "max_zoom": 22,
                "tile_size": 256,
                "enabled": True,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_init_without_tile_size_field(self):
        """
        Reproduce KeyError: 'tile_size' when the field is not in the form.
        This happens in the admin 'add' view where get_fieldsets limits fields.
        """

        # Simulate a form that only has 'name' and 'base_layer_type'
        class LimitedMapBaseLayerForm(MapBaseLayerForm):
            class Meta(MapBaseLayerForm.Meta):
                fields = ["name", "base_layer_type"]

        # This should not raise KeyError
        try:
            LimitedMapBaseLayerForm()
        except KeyError as e:
            self.fail(f"MapBaseLayerForm raised KeyError: {e}")


class MapBaseLayerAdminTestCase(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User

        self.site = AdminSite()
        self.admin = MapBaseLayerAdmin(MapBaseLayer, self.site)
        self.factory = RequestFactory()
        self.request = self.factory.get("/admin/")
        self.request.user = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="password"
        )

    def test_get_queryset(self):
        enabled = MapBaseLayer.objects.create(
            name="Enabled", base_layer_type="raster", enabled=True
        )
        disabled = MapBaseLayer.objects.create(
            name="Disabled", base_layer_type="raster", enabled=False
        )
        qs = self.admin.get_queryset(self.request)
        self.assertIn(enabled, qs)
        self.assertIn(disabled, qs)

    def test_has_add_permission_true(self):
        self.assertTrue(self.admin.has_add_permission(self.request))

    def test_get_fieldsets_add_view(self):
        fieldsets = self.admin.get_fieldsets(self.request, obj=None)
        all_fields = []
        for label, opts in fieldsets:
            all_fields.extend(opts["fields"])
        flat_fields = []
        for f in all_fields:
            if isinstance(f, (list, tuple)):
                flat_fields.extend(f)
            else:
                flat_fields.append(f)
        self.assertIn("name", flat_fields)
        self.assertIn("base_layer_type", flat_fields)
        self.assertIn("style_url", flat_fields)
        self.assertIn("tile_size", flat_fields)

    def test_get_fieldsets_change_view(self):
        layer = MapBaseLayer.objects.create(name="test", base_layer_type="raster")
        fieldsets = self.admin.get_fieldsets(self.request, obj=layer)
        all_fields = []
        for label, opts in fieldsets:
            all_fields.extend(opts["fields"])
        flat_fields = []
        for f in all_fields:
            if isinstance(f, (list, tuple)):
                flat_fields.extend(f)
            else:
                flat_fields.append(f)

        self.assertIn("style_url", flat_fields)
        self.assertIn("tile_size", flat_fields)

    def test_get_inlines_add_view_not_empty(self):
        inlines = self.admin.get_inlines(self.request, obj=None)
        self.assertEqual(len(list(inlines)), 2)

    def test_get_inlines_change_view_not_empty(self):
        layer = MapBaseLayer.objects.create(name="test", base_layer_type="raster")
        inlines = self.admin.get_inlines(self.request, obj=layer)
        self.assertEqual(len(list(inlines)), 2)

    def test_get_formsets_with_inlines_raster(self):
        from mapbox_baselayer.admin import BaseLayerTileInline

        layer = MapBaseLayer.objects.create(name="test", base_layer_type="raster")
        formsets = list(self.admin.get_formsets_with_inlines(self.request, obj=layer))
        tile_formset = next(
            fs for fs, inline in formsets if isinstance(inline, BaseLayerTileInline)
        )
        self.assertEqual(tile_formset.min_num, 1)

    def test_get_formsets_with_inlines_style(self):
        from mapbox_baselayer.admin import BaseLayerTileInline

        layer = MapBaseLayer.objects.create(name="test", base_layer_type="mapbox")
        formsets = list(self.admin.get_formsets_with_inlines(self.request, obj=layer))
        tile_formset = next(
            fs for fs, inline in formsets if isinstance(inline, BaseLayerTileInline)
        )
        self.assertEqual(tile_formset.min_num, 0)

    def test_get_formsets_with_inlines_creation_post_raster(self):
        from mapbox_baselayer.admin import BaseLayerTileInline

        self.request.method = "POST"
        self.request.POST = {"base_layer_type": "raster"}
        formsets = list(self.admin.get_formsets_with_inlines(self.request, obj=None))
        tile_formset = next(
            fs for fs, inline in formsets if isinstance(inline, BaseLayerTileInline)
        )
        self.assertEqual(tile_formset.min_num, 1)

    def test_get_formsets_with_inlines_creation_post_style(self):
        from mapbox_baselayer.admin import BaseLayerTileInline

        self.request.method = "POST"
        self.request.POST = {"base_layer_type": "mapbox"}
        formsets = list(self.admin.get_formsets_with_inlines(self.request, obj=None))
        tile_formset = next(
            fs for fs, inline in formsets if isinstance(inline, BaseLayerTileInline)
        )
        self.assertEqual(tile_formset.min_num, 0)

    def test_has_delete_permission_true(self):
        self.assertTrue(self.admin.has_delete_permission(self.request))

    def test_has_change_permission_true(self):
        self.assertTrue(self.admin.has_change_permission(self.request))


class PMTilesInlineTestCase(TestCase):
    def test_get_size_with_file(self):
        from unittest.mock import Mock

        from mapbox_baselayer.admin import PMTilesInline
        from mapbox_baselayer.models import PMTile

        inline = PMTilesInline(PMTile, AdminSite())
        pmtile = Mock()
        pmtile.pmtiles_file = Mock()
        pmtile.pmtiles_file.size = 2097152  # 2 MB
        self.assertEqual(inline.get_size(pmtile), "2.00 MB")

    def test_get_size_without_file(self):
        from unittest.mock import Mock

        from mapbox_baselayer.admin import PMTilesInline
        from mapbox_baselayer.models import PMTile

        inline = PMTilesInline(PMTile, AdminSite())
        pmtile = Mock()
        pmtile.pmtiles_file = None
        self.assertEqual(inline.get_size(pmtile), "N/A")
