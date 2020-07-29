"""Tests for stac_reader."""

import os
from unittest.mock import patch

import morecantile
import pytest
import rasterio

from rio_tiler.errors import InvalidBandName
from rio_tiler_crs import STACReader

prefix = os.path.join(os.path.dirname(__file__), "fixtures")
STAC_PATH = os.path.join(prefix, "item.json")
ALL_ASSETS = [
    "thumbnail",
    "overview",
    "info",
    "metadata",
    "visual",
    "B01",
    "B02",
    "B03",
    "B04",
    "B05",
    "B06",
    "B07",
    "B08",
    "B8A",
    "B09",
    "B11",
    "B12",
    "AOT",
    "WVP",
    "SCL",
]


def mock_rasterio_open(asset):
    """Mock rasterio Open."""
    assert asset.startswith("https://somewhereovertherainbow.io")
    asset = asset.replace("https://somewhereovertherainbow.io", prefix)
    return rasterio.open(asset)


def test_fetch_stac():
    with STACReader(STAC_PATH, include_asset_types=None) as stac:
        assert stac.minzoom == 0
        assert stac.maxzoom == 24
        assert stac.tms.identifier == "WebMercatorQuad"
        assert stac.filepath == STAC_PATH
        assert stac.assets == ALL_ASSETS

    with STACReader(STAC_PATH) as stac:
        assert stac.minzoom == 0
        assert stac.maxzoom == 24
        assert stac.tms.identifier == "WebMercatorQuad"
        assert stac.filepath == STAC_PATH
        assert "metadata" not in stac.assets
        assert "thumbnail" not in stac.assets
        assert "info" not in stac.assets

    with STACReader(STAC_PATH, include_assets={"B01", "B02"}) as stac:
        assert stac.assets == ["B01", "B02"]

    with STACReader(STAC_PATH, include_assets={"B01", "B02"}) as stac:
        assert stac.assets == ["B01", "B02"]

    with STACReader(
        STAC_PATH, exclude_assets={"overview", "visual", "AOT", "WVP", "SCL"}
    ) as stac:
        assert stac.assets == [
            "B01",
            "B02",
            "B03",
            "B04",
            "B05",
            "B06",
            "B07",
            "B08",
            "B8A",
            "B09",
            "B11",
            "B12",
        ]

    with STACReader(STAC_PATH, include_asset_types={"application/xml"}) as stac:
        assert stac.assets == ["metadata"]

    with STACReader(
        STAC_PATH,
        include_asset_types={"application/xml", "image/png"},
        include_assets={"metadata", "overview"},
    ) as stac:
        assert stac.assets == ["metadata"]


@patch("rio_tiler.io.cogeo.rasterio")
def test_reader_tiles(rio):
    """Test STACReader.tile."""
    rio.open = mock_rasterio_open

    tile = morecantile.Tile(z=9, x=289, y=207)

    with STACReader(STAC_PATH) as stac:
        with pytest.raises(InvalidBandName):
            stac.tile(*tile, assets="B1")

        with pytest.raises(InvalidBandName):
            stac.tile(*tile)

        data, mask = stac.tile(*tile, assets="B01")
        assert data.shape == (1, 256, 256)
        assert mask.shape == (256, 256)

    with STACReader(STAC_PATH) as stac:
        data, mask = stac.tile(*tile, expression="B01/B02")
        assert data.shape == (1, 256, 256)
        assert mask.shape == (256, 256)

    with STACReader(STAC_PATH) as stac:
        data, mask = stac.tile(*tile, assets=["B01", "B02"])
        assert data.shape == (2, 256, 256)
        assert mask.shape == (256, 256)

    # This is possible but user should not to it ;-)
    # We are reading B01 and B02 and telling rasterio to return twice bidx 1.
    with STACReader(STAC_PATH) as stac:
        data, mask = stac.tile(*tile, assets=["B01", "B02"], indexes=(1, 1))
        assert data.shape == (4, 256, 256)
        assert mask.shape == (256, 256)

    # Power User might use expression for each assets
    with STACReader(STAC_PATH) as stac:
        data, mask = stac.tile(*tile, assets=["B01", "B02"], asset_expression="b1/2")
        assert data.shape == (2, 256, 256)
        assert mask.shape == (256, 256)

    with STACReader(STAC_PATH, tms=morecantile.tms.get("WorldCRS84Quad")) as stac:
        data, mask = stac.tile(4, 1, 2, assets="B01")
        assert data.shape == (1, 256, 256)
        assert mask.shape == (256, 256)


@patch("rio_tiler.io.cogeo.rasterio")
def test_reader_part(rio):
    """Test STACReader.part."""
    rio.open = mock_rasterio_open

    bbox = (23.7, 31.506, 24.1, 32.514)

    with STACReader(STAC_PATH) as stac:
        with pytest.raises(InvalidBandName):
            stac.part(bbox, assets="B1")

        with pytest.raises(Exception):
            stac.part(bbox)

        data, mask = stac.part(bbox, assets="B01")
        assert data.shape == (1, 172, 69)
        assert mask.shape == (172, 69)

    with STACReader(STAC_PATH) as stac:
        data, mask = stac.part(bbox, expression="B04/B02")
        assert data.shape == (1, 1024, 407)
        assert mask.shape == (1024, 407)

    with STACReader(STAC_PATH) as stac:
        data, mask = stac.part(bbox, assets=["B04", "B02"])
        assert data.shape == (2, 1024, 407)
        assert mask.shape == (1024, 407)

    # This is possible but user should not to it ;-)
    # We are reading B01 and B02 and telling rasterio to return twice bidx 1.
    with STACReader(STAC_PATH) as stac:
        data, mask = stac.part(bbox, assets=["B04", "B02"], indexes=(1, 1))
        assert data.shape == (4, 1024, 407)
        assert mask.shape == (1024, 407)

    # Power User might use expression for each assets
    with STACReader(STAC_PATH) as stac:
        data, mask = stac.part(bbox, assets=["B04", "B02"], asset_expression="b1/2")
        assert data.shape == (2, 1024, 407)
        assert mask.shape == (1024, 407)

    with STACReader(STAC_PATH) as stac:
        data, mask = stac.part(bbox, assets="B04", max_size=None)
        assert data.shape == (1, 1030, 409)
        assert mask.shape == (1030, 409)


