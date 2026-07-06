from copy import deepcopy
from urllib.parse import unquote

from django.http import JsonResponse
from django.views import View
from django.views.generic.detail import BaseDetailView

from mapbox_baselayer import models
from mapbox_baselayer.utils import DEFAULT_OSM_TILEJSON, get_map_base_layers


class MapboxBaseLayerJsonDetailView(BaseDetailView):
    queryset = models.MapBaseLayer.objects.all()

    def get(self, request, *args, **kwargs):
        tilejson = deepcopy(self.get_object().tilejson)
        glyphs_url = tilejson.get("glyphs")
        if glyphs_url and not glyphs_url.startswith(("http", "mapbox")):
            glyphs_url = request.build_absolute_uri(tilejson["glyphs"])
            tilejson["glyphs"] = unquote(glyphs_url)
        return JsonResponse(tilejson)


class DefaultOSMTileJsonView(View):
    def get(self, request, *args, **kwargs):
        tilejson = deepcopy(DEFAULT_OSM_TILEJSON)
        glyphs_url = request.build_absolute_uri(tilejson["glyphs"])
        tilejson["glyphs"] = unquote(glyphs_url)
        return JsonResponse(tilejson)


class MapLayerListView(View):
    def get(self, request, *args, **kwargs):
        results = get_map_base_layers()
        return JsonResponse(results)
