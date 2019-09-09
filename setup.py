"""Setup for rio-tiler-crs."""

from setuptools import setup, find_packages

with open("README.md") as f:
    long_description = f.read()

inst_reqs = ["rasterio~=1.0.26", "rio-tiler~=1.2.10", "pyproj~=2.3.0"]

extra_reqs = {
    "test": ["pytest", "pytest-cov"],
    "dev": ["pytest", "pytest-cov", "pre-commit"],
}


setup(
    name="rio-tiler-crs",
    version="0.0.1dev",
    description=u"""A rio-tiler plugin to create tile of arbitraty grid""",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 2.7",
        "Topic :: Scientific/Engineering :: GIS",
    ],
    keywords="COG GIS",
    author=u"Vincent Sarago",
    author_email="vincent@developmentseed.org",
    url="https://github.com/cogeotiff/rio-tiler-crs",
    license="MIT",
    packages=find_packages(exclude=["ez_setup", "examples", "tests"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=inst_reqs,
    extras_require=extra_reqs,
)
