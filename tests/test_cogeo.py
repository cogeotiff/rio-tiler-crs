"""Tests for rio_tiler_crs."""

import os

import morecantile
import pytest
from rasterio.crs import CRS

from rio_tiler.errors import TileOutsideBounds
from rio_tiler_crs import COGReader
from rio_tiler_crs.cogeo import geotiff_options

COG_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "cog.tif")
COG_CMAP_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "cog_cmap.tif")
COG_SCALE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "cog_scale.tif")
COG_TAGS_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "cog_tags.tif")


def test_reader_tiles():
    """Test COGReader.tile."""
    lon = -58.181
    lat = 73.8794
    zoom = 7

    tms = morecantile.tms.get("WebMercatorQuad")
    x, y, z = tms.tile(lon, lat, zoom)

    with COGReader(COG_PATH, tms=tms) as cog:
        data, mask = cog.tile(x, y, z)
    assert data.shape == (1, 256, 256)
    assert mask.shape == (256, 256)

    with COGReader(COG_PATH, tms=tms) as cog:
        data, mask = cog.tile(x, y, z, indexes=(1, 1))
    assert data.shape == (2, 256, 256)
    assert mask.shape == (256, 256)

    with COGReader(COG_PATH, tms=tms) as cog:
        # indexes should be ignored, TODO: add warning
        data, mask = cog.tile(x, y, z, indexes=1, expression="B1+2,B1/3")
    assert data.shape == (2, 256, 256)
    assert mask.shape == (256, 256)

    crs = CRS.from_epsg(32621)
    extent = [166021.44, 0.00, 534994.66, 9329005.18]  # from http://epsg.io/32621
    tms = morecantile.TileMatrixSet.custom(extent, crs)
    x, y, z = tms.tile(lon, lat, zoom)

    with COGReader(COG_PATH, tms=tms) as cog:
        data, mask = cog.tile(x, y, z)
        assert data.shape == (1, 256, 256)
        assert mask.shape == (256, 256)
        x, y, z = tms.tile(lon + 10, lat, zoom)
        with pytest.raises(TileOutsideBounds):
            cog.tile(x, y, z)


def test_reader_part():
    """Test COGReader.part."""
    lon = -58.181
    lat = 73.8794
    zoom = 7
    tms = morecantile.tms.get("WebMercatorQuad")
    bounds = tms.bounds(tms.tile(lon, lat, zoom))

    with COGReader(COG_PATH) as cog:
        data, mask = cog.part(bounds, dst_crs=cog.dataset.crs)
    assert data.shape == (1, 896, 906)
    assert mask.shape == (896, 906)

    with COGReader(COG_PATH) as cog:
        data, mask = cog.part(bounds, indexes=(1, 1), dst_crs=cog.dataset.crs)
    assert data.shape == (2, 896, 906)
    assert mask.shape == (896, 906)

    with COGReader(COG_PATH) as cog:
        data, mask = cog.part(bounds, max_size=512, dst_crs=cog.dataset.crs)
    assert data.shape == (1, 507, 512)
    assert mask.shape == (507, 512)

    with COGReader(COG_PATH) as cog:
        data, mask = cog.part(bounds, expression="B1/2,B1+3", dst_crs=cog.dataset.crs)
    assert data.shape == (2, 896, 906)
    assert mask.shape == (896, 906)


def test_reader_preview():
    """Test COGReader.preview."""

    with COGReader(COG_PATH) as cog:
        data, mask = cog.preview()
    assert data.shape == (1, 1024, 1021)
    assert mask.shape == (1024, 1021)

    with COGReader(COG_PATH) as cog:
        data, mask = cog.preview(indexes=(1, 1))
    assert data.shape == (2, 1024, 1021)
    assert mask.shape == (1024, 1021)

    with COGReader(COG_PATH) as cog:
        data, mask = cog.preview(expression="B1/2,B1+3")
    assert data.shape == (2, 1024, 1021)
    assert mask.shape == (1024, 1021)


def test_reader_point():
    """Test COGReader.point."""
    lon = -58.181
    lat = 73.8794

    with COGReader(COG_PATH) as cog:
        data = cog.point(lon, lat)
    assert len(data) == 1

    with COGReader(COG_PATH) as cog:
        data = cog.point(lon, lat, indexes=(1, 1))
    assert len(data) == 2

    with COGReader(COG_PATH) as cog:
        data = cog.point(lon, lat, expression="B1/2,B1+3")
    assert len(data) == 2


def test_reader_stats():
    """Test COGReader.stats."""
    with COGReader(COG_PATH) as cog:
        data = cog.stats()
    assert data[1]["min"] == 1
    assert data[1]["max"] == 7872

    with COGReader(COG_CMAP_PATH) as cog:
        data = cog.stats()
    assert data[1]["histogram"][1] == [
        0,
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
    ]


def test_reader_metadata():
    """Test COGReader.info."""
    with COGReader(COG_PATH) as cog:
        info = cog.metadata()
    assert info["band_metadata"]
    assert info["band_descriptions"]
    assert info["statistics"][1]


def test_reader_get_zoom():
    """Test COGReader._get_zooms function with different projection."""
    with COGReader(COG_PATH) as cog:
        assert cog.minzoom == 5
        assert cog.maxzoom == 8

    tms = morecantile.tms.get("WorldCRS84Quad")
    with COGReader(COG_PATH, tms=tms) as cog:
        assert cog.minzoom == 4
        assert cog.maxzoom == 8


def test_reader_info():
    """Test COGReader.info."""
    with COGReader(COG_PATH) as cog:
        info = cog.info()
    assert info["minzoom"] == 5
    assert info["maxzoom"] == 8
    assert info["center"][-1] == 5
    assert info["bounds"]
    assert info["band_metadata"]
    assert info["band_descriptions"]
    assert info["dtype"]
    assert info["colorinterp"]
    assert info["nodata_type"]
    assert not info.get("colormap")
    assert not info.get("scale")
    assert not info.get("offset")

    with COGReader(COG_CMAP_PATH) as cog:
        info = cog.info()
    assert info["colormap"]

    with COGReader(COG_SCALE_PATH) as cog:
        info = cog.info()
    assert info["scale"]
    assert info["offset"]


def test_GTiffOptions():
    """Test rio_tiler_crs.reader.geotiff_options function with different projection."""
    info = geotiff_options(1, 1, 1)
    assert info["crs"] == CRS.from_epsg(3857)

    tms = morecantile.tms.get("WorldCRS84Quad")
    info = geotiff_options(1, 1, 1, tms=tms)
    assert info["crs"] == CRS.from_epsg(4326)


def test_COGReader_Options():
    """Set options in reader."""
    with COGReader(COG_PATH, nodata=1) as cog:
        meta = cog.metadata()
        assert meta["statistics"][1]["pc"] == [2720, 6896]

    with COGReader(COG_PATH, nodata=1) as cog:
        _, mask = cog.tile(43, 25, 7)
        assert not mask.all()

    with COGReader(COG_SCALE_PATH, unscale=True) as cog:
        p = cog.point(310000, 4100000, coord_crs=cog.dataset.crs)
        assert round(p[0], 3) == 1000.892

        # passing unscale in method should overwrite the defaults
        p = cog.point(310000, 4100000, coord_crs=cog.dataset.crs, unscale=False)
        assert p[0] == 8917

    cutline = "POLYGON ((13 1685, 1010 6, 2650 967, 1630 2655, 13 1685))"
    with COGReader(COG_PATH, vrt_options={"cutline": cutline}) as cog:
        _, mask = cog.preview()
        assert not mask.all()
