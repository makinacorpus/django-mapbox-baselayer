import json
import logging
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

import mercantile
import requests
from django.contrib.gis.geos import Polygon
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.core.management import CommandError
from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from pmtiles.tile import Compression, TileType, zxy_to_tileid
from pmtiles.writer import Writer
from tqdm import tqdm

from mapbox_baselayer.choices import LayerType
from mapbox_baselayer.models import MapBaseLayer, PMTile
from mapbox_baselayer.settings import default_config

RETRY_COUNT = 3
TMP_FOLDER = default_config.get("TMP_FOLDER")


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Create pmtiles of the selected baselayer with parallel downloads"

    def format_request_error(self, exception):
        response = getattr(exception, "response", None)
        if response is None:
            return str(exception)

        message = response.reason or str(exception)
        return f"HTTP {response.status_code}: {message}"

    def add_arguments(self, parser):
        parser.add_argument("id", type=int, help="Baselayer id in MapBaselayer model")
        parser.add_argument(
            "--minzoom", nargs="?", default=None, type=int, help="Minimum zoom level"
        )
        parser.add_argument(
            "--maxzoom", nargs="?", default=None, type=int, help="Maximum zoom level"
        )
        parser.add_argument(
            "--name",
            nargs="?",
            default=None,
            type=str,
            help="Name of the PMTile instance",
        )
        parser.add_argument(
            "--bbox",
            action="store",
            help="Override DEFAULT_BBOX. Format: LNG_MIN,LAT_MIN,LNG_MAX,LAT_MAX (WGS84).",
            type=str,
            default=None,
        )

    def get_extent(self, input_bbox):
        try:
            if input_bbox is not None:
                parts = [p.strip() for p in input_bbox.split(",")]
            else:
                parts = list(default_config["DEFAULT_BBOX"])

            if len(parts) != 4:
                msg = "bbox must be a comma-separated list of 4 numbers"
                raise ValueError(msg)

            west, south, east, north = [float(x) for x in parts]
            if west >= east or south >= north:
                msg = "bbox coordinates must satisfy west < east and south < north"
                raise ValueError(msg)

            bbox = Polygon.from_bbox((west, south, east, north))
            bbox.srid = 4326
            return bbox
        except (TypeError, ValueError, KeyError) as exc:
            msg = _("Invalid bbox: %(exc)s") % {"exc": exc}
            raise CommandError(msg)

    def get_baselayer(self, pk):
        try:
            return MapBaseLayer.objects.get(pk=pk)
        except MapBaseLayer.DoesNotExist:
            msg = _("MapBaseLayer %(pk)s does not exist") % {"pk": pk}
            raise MapBaseLayer.DoesNotExist(msg)

    def get_zooms(self, min_zoom, max_zoom, baselayer):
        if min_zoom is None or min_zoom < baselayer.min_zoom:
            min_zoom = baselayer.min_zoom
            msg = _("Baselayer min zoom has been selected: %(min_zoom)s") % {
                "min_zoom": baselayer.min_zoom
            }
            self.stdout.write(self.style.WARNING(msg))
            logger.warning(msg)
        if max_zoom is None or max_zoom > baselayer.max_zoom:
            max_zoom = baselayer.max_zoom
            msg = _("Baselayer max zoom has been selected: %(max_zoom)s ") % {
                "max_zoom": baselayer.max_zoom
            }
            self.stdout.write(self.style.WARNING(msg))
            logger.warning(msg)

        return list(range(min_zoom, max_zoom + 1))

    def get_json(self, baselayer):
        if baselayer.base_layer_type == LayerType.RASTER:
            return baselayer.tilejson
        elif baselayer.base_layer_type == LayerType.STYLE_URL:
            url = baselayer.real_url
            response = self.get_or_retry(url)
            return response.json()

    def get_tile_url(self, data):
        source = next(iter(data["sources"].values()))
        return source["tiles"][0]

    def get_request_headers(self):
        return {
            "User-Agent": default_config.get("USER_AGENT"),
            "Referer": default_config.get("REFERRER"),
            "Cache-Control": "max-age=0",
        }

    def get_or_retry(self, url):
        last_exc = None
        for attempt in range(RETRY_COUNT):
            try:
                response = requests.get(
                    url,
                    timeout=30,
                    headers=self.get_request_headers(),
                )
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                last_exc = e
                error_details = self.format_request_error(e)
                logger.warning(
                    "Failed attempt %d/%d for %s: %s",
                    attempt + 1,
                    RETRY_COUNT,
                    url,
                    error_details,
                )
                if attempt < RETRY_COUNT - 1:
                    time.sleep(2 ** (attempt + 1))
        msg = (
            f"Failed after {RETRY_COUNT} attempts for {url}: "
            f"{self.format_request_error(last_exc)}"
        )
        raise requests.exceptions.RetryError(msg) from last_exc

    def get_tile_type(self, baselayer):
        if baselayer.base_layer_type == LayerType.RASTER:
            return TileType.PNG
        elif baselayer.base_layer_type == LayerType.STYLE_URL:
            return TileType.MVT
        return None

    def download_tile_worker(self, tile_id, url):
        """Worker executed in parallel to download the raw content of a tile."""
        try:
            response = requests.get(
                url,
                timeout=30,
                headers=self.get_request_headers(),
            )
            response.raise_for_status()
            return tile_id, response.content
        except requests.exceptions.RequestException as e:
            response = getattr(e, "response", None)
            error = f"HTTP {response.status_code}" if response is not None else str(e)
            logger.warning("%s (%s)", url, error)
            return tile_id, None

    def handle(self, *args, **options):
        baselayer_id = options["id"]
        input_minzoom = options["minzoom"]
        input_maxzoom = options["maxzoom"]

        start_time = time.perf_counter()

        # 1. Initialize and configure zoom levels
        baselayer = self.get_baselayer(baselayer_id)
        zooms = self.get_zooms(input_minzoom, input_maxzoom, baselayer)

        # 2. Spatial extent projection
        bbox = self.get_extent(options["bbox"])
        west, south, east, north = bbox.extent

        json_data = self.get_json(baselayer)
        tile_url = self.get_tile_url(json_data)
        filename_tiles = f"{baselayer.slug}.pmtiles"

        # 3. Collect and count all tiles
        self.stdout.write("Calcul du nombre total de tuiles...")
        total_tiles = 0
        for zoom in zooms:
            # mercantile.tile_count is much faster as it only does math
            z_tiles_count = (
                mercantile.tile(east, south, zoom).x
                - mercantile.tile(west, north, zoom).x
                + 1
            ) * (
                mercantile.tile(west, south, zoom).y
                - mercantile.tile(east, north, zoom).y
                + 1
            )
            total_tiles += z_tiles_count

        self.stdout.write(f"Nombre total de tuiles à télécharger : {total_tiles}")

        if total_tiles == 0:
            self.stdout.write("Aucune tuile à générer.")
            return

        # 4. Parallel download & ordered writing
        self.stdout.write("Début de la génération parallélisée...")

        # Temporary cache to store tiles received out of order
        downloaded_cache = {}

        def tile_generator():
            for zoom in zooms:
                # Use a generator to avoid loading everything into memory.
                # PMTiles requires tiles to be sorted by tile_id.
                # mercantile.tiles yields tiles by zoom, then y, then x.
                # zxy_to_tileid generally follows this order within a zoom level,
                # and in practice tile_id increases with zoom.
                for t in mercantile.tiles(west, south, east, north, [zoom]):
                    t_id = zxy_to_tileid(t.z, t.x, t.y)
                    t_url = tile_url.format(z=t.z, x=t.x, y=t.y)
                    yield t_id, t_url

        temp_pmtiles = NamedTemporaryFile(dir=TMP_FOLDER, suffix=".pmtiles")
        temp_style = NamedTemporaryFile(dir=TMP_FOLDER, suffix=".json", mode="w")

        with open(temp_pmtiles.name, "wb") as pmtiles_file:
            writer = Writer(pmtiles_file)

            with ThreadPoolExecutor(
                max_workers=default_config.get("MAX_WORKERS")
            ) as executor:
                with tqdm(
                    total=total_tiles, desc="Progression", unit="tuile", ncols=100
                ) as pbar:
                    # Index of the next expected tile to preserve strict PMTiles ordering
                    next_tile_index = 0
                    # Submit tasks in batches to limit memory usage
                    chunk_size = 100
                    tile_iterator = tile_generator()

                    # Keep track of submitted tile IDs to preserve writing order
                    ordered_ids = []

                    def enqueue_tiles(it, count):
                        new_futures = {}
                        for _ in range(count):
                            try:
                                t_id, t_url = next(it)
                                ordered_ids.append(t_id)
                                new_futures[
                                    executor.submit(
                                        self.download_tile_worker, t_id, t_url
                                    )
                                ] = t_id
                            except StopIteration:
                                break
                        return new_futures

                    future_to_tile = enqueue_tiles(tile_iterator, chunk_size)

                    while future_to_tile:
                        done, _ = wait(
                            future_to_tile.keys(), return_when=FIRST_COMPLETED
                        )

                        for future in done:
                            t_id, tile_content = future.result()
                            future_to_tile.pop(future)

                            # Store temporarily in RAM (None if tile is unavailable)
                            downloaded_cache[t_id] = tile_content

                        # Immediately write all ready tiles in ascending order
                        while next_tile_index < total_tiles:
                            # next_tile_index is the global index within total_tiles;
                            # ordered_ids holds tile IDs in the order yielded by tile_generator()
                            if next_tile_index < len(ordered_ids):
                                expected_id = ordered_ids[next_tile_index]

                                if expected_id in downloaded_cache:
                                    content = downloaded_cache.pop(expected_id)
                                    if content is not None:
                                        writer.write_tile(expected_id, content)
                                    next_tile_index += 1
                                    pbar.update(1)
                                else:
                                    break
                            else:
                                # Next ID has not been generated in ordered_ids yet
                                break

                        # Refill the download queue
                        new_tiles_count = chunk_size - len(future_to_tile)
                        if new_tiles_count > 0:
                            future_to_tile.update(
                                enqueue_tiles(tile_iterator, new_tiles_count)
                            )

                    # Release memory used by ordered_ids
                    ordered_ids.clear()

            # 5. Finalize the PMTiles archive
            self.stdout.write("Finalisation et indexation du conteneur PMTiles...")
            writer.finalize(
                {
                    "tile_type": self.get_tile_type(baselayer),
                    "tile_compression": Compression.NONE,
                    "min_zoom": zooms[0],
                    "max_zoom": zooms[-1],
                    "min_lon_e7": int(west * 10000000),
                    "min_lat_e7": int(south * 10000000),
                    "max_lon_e7": int(east * 10000000),
                    "max_lat_e7": int(north * 10000000),
                },
                {
                    "attribution": baselayer.attribution,
                    "type": "baselayer",
                },
            )

        # 6. Generate style JSON file (without the sources key)
        json_data.pop("sources", None)
        filename_style = f"{baselayer.slug}.json"
        with open(temp_style.name, "w") as style_file:
            json.dump(json_data, style_file)

        # 7. Create the PMTile model instance
        pmtile_name = options["name"] or f"{baselayer.name}"
        self.stdout.write(f"Enregistrement de l'instance PMTile '{pmtile_name}'...")

        pmtile_instance = PMTile.objects.create(
            layer=baselayer,
            name=pmtile_name,
            min_zoom=zooms[0],
            max_zoom=zooms[-1],
            bbox=bbox,
        )

        with open(temp_pmtiles.name, "rb") as f:
            pmtile_instance.pmtiles_file.save(filename_tiles, File(f), save=False)

        with open(temp_style.name, "rb") as f:
            pmtile_instance.pmtiles_style.save(filename_style, File(f), save=False)

        pmtile_instance.save()

        end_time = time.perf_counter()
        self.stdout.write(
            self.style.SUCCESS(
                f"PMTiles et Style générés et enregistrés avec succès en {end_time - start_time:.2f} secondes."
            )
        )
