# rio-tiler-crs

A rio-tiler plugin to create tiles in different projection


[![Packaging status](https://badge.fury.io/py/rio-tiler-crs.svg)](https://badge.fury.io/py/rio-tiler-crs)
[![CircleCI](https://circleci.com/gh/cogeotiff/rio-tiler-crs.svg?style=svg)](https://circleci.com/gh/cogeotiff/rio-tiler-crss)
[![codecov](https://codecov.io/gh/cogeotiff/rio-tiler-crs/branch/master/graph/badge.svg)](https://codecov.io/gh/cogeotiff/rio-tiler-cr)

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

epsg = 3031
extent = [-948.75, -543592.47, 5817.41, -3333128.95]  # From https:///epsg.io/3031
ts = morecantile.TileSchema(CRS.from_epsg(epsg), extent)
```

2. read tile

```python
from rio_tiler_crs import tiler

# Read tile x=10, y=10, z=4
tile, mask = tiler.tile("myfile.tif", 10, 10, 4, tilesize=256, tileSchema=ts)
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

**Python3.7 only**

This repo is set to use `pre-commit` to run *flake8*, *pydocstring* and *black* ("uncompromising Python code formatter") when commiting new code.

```bash
$ pre-commit install
```