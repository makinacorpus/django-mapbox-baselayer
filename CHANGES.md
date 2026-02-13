CHANGELOG
=========

1.2.1         (2026-02-13)
--------------------------

**Improvements**

* Provide function to get layer list without url fetch.


1.2.0         (2026-02-10)
--------------------------

**Improvements**

* Provide default OSM base layer if no layer in database.
* Change default glyph by demo glyph to avoid map style problems on raster based layer.
* Commands are replaced by `ìnstall_layer` command with different options to install different layers.
* Use proxy models in admin for Base layers / Overlays / Style URL / Raster.
* Customize forms for Raster or Style URL layers
* Ability to enable / disable layers in admin without deleting them.


1.1.1         (2026-02-07)
--------------------------

**Improvements**

* mapbox url is now labeled as "Style URL".
* IGN Plan Vector tile layer is available

**Bugfixes**
* IGN layers are updated to use the new style url instead of the old tile url.

**Development**

* Use ruff instead of flake / black / isort


1.1.0         (2026-02-06)
--------------------------

**New features**

* Add overlays concept to allow adding layers on top of baselayers. This is useful for example to add a layer with markers on top of a baselayer.
* Add JSON endpoint to get baselayer data. This is useful for example to get the real url of a mapbox style.

**Improvements**

* Add example view


**Maintenance**

* Drop official support for python <= 3.9
* Add official support for python 3.13
* Add official support for python 5.2 and 6.0


1.0.0         (2023-07-11)
--------------------------

* Increase attribution size to 1024 chars.
* Support django 4.2, drop django 2.2
* Support python 3.11


0.0.9         (2022-11-09)
--------------------------

* Improve install_ign_baselayer command. Add Plan IGN V2 and fix multi layer import.
* Support django 3.2, 4.0 and 4.1
* Support python 3.10


0.0.8         (2020-11-03)
--------------------------

* Add command to create Mapbox layer
* Add command to create different IGN layers

0.0.7         (2020-10-30)
--------------------------

* Admin is now registered by default. Delete enabling code in your project.
* Set default mapbox glyphs to avoid map style problems on raster based layer
* Add commands to create OSM and OpenTopoMap base layers

0.0.6         (2020-09-09)
--------------------------

* Support django 3.1

0.0.5         (2020-06-03)
--------------------------

* Fix translations


0.0.4         (2019-12-04)
--------------------------

* Allow using map_box_url to store vector external json


0.0.3         (2019-12-03)
--------------------------

* add tile Size option for raster layers
* add attribution option for all layers
* Add real_url property to model MapBaseLayer, to get real url for mapbox styles
* fix MapBaseLayer deletion
* Enable fr translation


0.0.2         (2019-11-29)
--------------------------

* Increase tile url max size


0.0.1         (2019-11-25)
--------------------------

* First release
