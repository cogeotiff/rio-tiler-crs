## 3.0.0-beta.7 (2020-10-07)

* remove `pkg_resources` (https://github.com/pypa/setuptools/issues/510)

Note: We changed the versioning scheme to `{major}.{minor}.{path}-{pre}{prenum}`

## 3.0b6 (2020-10-01)

* Adapt for rio-tiler==2.0b13

## 3.0b5 (2020-09-01)

* Forward reader_options in kwargs for COGReader.tile (#13)

## 3.0b4 (2020-08-21)

* Update to rio-tiler 2.0b7 and switch to attr (ref: https://github.com/cogeotiff/rio-tiler/pull/225)

## 3.0b3 (2020-07-30)

* Update rio-tiler and raise MissingAsset exception instead of InvalidBandName (#10)

## 3.0b2 (2020-07-28)

* STACReader.tile raises rio-tiler.error.InvalidBandName when no asset nor expression (#8)

## 3.0b1 (2020-07-22)

* Use rio-tiler 2.0b1 and its new COGReader and STACReader
