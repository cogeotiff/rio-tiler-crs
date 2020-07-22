"""rio-tiler-crs: Create tiles in different projection."""

import pkg_resources

from .cogeo import COGReader  # noqa
from .stac import STACReader  # noqa

version = pkg_resources.get_distribution(__package__).version
