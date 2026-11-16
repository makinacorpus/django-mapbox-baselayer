from copy import deepcopy
from urllib.parse import unquote

from django.http import Http404, HttpResponse, JsonResponse
from django.views import View
from django.views.generic.detail import BaseDetailView
from pmtiles.reader import MmapSource, Reader
from pmtiles.tile import (
    Compression,
    MagicNumberNotFound,
    SpecVersionUnsupported,
    TileType,
)

from mapbox_baselayer import models
from mapbox_baselayer.utils import (
    DEFAULT_OSM_TILEJSON,
    get_map_base_layers,
    get_pmtiles,
)

TILE_CONTENT_TYPES = {
    TileType.MVT: "application/vnd.mapbox-vector-tile",
    TileType.PNG: "image/png",
    TileType.JPEG: "image/jpeg",
    TileType.WEBP: "image/webp",
    TileType.AVIF: "image/avif",
}

TILE_CONTENT_ENCODINGS = {
    Compression.GZIP: "gzip",
    Compression.BROTLI: "br",
    Compression.ZSTD: "zstd",
}


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
        results = get_map_base_layers(request)
        return JsonResponse(results)


class PMTilesView(View):
    def get(self, request, *args, **kwargs):
        data = get_pmtiles(request)
        return JsonResponse(data, safe=False)


class PMTileTileView(BaseDetailView):
    queryset = models.PMTile.objects.all()

    def get(self, request, *args, **kwargs):
        pmtile = self.get_object()
        z = kwargs["z"]
        x = kwargs["x"]
        y = kwargs["y"]

        try:
            with pmtile.pmtiles_file.open("rb") as f:
                reader = Reader(MmapSource(f))
                header = reader.header()
                try:
                    tile_data = reader.get(z, x, y)
                except (ValueError, OverflowError):
                    return HttpResponse(status=204)
        except (
            FileNotFoundError,
            ValueError,
            MagicNumberNotFound,
            SpecVersionUnsupported,
        ) as exc:
            msg = "Invalid or missing PMTiles file"
            raise Http404(msg) from exc

        if tile_data is None:
            return HttpResponse(status=204)

        content_type = TILE_CONTENT_TYPES.get(
            header.get("tile_type"), "application/octet-stream"
        )
        response = HttpResponse(tile_data, content_type=content_type)
        encoding = TILE_CONTENT_ENCODINGS.get(header.get("tile_compression"))
        if encoding:
            response["Content-Encoding"] = encoding
        return response
