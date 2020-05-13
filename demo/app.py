"""rio-tiler-crs tile server."""

import logging
import os
from enum import Enum
from typing import Any, Dict, List

import morecantile
import rasterio
import uvicorn
from fastapi import FastAPI, Path, Query
from rasterio.crs import CRS
from rasterio.warp import transform_bounds
from rio_tiler.profiles import img_profiles
from rio_tiler.utils import render
from starlette.background import BackgroundTask
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request
from starlette.responses import Response

from rio_tiler_crs import tiler

log = logging.getLogger()

# From developmentseed/titiler
drivers = dict(jpg="JPEG", png="PNG", tif="GTiff", webp="WEBP")
mimetype = dict(
    png="image/png",
    npy="application/x-binary",
    tif="image/tiff",
    jpg="image/jpg",
    webp="image/webp",
)
WGS84_CRS = CRS.from_epsg(4326)

# CUSTOM TMS for EPSG:3413
extent = (-2353926.81, 2345724.36, -382558.89, 383896.60)
crs = CRS.from_epsg(3413)
EPSG3413 = morecantile.TileMatrixSet.custom(extent, crs, identifier="EPSG3413")
morecantile.tms.register(EPSG3413)


class ImageType(str, Enum):
    """Image Type Enums."""

    png = "png"
    npy = "npy"
    tif = "tif"
    jpg = "jpg"
    webp = "webp"


class XMLResponse(Response):
    """XML Response"""

    media_type = "application/xml"


class TileResponse(Response):
    """Tiler's response."""

    def __init__(
        self,
        content: bytes,
        media_type: str,
        status_code: int = 200,
        headers: dict = {},
        background: BackgroundTask = None,
        ttl: int = 3600,
    ) -> None:
        """Init tiler response."""
        headers.update({"Content-Type": media_type})
        if ttl:
            headers.update({"Cache-Control": "max-age=3600"})
        self.body = self.render(content)
        self.status_code = 200
        self.media_type = media_type
        self.background = background
        self.init_headers(headers)


def ogc_wmts(
    endpoint: str,
    tms: morecantile.TileMatrixSet,
    bounds: List[float] = [-180.0, -90.0, 180.0, 90.0],
    minzoom: int = 0,
    maxzoom: int = 24,
    query_string: str = "",
    title: str = "Cloud Optimizied GeoTIFF",
) -> str:
    """
    Create WMTS XML template.

    Attributes
    ----------
    endpoint : str, required
        tiler endpoint.
    tms : morecantile.TileMatrixSet
        Custom Tile Matrix Set.
    bounds : tuple, optional
        WGS84 layer bounds (default: [-180.0, -90.0, 180.0, 90.0]).
    query_string : str, optional
        Endpoint querystring.
    minzoom : int, optional (default: 0)
        min zoom.
    maxzoom : int, optional (default: 25)
        max zoom.
    title: str, optional (default: "Cloud Optimizied GeoTIFF")
        Layer title.

    Returns
    -------
    xml : str
        OGC Web Map Tile Service (WMTS) XML template.

    """
    content_type = f"image/png"
    layer = tms.identifier

    tileMatrixArray = []
    for zoom in range(minzoom, maxzoom + 1):
        matrix = tms.matrix(zoom)
        tm = f"""
                <TileMatrix>
                    <ows:Identifier>{matrix.identifier}</ows:Identifier>
                    <ScaleDenominator>{matrix.scaleDenominator}</ScaleDenominator>
                    <TopLeftCorner>{matrix.topLeftCorner[0]} {matrix.topLeftCorner[1]}</TopLeftCorner>
                    <TileWidth>{matrix.tileWidth}</TileWidth>
                    <TileHeight>{matrix.tileHeight}</TileHeight>
                    <MatrixWidth>{matrix.matrixWidth}</MatrixWidth>
                    <MatrixHeight>{matrix.matrixHeight}</MatrixHeight>
                </TileMatrix>"""
        tileMatrixArray.append(tm)
    tileMatrix = "\n".join(tileMatrixArray)

    xml = f"""<Capabilities
        xmlns="http://www.opengis.net/wmts/1.0"
        xmlns:ows="http://www.opengis.net/ows/1.1"
        xmlns:xlink="http://www.w3.org/1999/xlink"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:gml="http://www.opengis.net/gml"
        xsi:schemaLocation="http://www.opengis.net/wmts/1.0 http://schemas.opengis.net/wmts/1.0/wmtsGetCapabilities_response.xsd"
        version="1.0.0">
        <ows:ServiceIdentification>
            <ows:Title>{title}</ows:Title>
            <ows:ServiceType>OGC WMTS</ows:ServiceType>
            <ows:ServiceTypeVersion>1.0.0</ows:ServiceTypeVersion>
        </ows:ServiceIdentification>
        <ows:OperationsMetadata>
            <ows:Operation name="GetCapabilities">
                <ows:DCP>
                    <ows:HTTP>
                        <ows:Get xlink:href="{endpoint}/{layer}/wmts?{query_string}">
                            <ows:Constraint name="GetEncoding">
                                <ows:AllowedValues>
                                    <ows:Value>RESTful</ows:Value>
                                </ows:AllowedValues>
                            </ows:Constraint>
                        </ows:Get>
                    </ows:HTTP>
                </ows:DCP>
            </ows:Operation>
            <ows:Operation name="GetTile">
                <ows:DCP>
                    <ows:HTTP>
                        <ows:Get xlink:href="{endpoint}/{layer}/wmts?{query_string}">
                            <ows:Constraint name="GetEncoding">
                                <ows:AllowedValues>
                                    <ows:Value>RESTful</ows:Value>
                                </ows:AllowedValues>
                            </ows:Constraint>
                        </ows:Get>
                    </ows:HTTP>
                </ows:DCP>
            </ows:Operation>
        </ows:OperationsMetadata>
        <Contents>
            <Layer>
                <ows:Identifier>{layer}</ows:Identifier>
                <ows:WGS84BoundingBox crs="urn:ogc:def:crs:OGC:2:84">
                    <ows:LowerCorner>{bounds[0]} {bounds[1]}</ows:LowerCorner>
                    <ows:UpperCorner>{bounds[2]} {bounds[3]}</ows:UpperCorner>
                </ows:WGS84BoundingBox>
                <Style isDefault="true">
                    <ows:Identifier>default</ows:Identifier>
                </Style>
                <Format>{content_type}</Format>
                <TileMatrixSetLink>
                    <TileMatrixSet>{layer}</TileMatrixSet>
                </TileMatrixSetLink>
                <ResourceURL
                    format="{content_type}"
                    resourceType="tile"
                    template="{endpoint}/tiles/{layer}/{{TileMatrix}}/{{TileCol}}/{{TileRow}}.png?{query_string}"/>
            </Layer>
            <TileMatrixSet>
                <ows:Identifier>{layer}</ows:Identifier>
                <ows:SupportedCRS>EPSG:{tms.crs.to_epsg()}</ows:SupportedCRS>
                {tileMatrix}
            </TileMatrixSet>
        </Contents>
        <ServiceMetadataURL xlink:href='{endpoint}/{layer}/wmts?{query_string}'/>
    </Capabilities>"""

    return xml


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

