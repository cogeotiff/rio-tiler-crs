"""rio-tiler-crs.reader."""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import morecantile
import numexpr
import numpy
import rasterio
from rasterio.crs import CRS
from rasterio.io import DatasetReader, DatasetWriter, MemoryFile
from rasterio.transform import from_bounds
from rasterio.vrt import WarpedVRT
from rasterio.warp import calculate_default_transform, transform_bounds

from rio_tiler import constants, reader
from rio_tiler.errors import TileOutsideBounds
from rio_tiler.utils import has_alpha_band, has_mask_band

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


def _parse_expression(expression: str) -> Sequence[int]:
    """Parse rio-tiler band math expression."""
    bands = set(re.findall(r"b(?P<bands>\d+)", expression, re.IGNORECASE))
    return tuple(map(int, bands))


def _apply_expression(
    blocks: Sequence[str], bands: Sequence[str], data: numpy.ndarray
) -> numpy.ndarray:
    """Apply rio-tiler expression."""
    data = dict(zip(bands, data))
    return numpy.array(
        [
            numpy.nan_to_num(numexpr.evaluate(bloc.strip(), local_dict=data))
            for bloc in blocks
        ]
    )


@dataclass
class COGReader:
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

    filepath: str
    dataset: Optional[Union[DatasetReader, DatasetWriter, MemoryFile, WarpedVRT]] = None
    tms: morecantile.TileMatrixSet = default_tms
    _minzoom: Optional[int] = None
    _maxzoom: Optional[int] = None
    _colormap: Optional[Dict] = None

    def __enter__(self):
        """Support using with Context Managers."""
        self.dataset = self.dataset or rasterio.open(self.filepath)

        self.bounds: Tuple[float, float, float, float] = transform_bounds(
            self.dataset.crs, constants.WGS84_CRS, *self.dataset.bounds, densify_pts=21
        )

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Support using with Context Managers."""
        if self.filepath:
            self.dataset.close()

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

        self._minzoom = self._minzoom or min_zoom
        self._maxzoom = self._maxzoom or max_zoom

        return

    def _get_colormap(self):
        """Retrieve the internal colormap."""
        try:
            self._colormap = self.dataset.colormap(1)
        except ValueError:
            self._colormap = {}
            pass

    def _tile_exists(self, tile: morecantile.Tile):
        """Check if a tile is inside a given bounds."""
        tile_bounds = self.tms.bounds(*tile)
        return (
            (tile_bounds[0] < self.bounds[2])
            and (tile_bounds[2] > self.bounds[0])
            and (tile_bounds[3] > self.bounds[1])
            and (tile_bounds[1] < self.bounds[3])
        )

    @property
    def colormap(self) -> Dict[int, Tuple[int, int, int, int]]:
        """COG internal Colormap."""
        if self._colormap is None:
            self._get_colormap()
        return self._colormap

    @property
    def minzoom(self) -> int:
        """COG Min zoom in TMS."""
        if self._minzoom is None:
            self._get_zooms()
        return self._minzoom

    @property
    def maxzoom(self) -> int:
        """COG Max zoom in TMS."""
        if self._maxzoom is None:
            self._get_zooms()
        return self._maxzoom

    @property
    def center(self) -> Tuple[float, float, int]:
        """Return COG center + minzoom."""
        return (
            (self.bounds[0] + self.bounds[2]) / 2,
            (self.bounds[1] + self.bounds[3]) / 2,
            self.minzoom,
        )

    @property
    def info(self) -> Dict:
        """Return COG info."""

        def _get_descr(ix):
            """Return band description."""
            name = self.dataset.descriptions[ix - 1]
            if not name:
                name = "band{}".format(ix)
            return name

        indexes = self.dataset.indexes
        band_descr = [(ix, _get_descr(ix)) for ix in indexes]
        band_meta = [(ix, self.dataset.tags(ix)) for ix in indexes]
        colorinterp = [self.dataset.colorinterp[ix - 1].name for ix in indexes]

        if has_alpha_band(self.dataset):
            nodata_type = "Alpha"
        elif has_mask_band(self.dataset):
            nodata_type = "Mask"
        elif self.dataset.nodata is not None:
            nodata_type = "Nodata"
        else:
            nodata_type = "None"

        other_meta = {}
        if self.dataset.scales[0] and self.dataset.offsets[0]:
            other_meta.update(
                {"scale": self.dataset.scales[0], "offset": self.dataset.offsets[0]}
            )

        if self.colormap:
            other_meta.update({"colormap": self.colormap})

        meta = {
            "bounds": self.bounds,
            "center": self.center,
            "minzoom": self.minzoom,
            "maxzoom": self.maxzoom,
            "band_metadata": band_meta,
            "band_descriptions": band_descr,
            "dtype": self.dataset.meta["dtype"],
            "colorinterp": colorinterp,
            "nodata_type": nodata_type,
        }
        meta.update(**other_meta)
        return meta

    def tile(
        self,
        tile_x: int,
        tile_y: int,
        tile_z: int,
        tilesize: int = 256,
        indexes: Optional[Union[int, Sequence]] = None,
        expression: Optional[str] = "",
        **kwargs: Any,
    ) -> Tuple[numpy.ndarray, numpy.ndarray]:
        """Read a TMS map tile from a COG."""
        if isinstance(indexes, int):
            indexes = (indexes,)

        if expression:
            indexes = _parse_expression(expression)

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
            tile = _apply_expression(blocks, bands, tile)

        return tile, mask

    def part(
        self,
        bbox: Tuple[float, float, float, float],
        dst_crs: Optional[CRS] = None,
        bounds_crs: CRS = constants.WGS84_CRS,
        max_size: int = 1024,
        indexes: Optional[Union[int, Sequence]] = None,
        expression: Optional[str] = "",
        **kwargs: Any,
    ) -> Tuple[numpy.ndarray, numpy.ndarray]:
        """Read part of a COG."""
        if isinstance(indexes, int):
            indexes = (indexes,)

        if expression:
            indexes = _parse_expression(expression)

        if not dst_crs:
            dst_crs = self.dataset.crs

        data, mask = reader.part(
            self.dataset,
            bbox,
            max_size=max_size,
            bounds_crs=bounds_crs,
            dst_crs=dst_crs,
            indexes=indexes,
            **kwargs,
        )

        if expression:
            blocks = expression.lower().split(",")
            bands = [f"b{bidx}" for bidx in indexes]
            data = _apply_expression(blocks, bands, data)

        return data, mask

    def preview(
        self,
        indexes: Optional[Union[int, Sequence]] = None,
        expression: Optional[str] = "",
        **kwargs: Any,
    ) -> Tuple[numpy.ndarray, numpy.ndarray]:
        """Return a preview of a COG."""
        if isinstance(indexes, int):
            indexes = (indexes,)

        if expression:
            indexes = _parse_expression(expression)

        data, mask = reader.preview(self.dataset, indexes=indexes, **kwargs)

        if expression:
            blocks = expression.lower().split(",")
            bands = [f"b{bidx}" for bidx in indexes]
            data = _apply_expression(blocks, bands, data)

        return data, mask

    def point(
        self,
        lon: float,
        lat: float,
        indexes: Optional[Union[int, Sequence]] = None,
        expression: Optional[str] = "",
        **kwargs: Any,
    ) -> List:
        """Read a value from a COG."""
        if isinstance(indexes, int):
            indexes = (indexes,)

        if expression:
            indexes = _parse_expression(expression)

        point = reader.point(self.dataset, (lon, lat), indexes=indexes, **kwargs)

        if expression:
            blocks = expression.lower().split(",")
            bands = [f"b{bidx}" for bidx in indexes]
            point = _apply_expression(blocks, bands, point).tolist()

        return point

    def stats(
        self,
        pmin: float = 2.0,
        pmax: float = 98.0,
        hist_options: Dict = {},
        **kwargs: Any,
    ) -> Dict:
        """Return array statistics from a COG."""
        if self.colormap and not hist_options.get("bins"):
            hist_options["bins"] = [
                k for k, v in self.colormap.items() if v != (0, 0, 0, 255)
            ]
        return reader.stats(
            self.dataset, percentiles=(pmin, pmax), hist_options=hist_options, **kwargs,
        )

    def metadata(self, pmin: float = 2.0, pmax: float = 98.0, **kwargs: Any) -> Dict:
        """Return COG info and statistics."""
        info = self.info.copy()
        info["statistics"] = self.stats(pmin, pmax, **kwargs)
        return info
