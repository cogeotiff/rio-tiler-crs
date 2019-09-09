"""
rio_tiler_crs.projectile is a custom fork of tiletanic module from Digitalglobe.

Origin: https://github.com/DigitalGlobe/tiletanic/blob/master/tiletanic/tileschemes.py

"""
import re
import abc

from math import floor
from collections import namedtuple
from pyproj import CRS, Transformer


# Python 2 and 3 compat
# see https://stackoverflow.com/a/38668373
ABC = abc.ABCMeta("ABC", (object,), {"__slots__": ()})


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

qk_regex = re.compile(r"[0-3]+$")


class TileSchema(object):
    """
    Custom Tiling schema.

    The whole class is from tiletanic.tileschemes.BasicTilingTopLeft
    url: https://github.com/DigitalGlobe/tiletanic/blob/master/tiletanic/tileschemes.py

    The origin of a tile (row, column) is the top left of the bounds.

    Attributes
    ----------
        epsg_code: int
            The EPSG Code for the projection that the tiling scheme is defined for.

    """

    def __init__(self, epsg_code: int, transform=(1, 1)):
        """
        Construct a tile scheme for an epsg code and a transform.

        Attributes
        ----------
            epsg_code: int
                EPSG Code.

        """
        dst_crs = CRS.from_epsg(epsg_code)
        transformer = Transformer.from_crs(
            "epsg:4326", CRS.from_epsg(epsg_code), always_xy=True
        )
        xmin, ymin, xmax, ymax = dst_crs.area_of_use.bounds
        xmin, ymin = transformer.transform(xmin, ymin)
        xmax, ymax = transformer.transform(xmax, ymax)

        if xmax <= xmin:
            raise ValueError("xmax must be greater than xmin")
        if ymax <= ymin:
            raise ValueError("ymax must be greater than ymin")

        self.bounds = CoordsBbox(float(xmin), float(ymin), float(xmax), float(ymax))
        self.transform = transform

    def tile(self, xcoord, ycoord, zoom):
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

    def parent(self, *tile):
        """
        Return the parent of the (x, y, z) tile.

        Attributes
        ----------
            tile: (x, y, z) tile coordinates or a Tile object we want the parent of.

        Returns
        -------
            A Tile object representing the parent of the input.

        """
        if len(tile) == 1:  # Handle if a Tile object was inputted.
            tile = tile[0]

        x, y, z = tile

        if x % 2 == 0 and y % 2 == 0:  # x and y even
            return Tile(x // 2, y // 2, z - 1)
        elif x % 2 == 0:  # x even, y odd
            return Tile(x // 2, (y - 1) // 2, z - 1)
        elif y % 2 == 0:  # x odd, y even
            return Tile((x - 1) // 2, y // 2, z - 1)
        else:  # x odd, y odd
            return Tile((x - 1) // 2, (y - 1) // 2, z - 1)

    def children(self, *tile):
        """
        Return the children of the (x, y, z) tile.

        Attributes
        ----------
            tile: (x, y, z) tile coordinates or a Tile object we want the children of.

        Returns
        -------
            A list of Tile objects representing the children of
            this tile.

        """
        if len(tile) == 1:  # Handle if a Tile object was inputted.
            tile = tile[0]

        x, y, z = tile

        return [
            Tile(2 * x, 2 * y, z + 1),
            Tile(2 * x + 1, 2 * y, z + 1),
            Tile(2 * x, 2 * y + 1, z + 1),
            Tile(2 * x + 1, 2 * y + 1, z + 1),
        ]

    def ul(self, *tile):
        """
        Return the upper left coordinate of the (x, y, z) tile.

        Attributes
        ----------
            tile: (x, y, z) tile coordinates or a Tile object we want the upper left geospatial coordinates of.

        Returns
        -------
            The upper left geospatial coordiantes of the input tile.

        """
        if len(tile) == 1:  # Handle if a Tile object was inputted.
            tile = tile[0]

        x, y, z = tile

        return Coords(self._xcoord(x, z), self._ycoord(y, z))

    def br(self, *tile):
        """
        Return the bottom right coordinate of the (x, y, z) tile.

        Attributes
        ----------
            tile: (x, y, z) tile coordinates or a Tile object we want the bottom right geospatial coordinates of.

        Returns
        -------
            The bottom right geospatial coordiantes of the input tile.

        """
        if len(tile) == 1:  # Handle if a Tile object was inputted.
            tile = tile[0]

        x, y, z = tile

        return Coords(self._xcoord(x + 1, z), self._ycoord(y + 1, z))

    def bbox(self, *tile):
        """
        Return the bounding box of the (x, y, z) tile.

        Attributes
        ----------
            tile: A tuple of (x, y, z) tile coordinates or a Tile object we want the bounding box of.

        Returns
        -------
            The bounding box of the input tile.

        """
        if len(tile) == 1:  # Handle if a Tile object was inputted.
            tile = tile[0]

        x, y, z = tile

        west, north = self.ul(tile)
        east, south = self.br(tile)
        return CoordsBbox(west, south, east, north)

    def xy_bounds(self, *tile):
        """Alias for bbox."""
        return self.bbox(*tile)

    def quadkey(self, *tile):
        """
        Return the quadkey of the (x, y, z) tile.

        Attributes
        ----------
            tile: A tuple of (x, y, z) tile coordinates or a Tile object we want the quadkey of.

        Returns
        -------
            The quadkey of the input tile.

        """
        if len(tile) == 1:  # Handle if a Tile object was inputted.
            tile = tile[0]

        x, y, z = [int(i) for i in tile]

        quadkey = []
        for zoom in range(z, 0, -1):
            digit = 0
            mask = 1 << (zoom - 1)
            if int(x) & mask:
                digit += 1
            if int(y) & mask:
                digit += 2
            quadkey.append(digit)
        return "".join(str(d) for d in quadkey)

    def quadkey_to_tile(self, qk):
        """
        Return the Tile object represented by the input quadkey.

        Attributes
        ----------
            qk: A string representing the quadkey.

        Returns
        -------
            The Tile object represented by the input quadkey.

        """
        if not qk_regex.match(qk):
            raise ValueError("Input quadkey is invalid.")

        x = 0
        y = 0
        for i, digit in enumerate(reversed(qk)):
            mask = 1 << i
            if digit == "1":
                x = x | mask
            elif digit == "2":
                y = y | mask
            elif digit == "3":
                x = x | mask
                y = y | mask
        return Tile(x, y, len(qk))

    # def TileBounds(self, tx, ty, zoom):
    #     """Return bounds of the given tile."""
    #     res = self.resFact / 2**zoom
    #     return (
    #         tx * self.tile_size * res - 180,
    #         ty * self.tile_size * res - 90,
    #         (tx + 1) * self.tile_size * res - 180,
    #         (ty + 1) * self.tile_size * res - 90
    #     )

    def _xcoord(self, x, z):
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
        return (
            x / (2.0 ** z) * (self.bounds.xmax - self.bounds.xmin) * self.transform[0]
        ) + self.bounds.xmin

    def _ycoord(self, y, z):
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
        return self.bounds.ymax - (
            y / (2.0 ** z) * (self.bounds.ymax - self.bounds.ymin) * self.transform[1]
        )

    def _x(self, xcoord, zoom):
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
        return int(
            floor(
                (2.0 ** zoom)
                * (xcoord - self.bounds.xmin)
                / (self.bounds.xmax - self.bounds.xmin)
                * self.transform[0]
            )
        )

    def _y(self, ycoord, zoom):
        """
        Get the y coordinate (row) of this tile at this zoom level.
        Note that this function assumes that the origin is on the
        top, not the bottom!

        Attributes
        ----------
            ycoord: y coordinate to covert to tile index.
            zoom: zoom level of th tile we want.

        Returns
        -------
            The y coordinate (row) of the tile.

        """
        return int(
            floor(
                (2.0 ** zoom)
                * (self.bounds.ymax - ycoord)
                / (self.bounds.ymax - self.bounds.ymin)
                * self.transform[0]
            )
        )
