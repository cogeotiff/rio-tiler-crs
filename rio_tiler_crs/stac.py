"""rio-tiler-crs.stac."""

from dataclasses import dataclass
from typing import Any, Optional, Sequence, Tuple, Union

import morecantile
import numpy

from rio_tiler.expression import apply_expression
from rio_tiler.io import STACReader as RioTilerReader

from .cogeo import multi_tile

TMS = morecantile.tms.get("WebMercatorQuad")


@dataclass
class STACReader(RioTilerReader):
    """
    STAC + Cloud Optimized GeoTIFF Reader.

    Examples
    --------
    with STACReader(stac_path) as stac:
        stac.tile(...)

    my_stac = {
        "type": "Feature",
        "stac_version": "1.0.0",
        ...
    }
    with STACReader(None, item=my_stac) as stac:
        stac.tile(...)

    Attributes
    ----------
    filepath: str
        STAC Item path, URL or S3 URL.
    item: Dict, optional
        STAC Item dict.
    tms: morecantile.TileMatrixSet, optional
        TileMatrixSet to use, default is WebMercatorQuad.
    minzoom: int, optional
        Set minzoom for the tiles.
    minzoom: int, optional
        Set maxzoom for the tiles.
    include_assets: Set, optional
        Only accept some assets.
    exclude_assets: Set, optional
        Exclude some assets.
    include_asset_types: Set, optional
        Only include some assets base on their type
    include_asset_types: Set, optional
        Exclude some assets base on their type

    Properties
    ----------
    bounds: tuple[float]
        STAC bounds in WGS84 crs.
    center: tuple[float, float, int]
        STAC item center + minzoom

    Methods
    -------
    tile(0, 0, 0, assets="B01", expression="B01/B02")
        Read a map tile from the COG.
    part((0,10,0,10), assets="B01", expression="B1/B20", max_size=1024)
        Read part of the COG.
    preview(assets="B01", max_size=1024)
        Read preview of the COG.
    point((10, 10), assets="B01")
        Read a point value from the COG.
    stats(assets="B01", pmin=5, pmax=95)
        Get Raster statistics.
    info(assets="B01")
        Get Assets raster info.
    metadata(assets="B01", pmin=5, pmax=95)
        info + stats

    """

    tms: morecantile.TileMatrixSet = TMS
    maxzoom: int = TMS.maxzoom
    minzoom: int = TMS.minzoom

    def tile(
        self,
        tile_x: int,
        tile_y: int,
        tile_z: int,
        tilesize: int = 256,
        assets: Union[Sequence[str], str] = None,
        expression: Optional[str] = "",  # Expression based on asset names
        asset_expression: Optional[
            str
        ] = "",  # Expression for each asset based on index names
        **kwargs: Any,
    ) -> Tuple[numpy.ndarray, numpy.ndarray]:
        """Read a TMS map tile from COGs."""
        if isinstance(assets, str):
            assets = (assets,)

        if expression:
            assets = self._parse_expression(expression)

        if not assets:
            raise Exception(
                "assets must be passed either via expression or assets options."
            )

        asset_urls = self._get_href(assets)
        data, mask = multi_tile(
            asset_urls,
            tile_x,
            tile_y,
            tile_z,
            expression=asset_expression,
            tms=self.tms,
            **kwargs,
        )

        if expression:
            blocks = expression.split(",")
            data = apply_expression(blocks, assets, data)

        return data, mask
