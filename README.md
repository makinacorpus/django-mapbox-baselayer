[![codecov](https://codecov.io/gh/makinacorpus/django-mapbox-baselayer/branch/master/graph/badge.svg)](https://codecov.io/gh/makinacorpus/django-mapbox-baselayer)
[![CI](https://github.com/makinacorpus/django-mapbox-baselayer/actions/workflows/python-ci.yml/badge.svg)](https://github.com/makinacorpus/django-mapbox-baselayer/actions/workflows/python-ci.yml)

# Django Mapbox Baselayer

Django application to store, manage and serve map base layers and overlay configurations for **MapLibre GL JS** and **Mapbox GL JS**.

This package provides:
- Django models to store base layers and overlay layers configuration
- Admin interface to manage layers
- API endpoints to serve layer configurations as TileJSON
- Support for raster tiles, vector tiles, and Mapbox styles

![Map Example](docs/map_example.png)

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

For Mapbox base layers, you do not need to describe the tiles with the `BaseLayerTile` object, but an url is mandatory.

For Raster base layers, is it necessary to create a `BaseLayerTile` for each url (`a.tiles.xxx`, `b.tiles.xxx`, etc ...)

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

#### Mapbox base layer

```bash
./manage.py install_mapbox_baselayer (use mapbox://styles/mapbox/streets-v11 as default)
./manage.py install_mapbox_baselayer --mapbox-url=mapbox://styles/mapbox/satellite-streets-v11
```

#### IGN base layer

```bash
./manage.py install_ign_baselayer --layers ortho plan maps scan_25 cadastre plan_vt
```
