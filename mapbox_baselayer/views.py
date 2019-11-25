from django.http import JsonResponse
from django.views.generic.detail import BaseDetailView


from mapbox_baselayer import models


class MapboxBaseLayerJsonDetailView(BaseDetailView):
    queryset = models.MapBaseLayer.objects.exclude(base_layer_type='mapbox')  # mapbox provide its own json

    def get(self, request, *args, **kwargs):
        return JsonResponse(self.get_object().tilejson)
