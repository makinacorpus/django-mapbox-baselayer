from django.views.generic import TemplateView
from mapbox_baselayer import models


class MapExampleView(TemplateView):
    template_name = 'test_app/map_example.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['base_layers'] = models.MapBaseLayer.objects.all()
        return context
