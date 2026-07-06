from django.conf import settings

default_config = {
    "GLYPHS_URL": "/static/map-utils/fonts/{fontstack}/{range}.pbf",
    "TMP_FOLDER": "/tmp",
    "DEFAULT_BBOX": (
        1.219023768792979,
        43.438103355726305,
        1.679428775337492,
        43.77155291644277,
    ),
    "DEFAULT_MIN_ZOOM": 0,
    "DEFAULT_MAX_ZOOM": 17,
    "MAX_WORKERS": 10,
}

if hasattr(settings, "MAP_UTILS_CONFIG"):
    default_config.update(settings.MAP_UTILS_CONFIG)
