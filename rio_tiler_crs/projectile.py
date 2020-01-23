"""
rio_tiler_crs.projectile an adpatation of mapbox/mercantile to work with custom projection.

Refs:
    - mapproxy: https://github.com/mapproxy/mapproxy
    - mercantile: https://github.com/mapbox/mercantile
    - tiletanic: https://github.com/DigitalGlobe/tiletanic

"""
from typing import Any, Dict, List

import re
import math
from collections import namedtuple

from rasterio.crs import CRS
from rasterio.warp import transform_bounds

from rio_tiler_crs.errors import TileArgParsingError, ParentTileError, InvalidZoomError

qk_regex = re.compile(r"[0-3]+$")


# Enums
Tile = namedtuple("Tile", ["x", "y", "z"])
"""
An XYZ tile.

Attributes
----------
x, y, z : int
    x and y indexes of the tile and zoom level z.
"""

Coords = namedtuple("Coords", ["x", "y"])
"""
A X,Y Coordinates pair.

Attributes
----------
X, Y : float
    X, Y coordinates in input projection unit.
"""

CoordsBbox = namedtuple("CoordsBbox", ["xmin", "ymin", "xmax", "ymax"])
"""
A geographic bounding box.

Attributes
----------
xmin, ymin, xmax, ymax : float
    Bounding values in input projection unit.
"""


def _parse_tile_arg(*args) -> Tile:
    """
    Parse the *tile arg of module functions.

    Originaly from https://github.com/mapbox/mercantile/blob/master/mercantile/__init__.py

    Parameters
    ----------
        tile : Tile or sequence of int
            May be be either an instance of Tile or 3 ints, X, Y, Z.

    Returns
    -------
        Tile

    Raises
    ------
    TileArgParsingError

    """
    if len(args) == 1:
        args = args[0]
    if len(args) == 3:
        return Tile(*args)
    else:
        raise TileArgParsingError(
            "the tile argument may have 1 or 3 values. Note that zoom is a keyword-only argument"
        )


