SELECT
    -- Needed to compute ID and satisfy Overture requirements:
    type,
    id,
    version,
    min_lon,
    max_lon,
    min_lat,
    max_lat,
    created_at AS update_time,

    -- Determine class from subclass or tags
    CASE
        WHEN subclass IN ('glacier', 'reef') THEN subclass
        WHEN subclass IN ('forest', 'wood') THEN 'forest'
        WHEN subclass IN ('fell','grass', 'grassland','meadow','tundra') THEN 'grass'
        WHEN subclass IN ('hill', 'peak', 'valley', 'volcano') THEN 'physical'
        WHEN subclass IN ('bare_rock','rock','scree','shingle') THEN 'rock'
        WHEN subclass IN ('sand', 'beach', 'dune') THEN 'sand'
        WHEN subclass IN ('heath','scrub','shrub','shrubbery') THEN 'shrub'
        WHEN subclass IN ('tree', 'tree_row') THEN 'tree'
        WHEN tags [ 'natural' ] IN ('wetland') THEN 'wetland'
    END AS subtype,
    subclass AS class,

    '__OVERTURE_NAMES_QUERY' AS names,

    -- Relevant OSM tags for land type
    MAP_FILTER(tags, (k,v) -> k IN (
            'landcover',
            'landuse',
            'natural',
            'surface'
        )
    ) AS source_tags,

    -- Add all OSM Tags for debugging
    tags AS osm_tags,

    -- Sources are an array of structs.
    ARRAY [ CAST(
        ROW(
            '',
            'OpenStreetMap',
            SUBSTR(type, 1, 1) || CAST(id AS varchar) || '@' || CAST(version AS varchar),
            NULL
        )
        AS ROW(
            property varchar,
            dataset varchar,
            record_id varchar,
            confidence double
        )
    ) ] AS sources,

    -- Wikidata is a top-level property in the OSM Container
    tags['wikidata'] as wikidata,

    -- Elevation as integer (meters above sea level)
    TRY_CAST(tags['ele'] AS integer) AS elevation,

    -- Apparently there are corrupt geometries that are breaking Athena, so write WKT for now:
    wkt_geometry

FROM (
    SELECT
        *,
        -- Determine subclass
        CASE
            -- Natural tags that become subclasses
            WHEN tags [ 'natural' ] IN (
                'bare_rock',
                'beach',
                'dune',
                'fell',
                'forest',
                'glacier',
                'grassland',
                'heath',
                'hill',
                'peak',
                'reef',
                'rock',
                'sand',
                'scree',
                'scrub',
                'shingle',
                'shrub',
                'shrubbery',
                'tree_row',
                'tree',
                'tundra',
                'valley',
                'volcano',
                'wetland',
                'wood'
            ) THEN tags [ 'natural' ]

            -- Surface tags that become subclasses
            WHEN tags [ 'surface' ] IN ('grass') THEN tags [ 'surface' ]
            WHEN tags [ 'landcover' ] = 'trees' THEN 'forest'
            WHEN tags [ 'landcover' ] IN ('grass', 'scrub', 'tree') THEN tags [ 'landcover' ] -- These landuse tags become subclasses

            WHEN tags['name'] IS NULL AND tags [ 'meadow' ] IS NULL
                AND tags [ 'landuse' ] IN ('forest', 'meadow', 'grass') THEN tags [ 'landuse' ]
            ELSE NULL
        END AS subclass
    FROM (
        SELECT
            id,
            type,
            version,
            tags,
            created_at,
            -- ST_GeometryFromText(wkt) AS geom,
            wkt AS wkt_geometry,
            min_lon,
            max_lon,
            min_lat,
            max_lat
            -- These two lines get injected.
            FROM
                {daylight_table}
            WHERE
                release = '{daylight_version}'
            -- These features belong in other themes / types
            AND tags [ 'highway' ] IS NULL
            AND tags [ 'building' ] IS NULL
            AND tags [ 'golf' ] IS NULL
            AND tags [ 'sport' ] IS NULL
            AND tags [ 'leisure' ] IS NULL
            AND (
                tags [ 'natural' ] IS NOT NULL
                OR tags [ 'surface' ] IS NOT NULL
                OR tags [ 'landcover' ] IS NOT NULL
                OR tags [ 'landuse' ] IN ('forest', 'meadow', 'grass')
            )
    )
)
WHERE
    subclass IS NOT NULL -- The only points/lines allowed are trees and peaks
    -- everything else should be a polygon:
    AND (
        wkt_geometry LIKE '%POLYGON%'
        -- ST_GEOMETRYTYPE(geom) IN ('ST_Polygon', 'ST_MultiPolygon')
        OR (
            wkt_geometry LIKE '%POINT%'
            -- ST_GEOMETRYTYPE(geom) IN ('ST_Point', 'ST_MultiPoint')
            AND subclass IN ('hill', 'peak', 'tree', 'shrub', 'valley', 'volcano')
        )
        OR (
            wkt_geometry LIKE '%LINESTRING%'
            -- ST_GEOMETRYTYPE(geom) IN ('ST_LineString', 'ST_MultiLineString')
            AND subclass = 'tree_row'
        )
    )

UNION ALL
-- Land derived from the OSM Coastline tool
SELECT
    -- Needed to compute ID and satisfy Overture requirements.
    'area' AS type,
    NULL AS id,
    0 version,
    ST_XMIN(ST_GeometryFromText(wkt)) as min_lon,
    ST_XMAX(ST_GeometryFromText(wkt)) as max_lon,
    ST_YMIN(ST_GeometryFromText(wkt)) AS min_lat,
    ST_YMAX(ST_GeometryFromText(wkt)) AS max_lat,
    -- Stub with today's date for now
    TO_ISO8601(cast(now() as timestamp) AT TIME ZONE 'UTC') AS update_time,
    class as subType,
    subclass as class,
    NULL AS names,
    MAP() AS sourceTags,
    MAP() AS osmTags,
    -- Source is OSM
    ARRAY [ CAST(
        ROW(
            '',
            'OpenStreetMap',
            NULL,
            NULL
        ) AS ROW(
            property varchar,
            dataset varchar,
            record_id varchar,
            confidence double
        )
    ) ] as sources,
    NULL AS wikidata,
    NULL AS elevation,
    wkt AS wkt_geometry
FROM {daylight_earth_table}
WHERE release = '{daylight_version}'
    AND theme = 'land'
    AND class = 'land'
    AND subclass = 'land'
