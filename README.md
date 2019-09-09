# rio-tiler-crs

[![Packaging status](https://badge.fury.io/py/rio-tiler-crs.svg)](https://badge.fury.io/py/rio-tiler-crs)
[![CircleCI](https://circleci.com/gh/cogeotiff/rio-tiler-crs.svg?style=svg)](https://codecov.io/gh/cogeotiff/rio-tiler-crs)
[![codecov](https://codecov.io/gh/cogeotiff/rio-tiler-crs/branch/master/graph/badge.svg)](https://circleci.com/gh/cogeotiff/rio-tiler-crs)


A rio-tiler plugin to create tiles in other CRS

## Install

### Requirements

```bash
$ pip install rio-tiler-crs
```
Or 
```bash
$ git clone http://github.com/cogeotiff/rio-tiler-crs
$ cd rio-tiler-crs
$ pip install -e .
```

### API

#### TODO

## Contribution & Development

Issues and pull requests are more than welcome.

**dev install**

```bash
$ git clone https://github.com/cogeotiff/rio-tiler-crs.git
$ cd rio-tiler-crs
$ pip install -e .[dev]
```

**Python3.6 only**

This repo is set to use `pre-commit` to run *flake8*, *pydocstring* and *black* ("uncompromising Python code formatter") when commiting new code.

```bash
$ pre-commit install
```