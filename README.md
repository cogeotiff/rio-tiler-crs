# rio-tiler-crs

A rio-tiler plugin to create tiles in different projection


[![Packaging status](https://badge.fury.io/py/rio-tiler-crs.svg)](https://badge.fury.io/py/rio-tiler-crs)
[![CircleCI](https://circleci.com/gh/cogeotiff/rio-tiler-crs.svg?style=svg)](https://circleci.com/gh/cogeotiff/rio-tiler-crss)
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
tms = morecantile.TileMatrixSet.load("WorldCRS84Quad")

# or create a custom TMS
crs = CRS.from_epsg(3031)  # Morecantile TileMatrixSet uses Rasterio CRS object
extent = [-948.75, -543592.47, 5817.41, -3333128.95]  # From https:///epsg.io/3031
tms = morecantile.TileMatrixSet(extent, crs)
```

2. read tile

```python
from rio_tiler_crs import tiler

# Read tile x=10, y=10, z=4
tile, mask = tiler.tile("myfile.tif", 10, 10, 4, tms=tms)
```

## API
- **rio_tiler_crs.tiler.get_zoom**: Get Min/Max zoom for a specific Raster in a specific TMS system

```python
tms = morecantile.TileMatrixSet.load("WorldCRS84Quad")
with rasterio.open("myfile.tif") as src_dst:
    minzoom, maxzoom = tiler.get_zoom(src_dst, tms)
```

- **rio_tiler_crs.tiler.spatial_info**: Return Raster spatial info for a specific TMS system

```python
tms = morecantile.TileMatrixSet.load("WorldCRS84Quad")
tiler.spatial_info("myfile.tif", tms)
{
    "address": "myfile.tif",
    "bounds": List[float],  # raster bounds in tms's CRS
    "center": Tuple[float, float, int],  # raster center in tms's CRS
    "minzoom": int,  # raster minzoom in tms
    "maxzoom": int,  # raster maxzoom in tms

}
```

- **rio_tiler_crs.tiler.bounds**: Return Raster bounds for a specific CRS

```python
dst_crs = CRS.from_epsg(3031)
tiler.bounds("myfile.tif", dst_crs)

{
    "address": "myfile.tif",
    "bounds": List[float],  # raster bounds in dst_crs
}
```

- **rio_tiler_crs.tiler.metadata**: same as rio_tiler.io.cogeo.metadata

- **rio_tiler_crs.tiler.info**: Return simple metadata about the raster

```python
tms = morecantile.TileMatrixSet.load("WorldCRS84Quad")
tiler.info("myfile.tif", tms)

{
    "address": "myfile.tif",
    "bounds": List[float],  # raster bounds in tms's CRS
    "center": Tuple[float, float, int],  # raster center in tms's CRS
    "minzoom": int,  # raster minzoom in tms
    "maxzoom": int,  # raster maxzoom in tms
    "band_metadata": List[Tulple[int, Dict]],  # List of band tags
    "band_descriptions": List[str],  # List of band names
    "dtype": str,  # raster datatype
    "colorinterp": List[str],  # List of band colorinterpretation values
    "nodata_type": str,  # raster io nodata type
    "scale": float,  # raster scaling factor
    "offset": float,  # raster offset factor
    "cmap":  Dict,  # raster internal colormap
}
```

- **rio_tiler_crs.tiler.tile**: Return map tile from a raster

```python
tms = morecantile.TileMatrixSet.load("WorldCRS84Quad")
tile, mask = tiler.tile("myfile.tif", 1, 2, 3, 256, tms)
```

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