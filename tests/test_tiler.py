"""Tests for rio_tiler_crs."""

import os

import morecantile
import pytest
import rasterio
from rasterio.crs import CRS
from rio_tiler.errors import TileOutsideBounds

from rio_tiler_crs import tiler

COG_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "cog.tif")


def test_tiler_tiles():
    """Test rio_tiler_crs.tiler.tile function with different projection."""
    lon = -58.181
    lat = 73.8794
    zoom = 7

    tms = morecantile.TileMatrixSet.load("WebMercatorQuad")
    x, y, z = tms.tile(lon, lat, zoom)

    data, mask = tiler.tile(COG_PATH, x, y, z, tms=tms)
    assert data.shape == (1, 256, 256)
    assert mask.shape == (256, 256)

    crs = CRS.from_epsg(32621)
    extent = [166021.44, 0.00, 534994.66, 9329005.18]  # from http://epsg.io/32621
    tms = morecantile.TileMatrixSet.custom(extent, crs)
    x, y, z = tms.tile(lon, lat, zoom)

    data, mask = tiler.tile(COG_PATH, x, y, z, tms=tms)
    assert data.shape == (1, 256, 256)
    assert mask.shape == (256, 256)

    x, y, z = tms.tile(lon + 10, lat, zoom)
    with pytest.raises(TileOutsideBounds):
        tiler.tile(COG_PATH, x, y, z, tms=tms)


def test_get_zoom():
    """Test rio_tiler_crs.tiler.get_zooms function with different projection."""
    with rasterio.open(COG_PATH) as src_dst:
        minzoom, maxzoom = tiler.get_zooms(src_dst)
        assert minzoom == 5
        assert maxzoom == 8

    tms = morecantile.TileMatrixSet.load("WorldCRS84Quad")
    with rasterio.open(COG_PATH) as src_dst:
        minzoom, maxzoom = tiler.get_zooms(src_dst, tms)
        assert minzoom == 4
        assert maxzoom == 8


def test_spatial_info():
    """Test rio_tiler_crs.tiler.spatial_info function with different projection."""
    info = tiler.spatial_info(COG_PATH)
    assert info["minzoom"] == 5
    assert info["maxzoom"] == 8
    assert info["center"][-1] == 5

    tms = morecantile.TileMatrixSet.load("WorldCRS84Quad")
    info = tiler.spatial_info(COG_PATH, tms)
    assert info["minzoom"] == 4
    assert info["maxzoom"] == 8
    assert info["center"][-1] == 4


def test_bounds():
    """Test rio_tiler_crs.tiler.bounds function with different projection."""
    info = tiler.bounds(COG_PATH)
    assert round(info["bounds"][0], 3) == -61.288

    crs = CRS.from_epsg(3857)
    info = tiler.bounds(COG_PATH, dst_crs=crs)
    assert round(info["bounds"][0], 3) == -6822507.143


def test_info():
    """Test rio_tiler_crs.tiler.info function with different projection."""
    info = tiler.info(COG_PATH)
    assert info["minzoom"] == 5
    assert info["maxzoom"] == 8
    assert info["center"][-1] == 5

    tms = morecantile.TileMatrixSet.load("WorldCRS84Quad")
    info = tiler.info(COG_PATH, tms)
    assert info["minzoom"] == 4
    assert info["maxzoom"] == 8
    assert info["center"][-1] == 4


def test_GTiffOptions():
    """Test rio_tiler_crs.tiler.geotiff_options function with different projection."""
    info = tiler.geotiff_options(1, 1, 1)
    assert info["crs"] == CRS.from_epsg(3857)

    tms = morecantile.TileMatrixSet.load("WorldCRS84Quad")
    info = tiler.geotiff_options(1, 1, 1, tms=tms)
    assert info["crs"] == CRS.from_epsg(4326)
