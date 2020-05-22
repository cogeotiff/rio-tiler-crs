"""rio-tiler-crs.main: create tiles."""

from typing import Any, Dict, Tuple, Union

import morecantile
import numpy
import rasterio
from rasterio.crs import CRS
from rasterio.io import DatasetReader, DatasetWriter
from rasterio.transform import from_bounds
from rasterio.vrt import WarpedVRT
from rasterio.warp import calculate_default_transform, transform_bounds
from rio_tiler import constants, reader
from rio_tiler.errors import TileOutsideBounds
from rio_tiler.io import cogeo
from rio_tiler.utils import has_alpha_band, has_mask_band

default_tms = morecantile.tms.get("WebMercatorQuad")

# Default from rio_tiler
metadata = cogeo.metadata
point = cogeo.point
area = cogeo.area


def _tile_exists(raster_bounds, tile_bounds):
    """Check if a tile is inside a given bounds."""
    return (
        (tile_bounds[0] < raster_bounds[2])
        and (tile_bounds[2] > raster_bounds[0])
        and (tile_bounds[3] > raster_bounds[1])
        and (tile_bounds[1] < raster_bounds[3])
    )


def geotiff_options(
    x: int,
    y: int,
    z: int,
    tilesize: int = 256,
    tms: morecantile.TileMatrixSet = default_tms,
) -> Dict:
    """
    GeoTIFF options.

    Attributes
    ----------
    x : int
        Mercator tile X index.
    y : int
        Mercator tile Y index.
    z : int
        Mercator tile ZOOM level.
    tilesize : int, optional
        Output tile size. Default is 256.
    tms : morecantile.TileMatrixSet
        morecantile TileMatrixSet to use (default: WebMercator).

    Returns
    -------
    dict

    """
    bounds = tms.xy_bounds(morecantile.Tile(x=x, y=y, z=z))
    dst_transform = from_bounds(*bounds, tilesize, tilesize)
    return dict(crs=tms.crs, transform=dst_transform)


def get_zooms(src_dst, tms: morecantile.TileMatrixSet = default_tms) -> Tuple[int, int]:
    """
    Calculate raster min/max zoom level.

    Parameters
    ----------
    src_dst: rasterio.io.DatasetReader
        Rasterio io.DatasetReader object
    tms : morecantile.TileMatrixSet
        morecantile TileMatrixSet to use (default: WebMercator).

    Returns
    -------
    min_zoom, max_zoom: Tuple
        Min/Max zoom levels.

    """

    def _zoom_for_pixelsize(pixel_size, max_z=24):
        """Get zoom level corresponding to a pixel resolution."""
        for z in range(max_z):
            matrix = tms.matrix(z)
            if pixel_size > tms._resolution(matrix):
                return max(0, z - 1)  # We don't want to scale up

        return max_z - 1

    dst_affine, w, h = calculate_default_transform(
        src_dst.crs, tms.crs, src_dst.width, src_dst.height, *src_dst.bounds
    )
    resolution = max(abs(dst_affine[0]), abs(dst_affine[4]))
    max_zoom = _zoom_for_pixelsize(resolution)

    matrix = tms.tileMatrix[0]
    ovr_resolution = resolution * max(h, w) / max(matrix.tileWidth, matrix.tileHeight)
    min_zoom = _zoom_for_pixelsize(ovr_resolution)
    return (min_zoom, max_zoom)


