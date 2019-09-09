"""rio-tiler-crs.main: create tiles."""

from typing import Dict, Tuple

import numpy

import rasterio
from rasterio.crs import CRS
from rasterio.warp import transform_bounds

from rio_tiler.utils import tile_read
from rio_tiler.errors import TileOutsideBounds
from rio_tiler_crs import projectile


def tile(
    address: str,
    tile_x: int,
    tile_y: int,
    tile_z: int,
    tilesize: int = 256,
    epsg: int = 4326,
    transform: Tuple = (0.5, 1),
    **kwargs: Dict
) -> Tuple[numpy.ndarray, numpy.ndarray]:
    """
    Create mercator tile from any images.

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
    epsg : int,
        TODO
    transfor : tuple,
        TODO
    kwargs: dict, optional
        These will be passed to the 'rio_tiler.utils._tile_read' function.

    Returns
    -------
    data : numpy ndarray
    mask: numpy array

    """
    ts = projectile.TileSchema(epsg, transform=transform)
    dst_crs = CRS.from_epsg(epsg)

    def _tile_exists(bounds, z, x, y):
        """Check if a tile is inside a given bounds."""
        mintile = ts.tile(bounds[0], bounds[3], z)
        maxtile = ts.tile(bounds[2], bounds[1], z)
        return (
            (x <= maxtile.x + 1)
            and (x >= mintile.x)
            and (y <= maxtile.y + 1)
            and (y >= mintile.y)
        )

    with rasterio.open(address) as src:
        bounds = transform_bounds(
            *[src.crs, dst_crs] + list(src.bounds), densify_pts=21
        )

        tile = projectile.Tile(x=tile_x, y=tile_y, z=tile_z)
        tile_bounds = ts.xy_bounds(*tile)

        if not _tile_exists(bounds, tile_z, tile_x, tile_y):
            raise TileOutsideBounds(
                "Tile {}/{}/{} is outside image bounds".format(tile_z, tile_x, tile_y)
            )

        return tile_read(src, tile_bounds, tilesize, dst_crs=dst_crs, **kwargs)
