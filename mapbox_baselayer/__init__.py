import os

default_app_config = "mapbox_baselayer.apps.MapboxBaselayerConfig"
with open(os.path.join(os.path.dirname(__file__), "VERSION.md")) as f:
    __version__ = f.read().strip()