class TileSchema(object):
    """
    Custom Tiling schema.

    Ref: OGC Tile Matrix Specification http://docs.opengeospatial.org/is/17-083r2/17-083r2.html
    """

    def __init__(
        self,
        crs: CRS = CRS({"init": "EPSG:4326"}),
        extent: List[float] = [-180.0, -90.0, 180.0, 90.0],
        extent_crs: CRS = None,
        tile_size: List[int] = [256, 256],
        matrix_scale: List[int] = [2, 1],
    ) -> None:
        """
        Construct a custom tile scheme.

        Attributes
        ----------
            crs: rasterio.crs.CRS
                Tiling schema coordinate reference system, as a rasterio CRS object
                (default: CRS({'init': 'EPSG:4326'}))
            extent: list
                Bounding box of the tiling schema (default: [-180.0, -90.0, 180.0, 90.0])
            extent_crs: rasterio.crs.CRS
                Extent's coordinate reference system, as a rasterio CRS object.
                (default: assuming same as input crs)
            tile_size: list
                Tiling schema tile sizes (default: [256, 256])
            matrix_scale: list
                Tiling schema coalescence coefficient (default: [2, 1] for WGS84).
                Should be set to [1, 1] when using Equirectangular Plate Carree projection.
                see: http://docs.opengeospatial.org/is/17-083r2/17-083r2.html#14

        """
        self.crs = crs
        bbox = (
            transform_bounds(extent_crs, self.crs, *extent, densify_pts=21)
            if extent_crs
            else extent
        )
        self.extent = CoordsBbox(*bbox)
        self.wgs84extent = transform_bounds(
            self.crs, CRS({"init": "EPSG:4326"}), *self.extent, densify_pts=21
        )
        self.origin = Coords(float(self.extent.xmin), float(self.extent.ymax))
        self.tile_size = tile_size
        self.matrix_scale = matrix_scale
        self.meters_per_unit = (
            # self.crs.linear_units_factor[1]  GDAL 3.0
            1.0
            if self.crs.linear_units == "metre"
            else 2 * math.pi * 6378137 / 360.0
        )

    def _resolution(self, zoom: int) -> float:
        """Tile resolution for a zoom level."""
        width = abs(self.extent.xmax - self.extent.xmin)
        height = abs(self.extent.ymax - self.extent.ymin)
        return max(
            width / (self.tile_size[0] * self.matrix_scale[0]) / 2.0 ** zoom,
            height / (self.tile_size[1] * self.matrix_scale[1]) / 2.0 ** zoom,
        )

    def get_ogc_tilematrix(self, zoom: int) -> Dict:
        """
        Construct TileMatrixType dict.

        Attributes
        ----------
            zoom: the zoom level

        Returns
        -------
            Dict of the OGC TileMatrix information.

        """
        return {
            "type": "TileMatrixType",
            "identifier": str(zoom),
            "scaleDenominator": self._resolution(zoom) * self.meters_per_unit / 0.00028,
            "topLeftCorner": self.origin,
            "tileWidth": self.tile_size[0],
            "tileHeight": self.tile_size[1],
            "matrixWidth": self.matrix_scale[0] * 2 ** zoom,
            "matrixHeight": self.matrix_scale[1] * 2 ** zoom,
        }

    def _x(self, xcoord: float, zoom: int) -> float:
        """
        Get the x coordinate (column) of this tile at this zoom level.

        Attributes
        ----------
            xcoord: x coordinate to covert to tile index.
            zoom: zoom level of th tile we want.

        Returns
        -------
            The x coordinate (column) of the tile.

        """
        res = self._resolution(zoom)
        return int(
            math.floor(
                (xcoord - self.extent.xmin)
                / float(res * self.tile_size[0] * self.matrix_scale[0])
            )
        )

    def _y(self, ycoord: float, zoom: int) -> float:
        """
        Get the y coordinate (row) of this tile at this zoom level.

        Attributes
        ----------
            ycoord: y coordinate to covert to tile index.
            zoom: zoom level of th tile we want.

        Returns
        -------
            The y coordinate (row) of the tile.

        """
        res = self._resolution(zoom)
        return int(
            math.floor(
                (ycoord - self.extent.ymin)
                / float(res * self.tile_size[1] * self.matrix_scale[1])
            )
        )

    def tile(self, xcoord: float, ycoord: float, zoom: int) -> Tile:
        """
        Return the (x, y, z) tile at the given zoom level that contains the input coordinates.

        Attributes
        ----------
            xcoord: float
                x direction geospatial coordinate within the tile we want.
            ycoord: float
                y direction geospatial coordinate within the tile we want.
            zoom: int
                zoom level of the tile we want.

        Returns
        -------
            A Tile object that covers the given coordinates at the
            provided zoom level.

        """
        return Tile(x=self._x(xcoord, zoom), y=self._y(ycoord, zoom), z=zoom)

    def _xcoord(self, x: int, z: int) -> float:
        """
        Left geospatial coordinate of tile at given column and zoom.

        Attributes
        ----------
            x: The tile's column coordinate.
            z: The zoom level.

        Returns
        -------
            The left geospatial coordinate of this tile.

        """
        res = self._resolution(z)
        return self.extent.xmin + x * res * self.tile_size[0]

    def _ycoord(self, y: int, z: int) -> float:
        """
        Top geospatial coordinate of tile at given row and zoom.

        Attributes
        ----------
            y: The tile's row coordinate.
            z: The zoom level.

        Returns
        -------
            The bottom geospatial coordinate of this tile.

        """
        res = self._resolution(z)
        return self.extent.ymax - y * res * self.tile_size[1]

    def ul(self, *tile: Tile) -> Coords:
        """
        Return the upper left coordinate of the (x, y, z) tile.

        Attributes
        ----------
            tile: (x, y, z) tile coordinates or a Tile object we want the upper left geospatial coordinates of.

        Returns
        -------
            The upper left geospatial coordiantes of the input tile.

        """
        tile = _parse_tile_arg(*tile)
        xtile, ytile, zoom = tile
        return Coords(self._xcoord(xtile, zoom), self._ycoord(ytile, zoom))

    def bounds(self, *tile: Tile) -> CoordsBbox:
        """
        Return the bounding box of the (x, y, z) tile.

        Attributes
        ----------
            tile: A tuple of (x, y, z) tile coordinates or a Tile object we want the bounding box of.

        Returns
        -------
            The bounding box of the input tile.

        """
        tile = _parse_tile_arg(*tile)
        xtile, ytile, zoom = tile
        left, top = self.ul(xtile, ytile, zoom)
        right, bottom = self.ul(xtile + 1, ytile + 1, zoom)
        return CoordsBbox(left, bottom, right, top)

    def parent(self, *tile: Tile, **kwargs: Any) -> Tile:
        """
        Get the parent of a tile.

        The parent is the tile of one zoom level
        lower that contains the given "child" tile.
        Originaly from https://github.com/mapbox/mercantile/blob/master/mercantile/__init__.py

        Parameters
        ----------
            tile : Tile or sequence of int
                May be be either an instance of Tile or 3 ints, X, Y, Z.
            zoom : int, optional
                Determines the *zoom* level of the returned parent tile.
                This defaults to one lower than the tile (the immediate parent).

        Returns
        -------
            Tile

        Examples
        --------
        >>> parent(Tile(0, 0, 2))
        Tile(x=0, y=0, z=1)
        >>> parent(Tile(0, 0, 2), zoom=0)
        Tile(x=0, y=0, z=0)

        """
        tile = _parse_tile_arg(*tile)

        # zoom is a keyword-only argument.
        zoom = kwargs.get("zoom", None)

        if zoom is not None and (tile[2] < zoom or zoom != int(zoom)):
            raise InvalidZoomError(
                "zoom must be an integer and less than that of the input tile"
            )

        x, y, z = tile
        if x != int(x) or y != int(y) or z != int(z):
            raise ParentTileError("the parent of a non-integer tile is undefined")

        target_zoom = z - 1 if zoom is None else zoom

        # Algorithm heavily inspired by https://github.com/mapbox/tilebelt.
        return_tile = tile
        while return_tile[2] > target_zoom:
            xtile, ytile, ztile = return_tile
            if xtile % 2 == 0 and ytile % 2 == 0:
                return_tile = Tile(xtile // 2, ytile // 2, ztile - 1)
            elif xtile % 2 == 0:
                return_tile = Tile(xtile // 2, (ytile - 1) // 2, ztile - 1)
            elif not xtile % 2 == 0 and ytile % 2 == 0:
                return_tile = Tile((xtile - 1) // 2, ytile // 2, ztile - 1)
            else:
                return_tile = Tile((xtile - 1) // 2, (ytile - 1) // 2, ztile - 1)
        return return_tile

    def children(*tile: Tile, **kwargs: Any) -> List[Tile]:
        """
        Get the children of a tile.

        The children are ordered: top-left, top-right, bottom-right, bottom-left.
        Originaly from https://github.com/mapbox/mercantile/blob/master/mercantile/__init__.py

        Parameters
        ----------
            tile : Tile or sequence of int
                May be be either an instance of Tile or 3 ints, X, Y, Z.
            zoom : int, optional
                Returns all children at zoom *zoom*, in depth-first clockwise winding order.
                If unspecified, returns the immediate (i.e. zoom + 1) children of the tile.
        Returns
        -------
            list

        Examples
        --------
        >>> children(Tile(0, 0, 0))
        [Tile(x=0, y=0, z=1), Tile(x=0, y=1, z=1), Tile(x=1, y=0, z=1), Tile(x=1, y=1, z=1)]
        >>> children(Tile(0, 0, 0), zoom=2)
        [Tile(x=0, y=0, z=2), Tile(x=0, y=1, z=2), Tile(x=0, y=2, z=2), Tile(x=0, y=3, z=2), ...]

        """
        tile = _parse_tile_arg(*tile)

        # zoom is a keyword-only argument.
        zoom = kwargs.get("zoom", None)

        xtile, ytile, ztile = tile

        if zoom is not None and (ztile > zoom or zoom != int(zoom)):
            raise InvalidZoomError(
                "zoom must be an integer and greater than that of the input tile"
            )

        target_zoom = zoom if zoom is not None else ztile + 1

        tiles = [tile]
        while tiles[0][2] < target_zoom:
            xtile, ytile, ztile = tiles.pop(0)
            tiles += [
                Tile(xtile * 2, ytile * 2, ztile + 1),
                Tile(xtile * 2 + 1, ytile * 2, ztile + 1),
                Tile(xtile * 2 + 1, ytile * 2 + 1, ztile + 1),
                Tile(xtile * 2, ytile * 2 + 1, ztile + 1),
            ]
        return tiles

    def quadkey(self, *tile: Tile) -> str:
        """
        Return the quadkey of the (x, y, z) tile.

        Originaly from https://github.com/mapbox/mercantile/blob/master/mercantile/__init__.py

        Attributes
        ----------
            tile: A tuple of (x, y, z) tile coordinates or a Tile object we want the quadkey of.

        Returns
        -------
            The quadkey of the input tile.

        """
        tile = _parse_tile_arg(*tile)
        xtile, ytile, zoom = tile

        qk = []
        for z in range(zoom, 0, -1):
            digit = 0
            mask = 1 << (z - 1)
            if xtile & mask:
                digit += 1
            if ytile & mask:
                digit += 2
            qk.append(str(digit))

        return "".join(qk)

    def quadkey_to_tile(self, qk: str) -> Tile:
        """
        Get the tile corresponding to a quadkey.

        Originaly from https://github.com/mapbox/mercantile/blob/master/mercantile/__init__.py

        Parameters
        ----------
        qk : str
            A quadkey string.

        Returns
        -------
        Tile

        """
        if not qk_regex.match(qk):
            raise ValueError("Input quadkey is invalid.")

        if len(qk) == 0:
            return Tile(0, 0, 0)

        xtile, ytile = 0, 0
        for i, digit in enumerate(reversed(qk)):
            mask = 1 << i
            if digit == "1":
                xtile = xtile | mask
            elif digit == "2":
                ytile = ytile | mask
            elif digit == "3":
                xtile = xtile | mask
                ytile = ytile | mask

        return Tile(xtile, ytile, i + 1)

    def feature(self, tile, fid=None, props=None, precision=None) -> Dict:
        """
        Get the GeoJSON feature corresponding to a tile.

        Originaly from https://github.com/mapbox/mercantile/blob/master/mercantile/__init__.py

        Parameters
        ----------
            tile : Tile or sequence of int
                May be be either an instance of Tile or 3 ints, X, Y, Z.
            fid : str, optional
                A feature id.
            props : dict, optional
                Optional extra feature properties.
            precision : int, optional
                GeoJSON coordinates will be truncated to this number of decimal
                places.
        Returns
        -------
            dict

        """
        west, south, east, north = transform_bounds(
            self.crs, CRS({"init": "EPSG:4326"}), *self.bounds(tile), densify_pts=21
        )

        if precision and precision >= 0:
            west, south, east, north = (
                round(v, precision) for v in (west, south, east, north)
            )
        bbox = [min(west, east), min(south, north), max(west, east), max(south, north)]
        geom = {
            "type": "Polygon",
            "coordinates": [
                [
                    [west, south],
                    [west, north],
                    [east, north],
                    [east, south],
                    [west, south],
                ]
            ],
        }
        xyz = str(tile)
        feat = {
            "type": "Feature",
            "bbox": bbox,
            "id": xyz,
            "geometry": geom,
            "properties": {"title": f"XYZ tile {xyz}", "crs": self.crs.to_string()},
        }
        if props:
            feat["properties"].update(props)

        if fid is not None:
            feat["id"] = fid

        return feat
