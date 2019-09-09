"""rio-tiler-crs tile server."""

from typing import BinaryIO

import uvicorn


from rio_tiler import main as cogTiler
from rio_tiler_crs import main as crsTiler
from rio_tiler.profiles import img_profiles
from rio_tiler.utils import array_to_image

from starlette.responses import Response
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from fastapi import FastAPI, Path, Query


app = FastAPI(
    title="rio-tiler-crs",
    description="A lightweight Cloud Optimized GeoTIFF tile server",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=0)


def TileResponse(content: BinaryIO, media_type: str) -> Response:
    """Binary tile response."""
    headers = {"Content-Type": f"image/{media_type}"}
    return Response(
        content=content,
        status_code=200,
        headers=headers,
        media_type=f"image/{media_type}",
    )


@app.get(
    "/tiles/epsg{epsg}/{z}/{x}/{y}\\.png",
    responses={
        200: {
            "content": {"image/png": {}, "image/jpg": {}, "image/webp": {}},
            "description": "Return an image.",
        }
    },
    description="Read COG and return a tile",
)
async def crs_tile(
    z: int,
    x: int,
    y: int,
    epsg: int = Path(4326, title="EPSG code"),
    filename: str = Query(...),
):
    """Handle /tiles requests."""
    tile, mask = crsTiler.tile(f"{filename}.tif", x, y, z, tilesize=256, epsg=epsg)

    options = img_profiles.get("png", {})
    img = array_to_image(tile, mask, img_format="png", **options)
    return TileResponse(img, media_type="png")


@app.get(
    "/tiles/{z}/{x}/{y}\\.png",
    responses={
        200: {
            "content": {"image/png": {}, "image/jpg": {}, "image/webp": {}},
            "description": "Return an image.",
        }
    },
    description="Read COG and return a tile",
)
async def wm_tile(z: int, x: int, y: int, filename: str = Query(...)):
    """Handle /tiles requests."""
    tile, mask = cogTiler.tile(f"{filename}.tif", x, y, z, tilesize=256)

    options = img_profiles.get("png", {})
    img = array_to_image(tile, mask, img_format="png", **options)
    return TileResponse(img, media_type="png")


if __name__ == "__main__":
    uvicorn.run(app=app, host="0.0.0.0", port=8501, log_level="info")
