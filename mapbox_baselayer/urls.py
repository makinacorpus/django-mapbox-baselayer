from django.urls import path

from mapbox_baselayer import views

app_name = 'mapbox_baselayer'

urlpatterns = [
    path('mapbox-baselayers/<int:pk>/tilejson/', views.MapboxBaseLayerJsonDetailView.as_view(), name='tilejson')
]
