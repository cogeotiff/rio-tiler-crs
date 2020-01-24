"""Tests for rio_tiler_crs."""

import os
import pytest

import morecantile

import rasterio
from rasterio.crs import CRS
from rio_tiler_crs import tiler
from rio_tiler.errors import TileOutsideBounds

COG_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "cog.tif")


def test_tiler_default():
    """Test rio_tiler_crs.tiler.tile function with different projection."""
    lon = -58.181
    lat = 73.8794
    zoom = 7

    ts = morecantile.TileSchema()
    x, y, z = ts.tile(lon, lat, zoom)

    data, mask = tiler.tile(COG_PATH, x, y, z, tileSchema=ts)
    assert data.shape == (1, 256, 256)
    assert mask.shape == (256, 256)

    crs = CRS.from_epsg(32621)
    extent = [166021.44, 0.00, 534994.66, 9329005.18]  # from http://epsg.io/32621
    ts = morecantile.TileSchema(crs, extent)
    x, y, z = ts.tile(lon, lat, zoom)

    data, mask = tiler.tile(COG_PATH, x, y, z, tileSchema=ts)
    assert data.shape == (1, 256, 256)
    assert mask.shape == (256, 256)

    x, y, z = ts.tile(lon + 10, lat, zoom)
    with pytest.raises(TileOutsideBounds):
        tiler.tile(COG_PATH, x, y, z, tileSchema=ts)


def test_get_zoom():
    """Test rio_tiler_crs.tiler.get_zooms function with different projection."""
    with rasterio.open(COG_PATH) as src_dst:
        minzoom, maxzoom = tiler.get_zooms(src_dst)
        assert minzoom == 5
        assert maxzoom == 8

    crs, args = morecantile.default_grids.get(4326)
    ts = morecantile.TileSchema(crs, **args)

    with rasterio.open(COG_PATH) as src_dst:
        minzoom, maxzoom = tiler.get_zooms(src_dst, tileSchema=ts)
        assert minzoom == 4
        assert maxzoom == 8
