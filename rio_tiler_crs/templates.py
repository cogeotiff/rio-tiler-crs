"""rio_tiler_crs.templates."""

from typing import List

from rio_tiler_crs.projectile import TileSchema


def ogc_wmts(
    endpoint: str,
    layer: str,
    ts: TileSchema,
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
        ts : rio_tiler_crs.projectile.TileSchema
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
