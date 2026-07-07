from django.db import models

from mapbox_baselayer.choices import LayerType


class BaseLayerManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_overlay=False)


class OverlayLayerManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_overlay=True)


class BaseLayerRasterManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(is_overlay=False, base_layer_type=LayerType.RASTER)
        )


class BaseLayerStyleManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(is_overlay=False, base_layer_type=LayerType.STYLE_URL)
        )


class OverlayRasterManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(is_overlay=True, base_layer_type=LayerType.RASTER)
        )


class OverlayStyleManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(is_overlay=True, base_layer_type=LayerType.STYLE_URL)
        )
