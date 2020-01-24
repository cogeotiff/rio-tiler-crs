"""rio-tiler-crs tile server."""

from typing import BinaryIO, List

import os
import uvicorn

import rasterio
from rasterio.crs import CRS
from rasterio.warp import transform_bounds

import morecantile

from rio_tiler_crs import tiler

from rio_tiler.profiles import img_profiles
from rio_tiler.utils import array_to_image

from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from fastapi import FastAPI, Path, Query


wm_bounds = [
    -20037508.342789244,
    -20037508.342789244,
    20037508.342789244,
    20037508.342789244,
]
# list of supported projection
epsg_grid_info = {
    # WGS 84 - WGS84 - World Geodetic System 1984
    4326: {"extent": [-180, -90, 180, 90], "matrix_scale": [2, 1]},
    # WGS 84 / NSIDC Sea Ice Polar Stereographic North
    3413: {
        "extent": [-2353926.81, 2345724.36, -382558.89, 383896.60],
        "matrix_scale": [1, 1],
    },
    # WGS 84 / Antarctic Polar Stereographic
    3031: {
        "extent": [-948.75, -543592.47, 5817.41, -3333128.95],
        "matrix_scale": [1, 1],
    },
    # ETRS89-extended / LAEA Europe
    3035: {
        "extent": [1896628.62, 1507846.05, 4662111.45, 6829874.45],
        "matrix_scale": [1, 1],
    },
    # WGS 84 / Pseudo-Mercator - Spherical Mercator, Google Maps, OpenStreetMap, Bing, ArcGIS, ESRI
    3857: {"extent": wm_bounds, "matrix_scale": [1, 1]},
    # WGS 84 / UTM zone 18N
    32618: {"extent": [166021.44, 0.00, 534994.66, 9329005.18], "matrix_scale": [1, 1]},
}


def ogc_wmts(
    endpoint: str,
    layer: str,
    ts: morecantile.TileSchema,
    bounds: List[float] = [-180.0, -90.0, 180.0, 90.0],
    query_string: str = "",
    minzoom: int = 0,
    maxzoom: int = 25,
    title: str = "Cloud Optimizied GeoTIFF",
) -> str:
    """
    Create WMTS XML template.

    Attributes
    ----------
        endpoint : str, required
            tiler endpoint.
        layer : str, required
            Tile matrix set identifier name.
        ts : morecantile.TileSchema
            Custom tile schema.
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

    tileMatrix = []
    for zoom in range(minzoom, maxzoom + 1):
        meta = ts.get_ogc_tilematrix(zoom)
        tm = f"""
                <TileMatrix>
                    <ows:Identifier>{zoom}</ows:Identifier>
                    <ScaleDenominator>{meta["scaleDenominator"]}</ScaleDenominator>
                    <TopLeftCorner>{meta["topLeftCorner"][0]} {meta["topLeftCorner"][1]}</TopLeftCorner>
                    <TileWidth>{meta["tileWidth"]}</TileWidth>
                    <TileHeight>{meta["tileHeight"]}</TileHeight>
                    <MatrixWidth>{meta["matrixWidth"]}</MatrixWidth>
                    <MatrixHeight>{meta["matrixHeight"]}</MatrixHeight>
                </TileMatrix>"""
        tileMatrix.append(tm)
    tileMatrix = "\n".join(tileMatrix)

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
                <ows:SupportedCRS>EPSG:{ts.crs.to_epsg()}</ows:SupportedCRS>
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


def TileResponse(content: BinaryIO, media_type: str) -> Response:
    """Binary tile response."""
    headers = {"Content-Type": f"image/{media_type}"}
    return Response(
        content=content,
        status_code=200,
        headers=headers,
        media_type=f"image/{media_type}",
    )


class XMLResponse(Response):
    """XML response."""

    media_type = "application/xml"


@app.get(
    "/tiles/epsg{epsg}/{z}/{x}/{y}\\.png",
    responses={200: {"content": {"image/png": {}}, "description": "Return an image."}},
    description="Read COG and return a tile",
)
async def _tile(
    z: int,
    x: int,
    y: int,
    epsg: int = Path(4326, title="EPSG code"),
    filename: str = Query(...),
):
    """Handle /tiles requests."""
    try:
        args = epsg_grid_info[epsg]
    except KeyError:
        raise Exception(f"EPSG:{epsg} is not supported")

    ts = morecantile.TileSchema(crs=CRS.from_epsg(epsg), **args)
    tile, mask = tiler.tile(f"{filename}.tif", x, y, z, tilesize=256, tileSchema=ts)

    options = img_profiles.get("png", {})
    img = array_to_image(tile, mask, img_format="png", **options)
    return TileResponse(img, media_type="png")


@app.get(
    "/epsg{epsg}/wmts",
    responses={
        200: {
            "content": {"application/xml": {}},
            "description": "Return an OGC WMTS document.",
        }
    },
)
async def _wmts(
    request: Request,
    response: Response,
    epsg: int = Path(4326, title="EPSG code"),
    filename: str = Query(...),
):
    """Handle /tiles requests."""
    host = request.headers["host"]
    scheme = request.url.scheme
    endpoint = f"{scheme}://{host}"

    try:
        args = epsg_grid_info[epsg]
    except KeyError:
        raise Exception(f"EPSG:{epsg} is not supported")

    ts = morecantile.TileSchema(crs=CRS.from_epsg(epsg), **args)
    with rasterio.open(f"{filename}.tif") as src_dst:
        bounds = transform_bounds(
            src_dst.crs, "epsg:4326", *src_dst.bounds, densify_pts=21
        )
        minzoom, maxzoom = tiler.get_zooms(src_dst, tileSchema=ts)

    return XMLResponse(
        ogc_wmts(
            endpoint,
            f"epsg{epsg}",
            ts,
            bounds=bounds,
            query_string=f"filename={filename}",
            minzoom=minzoom,
            maxzoom=maxzoom,
            title=os.path.basename(filename),
        )
    )


if __name__ == "__main__":
    uvicorn.run(app=app, host="0.0.0.0", port=8501, log_level="info")
