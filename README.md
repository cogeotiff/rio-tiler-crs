# rio-tiler-crs

A rio-tiler plugin to create tiles in different projection


[![Packaging status](https://badge.fury.io/py/rio-tiler-crs.svg)](https://badge.fury.io/py/rio-tiler-crs)
[![CircleCI](https://circleci.com/gh/cogeotiff/rio-tiler-crs.svg?style=svg)](https://circleci.com/gh/cogeotiff/rio-tiler-crs)
[![codecov](https://codecov.io/gh/cogeotiff/rio-tiler-crs/branch/master/graph/badge.svg)](https://codecov.io/gh/cogeotiff/rio-tiler-crs)

![](https://user-images.githubusercontent.com/10407788/73080923-9d198a00-3e94-11ea-9644-ce39ffb3882a.jpg)


## Install

```bash
$ pip install pip -U
$ pip install rio-tiler-crs

# Or using source

$ pip install git+http://github.com/cogeotiff/rio-tiler-crs
```

## How To

rio-tiler-crs uses [morecantile](https://github.com/developmentseed/morecantile) to define the custom tiling grid schema.

1. Define grid system
```python
import morecantile
from rasterio.crs import CRS

# Use default TMS
tms = morecantile.tms.get("WorldCRS84Quad")

# or create a custom TMS
crs = CRS.from_epsg(3031)  # Morecantile TileMatrixSet uses Rasterio CRS object
extent = [-948.75, -543592.47, 5817.41, -3333128.95]  # From https:///epsg.io/3031
tms = morecantile.TileMatrixSet.custom(extent, crs)
```

2. read tile

```python
from rio_tiler_crs import COGReader

# Read tile x=10, y=10, z=4
with COGReader("myfile.tif", tms=tms) as cog:
    tile, mask = cog.tile( 10, 10, 4)
```

## API

<details>

```python
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

    """
```

</details>


- **COGReader.tile()**: Read map tile from a raster

```python
tms = morecantile.tms.get("WorldCRS84Quad")
with COGReader("myfile.tif", tms=tms) as cog:
    tile, mask = cog.tile(1, 2, 3, tilesize=256)

# With indexes
with COGReader("myfile.tif", tms=tms) as cog:
    tile, mask = cog.tile(1, 2, 3, tilesize=256, indexes=1)

# With expression
with COGReader("myfile.tif", tms=tms) as cog:
    tile, mask = cog.tile(1, 2, 3, tilesize=256, expression="B1/B2")
```

- **COGReader.part()**: Read part of a raster

Note: `tms` has no effect on `part` read.

```python
tms = morecantile.tms.get("WorldCRS84Quad")
with COGReader("myfile.tif", tms=tms) as cog:
    data, mask = cog.part((10, 10, 20, 20))

# Limit output size (default is set to 1024)
with COGReader("myfile.tif", tms=tms) as cog:
    data, mask = cog.part((10, 10, 20, 20), max_size=2000)

# Read high resolution
with COGReader("myfile.tif", tms=tms) as cog:
    data, mask = cog.part((10, 10, 20, 20), max_size=None)

# With indexes
with COGReader("myfile.tif", tms=tms) as cog:
     data, mask = cog.part((10, 10, 20, 20), indexes=1)

# With expression
with COGReader("myfile.tif", tms=tms) as cog:
    data, mask = cog.part((10, 10, 20, 20), expression="B1/B2")
```

- **COGReader.preview()**: Read a preview of a raster

Note: `tms` has no effect on `part` read.

```python
with COGReader("myfile.tif") as cog: 
    data, mask = cog.preview()

# With indexes
with COGReader("myfile.tif") as cog: 
    data, mask = cog.preview(indexes=1)

# With expression
with COGReader("myfile.tif") as cog: 
    data, mask = cog.preview(expression="B1+2,B1*4")
```

- **COGReader.point()**: Read point value of a raster

Note: `tms` has no effect on `part` read.

```python
with COGReader("myfile.tif") as cog: 
    print(cog.point(-100, 25))

# With indexes
with COGReader("myfile.tif") as cog: 
    print(cog.point(-100, 25, indexes=1)) 
[1]

# With expression
with COGReader("myfile.tif") as cog: 
    print(cog.point(-100, 25, expression="B1+2,B1*4"))
[3, 4]
```

- **COGReader.info**: Return simple metadata about the raster

```python
with COGReader("myfile.tif") as cog:
    print(cog.info)
{
    "bounds": [-119.05915661478785, 13.102845359730287, -84.91821332299578, 33.995073647795806],
    "center": [-101.98868496889182, 23.548959503763047, 3],
    "minzoom": 3,
    "maxzoom": 12,
    "band_metadata": [[1, {}]],
    "band_descriptions": [[1,"band1"]],
    "dtype": "int8",
    "colorinterp": ["palette"],
    "nodata_type": "Nodata",
    "colormap": {
        "0": [0, 0, 0, 0],
        "1": [0, 61, 0, 255],
        ...
    }
}
```

- **COGReader.stats()**: Return image statistics (Min/Max/Stdev)

```python
with COGReader("myfile.tif") as cog:
    print(cog.stats())
{
    "1": {
        "pc": [1, 16],
        "min": 1,
        "max": 18,
        "std": 4.069636227214257,
        "histogram": [
            [0, 10851, 2246, 10466, 20338, 13882, 6466, 55215, 12206, 14346, 8874, 4782, 4861, 4089, 4633, 20670, 3416, 1875, 875],
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
        ]
    }
}
```
Note: in the example above the histrogram is calculated for each value for the raster matching its colormap value (when it's not set to `0, 0, 0, 255`)

## Example

See [/demo](/demo)

## Contribution & Development

Issues and pull requests are more than welcome.

**dev install**

```bash
$ git clone https://github.com/cogeotiff/rio-tiler-crs.git
$ cd rio-tiler-crs
$ pip install -e .[dev]
```

**Python >=3.7 only**

This repo is set to use `pre-commit` to run *isort*, *flake8*, *pydocstring*, *black* ("uncompromising Python code formatter") and mypy when committing new code.

```
$ pre-commit install

$ git add .

$ git commit -m'my change'
isort....................................................................Passed
black....................................................................Passed
Flake8...................................................................Passed
Verifying PEP257 Compliance..............................................Passed
mypy.....................................................................Passed

$ git push origin
```