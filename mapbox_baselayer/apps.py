from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MapboxBaselayerConfig(AppConfig):
    name = 'mapbox_baselayer'
    verbose_name = _('MapBox Utils')