responses = {
    200: {
        "content": {
            "image/png": {},
            "image/jpg": {},
            "image/webp": {},
            "image/tiff": {},
            "application/x-binary": {},
        },
        "description": "Return an image.",
    }
}
tile_routes_params: Dict[str, Any] = dict(
    responses=responses, tags=["tiles"], response_class=TileResponse
)


@app.get("/tiles/{z}/{x}/{y}\\.png", **tile_routes_params)
@app.get("/tiles/{identifier}/{z}/{x}/{y}\\.png", **tile_routes_params)
def _tile(
    z: int,
    x: int,
    y: int,
    identifier: str = Query("WebMercatorQuad", title="TMS identifier"),
    filename: str = Query(...),
):
    """Handle /tiles requests."""
    tms = morecantile.tms.get(identifier)

    tile, mask = tiler.tile(f"{filename}.tif", x, y, z, tilesize=256, tms=tms)

    ext = ImageType.png
    driver = drivers[ext.value]
    options = img_profiles.get(driver.lower(), {})

    img = render(tile, mask, img_format="png", **options)

    return TileResponse(img, media_type=mimetype[ext.value])


@app.get(
    r"/WMTSCapabilities.xml",
    responses={200: {"content": {"application/xml": {}}}},
    response_class=XMLResponse,
)
@app.get(
    r"/{identifier}/WMTSCapabilities.xml",
    responses={200: {"content": {"application/xml": {}}}},
    response_class=XMLResponse,
)
def _wmts(
    request: Request,
    response: Response,
    identifier: str = Path("WebMercatorQuad", title="TMS identifier"),
    filename: str = Query(...),
):
    """Handle /tiles requests."""
    tms = morecantile.tms.get(identifier)

    host = request.headers["host"]
    scheme = request.url.scheme
    endpoint = f"{scheme}://{host}"

    with rasterio.open(f"{filename}.tif") as src_dst:
        bounds = transform_bounds(
            src_dst.crs, WGS84_CRS, *src_dst.bounds, densify_pts=21
        )
        minzoom, maxzoom = tiler.get_zooms(src_dst, tms)

    return XMLResponse(
        ogc_wmts(
            endpoint,
            tms,
            bounds=bounds,
            query_string=f"filename={filename}",
            minzoom=minzoom,
            maxzoom=maxzoom,
            title=os.path.basename(filename),
        )
    )


if __name__ == "__main__":
    uvicorn.run(app=app, host="0.0.0.0", port=8501, log_level="info")
