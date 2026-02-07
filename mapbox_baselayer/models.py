from django.db import models
from django.db.models import TextChoices
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class MapBaseLayer(models.Model):
    class LayerType(TextChoices):
        STYLE_URL = "mapbox", _("Style URL")
        RASTER = "raster", _("Raster tiles")
        VECTOR = "vector", _("Vector tiles")

    name = models.CharField(max_length=50, unique=True)
    is_overlay = models.BooleanField(default=False, verbose_name=_("Is overlay"))
    order = models.PositiveIntegerField(default=0)
    slug = models.SlugField(unique=True, editable=False)
    base_layer_type = models.CharField(
        max_length=25, choices=LayerType.choices, db_index=True, blank=False
    )
    map_box_url = models.CharField(
        max_length=255, blank=True, help_text=_("Mapbox or tilejson URL")
    )
    sprite = models.CharField(max_length=255, blank=True)
    glyphs = models.CharField(max_length=255, blank=True)
    min_zoom = models.PositiveSmallIntegerField(default=0)
    max_zoom = models.PositiveSmallIntegerField(default=22)
    tile_size = models.PositiveSmallIntegerField(
        default=512,
        help_text=_("Raster tile size. Set 256 for 3rd party raster tilesets."),
    )
    attribution = models.CharField(max_length=1024, blank=True, default="")

    class Meta:
        verbose_name = _("Map base layers")
        verbose_name_plural = _("Map base layers")
        ordering = ("is_overlay", "order", "name")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        import uuid

        base_slug = slugify(self.name)
        if not self.pk:
            # temporary unique slug to satisfy unique constraint on first insert
            self.slug = f"{base_slug[:41]}-{uuid.uuid4().hex[:8]}"
            super().save(*args, **kwargs)
        # always include pk for uniqueness
        self.slug = f"{base_slug}-{self.pk}"
        super().save(update_fields=["slug"])

    def get_source(self):
        source = {
            "type": f"{self.base_layer_type}",
            "tiles": list(self.tiles.values_list("url", flat=True)),
            "minzoom": self.min_zoom,
            "maxzoom": self.max_zoom,
            "attribution": self.attribution,
        }

        if self.base_layer_type == self.LayerType.RASTER:
            # only available for raster layers
            source["tileSize"] = self.tile_size

        return source

    @cached_property
    def tilejson(self):
        data = {
            "version": 8,
            "sources": {
                f"{self.slug}": self.get_source(),
            },
            "layers": [
                {
                    "id": f"{self.slug}-background",
                    "type": f"{self.base_layer_type}",
                    "source": f"{self.slug}",
                }
            ],
        }
        # prevents mapbox problems by set glyphs and sprite only if specified
        if self.sprite:
            data["sprite"] = self.sprite

        data["glyphs"] = self.glyphs or "mapbox://fonts/mapbox/{fontstack}/{range}.pbf"

        return data

    @cached_property
    def url(self):
        if self.base_layer_type != self.LayerType.STYLE_URL:
            return reverse("mapbox_baselayer:tilejson", args=(self.pk,))
        else:
            return self.map_box_url

    @cached_property
    def real_url(self):
        if self.base_layer_type not in (
            self.LayerType.STYLE_URL,
            self.LayerType.VECTOR,
        ):
            return self.url
        else:
            return self.map_box_url.replace(
                "mapbox://styles", "https://api.mapbox.com/styles/v1"
            )


class BaseLayerManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_overlay=False)


class OverlayLayerManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_overlay=True)


class BaseLayer(MapBaseLayer):
    """Proxy model for base layers (is_overlay=False)"""

    objects = BaseLayerManager()

    class Meta:
        proxy = True
        verbose_name = _("Base layer")
        verbose_name_plural = _("Base layers")

    def save(self, *args, **kwargs):
        self.is_overlay = False
        super().save(*args, **kwargs)


class OverlayLayer(MapBaseLayer):
    """Proxy model for overlay layers (is_overlay=True)"""

    objects = OverlayLayerManager()

    class Meta:
        proxy = True
        verbose_name = _("Overlay layer")
        verbose_name_plural = _("Overlay layers")

    def save(self, *args, **kwargs):
        self.is_overlay = True
        super().save(*args, **kwargs)


class BaseLayerTile(models.Model):
    base_layer = models.ForeignKey(
        MapBaseLayer, related_name="tiles", on_delete=models.CASCADE
    )
    url = models.CharField(max_length=512)

    def __str__(self):
        return f"{self.base_layer.name} - {self.url}"