def spatial_info(address: str, tms: morecantile.TileMatrixSet = default_tms) -> Dict:
    """
    Return COGEO spatial info.

    Attributes
    ----------
    address : str or PathLike object
        A dataset path or URL. Will be opened in "r" mode.
    tms : morecantile.TileMatrixSet
        morecantile TileMatrixSet to use (default: WebMercator).

    Returns
    -------
    out : dict.

    """
    with rasterio.open(address) as src_dst:
        minzoom, maxzoom = get_zooms(src_dst, tms)
        bounds = transform_bounds(
            src_dst.crs, constants.WGS84_CRS, *src_dst.bounds, densify_pts=21
        )
        center = ((bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2, minzoom)

    return dict(
        address=address, bounds=bounds, center=center, minzoom=minzoom, maxzoom=maxzoom
    )


def bounds(address: str, dst_crs: CRS = constants.WGS84_CRS) -> Dict:
    """
    Retrieve image bounds.

    Attributes
    ----------
    address : str
        file url.
    dst_crs: CRS
        Target CRS (default is EPSG:4326).

    Returns
    -------
    out : dict
        dictionary with image bounds.

    """
    with rasterio.open(address) as src_dst:
        bounds = transform_bounds(src_dst.crs, dst_crs, *src_dst.bounds, densify_pts=21)

    return dict(address=address, bounds=bounds)


def info(address: str, tms: morecantile.TileMatrixSet = default_tms) -> Dict:
    """
    Return simple metadata about the file.

    Attributes
    ----------
    address : str or PathLike object
        A dataset path or URL. Will be opened in "r" mode.
    tms : morecantile.TileMatrixSet
        morecantile TileMatrixSet to use (default: WebMercator).

    Returns
    -------
    out : dict.

    """
    with rasterio.open(address) as src_dst:
        minzoom, maxzoom = get_zooms(src_dst, tms)
        bounds = transform_bounds(
            src_dst.crs, constants.WGS84_CRS, *src_dst.bounds, densify_pts=21
        )
        center = [(bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2, minzoom]

        def _get_descr(ix):
            """Return band description."""
            name = src_dst.descriptions[ix - 1]
            if not name:
                name = "band{}".format(ix)
            return name

        band_descriptions = [(ix, _get_descr(ix)) for ix in src_dst.indexes]
        tags = [(ix, src_dst.tags(ix)) for ix in src_dst.indexes]

        other_meta = dict()
        if src_dst.scales[0] and src_dst.offsets[0]:
            other_meta.update(dict(scale=src_dst.scales[0]))
            other_meta.update(dict(offset=src_dst.offsets[0]))

        if has_alpha_band(src_dst):
            nodata_type = "Alpha"
        elif has_mask_band(src_dst):
            nodata_type = "Mask"
        elif src_dst.nodata is not None:
            nodata_type = "Nodata"
        else:
            nodata_type = "None"

        try:
            cmap = src_dst.colormap(1)
            other_meta.update(dict(colormap=cmap))
        except ValueError:
            pass

        return dict(
            address=address,
            bounds=bounds,
            center=center,
            minzoom=minzoom,
            maxzoom=maxzoom,
            band_metadata=tags,
            band_descriptions=band_descriptions,
            dtype=src_dst.meta["dtype"],
            colorinterp=[src_dst.colorinterp[ix - 1].name for ix in src_dst.indexes],
            nodata_type=nodata_type,
            **other_meta,
        )


def _tile(
    src_dst: Union[DatasetReader, DatasetWriter, WarpedVRT],
    tile_x: int,
    tile_y: int,
    tile_z: int,
    tilesize: int = 256,
    tms: morecantile.TileMatrixSet = default_tms,
    **kwargs: Any,
) -> Tuple[numpy.ndarray, numpy.ndarray]:
    """
    Attributes
    ----------
    address : rasterio.io.DatasetReader
        rasterio.io.DatasetReader object.
    tile_x : int
        Mercator tile X index.
    tile_y : int
        Mercator tile Y index.
    tile_z : int
        Mercator tile ZOOM level.
    tilesize : int, optional (default: 256)
        Output image size.
    tms : morecantile.TileMatrixSet
        morecantile TileMatrixSet to use (default: WebMercator).
    kwargs: dict, optional
        These will be passed to the 'rio_tiler.utils._tile_read' function.

    Returns
    -------
    data : numpy ndarray
    mask: numpy array

    """
    raster_bounds = transform_bounds(
        src_dst.crs, tms.crs, *src_dst.bounds, densify_pts=21
    )
    tile = morecantile.Tile(x=tile_x, y=tile_y, z=tile_z)
    tile_bounds = tms.xy_bounds(*tile)
    if not _tile_exists(raster_bounds, tile_bounds):
        raise TileOutsideBounds(
            "Tile {}/{}/{} is outside image bounds".format(tile_z, tile_x, tile_y)
        )

    return reader.part(
        src_dst, tile_bounds, tilesize, tilesize, dst_crs=tms.crs, **kwargs,
    )


def tile(
    src_path: Union[DatasetReader, DatasetWriter, WarpedVRT, str],
    tile_x: int,
    tile_y: int,
    tile_z: int,
    tilesize: int = 256,
    tms: morecantile.TileMatrixSet = default_tms,
    **kwargs: Any,
) -> Tuple[numpy.ndarray, numpy.ndarray]:
    """
    Create tile from any images.

    Attributes
    ----------
    address : str or rasterio dataset
        file url.
    tile_x : int
        Mercator tile X index.
    tile_y : int
        Mercator tile Y index.
    tile_z : int
        Mercator tile ZOOM level.
    tilesize : int, optional (default: 256)
        Output image size.
    tms : morecantile.TileMatrixSet
        morecantile TileMatrixSet to use (default: WebMercator).
    kwargs: dict, optional
        These will be passed to the 'rio_tiler.utils._tile_read' function.

    Returns
    -------
    data : numpy ndarray
    mask: numpy array

    """
    if isinstance(src_path, (DatasetReader, DatasetWriter, WarpedVRT)):
        return _tile(src_path, tile_x, tile_y, tile_z, tilesize, tms=tms, **kwargs)
    else:
        with rasterio.open(src_path) as src_dst:
            return _tile(src_dst, tile_x, tile_y, tile_z, tilesize, tms=tms, **kwargs)
