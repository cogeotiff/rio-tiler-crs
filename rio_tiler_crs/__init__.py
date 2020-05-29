"""rio-tiler-crs: Create tiles in different projection."""

import pkg_resources

from .reader import COGReader  # noqa

version = pkg_resources.get_distribution(__package__).version
