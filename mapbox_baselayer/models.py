from django.db import models
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class MapBaseLayer(models.Model):
    BASE_LAYER_TYPES = (
        ('mapbox', 'MapBox'),
        ('raster', 'Raster'),
        ('vector', 'Vector'),
    )
    name = models.CharField(max_length=50, unique=True)
    order = models.PositiveSmallIntegerField(default=0)
    slug = models.SlugField(unique=True, editable=False)
    base_layer_type = models.CharField(max_length=25, choices=BASE_LAYER_TYPES, db_index=True, blank=False)
    map_box_url = models.CharField(max_length=255, blank=True)  # required for mapbox
    sprite = models.CharField(max_length=255, blank=True)
    glyphs = models.CharField(max_length=255, blank=True)
    min_zoom = models.PositiveSmallIntegerField(default=0)
    max_zoom = models.PositiveSmallIntegerField(default=22)
    tile_size = models.PositiveSmallIntegerField(
        default=512, help_text=_("Raster tile size. Set 256 for 3rd party raster tilesets.")
    )
    attribution = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return self.name

    def get_source(self):
        source = {
            "type": f"{self.base_layer_type}",
            "tiles": list(self.tiles.values_list('url', flat=True)),
            "minzoom": self.min_zoom,
            "maxzoom": self.max_zoom,
            "attribution": self.attribution,
        }

        if self.base_layer_type == 'raster':
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
                {"id": f"{self.slug}-background",
                 "type": f"{self.base_layer_type}",
                 "source": f"{self.slug}"}
            ]
        }
        # prevents mapbox problems by set glyphs and sprite only if specified
        if self.sprite:
            data["sprite"] = self.sprite

        if self.glyphs:
            data["glyphs"] = self.glyphs

        return data

    @cached_property
    def url(self):
        if self.base_layer_type != 'mapbox':
            return reverse('mapbox_baselayer:tilejson', args=(self.pk, ))
        else:
            return self.map_box_url

    @cached_property
    def real_url(self):
        if self.base_layer_type != 'mapbox':
            return self.url
        else:
            return self.map_box_url.replace("mapbox://styles",
                                            "https://api.mapbox.com/styles/v1")

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Map base layers")
        verbose_name_plural = _("Map base layers")
        ordering = (
            'order', 'name'
        )


class BaseLayerTile(models.Model):
    base_layer = models.ForeignKey(MapBaseLayer, related_name='tiles', on_delete=models.CASCADE)
    url = models.CharField(max_length=512)
