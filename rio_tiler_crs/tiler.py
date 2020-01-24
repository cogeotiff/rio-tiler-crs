"""rio-tiler-crs.main: create tiles."""

from typing import Any, Tuple

import numpy

import rasterio
from rasterio.warp import transform_bounds, calculate_default_transform

from rio_tiler.utils import tile_read
from rio_tiler.errors import TileOutsideBounds
import morecantile


def _tile_exists(raster_bounds, tile_bounds):
    """Check if a tile is inside a given bounds."""
    return (
        (tile_bounds[0] < raster_bounds[2])
        and (tile_bounds[2] > raster_bounds[0])
        and (tile_bounds[3] > raster_bounds[1])
        and (tile_bounds[1] < raster_bounds[3])
    )


def get_zooms(
    src_dst, tileSchema: morecantile.TileSchema = morecantile.TileSchema()
) -> Tuple[int, int]:
    """
    Calculate raster min/max zoom level.

    Parameters
    ----------
        src_dst: rasterio.io.DatasetReader
            Rasterio io.DatasetReader object
        tileSchema : morecantile.TileSchema
            Tile Schema to use (default: WebMercator).

    Returns
    -------
    min_zoom, max_zoom: Tuple
        Min/Max zoom levels.

    """

    def _zoom_for_pixelsize(pixel_size, max_z=24):
        """Get zoom level corresponding to a pixel resolution."""
        for z in range(max_z):
            if pixel_size > tileSchema._resolution(z):
                return max(0, z - 1)  # We don't want to scale up
        return max_z - 1

    dst_affine, w, h = calculate_default_transform(
        src_dst.crs, tileSchema.crs, src_dst.width, src_dst.height, *src_dst.bounds
    )
    resolution = max(abs(dst_affine[0]), abs(dst_affine[4]))
    max_zoom = _zoom_for_pixelsize(resolution)
    ovr_resolution = resolution * max(h, w) / max(tileSchema.tile_size)
    min_zoom = _zoom_for_pixelsize(ovr_resolution)
    return (min_zoom, max_zoom)


def tile(
    address: str,
    tile_x: int,
    tile_y: int,
    tile_z: int,
    tilesize: int = 256,
    tileSchema: morecantile.TileSchema = morecantile.TileSchema(),
    **kwargs: Any
) -> Tuple[numpy.ndarray, numpy.ndarray]:
    """
    Create tile from any images.

    Attributes
    ----------
        address : str
            file url.
        tile_x : int
            Mercator tile X index.
        tile_y : int
            Mercator tile Y index.
        tile_z : int
            Mercator tile ZOOM level.
        tilesize : int, optional (default: 256)
            Output image size.
        tileSchema : morecantile.TileSchema
            Tile Schema to use (default: WebMercator).
        kwargs: dict, optional
            These will be passed to the 'rio_tiler.utils._tile_read' function.

    Returns
    -------
        data : numpy ndarray
        mask: numpy array

    """
    with rasterio.open(address) as src:
        raster_bounds = transform_bounds(
            src.crs, tileSchema.crs, *src.bounds, densify_pts=21
        )
        tile = morecantile.Tile(x=tile_x, y=tile_y, z=tile_z)
        tile_bounds = tileSchema.xy_bounds(*tile)
        if not _tile_exists(raster_bounds, tile_bounds):
            raise TileOutsideBounds(
                "Tile {}/{}/{} is outside image bounds".format(tile_z, tile_x, tile_y)
            )
        return tile_read(src, tile_bounds, tilesize, dst_crs=tileSchema.crs, **kwargs)
