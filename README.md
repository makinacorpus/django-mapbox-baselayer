[![codecov](https://codecov.io/gh/makinacorpus/django-mapbox-baselayer/branch/master/graph/badge.svg)](https://codecov.io/gh/makinacorpus/django-mapbox-baselayer)
[![Build Status](https://travis-ci.org/makinacorpus/django-mapbox-baselayer.svg?branch=master)](https://travis-ci.org/makinacorpus/django-mapbox-baselayer)


Django model and view to store, generate and serve configuration for MapBox GL JS map base layer


# Getting started
### Installation
Install it in your project like any dependency
```bash
pip install django-mapbox-baselayer
```

### Usage
Declare django-mapbox-baselayer in the `INSTALLED_APPS`
```python
# settings.py

INSTALLED_APPS  = [
    # ... other django apps
    "mapbox_baselayer",
]
```

/!\ Note: for now, the apps is not registered in the admin. But you can register it in your project if you want to use it


```python
# admin.py

from django.contrib import admin
from mapbox_baselayer.admin import MapBaseLayerAdmin
from mapbox_baselayer.models import MapBaseLayer

admin.site.register(MapBaseLayer, MapBaseLayerAdmin)
```

For mapbox layers, you do not need to describe the tiles with the `BaseLayerTile` object, but an url is mandatory.

For raster layers, is it necessary to create a `BaseLayerTile` for each url (`a.tiles.xxx`, `b.tiles.xxx`, etc ...)

Tile size should be 256 for raster and 512 for vector.

### Commands

#### OSM base layer

```bash
./manage.py install_osm_baselayer
```

#### OpenTopoMap base layer

```bash
./manage.py install_opentopomap_baselayer
```
