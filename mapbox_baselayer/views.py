from django.http import JsonResponse
from django.views import View
from django.views.generic.detail import BaseDetailView


from mapbox_baselayer import models


class MapboxBaseLayerJsonDetailView(BaseDetailView):
    queryset = models.MapBaseLayer.objects.exclude(base_layer_type='mapbox')  # mapbox provide its own json

    def get(self, request, *args, **kwargs):
        return JsonResponse(self.get_object().tilejson)


class MapLayerListView(View):
    def get(self, request, *args, **kwargs):
        layers = models.MapBaseLayer.objects.all()
        base_layers = layers.filter(is_overlay=False)
        overlay_layers = layers.filter(is_overlay=True)

        data = {
            "base_layers": [
                {"name": bl.name, "slug": bl.slug, "url": bl.url}
                for bl in base_layers
            ],
            "overlay_layers": [
                {"name": ol.name, "slug": ol.slug, "url": ol.url}
                for ol in overlay_layers
            ],
        }
        return JsonResponse(data)
