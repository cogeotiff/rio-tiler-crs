"""rio-tiler-crs.cogeo."""

from concurrent import futures
from typing import Any, Dict, Optional, Sequence, Tuple

import attr
import morecantile
import numpy
from rasterio.transform import from_bounds
from rasterio.warp import calculate_default_transform

from rio_tiler import constants, reader
from rio_tiler.errors import TileOutsideBounds
from rio_tiler.expression import apply_expression, parse_expression
from rio_tiler.io import COGReader as RioTilerReader

default_tms = morecantile.tms.get("WebMercatorQuad")


def geotiff_options(
    x: int,
    y: int,
    z: int,
    tilesize: int = 256,
    tms: morecantile.TileMatrixSet = default_tms,
) -> Dict:
    """GeoTIFF options."""
    bounds = tms.xy_bounds(morecantile.Tile(x=x, y=y, z=z))
    dst_transform = from_bounds(*bounds, tilesize, tilesize)
    return dict(crs=tms.crs, transform=dst_transform)


@attr.s
class COGReader(RioTilerReader):
    """
    Cloud Optimized GeoTIFF Reader.

    Examples
    --------
    with CogeoReader(src_path) as cog:
        cog.tile(...)

    with rasterio.open(src_path) as src_dst:
        with WarpedVRT(src_dst, ...) as vrt_dst:
            with CogeoReader(None, dataset=vrt_dst) as cog:
                cog.tile(...)

    with rasterio.open(src_path) as src_dst:
        with CogeoReader(None, dataset=src_dst) as cog:
            cog.tile(...)

    Attributes
    ----------
    filepath: str
        Cloud Optimized GeoTIFF path.
    dataset: rasterio.DatasetReader, optional
        Rasterio dataset.
    tms: morecantile.TileMatrixSet, optional
        TileMatrixSet to use, default is WebMercatorQuad.

    Properties
    ----------
    minzoom: int
        COG minimum zoom level in TMS projection.
    maxzoom: int
        COG maximum zoom level in TMS projection.
    bounds: tuple[float]
        COG bounds in WGS84 crs.
    center: tuple[float, float, int]
        COG center + minzoom
    colormap: dict
        COG internal colormap.
    info: dict
        General information about the COG (datatype, indexes, ...)

    Methods
    -------
    tile(0, 0, 0, indexes=(1,2,3), expression="B1/B2", tilesize=512, resampling_methods="nearest")
        Read a map tile from the COG.
    part((0,10,0,10), indexes=(1,2,3,), expression="B1/B20", max_size=1024)
        Read part of the COG.
    preview(max_size=1024)
        Read preview of the COG.
    point((10, 10), indexes=1)
        Read a point value from the COG.
    stats(pmin=5, pmax=95)
        Get Raster statistics.
    meta(pmin=5, pmax=95)
        Get info + raster statistics

    """

    tms: morecantile.TileMatrixSet = attr.ib(default=default_tms)

    def _get_zooms(self):
        """Calculate raster min/max zoom level."""

        def _zoom_for_pixelsize(pixel_size, max_z=24):
            """Get zoom level corresponding to a pixel resolution."""
            for z in range(max_z):
                matrix = self.tms.matrix(z)
                if pixel_size > self.tms._resolution(matrix):
                    return max(0, z - 1)  # We don't want to scale up

            return max_z - 1

        dst_affine, w, h = calculate_default_transform(
            self.dataset.crs,
            self.tms.crs,
            self.dataset.width,
            self.dataset.height,
            *self.dataset.bounds,
        )
        resolution = max(abs(dst_affine[0]), abs(dst_affine[4]))
        max_zoom = _zoom_for_pixelsize(resolution)

        matrix = self.tms.tileMatrix[0]
        ovr_resolution = (
            resolution * max(h, w) / max(matrix.tileWidth, matrix.tileHeight)
        )
        min_zoom = _zoom_for_pixelsize(ovr_resolution)

        self.minzoom = self.minzoom or min_zoom
        self.maxzoom = self.maxzoom or max_zoom

        return

    def _tile_exists(self, tile: morecantile.Tile):
        """Check if a tile is inside a given bounds."""
        tile_bounds = self.tms.bounds(*tile)
        return (
            (tile_bounds[0] < self.bounds[2])
            and (tile_bounds[2] > self.bounds[0])
            and (tile_bounds[3] > self.bounds[1])
            and (tile_bounds[1] < self.bounds[3])
        )

    def tile(
        self,
        tile_x: int,
        tile_y: int,
        tile_z: int,
        tilesize: int = 256,
        indexes: Optional[Sequence] = None,
        expression: Optional[str] = "",
        **kwargs: Any,
    ) -> Tuple[numpy.ndarray, numpy.ndarray]:
        """Read a TMS map tile from a COG."""
        kwargs = {**self._kwargs, **kwargs}

        if isinstance(indexes, int):
            indexes = (indexes,)

        if expression:
            indexes = parse_expression(expression)

        tile = morecantile.Tile(x=tile_x, y=tile_y, z=tile_z)
        if not self._tile_exists(tile):
            raise TileOutsideBounds(
                "Tile {}/{}/{} is outside image bounds".format(tile_z, tile_x, tile_y)
            )

        tile_bounds = self.tms.xy_bounds(*tile)
        tile, mask = reader.part(
            self.dataset,
            tile_bounds,
            tilesize,
            tilesize,
            dst_crs=self.tms.crs,
            indexes=indexes,
            **kwargs,
        )
        if expression:
            blocks = expression.lower().split(",")
            bands = [f"b{bidx}" for bidx in indexes]
            tile = apply_expression(blocks, bands, tile)

        return tile, mask


def multi_tile(
    assets: Sequence[str],
    *args: Any,
    tms: morecantile.TileMatrixSet = default_tms,
    **kwargs: Any,
) -> Tuple[numpy.ndarray, numpy.ndarray]:
    """Assemble multiple tiles."""

    def _worker(asset: str):
        with COGReader(asset, tms=tms) as cog:  # type: ignore
            return cog.tile(*args, **kwargs)

    with futures.ThreadPoolExecutor(max_workers=constants.MAX_THREADS) as executor:
        data, masks = zip(*list(executor.map(_worker, assets)))
        data = numpy.concatenate(data)
        mask = numpy.all(masks, axis=0).astype(numpy.uint8) * 255
        return data, mask
