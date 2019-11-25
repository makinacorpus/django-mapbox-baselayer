from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import gettext as _


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

    def __str__(self):
        return self.name

    @cached_property
    def tilejson(self):
        data = {
            "version": 8,
            "sources": {
                f"{self.slug}": {
                    "type": f"{self.base_layer_type}",
                    "tiles": list(self.tiles.values_list('url', flat=True)),
                    "minzoom": self.min_zoom,
                    "maxzoom": self.max_zoom
                }
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

    def check_validity(self):
        if self.base_layer_type == 'mapbox':
            if self.tiles.exists():
                # check if mapbox has not tiles
                raise ValidationError(_("Mapbox base layer should not have tiles associated."))
            if not self.map_box_url:
                raise ValidationError(_("Mapbox base layer should have mapbox url associated."))
        else:
            if self.map_box_url:
                raise ValidationError(_("Base layer should not have mapbox url associated."))

    def clean(self):
        """ auto used in model forms or admin // prevent exception """
        self.check_validity()

    def save(self, *args, **kwargs):
        self.check_validity()  # recheck validity for non ModelForm and admin
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Map base layers")
        verbose_name_plural = _("Map base layers")
        ordering = (
            'order', 'name'
        )


class BaseLayerTile(models.Model):
    base_layer = models.ForeignKey(MapBaseLayer, related_name='tiles', on_delete=models.PROTECT)
    url = models.CharField(max_length=255)
