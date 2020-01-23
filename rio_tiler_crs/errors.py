"""rio_tiler_crs.errors."""


class ProjecttileError(Exception):
    """Base exception."""


class InvalidZoomError(ProjecttileError):
    """Raised when a zoom level is invalid."""


class ParentTileError(ProjecttileError):
    """Raised when a parent tile cannot be determined."""


class TileArgParsingError(ProjecttileError):
    """Raised when errors occur in parsing a function's tile arg(s)."""