@patch("rio_tiler.io.cogeo.rasterio")
def test_reader_preview(rio):
    """Test STACReader.preview."""
    rio.open = mock_rasterio_open

    with STACReader(STAC_PATH) as stac:
        with pytest.raises(InvalidBandName):
            stac.preview(assets="B1")

        with pytest.raises(Exception):
            stac.preview()

        data, mask = stac.preview(assets="B01")
        assert data.shape == (1, 183, 183)
        assert mask.shape == (183, 183)

    with STACReader(STAC_PATH) as stac:
        data, mask = stac.preview(expression="B04/B02")
        assert data.shape == (1, 1024, 1024)
        assert mask.shape == (1024, 1024)

    with STACReader(STAC_PATH) as stac:
        data, mask = stac.preview(assets=["B04", "B02"])
        assert data.shape == (2, 1024, 1024)
        assert mask.shape == (1024, 1024)

    # This is possible but user should not to it ;-)
    # We are reading B01 and B02 and telling rasterio to return twice bidx 1.
    with STACReader(STAC_PATH) as stac:
        data, mask = stac.preview(assets=["B04", "B02"], indexes=(1, 1))
        assert data.shape == (4, 1024, 1024)
        assert mask.shape == (1024, 1024)

    # Power User might use expression for each assets
    with STACReader(STAC_PATH) as stac:
        data, mask = stac.preview(assets=["B04", "B02"], asset_expression="b1/2")
        assert data.shape == (2, 1024, 1024)
        assert mask.shape == (1024, 1024)

    with STACReader(STAC_PATH) as stac:
        data, mask = stac.preview(assets="B04", max_size=512)
        assert data.shape == (1, 512, 512)
        assert mask.shape == (512, 512)


@patch("rio_tiler.io.cogeo.rasterio")
def test_reader_point(rio):
    """Test STACReader.point."""
    rio.open = mock_rasterio_open

    lat = 32
    lon = 23.7

    with STACReader(STAC_PATH) as stac:
        with pytest.raises(InvalidBandName):
            stac.point(lon, lat, assets="B1")

        with pytest.raises(Exception):
            stac.point(lon, lat)

        data = stac.point(lon, lat, assets="B01")
        assert len(data) == 1

    with STACReader(STAC_PATH) as stac:
        data = stac.point(lon, lat, expression="B04/B02")
        assert len(data) == 1

    with STACReader(STAC_PATH) as stac:
        data = stac.point(lon, lat, assets=["B04", "B02"])
        assert len(data) == 2

    # This is possible but user should not to it ;-)
    # We are reading B01 and B02 and telling rasterio to return twice bidx 1.
    with STACReader(STAC_PATH) as stac:
        data = stac.point(lon, lat, assets=["B04", "B02"], indexes=(1, 1))
        assert len(data) == 2
        assert len(data[0]) == 2

    # Power User might use expression for each assets
    with STACReader(STAC_PATH) as stac:
        data = stac.point(lon, lat, assets=["B04", "B02"], asset_expression="b1/2")
        assert len(data) == 2


@patch("rio_tiler.io.cogeo.rasterio")
def test_reader_stats(rio):
    """Test STACReader.stats."""
    rio.open = mock_rasterio_open

    with STACReader(STAC_PATH) as stac:
        with pytest.raises(InvalidBandName):
            stac.stats(assets="B1")

        data = stac.stats(assets="B01")
        assert len(data.keys()) == 1
        assert data["B01"]

    with STACReader(STAC_PATH) as stac:
        data = stac.stats(assets=["B04", "B02"])
        assert len(data.keys()) == 2
        assert data["B02"]
        assert data["B04"]


@patch("rio_tiler.io.cogeo.rasterio")
def test_reader_info(rio):
    """Test STACReader.info."""
    rio.open = mock_rasterio_open

    with STACReader(STAC_PATH) as stac:
        with pytest.raises(InvalidBandName):
            stac.info(assets="B1")

        data = stac.info(assets="B01")
        assert len(data.keys()) == 1
        assert data["B01"]

    with STACReader(STAC_PATH) as stac:
        data = stac.info(assets=["B04", "B02"])
        assert len(data.keys()) == 2
        assert data["B02"]
        assert data["B04"]


@patch("rio_tiler.io.cogeo.rasterio")
def test_reader_metadata(rio):
    """Test STACReader.metadata."""
    rio.open = mock_rasterio_open

    with STACReader(STAC_PATH) as stac:
        with pytest.raises(InvalidBandName):
            stac.metadata(assets="B1")

        data = stac.metadata(assets="B01")
        assert len(data.keys()) == 1
        assert data["B01"]
        assert data["B01"]["statistics"]

    with STACReader(STAC_PATH) as stac:
        data = stac.metadata(assets=["B04", "B02"])
        assert len(data.keys()) == 2
        assert data["B02"]
        assert data["B04"]
