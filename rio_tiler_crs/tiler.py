"""rio-tiler-crs.main: create tiles."""

from typing import Any, Tuple

import numpy

import rasterio
from rasterio.warp import transform_bounds

from rio_tiler.utils import tile_read
from rio_tiler.errors import TileOutsideBounds
from rio_tiler_crs import projectile


def _tile_inside(rbs, tbs):
    """Check if a tile is inside a given bounds."""
    rbs = projectile.CoordsBbox(*rbs)
    tbs = projectile.CoordsBbox(*tbs)
    return (
        (tbs.xmin < rbs.xmax)
        and (tbs.xmax > rbs.xmin)
        and (tbs.ymax > rbs.ymin)
        and (tbs.ymin < rbs.ymax)
    )


def tile(
    address: str,
    tile_x: int,
    tile_y: int,
    tile_z: int,
    tilesize: int = 256,
    tileSchema: projectile.TileSchema = projectile.TileSchema(),
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
        tileSchema : rio_tiler_crs.projectile.TileSchema
            Tile Schema to use (default: WGS84).
        kwargs: dict, optional
            These will be passed to the 'rio_tiler.utils._tile_read' function.

    Returns
    -------
        data : numpy ndarray
        mask: numpy array

    """
    with rasterio.open(address) as src:
        bounds = transform_bounds(src.crs, tileSchema.crs, *src.bounds, densify_pts=21)
        tile = projectile.Tile(x=tile_x, y=tile_y, z=tile_z)
        tile_bounds = tileSchema.bounds(*tile)

        if not _tile_inside(bounds, tile_bounds):
            raise TileOutsideBounds(
                "Tile {}/{}/{} is outside image bounds".format(tile_z, tile_x, tile_y)
            )
        return tile_read(src, tile_bounds, tilesize, dst_crs=tileSchema.crs, **kwargs)
