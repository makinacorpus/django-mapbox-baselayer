from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class LayerType(TextChoices):
    STYLE_URL = "mapbox", _("Style URL")
    RASTER = "raster", _("Raster tiles")
    VECTOR = "vector", _("Vector tiles")
