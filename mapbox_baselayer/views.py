from django.http import JsonResponse
from django.views import View
from django.views.generic.detail import BaseDetailView

from mapbox_baselayer import models
from mapbox_baselayer.utils import DEFAULT_OSM_TILEJSON, get_map_base_layers


class MapboxBaseLayerJsonDetailView(BaseDetailView):
    queryset = models.MapBaseLayer.objects.exclude(
        base_layer_type="mapbox"
    )  # mapbox provide its own json

    def get(self, request, *args, **kwargs):
        return JsonResponse(self.get_object().tilejson)


class DefaultOSMTileJsonView(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse(DEFAULT_OSM_TILEJSON)


class MapLayerListView(View):
    def get(self, request, *args, **kwargs):
        results = get_map_base_layers()
        return JsonResponse(results)
